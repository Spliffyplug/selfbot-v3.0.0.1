import json
import asyncio
import os, sys, json, math, time, asyncio, signal
import discord

def _resolve_intents():
    candidates = []
    for path in (lambda: getattr(discord, 'Intents', None), lambda: getattr(getattr(discord, 'flags', None), 'Intents', None), lambda: __import__('discord.flags', fromlist=['Intents']).Intents if True else None):
        try:
            obj = path()
            if obj is not None:
                return obj
        except Exception:
            pass
    return None
_Intents = _resolve_intents()

def _is_self_build() -> bool:
    try:
        path = str(getattr(discord, '__file__', '') or '')
        ver = str(getattr(discord, '__version__', '') or '')
        markers = 0
        for name in ('Spotify', 'RelationshipType', 'FriendFlags', 'UserSettings'):
            if hasattr(discord, name):
                markers += 1
        if 'discord_py_self' in path or 'discord.py-self' in path:
            return True
        try:
            from discord import http as _http
            src = getattr(_http, 'HTTPClient', None)
            if src and 'bot' in str(getattr(src.static_login, '__code__', b'').co_varnames if hasattr(getattr(src, 'static_login', None), '__code__') else ()):
                pass
        except Exception:
            pass
        try:
            import discord_protos
            if markers >= 1:
                return True
        except Exception:
            pass
        if markers >= 2:
            return True
        return markers >= 1
    except Exception:
        return False
if not _is_self_build():
    print('[wilt] WARNING: this discord install may be upstream discord.py (bot-only)')
    print('[wilt] user tokens will 401. delete site-packages/discord + install discord.py-self only')
print('[wilt] discord', getattr(discord, '__file__', '?'), 'ver', getattr(discord, '__version__', '?'), 'Intents', _Intents is not None)
from discord.ext import commands
from dotenv import load_dotenv
from pathlib import Path
load_dotenv()
load_dotenv('.env')
load_dotenv('/home/container/.env')
try:
    from utils.ms_install import ensure_modifyself
    ensure_modifyself(log=print)
except Exception as _ms_e:
    print(f'[modifyself] auto-install skip: {_ms_e}')

def _load_cfg():
    try:
        with open('config.json', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def _save_cfg(cfg):
    try:
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f'[cfg] save failed: {e}')
_cfg = _load_cfg()

def _clean_token(raw):
    if raw is None:
        return ''
    t = str(raw).strip()
    for _ in range(3):
        if len(t) >= 2 and t[0] == t[-1] and (t[0] in ("'", '"', '`')):
            t = t[1:-1].strip()
        else:
            break
    for pfx in ('Bot ', 'Bearer ', 'bot ', 'bearer '):
        if t.startswith(pfx):
            t = t[len(pfx):].strip()
    for ch in ('\r', '\n', '\t', '\ufeff'):
        t = t.replace(ch, '')
    t = t.strip()
    return t

def _load_token():
    cands = []
    for path in ('.env', '/home/container/.env'):
        try:
            p = Path(path)
            if not p.is_file():
                continue
            for line in p.read_text(encoding='utf-8', errors='replace').splitlines():
                s = line.strip()
                if not s or s.startswith('#'):
                    continue
                up = s.upper()
                if up.startswith('TOKEN=') or up.startswith('USER_TOKEN=') or up.startswith('DISCORD_TOKEN='):
                    cands.append((path, s.split('=', 1)[1]))
                    break
        except Exception as e:
            print('[wilt] env read', path, e)
    for key in ('TOKEN', 'USER_TOKEN', 'DISCORD_TOKEN'):
        v = os.environ.get(key)
        if v:
            cands.append(('env:' + key, v))
    try:
        cfg = _load_cfg()
        if isinstance(cfg, dict):
            for key in ('token', 'TOKEN', 'user_token'):
                if cfg.get(key):
                    cands.append(('config', cfg[key]))
    except Exception:
        pass
    for src, raw in cands:
        t = _clean_token(raw)
        if len(t) > 50:
            print('[wilt] token from', src, 'len=', len(t), 'dots=', t.count('.'))
            return t
    return ''
