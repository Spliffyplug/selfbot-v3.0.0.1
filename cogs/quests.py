from __future__ import annotations
import asyncio
import json
import logging
import os
import random
import time
import traceback
from datetime import datetime, timezone
import aiohttp
import discord
from discord.ext import commands
from . import state as S
logger = logging.getLogger('wilt.quests')
API = 'https://discord.com/api/v9'

def _parse_lock_until(val):
    if val is None or val is False or val == '' or (val == 0):
        return None
    try:
        if isinstance(val, (int, float)):
            ts = float(val)
            if ts > 1000000000000.0:
                ts /= 1000.0
            if ts < time.time():
                return None
            return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        s = str(val).strip()
        if not s or s.lower() in ('null', 'none', '0'):
            return None
        ds = s.replace('Z', '+00:00') if s.endswith('Z') else s
        try:
            dt = datetime.fromisoformat(ds)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt.timestamp() < time.time():
                return None
            return s
        except Exception:
            return s
    except Exception:
        return None

def _token() -> str | None:
    t = getattr(S, 'TOKEN', None) or getattr(getattr(S, 'BOT', None), 'http', None)
    if hasattr(t, 'token'):
        t = t.token
    bot = getattr(S, 'BOT', None)
    if not t and bot is not None:
        t = getattr(getattr(bot, 'http', None), 'token', None)
    if not t:
        return None
    t = str(t).strip().strip('"').strip("'")
    if t.lower().startswith('bot '):
        t = t[4:].strip()
    return t or None

def _ua() -> str:
    return getattr(S, 'USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')

class Quest:

    def __init__(self, quest_id, title, description, task_type, status=None):
        self.id = quest_id
        self.title = title
        self.description = description
        self.task_type = task_type or 'Unknown'
        self.status = status
        self.enrolled_at = None
        self.completed_at = None
        self.progress = 0.0
        self.target = 0.0
        self.expires_at = None
        self.starts_at = None
        self.is_expired = False
        self.last_updated = time.time()
        self.application_id = None
        self.raw_tasks = {}

    def is_supported(self) -> bool:
        if self.is_expired:
            return False
        t = (self.task_type or '').lower()
        if 'watch' in t:
            return True
        if 'play' in t and 'desktop' in t:
            return True
        if 'play_on_desktop' in t or 'playondesktop' in t:
            return True
        if 'stream' in t:
            return True
        if t in ('watchvideo', 'watchvideomobile', 'playondesktop', 'playondesktopv2'):
            return True
        return False

    def check_expiration(self) -> bool:
        if not self.expires_at:
            return False
        try:
            exp = datetime.fromisoformat(self.expires_at.replace('Z', '+00:00'))
            now = datetime.now(exp.tzinfo)
            self.is_expired = now > exp
            return self.is_expired
        except Exception:
            return False