TOKEN = _load_token()
VERSION = '3.3.1'
ESC = '\x1b'
RESET = f'{ESC}[0m'
GREY = f'{ESC}[2;37m'
WHITE = f'{ESC}[1;37m'
CYAN = f'{ESC}[36m'
GREEN = f'{ESC}[32m'
RED = f'{ESC}[31m'
YELLOW = f'{ESC}[33m'
BLUE = f'{ESC}[34m'
DIM = f'{ESC}[2m'
DARK = f'{ESC}[30m'
BOLD = f'{ESC}[1m'
CYAN2 = f'{ESC}[0;36m'
WHITE2 = f'{ESC}[0;37m'
BLUE2 = f'{ESC}[0;34m'
BRAND = f'{ESC}[0;35m{ESC}[1m{ESC}[4m'

def _get_prefix(bot, message):
    from cogs import state as S
    try:
        gid = str(getattr(message.guild, 'id', '')) if message.guild else ''
        if gid and isinstance(getattr(S, '_server_prefixes', None), dict) and (gid in S._server_prefixes):
            p = S._server_prefixes[gid]
            if isinstance(p, str) and p:
                return p
    except Exception:
        pass
    p = getattr(S, 'PREFIX', '.')
    if callable(p):
        p = '.'
    if isinstance(p, (list, tuple)):
        p = p[0] if p else '.'
    if not isinstance(p, str) or not p:
        p = '.'
    return p
try:
    from utils.gateway import client_properties as _gw_props, apply_http_headers as _gw_headers, install_ws_identify_patch as _gw_ws_patch, encode_super_properties as _gw_xsp
    _GW_PROPS = _gw_props()
    _gw_ws_patch(_GW_PROPS)
except Exception as _gw_e:
    print(f'[wilt] gateway utils: {_gw_e}')
    _GW_PROPS = None

    def _gw_headers(*a, **k):
        return False

class WiltBot(commands.Bot):

    def __init__(self):
        kwargs = {'command_prefix': _get_prefix, 'help_command': None, 'chunk_guilds_at_startup': False, 'sync_presence': False}
        intents = None
        try:
            IntentsCls = None
            try:
                IntentsCls = getattr(discord, 'Intents', None) or _resolve_intents()
            except Exception:
                IntentsCls = None
            if IntentsCls is not None:
                intents = IntentsCls.default()
                for flag in ('message_content', 'members', 'guilds', 'dm_messages', 'presences'):
                    try:
                        setattr(intents, flag, True)
                    except Exception:
                        pass
        except Exception as e:
            print(f'[wilt] Intents unavailable: {e}')
            intents = None
        if intents is not None:
            kwargs['intents'] = intents
        for key, val in (('self_bot', True), ('bot', False)):
            try:
                kwargs[key] = val
                break
            except Exception:
                pass
        attempts = []
        if intents is not None:
            attempts.append({**kwargs, 'intents': intents, 'self_bot': True, 'sync_presence': False})
            attempts.append({**kwargs, 'intents': intents})
        attempts.append({**kwargs, 'self_bot': True, 'sync_presence': False})
        attempts.append({'command_prefix': _get_prefix, 'self_bot': True, 'sync_presence': False})
        attempts.append({'command_prefix': _get_prefix})
        if intents is not None:
            attempts.append({'command_prefix': _get_prefix, 'intents': intents})
        last = None
        for kw in attempts:
            try:
                super().__init__(**kw)
                print(f'[wilt] Bot init ok keys={list(kw.keys())}')
                break
            except TypeError as e:
                last = e
                continue
        else:
            raise TypeError(f'WiltBot init failed: {last}')
        self._wilt_delete_ids = set()

    async def setup_hook(self):
        try:
            _gw_headers(self, _GW_PROPS)
        except Exception as e:
            print(f'[gateway] setup_hook headers: {e}')
        COGS = ['cogs.general', 'cogs.bot', 'cogs.botbridge', 'cogs.settings', 'cogs.information', 'cogs.server', 'cogs.afk', 'cogs.auto', 'cogs.autoresponder', 'cogs.automod', 'cogs.backup', 'cogs.bumper', 'cogs.db', 'cogs.developer', 'cogs.downloads', 'cogs.filters', 'cogs.fun', 'cogs.pack', 'cogs.gc', 'cogs.guards', 'cogs.host', 'cogs.interactions', 'cogs.lastfm', 'cogs.loggers', 'cogs.mass', 'cogs.meta', 'cogs.monitor', 'cogs.multispoof', 'cogs.nickname', 'cogs.nuke', 'cogs.perms', 'cogs.pingtrack', 'cogs.profile', 'cogs.profile_ext', 'cogs.protect', 'cogs.quests', 'cogs.rpc', 'cogs.reminders', 'cogs.resilience', 'cogs.rolemgmt', 'cogs.scheduler', 'cogs.scrape', 'cogs.search', 'cogs.sniper', 'cogs.social', 'cogs.spoofer', 'cogs.status', 'cogs.tasks', 'cogs.tools', 'cogs.tracking', 'cogs.triggers', 'cogs.utility', 'cogs.voice', 'cogs.webhooks', 'cogs.ai', 'cogs.agc', 'cogs.cleardm', 'cogs.badge', 'cogs.serverclone', 'cogs.music', 'cogs.profilesteal', 'cogs.themes']
        ok = fail = 0
        seen = set()
        for cog in COGS:
            if cog in seen:
                continue
            seen.add(cog)
            try:
                if cog in getattr(self, 'extensions', {}):
                    continue
                await self.load_extension(cog)
                ok += 1
            except commands.ExtensionFailed as e:
                err = getattr(e, 'original', e)
                print(f'[boot] SKIP {cog}: {err}')
                fail += 1
            except Exception as e:
                print(f'[boot] SKIP {cog}: {e}')
                fail += 1
        print(f'[boot] cogs: {ok} loaded, {fail} failed')

    async def on_ready(self):
        try:
            _gw_headers(self, _GW_PROPS)
        except Exception:
            pass
        from cogs import state as S
        S.BOT = self
        S.TOKEN = getattr(getattr(self, 'http', None), 'token', None) or S.TOKEN
        S.PREFIX = _cfg.get("prefix", ".")
        S.STEALTH_DELETE = bool(_cfg.get('stealth_delete', True))
        S.STEALTH_DELETE_SECONDS = float(_cfg.get('stealth_delete_seconds', 5))
        S._live_prefix[0] = S.PREFIX
        try:
            S.load_afk()
        except Exception as e:
            print(f'[wilt] load_afk: {e}')
        try:
            from cogs import state as S
            S.TOKEN = getattr(getattr(self, 'http', None), 'token', None) or S.TOKEN
            if not isinstance(getattr(S, 'PREFIX', None), str) or not S.PREFIX:
                S.PREFIX = '.'
            if isinstance(S.PREFIX, list):
                S.PREFIX = S.PREFIX[0] if S.PREFIX else '.'
            try:
                cfg = S.load_config() if hasattr(S, 'load_config') else {}
                if isinstance(cfg, dict) and isinstance(cfg.get("prefix"), str) and cfg['prefix']:
                    S.PREFIX = cfg['prefix']
            except Exception:
                pass
        except Exception:
            pass
        print(f'[wilt] v{VERSION} | {self.user} | {len(self.guilds)} guilds')
        print(f'[wilt] stealth_delete={S.STEALTH_DELETE} prefix={S.PREFIX!r}')

    def _schedule_stealth_delete(self, msg, delay: float | None=None):
        if not msg:
            return
        mid = getattr(msg, 'id', None)
        if mid is None:
            return
        ids = getattr(self, '_wilt_delete_ids', None)
        if ids is None:
            self._wilt_delete_ids = set()
            ids = self._wilt_delete_ids
        if mid in ids:
            return
        ids.add(mid)
        if delay is None:
            from cogs import state as S
            delay = float(getattr(S, 'STEALTH_DELETE_SECONDS', 5) or 5)

        async def _del():
            await asyncio.sleep(delay)
            try:
                await msg.delete()
            except Exception:
                pass
            finally:
                try:
                    self._wilt_delete_ids.discard(mid)
                except Exception:
                    pass
        asyncio.create_task(_del())

    async def on_command_completion(self, ctx):
        from cogs import state as S
        try:
            if not getattr(S, 'STEALTH_DELETE', True):
                return
            if getattr(ctx, '_wilt_skip_delete', False):
                return
            self._schedule_stealth_delete(ctx.message)
        except Exception as e:
            print(f'[stealth-delete] {e}')

    async def on_command_error(self, ctx, error):
        from cogs import state as S
        try:
            if getattr(S, 'STEALTH_DELETE', True):
                self._schedule_stealth_delete(getattr(ctx, 'message', None))
        except Exception:
            pass
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.CommandOnCooldown):
            try:
                return await ctx.message.edit(content=f'```ansi\n  \x1b[31m✗\x1b[0m  cooldown: {error.retry_after:.1f}s\n```')
            except Exception:
                return
        if isinstance(error, commands.MissingRequiredArgument):
            try:
                return await ctx.message.edit(content=f'```ansi\n  \x1b[31m✗\x1b[0m  missing argument: {error.param}\n```')
            except Exception:
                return
        if isinstance(error, commands.BadArgument):
            try:
                return await ctx.message.edit(content=f'```ansi\n  \x1b[31m✗\x1b[0m  bad argument: {error}\n```')
            except Exception:
                return
        if isinstance(error, commands.NoPrivateMessage):
            try:
                return await ctx.message.edit(content=f'```ansi\n  \x1b[31m✗\x1b[0m  guild only\n```')
            except Exception:
                return
        err = getattr(error, 'original', error)
        print(f'[error] {ctx.command}: {type(err).__name__}: {err}')

    async def _dispatch_cog_event(self, event_name: str, *args, **kwargs):
        for cog_name, cog in list(self.cogs.items()):
            try:
                listeners = getattr(cog, '__cog_listeners__', None) or []
                for ev, method_name in listeners:
                    if ev != event_name:
                        continue
                    meth = getattr(cog, method_name, None)
                    if not meth:
                        continue
                    try:
                        await meth(*args, **kwargs)
                    except Exception as e:
                        print(f'[listener {cog_name}.{method_name}] {e}')
            except Exception as e:
                print(f'[cog-dispatch {cog_name}] {e}')

    async def on_message(self, message):
        from cogs import state as S
        await self._dispatch_cog_event('on_message', message)
        if not self.user or message.author.id != self.user.id:
            return
        if not isinstance(getattr(S, 'PREFIX', None), str) or not S.PREFIX:
            S.PREFIX = '.'
        try:
            ctx = await self.get_context(message)
        except Exception as e:
            print(f'[wilt] get_context: {e}')
            ctx = None
        if ctx is not None and ctx.command is not None:
            try:
                await self.invoke(ctx)
            except Exception as e:
                print(f'[wilt] invoke {ctx.command}: {e}')
            try:
                if getattr(S, 'STEALTH_DELETE', True):
                    self._schedule_stealth_delete(message)
            except Exception:
                pass
        else:
            try:
                await self.process_commands(message)
            except Exception as e:
                print(f'[wilt] process_commands: {e}')
            try:
                content = message.content or ''
                pfx = getattr(S, 'PREFIX', '.')
                if isinstance(pfx, str) and pfx and content.startswith(pfx) and (len(content) > len(pfx)):
                    rest = content[len(pfx):].split()[:1]
                    if rest and rest[0].replace('_', '').isalnum():
                        print(f'[wilt] no command matched: {content[:60]!r}')
            except Exception:
                pass
        try:
            auto = self.get_cog('auto')
            if auto is not None:
                await auto._handle_self_message(message)
        except Exception as e:
            print(f'[auto] self-hook: {e}')

    async def on_message_delete(self, message):
        await self._dispatch_cog_event('on_message_delete', message)

    async def on_message_edit(self, before, after):
        await self._dispatch_cog_event('on_message_edit', before, after)

    async def on_member_join(self, member):
        await self._dispatch_cog_event('on_member_join', member)

    async def on_member_remove(self, member):
        await self._dispatch_cog_event('on_member_remove', member)

    async def on_guild_channel_delete(self, channel):
        await self._dispatch_cog_event('on_guild_channel_delete', channel)

    async def on_guild_update(self, before, after):
        await self._dispatch_cog_event('on_guild_update', before, after)

    async def on_group_join(self, channel, user):
        await self._dispatch_cog_event('on_group_join', channel, user)

    async def on_connect(self):
        await self._dispatch_cog_event('on_connect')

    async def on_disconnect(self):
        await self._dispatch_cog_event('on_disconnect')

    async def on_resumed(self):
        await self._dispatch_cog_event('on_resumed')

    async def on_rate_limit(self, *args, **kwargs):
        await self._dispatch_cog_event('on_rate_limit', *args, **kwargs)

    async def process_commands(self, message):
        if not self.user or message.author.id != self.user.id:
            return
        await super().process_commands(message)