class Quests(commands.Cog, name='quests'):

    def __init__(self, bot):
        self.quests = []
        self.auto_complete = False
        self.bot = bot
        self.quests: dict[str, Quest] = {}
        self.auto_complete = False
        self.last_fetch_time = 0.0
        self.quest_completion_task = None
        self.cache: dict[str, float] = {}
        self.refresh_interval = 30 * 60
        self.excluded_quests: set = set()
        self._session: aiohttp.ClientSession | None = None
        self._preferred_task: str | None = None
        self._suspend_until = None
        self._block_until = None

    async def cog_unload(self):
        self.auto_complete = False
        if self.quest_completion_task and (not self.quest_completion_task.done()):
            self.quest_completion_task.cancel()
            try:
                await self.quest_completion_task
            except asyncio.CancelledError:
                pass
        if self._session and (not self._session.closed):
            await self._session.close()

    def _headers(self) -> dict:
        tok = _token()
        h = {'Authorization': tok or '', 'User-Agent': _ua(), 'Accept': '*/*', 'Accept-Language': 'en-US,en;q=0.9', 'Content-Type': 'application/json', 'Origin': 'https://discord.com', 'Referer': 'https://discord.com/channels/@me'}
        xsp = (os.environ.get("X_SUPER_PROPERTIES") or os.environ.get("DISCORD_X_SUPER_PROPERTIES") or getattr(S, 'X_SUPER_PROPERTIES', '') or '').strip()
        if xsp:
            h['X-Super-Properties'] = xsp
        return h

    async def _session_get(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _request(self, method: str, url: str, **kwargs):
        sess = await self._session_get()
        headers = self._headers()
        if not headers.get("Authorization"):
            return (401, {'message': 'no token'})
        try:
            async with sess.request(method, url, headers=headers, timeout=aiohttp.ClientTimeout(total=25), **kwargs) as r:
                text = await r.text()
                try:
                    data = json.loads(text) if text else None
                except Exception:
                    data = text
                return (r.status, data)
        except Exception as e:
            logger.error(f'[quest] request {method} {url}: {e}')
            return (0, {'error': str(e)})

    def determine_quest_task_type(self, config: dict) -> str:
        task_type = 'Unknown'
        for key in ('task_config_v2', 'task_config'):
            tasks = (config.get(key) or {}).get("tasks") or {}
            if not isinstance(tasks, dict):
                continue
            keys = {str(k).upper() for k in tasks.keys()}
            if 'WATCH_VIDEO' in keys or 'WATCH_VIDEO_ON_MOBILE' in keys or 'WATCH_VIDEO_ON_TV' in keys:
                if 'WATCH_VIDEO' in keys:
                    return 'WatchVideo'
                if 'WATCH_VIDEO_ON_MOBILE' in keys:
                    return 'WatchVideoMobile'
                return 'WatchVideo'
            if 'PLAY_ON_DESKTOP' in keys:
                return 'PlayOnDesktop'
            if 'PLAY_ON_DESKTOP_V2' in keys or 'PLAY_ON_DESKTOPV2' in keys:
                return 'PlayOnDesktopV2'
            if 'STREAM_ON_DESKTOP' in keys or 'STREAM' in keys:
                return 'StreamOnDesktop'
            for k in keys:
                if k.startswith('PLAY'):
                    return k.title().replace('_', '')
                if k.startswith('WATCH'):
                    return k.title().replace('_', '')
        features = config.get("features") or []
        if 3 in features:
            return 'WatchVideo'
        if 4 in features:
            return 'PlayOnDesktop'
        return task_type

    def _matches_preferred(self, quest: Quest) -> bool:
        if not self._preferred_task:
            return True
        pref = self._preferred_task.lower()
        t = (quest.task_type or '').lower()
        if pref in ('watch', 'video'):
            return 'watch' in t
        if pref in ('desktop', 'play', 'playondesktop'):
            return 'play' in t and 'desktop' in t
        if pref in ('stream',):
            return 'stream' in t
        return pref in t

    async def get_quests(self) -> bool:
        logger.info('[quest] fetching quests...')
        status, data = await self._request('GET', f'{API}/quests/@me')
        if status != 200:
            logger.error(f'[quest] fetch HTTP {status}: {str(data)[:200]}')
            return False
        if not isinstance(data, dict):
            logger.error(f'[quest] bad payload {type(data)}')
            return False
        self._suspend_until = _parse_lock_until(data.get("quest_access_suspended_until") or data.get("questAccessSuspendedUntil"))
        self._block_until = _parse_lock_until(data.get("quest_enrollment_blocked_until") or data.get("questEnrollmentBlockedUntil"))
        if self._suspend_until:
            logger.warning(f'[quest] access suspended until {self._suspend_until}')
        if self._block_until:
            logger.warning(f'[quest] enroll blocked until {self._block_until}')
        quest_list = data.get("quests") or data.get("Quest") or []
        if not isinstance(quest_list, list):
            quest_list = []
        for ex in data.get("excluded_quests") or data.get("excludedQuests") or []:
            if isinstance(ex, dict) and ex.get("id"):
                self.excluded_quests.add(str(ex['id']))
            elif isinstance(ex, (str, int)):
                self.excluded_quests.add(str(ex))
        if not quest_list and (not self._suspend_until):
            logger.info('[quest] 0 quests returned (not suspended) - accept on Quest Home')
        seen = set()
        for quest_data in quest_list:
            if not isinstance(quest_data, dict):
                continue
            quest_id = str(quest_data.get("id") or '')
            if not quest_id:
                continue
            seen.add(quest_id)
            config = quest_data.get("config") or {}
            starts_at = config.get("starts_at")
            expires_at = config.get("expires_at")
            title = 'Unknown Quest'
            app = config.get("application")
            if isinstance(app, dict) and app.get("name"):
                title = app['name']
            elif (config.get("messages") or {}).get("game_title"):
                title = config['messages']['game_title']
            description = (config.get("messages") or {}).get("quest_name", "")
            task_type = self.determine_quest_task_type(config)
            if quest_id in self.quests:
                q = self.quests[quest_id]
                q.task_type = task_type
                q.title = title
                q.description = description
                q.starts_at = starts_at
                q.expires_at = expires_at
                q.last_updated = time.time()
            else:
                q = Quest(quest_id, title, description, task_type)
                q.starts_at = starts_at
                q.expires_at = expires_at
                self.quests[quest_id] = q
            if isinstance(app, dict) and app.get("id"):
                q.application_id = str(app['id'])
            if expires_at:
                q.check_expiration()
            user_status = quest_data.get("user_status") or {}
            if user_status.get("completed_at"):
                q.status = 'completed'
                q.completed_at = user_status.get("completed_at")
                self.cache.pop(quest_id, None)
            elif user_status.get("enrolled_at"):
                q.status = 'enrolled'
                q.enrolled_at = user_status.get("enrolled_at")
            elif q.status not in ('completed', 'enrolled'):
                q.status = None
            progress_data = user_status.get("progress") or {}
            if isinstance(progress_data, dict):
                for key, val in progress_data.items():
                    if isinstance(val, dict) and 'value' in val:
                        try:
                            q.progress = float(val['value'])
                            self.cache[quest_id] = q.progress
                        except Exception:
                            pass
                        break
        for oid in list(self.quests.keys()):
            if oid not in seen and self.quests[oid].status != 'enrolled':
                pass
        self.last_fetch_time = time.time()
        logger.info(f'[quest] processed {len(seen)} quests (cache {len(self.quests)})')
        return True

    async def enroll_quest(self, quest_id: str) -> bool:
        paths = [f'/quests/{quest_id}/accept', f'/quests/{quest_id}/enroll', f'/quests/{quest_id}/join']
        for path in paths:
            st, data = await self._request('POST', API + path, json={})
            if st in (200, 201, 204):
                logger.info(f'[quest] enrolled {quest_id} via {path}')
                if quest_id in self.quests:
                    self.quests[quest_id].status = 'enrolled'
                    self.quests[quest_id].enrolled_at = datetime.now(timezone.utc).isoformat()
                return True
            logger.debug(f'[quest] enroll {path} -> {st} {str(data)[:120]}')
        return False

    async def enroll_all_available(self) -> int:
        n = 0
        for qid, q in list(self.quests.items()):
            if q.is_expired or not q.is_supported():
                continue
            if q.status in ('enrolled', 'completed'):
                continue
            if qid in self.excluded_quests:
                continue
            if not self._matches_preferred(q):
                continue
            if await self.enroll_quest(qid):
                n += 1
            await asyncio.sleep(0.4)
        return n

    def random_decimal(self) -> float:
        return round(random.random() * 1000000) / 1000000

    async def update_quest_progress(self, quest_id: str) -> bool:
        q = self.quests.get(quest_id)
        if not q or not q.is_supported() or q.status != 'enrolled' or (q.status == 'completed'):
            return False
        t = (q.task_type or '').lower()
        data = {}
        url = ''
        if 'watch' in t:
            default_progress = self.cache.get(quest_id, -29.0)
            if q.progress and abs(q.progress) > 0.01 and (quest_id not in self.cache):
                default_progress = float(q.progress)
            new_progress = float(default_progress) + 30.0 + self.random_decimal()
            self.cache[quest_id] = new_progress
            data = {'timestamp': new_progress}
            url = f'{API}/quests/{quest_id}/video-progress'
        elif 'play' in t and 'desktop' in t:
            data = {'stream_key': f'call:{quest_id}:1', 'terminal': False}
            url = f'{API}/quests/{quest_id}/heartbeat'
        elif 'stream' in t:
            data = {'stream_key': f'call:{quest_id}:1', 'terminal': False}
            url = f'{API}/quests/{quest_id}/heartbeat'
        else:
            return False
        st, response_data = await self._request('POST', url, json=data)
        if st != 200:
            logger.error(f'[quest] progress {quest_id} HTTP {st}: {str(response_data)[:160]}')
            if st in (401, 403, 404):
                self.excluded_quests.add(quest_id)
            return False
        if isinstance(response_data, dict):
            if response_data.get("completed_at"):
                q.status = 'completed'
                q.completed_at = response_data['completed_at']
                self.cache.pop(quest_id, None)
                logger.info(f'[quest] completed {q.title}')
            progress_data = response_data.get("progress") or {}
            if isinstance(progress_data, dict):
                for key, val in progress_data.items():
                    if isinstance(val, dict) and 'value' in val:
                        try:
                            q.progress = float(val['value'])
                            self.cache[quest_id] = q.progress
                        except Exception:
                            pass
                        break
        return True

    async def quest_completer(self):
        while self.auto_complete:
            try:
                if time.time() - self.last_fetch_time > self.refresh_interval:
                    await self.get_quests()
                enrolled = []
                need_manual = []
                for qid, q in self.quests.items():
                    if q.status == 'completed' or q.is_expired or (not q.is_supported()):
                        continue
                    if qid in self.excluded_quests:
                        continue
                    if not self._matches_preferred(q):
                        continue
                    if q.status == 'enrolled':
                        enrolled.append(qid)
                    else:
                        need_manual.append(qid)
                if need_manual:
                    for qid in need_manual[:5]:
                        ok = await self.enroll_quest(qid)
                        if ok:
                            enrolled.append(qid)
                        await asyncio.sleep(0.5)
                if not enrolled:
                    await self.get_quests()
                    enrolled = [qid for qid, q in self.quests.items() if q.status == 'enrolled' and q.is_supported() and (not q.is_expired) and (qid not in self.excluded_quests) and self._matches_preferred(q)]
                if not enrolled:
                    logger.info('[quest] no enrolled supported quests - accept on Quest Home then .queststart')
                    self.auto_complete = False
                    self.quest_completion_task = None
                    break
                logger.info(f'[quest] progress cycle | {len(enrolled)} enrolled')
                for qid in enrolled:
                    q = self.quests[qid]
                    if q.status == 'completed':
                        continue
                    await self.update_quest_progress(qid)
                    await asyncio.sleep(1.0)
                await asyncio.sleep(random.randint(45, 60))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f'[quest] completer: {e}\n{traceback.format_exc()}')
                await asyncio.sleep(20)

    def _start_completer(self) -> bool:
        if self.quest_completion_task and (not self.quest_completion_task.done()):
            return True
        self.auto_complete = True
        self.quest_completion_task = asyncio.create_task(self.quest_completer())
        return True

    def _stop_completer(self) -> bool:
        self.auto_complete = False
        if self.quest_completion_task and (not self.quest_completion_task.done()):
            self.quest_completion_task.cancel()
            self.quest_completion_task = None
            return True
        self.quest_completion_task = None
        return False

    @commands.command(name='questlist', aliases=['qlist', 'ql', 'qstat', 'qstatus', 'qst'], brief='List quests')
    async def questlist(self, ctx):
        try:
            await ctx.message.delete()
        except Exception:
            pass
        msg = await S.safe_send(ctx.channel, S.ui_info('fetching quests...'))
        ok = await self.get_quests()
        if not ok:
            return await S.safe_edit(msg, S.ui_err('fetch failed - check token'))
        enrolled = completed = available = expired = 0
        lines = []
        for q in self.quests.values():
            if q.is_expired:
                expired += 1
                continue
            if q.status == 'completed':
                completed += 1
            elif q.status == 'enrolled':
                enrolled += 1
                lines.append(f'* {q.title} [{q.task_type}] ~{q.progress}')
            else:
                available += 1
                lines.append(f'o {q.title} [{q.task_type}]')
        head = [f"auto={('on' if self.auto_complete else 'off')} | total={len(self.quests)}", f'enrolled={enrolled} available={available} done={completed} expired={expired}']
        if self._suspend_until:
            head.append(f'SUSPENDED until {self._suspend_until}')
        if self._block_until:
            head.append(f'enroll blocked until {self._block_until}')
        if not self._suspend_until and (not self.quests):
            head.append('no suspension | empty list - accept quests on Quest Home')
        body = '\n'.join(head + ([''] + lines[:20] if lines else []))
        await S.safe_edit(msg, S.ui_ok(body))

    @commands.command(name='queststart', aliases=['qstart', 'qs'], brief='Start quest auto-completer')
    async def queststart(self, ctx):
        try:
            await ctx.message.delete()
        except Exception:
            pass
        if self.auto_complete:
            return await S.safe_send(ctx.channel, S.ui_warn('already running'))
        msg = await S.safe_send(ctx.channel, S.ui_info('fetching + enroll...'))
        await self.get_quests()
        if self._suspend_until:
            return await S.safe_edit(msg, S.ui_err(f'Discord suspended quests until {self._suspend_until}'))
        new_enrolled = await self.enroll_all_available()
        await self.get_quests()
        enrolled = [q for q in self.quests.values() if q.status == 'enrolled' and (not q.is_expired) and q.is_supported() and (str(q.id) not in self.excluded_quests) and self._matches_preferred(q)]
        if not enrolled:
            types = sorted({q.task_type for q in self.quests.values()})
            return await S.safe_edit(msg, S.ui_warn(f"no enrolled supported quests | fetched={len(self.quests)} types={', '.join(types) or 'none'} | tried_enroll={new_enrolled}\naccept a quest on Quest Home, then .queststart again"))
        self._start_completer()
        supported = [q for q in enrolled if q.is_supported()]
        await S.safe_edit(msg, S.ui_ok(f'auto-completer on | {len(enrolled)} enrolled ({len(supported)} supported, {new_enrolled} newly enrolled)'))

    @commands.command(name='queststop', aliases=['qstop', 'qx'], brief='Stop quest auto-completer')
    async def queststop(self, ctx):
        try:
            await ctx.message.delete()
        except Exception:
            pass
        if not self.auto_complete:
            return await S.safe_send(ctx.channel, S.ui_warn('not running'))
        self._stop_completer()
        await S.safe_send(ctx.channel, S.ui_ok('stopped'))

    @commands.command(name='questrefresh', aliases=['qrefresh', 'qr'], brief='Refresh quest list')
    async def questrefresh(self, ctx):
        try:
            await ctx.message.delete()
        except Exception:
            pass
        ok = await self.get_quests()
        await S.safe_send(ctx.channel, S.ui_ok(f'refreshed | {len(self.quests)} quests') if ok else S.ui_err('refresh failed'))

    @commands.command(name='questdebug', aliases=['qdebug', 'qd'], brief='Raw quest API status')
    async def questdebug(self, ctx):
        try:
            await ctx.message.delete()
        except Exception:
            pass
        st, data = await self._request('GET', f'{API}/quests/@me')
        if st != 200 or not isinstance(data, dict):
            return await S.safe_send(ctx.channel, S.ui_err(f'HTTP {st}'))
        qlist = data.get("quests") or []
        sus = _parse_lock_until(data.get("quest_access_suspended_until") or data.get("questAccessSuspendedUntil"))
        blk = _parse_lock_until(data.get("quest_enrollment_blocked_until") or data.get("questEnrollmentBlockedUntil"))
        lines = [f'http {st}', f'quests {len(qlist)} | cache {len(self.quests)} | excluded {len(self.excluded_quests)}', f"token={('yes' if _token() else 'no')}"]
        if sus:
            lines.append(f'ACCESS SUSPENDED until {sus}')
        if blk:
            lines.append(f'enroll blocked until {blk}')
        if not sus and (not blk) and (len(qlist) == 0):
            lines.append('not suspended | Discord returned empty quests[]')
            lines.append('accept on Quest Home → .questrefresh')
        for qd in (qlist or [])[:8]:
            if not isinstance(qd, dict):
                continue
            cfg = qd.get("config") or {}
            us = qd.get("user_status") or {}
            name = (cfg.get("application") or {}).get("name") or qd.get("id")
            tt = self.determine_quest_task_type(cfg)
            stus = 'done' if us.get("completed_at") else 'enrolled' if us.get("enrolled_at") else 'open'
            lines.append(f'| {name} [{tt}] {stus}')
        await S.safe_send(ctx.channel, S.ui_ok('\n'.join(lines)))

    @commands.command(name='questtask', aliases=['qtask'], brief='Prefer task type: watch|desktop|all')
    async def questtask(self, ctx, kind: str='all'):
        try:
            await ctx.message.delete()
        except Exception:
            pass
        k = (kind or 'all').lower().strip()
        if k in ('all', 'any', 'clear', 'off'):
            self._preferred_task = None
            return await S.safe_send(ctx.channel, S.ui_ok('task filter: all'))
        if k in ('watch', 'video', 'desktop', 'play', 'stream'):
            self._preferred_task = k
            return await S.safe_send(ctx.channel, S.ui_ok(f'task filter: {k}'))
        await S.safe_send(ctx.channel, S.ui_err('use: watch | desktop | stream | all'))

async def setup(bot):
    if 'quests' in bot.cogs:
        await bot.remove_cog('quests')
    await bot.add_cog(Quests(bot))