client = WiltBot()
CATEGORY_ORDER = ['general', 'quests', 'sniper', 'afk', 'rpc', 'spoofer', 'status', 'social', 'profile', 'auto', 'voice', 'server', 'mass', 'search', 'fun', 'pack', 'utility', 'tools', 'settings', 'meta', 'host', 'bot', 'filters', 'loggers', 'tracking', 'reminders', 'guards', 'rolemgmt', 'information', 'nuke', 'developer', 'themes', 'multispoof', 'gc', 'webhooks', 'ai', 'downloads', 'protect']
CATEGORY_SHORT = {'general': 'core', 'quests': 'quests', 'sniper': 'snipe', 'afk': 'afk', 'rpc': 'rpc', 'spoofer': 'spoof', 'status': 'status', 'social': 'social', 'profile': 'profile', 'profile_ext': 'profile+', 'auto': 'auto', 'autoresponder': 'ar', 'voice': 'voice', 'server': 'server', 'mass': 'mass', 'search': 'search', 'fun': 'fun', 'pack': 'pack', 'utility': 'util', 'tools': 'tools', 'settings': 'cfg', 'meta': 'meta', 'host': 'host', 'bot': 'bot', 'filters': 'filter', 'loggers': 'log', 'tracking': 'track', 'reminders': 'remind', 'guards': 'guard', 'rolemgmt': 'roles', 'information': 'info', 'nuke': 'nuke', 'developer': 'dev', 'themes': 'theme', 'multispoof': 'mspoof', 'gc': 'gc', 'webhooks': 'hook', 'ai': 'ai', 'downloads': 'dl', 'protect': 'protect', 'triggers': 'trig', 'pingtrack': 'pings', 'scheduler': 'sched', 'tasks': 'tasks', 'resilience': 'res', 'monitor': 'mon', 'backup': 'backup', 'bumper': 'bump', 'agc': 'agc', 'automod': 'amod', 'interactions': 'ix', 'perms': 'perms', 'db': 'db', 'lastfm': 'lfm', 'scrape': 'scrape', 'nickname': 'nick'}

@client.command(name='help', aliases=['h'])
async def _help(ctx, *, query: str=''):
    from cogs import state as S
    import math
    raw = (query or '').strip().lower()
    pfx = getattr(S, 'PREFIX', '.')
    if not isinstance(pfx, str) or not pfx:
        pfx = '.'
    CPER, KPER = (14, 10)
    parts = raw.split()
    page = 1
    if parts and parts[-1].isdigit():
        page = max(1, int(parts.pop()))
    q = ' '.join(parts)
    cats = {}
    for cog in client.cogs.values():
        cname = cog.qualified_name.lower()
        cmds = [c for c in cog.get_commands() if not c.hidden and c.enabled]
        if cmds:
            cats[cname] = sorted(cmds, key=lambda c: c.name)
    if not q:
        seen, ordered = (set(), [])
        for name in CATEGORY_ORDER:
            if name in cats and name not in seen:
                ordered.append(name)
                seen.add(name)
        for name in sorted(cats):
            if name not in seen:
                ordered.append(name)
                seen.add(name)
        total = sum((len(v) for v in cats.values()))
        pages = max(1, math.ceil(len(ordered) / KPER))
        page = min(page, pages)
        chunk = ordered[(page - 1) * KPER:page * KPER]
        lines = [f'{BRAND}wilt{RESET} {DIM}v{VERSION}{RESET} {GREY}| {total} cmds | {len(ordered)} categories{RESET}', '']
        row = []
        for cat in chunk:
            n = len(cats[cat])
            label = cat[:14]
            row.append(f'{CYAN}{label:<14}{RESET}{DIM}{n:>3}{RESET}')
            if len(row) == 2:
                lines.append('  ' + '   '.join(row))
                row = []
        if row:
            lines.append(' ' + '  '.join(row))
        lines.append('')
        nav = f'{pfx}h <cat> | {pfx}h <cmd>'
        if pages > 1:
            nav = f'{pfx}h {page % pages + 1} | ' + nav
        lines.append(f'{DIM}{page}/{pages} | {nav}{RESET}')
        try:
            return await ctx.message.edit(content=S._ansi_block(lines))
        except Exception:
            return await S.safe_send(ctx.channel, S._ansi_block(lines))
    if q in cats:
        cmds = cats[q]
        pages = max(1, math.ceil(len(cmds) / CPER))
        page = min(page, pages)
        chunk = cmds[(page - 1) * CPER:page * CPER]
        col = min(14, max((len(c.name) for c in chunk), default=6))
        lines = [f'{BRAND}wilt{RESET} {DIM}{q}{RESET} {GREY}{page}/{pages} | {len(cmds)}{RESET}', '']
        for c in chunk:
            desc = (c.brief or (c.help or '').split('\n')[0] or '')[:28]
            pad = ' ' * max(0, col - len(c.name))
            lines.append(f' {CYAN}{c.name}{RESET}{pad} {DIM}{desc}{RESET}')
        lines.append('')
        if pages > 1:
            lines.append(f'{DIM}{pfx}h {q} {page % pages + 1} | {pfx}h{RESET}')
        else:
            lines.append(f'{DIM}{pfx}h{RESET}')
        try:
            return await ctx.message.edit(content=S._ansi_block(lines))
        except Exception:
            return await S.safe_send(ctx.channel, S._ansi_block(lines))
    cmd = client.get_command(q)
    if cmd:
        cog_name = cmd.cog.qualified_name.lower() if cmd.cog else '-'
        als = ' '.join(cmd.aliases[:4]) if cmd.aliases else '-'
        sig = (cmd.signature or '')[:40]
        desc = (cmd.help or cmd.brief or '-').split('\n')[0][:60]
        lines = [f'{BRAND}wilt{RESET} {CYAN}{pfx}{cmd.name}{RESET} {DIM}{sig}{RESET}', f' {GREY}{desc}{RESET}', f' {DIM}{cog_name} | {als}{RESET}']
        try:
            return await ctx.message.edit(content=S._ansi_block(lines))
        except Exception:
            return await S.safe_send(ctx.channel, S._ansi_block(lines))
    all_cmds = [c for cog in client.cogs.values() for c in cog.get_commands()]
    matches = [c for c in all_cmds if q in c.name][:6]
    if matches:
        lines = [f'{DIM}? {q}{RESET}', '']
        for c in matches:
            lines.append(f' {CYAN}{pfx}{c.name}{RESET}')
        try:
            return await ctx.message.edit(content=S._ansi_block(lines))
        except Exception:
            return await S.safe_send(ctx.channel, S._ansi_block(lines))
    try:
        await ctx.message.edit(content=S.ui_err(f'unknown: {q}'))
    except Exception:
        await S.safe_send(ctx.channel, S.ui_err(f'unknown: {q}'))

@client.command(name='ping')
async def _ping(ctx):
    from cogs import state as S
    ms = round(client.latency * 1000)
    try:
        hist = getattr(S, '_latency_history', None)
        if hist is None:
            S._latency_history = []
            hist = S._latency_history
        hist.append(ms)
        if len(hist) > 50:
            del hist[:-50]
        avg = sum(hist) / len(hist)
        await ctx.message.edit(content=S.ui_ok(f'pong - `{ms}ms` (avg `{avg:.0f}ms`)'))
    except Exception:
        await ctx.message.edit(content=S.ui_ok(f'pong - `{ms}ms`'))
if not TOKEN:
    sys.exit('TOKEN not set - put TOKEN=your_user_token in .env (no quotes)')
print('[wilt] starting client... len=%s dots=%s' % (len(TOKEN), TOKEN.count('.')))
try:
    client.run(TOKEN, log_handler=None)
except TypeError:
    client.run(TOKEN)
except Exception as e:
    print('[wilt] login failed:', type(e).__name__, e)
    print('[wilt] use a fresh USER token (Network → Authorization). not a bot token.')
    raise
