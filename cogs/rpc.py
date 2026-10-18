import discord
import asyncio
import time
import re
import json
import io
import aiohttp
import hashlib
from pathlib import Path
from discord.ext import commands
from . import state as S
from utils.ascii_helper import AsciiHelper
ascii = AsciiHelper()
DEFAULT_APP_ID = 1552026905023356938
PURPLESTREAM_URL = 'https://www.twitch.tv/hadeontop'
ICON_PLACEHOLDER = 'https://cdn.pfps.gg/pfps/20715-237182-lonely-girl-animated.gif'
TYPE_MAP = {'playing': 0, 'streaming': 1, 'listening': 2, 'watching': 3, 'competing': 5, 'purplestream': 1}
PLATFORM_ICON_KEYS = {'spotify': 'spotify', 'youtube': 'youtube', 'yt': 'youtube', 'xbox': 'xbox', 'ps': 'playstation', 'playstation': 'playstation', 'ps4': 'playstation', 'ps5': 'playstation', 'crunchy': 'crunchyroll', 'crunchyroll': 'crunchyroll', 'twitch': 'twitch', 'vrchat': 'vrchat', 'meta_quest': 'vrchat', 'quest': 'vrchat', 'roblox': 'roblox', 'rbx': 'roblox', 'minecraft': 'minecraft', 'mc': 'minecraft', 'fortnite': 'fortnite', 'fn': 'fortnite', 'valorant': 'valorant', 'val': 'valorant', 'netflix': 'netflix', 'vscode': 'code', 'code': 'code'}
PLATFORM_PRESET_MAP = {'xbox': {'application_id': 438122941302046720, 'platform': 'xbox', 'name': 'Xbox', 'type': 0}, 'ps': {'application_id': 1001158269215858728, 'platform': 'ps5', 'name': 'PlayStation', 'type': 0}, 'ps4': {'application_id': 1001158269215858728, 'platform': 'ps4', 'name': 'PlayStation 4', 'type': 0}, 'ps5': {'application_id': 1001158269215858728, 'platform': 'ps5', 'name': 'PlayStation 5', 'type': 0}, 'playstation': {'application_id': 1001158269215858728, 'platform': 'ps5', 'name': 'PlayStation', 'type': 0}, 'youtube': {'application_id': 880988207033802783, 'platform': None, 'name': 'YouTube', 'type': 3}, 'yt': {'application_id': 880988207033802783, 'platform': None, 'name': 'YouTube', 'type': 3}, 'twitch': {'application_id': 880988207033802783, 'platform': None, 'name': 'Twitch', 'type': 3}, 'roblox': {'application_id': 963434583335854120, 'platform': None, 'name': 'Roblox', 'type': 0}, 'rbx': {'application_id': 963434583335854120, 'platform': None, 'name': 'Roblox', 'type': 0}, 'minecraft': {'application_id': 356875770142195712, 'platform': None, 'name': 'Minecraft', 'type': 0}, 'mc': {'application_id': 356875770142195712, 'platform': None, 'name': 'Minecraft', 'type': 0}, 'fortnite': {'application_id': 432980957394370572, 'platform': None, 'name': 'Fortnite', 'type': 0}, 'fn': {'application_id': 432980957394370572, 'platform': None, 'name': 'Fortnite', 'type': 0}, 'valorant': {'application_id': 700785226400399401, 'platform': None, 'name': 'VALORANT', 'type': 0}, 'val': {'application_id': 700785226400399401, 'platform': None, 'name': 'VALORANT', 'type': 0}, 'league': {'application_id': 401518684763717642, 'platform': None, 'name': 'League of Legends', 'type': 0}, 'lol': {'application_id': 401518684763717642, 'platform': None, 'name': 'League of Legends', 'type': 0}, 'riot': {'application_id': 401518684763717642, 'platform': None, 'name': 'League of Legends', 'type': 0}, 'netflix': {'application_id': 880988207033802783, 'platform': None, 'name': 'Netflix', 'type': 3}, 'vscode': {'application_id': 383226320970055681, 'platform': None, 'name': 'Visual Studio Code', 'type': 0}, 'code': {'application_id': 383226320970055681, 'platform': None, 'name': 'Code', 'type': 0}, 'vrchat': {'application_id': 1498387526501535835, 'platform': 'meta_quest', 'name': 'VRChat', 'type': 0}, 'meta_quest': {'application_id': 1498387526501535835, 'platform': 'meta_quest', 'name': 'Meta Quest', 'type': 0}, 'quest': {'application_id': 1498387526501535835, 'platform': 'meta_quest', 'name': 'Meta Quest', 'type': 0}, 'meta': {'application_id': 1498387526501535835, 'platform': 'meta_quest', 'name': 'Meta Quest', 'type': 0}, 'oculus': {'application_id': 1498387526501535835, 'platform': 'meta_quest', 'name': 'Meta Quest', 'type': 0}, 'spotify': {'application_id': None, 'platform': None, 'name': 'Spotify', 'type': 2}, 'crunchyroll': {'application_id': None, 'platform': None, 'name': 'Crunchyroll', 'type': 3}, 'crunchy': {'application_id': None, 'platform': None, 'name': 'Crunchyroll', 'type': 3}}

_CUSTOM_PRESETS_PATH = Path('data/rpc_presets.json')
_RUNTIME_PRESETS = {}

def _load_custom_presets():
    global _RUNTIME_PRESETS
    _RUNTIME_PRESETS = {}
    try:
        if _CUSTOM_PRESETS_PATH.is_file():
            data = json.loads(_CUSTOM_PRESETS_PATH.read_text(encoding='utf-8'))
            if isinstance(data, dict):
                _RUNTIME_PRESETS = {str(k).lower(): v for k, v in data.items() if isinstance(v, dict)}
    except Exception as e:
        print('[RPC] custom presets load:', e)

def _save_custom_presets():
    try:
        _CUSTOM_PRESETS_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CUSTOM_PRESETS_PATH.write_text(json.dumps(_RUNTIME_PRESETS, indent=2), encoding='utf-8')
    except Exception as e:
        print('[RPC] custom presets save:', e)

def _all_presets():
    out = dict(PLATFORM_PRESET_MAP)
    out.update(_RUNTIME_PRESETS)
    return out

_load_custom_presets()

INLINE_KEYS = ['name', 'details', 'state', 'type', 'timestamp', 'platform', 'large_image_text', 'large_image', 'small_image', 'btn1', 'btn2']

class RPCCog(commands.Cog, name='rpc'):

    def __init__(self, bot):
        self.bot = bot
        self.rpc_slots = [None] * 6
        self._slot_platform_preset = [None] * 6
        self._asset_cache = {}
        self._asset_urls = {}
        self.status_rotation_active = False
        self.emoji_rotation_active = False
        self.current_status = ''
        self.current_emoji = ''
        self._original_ws_send = None
        self._interceptor_active = False
        self._clearing = False
        self._last_push = 0.0
        self._app_asset_map = {}
        self._app_assets_loaded = False
        self._bg_started = False

    async def _start_presence_interceptor(self):
        if self._interceptor_active:
            return
        for _ in range(30):
            if self.bot.ws and hasattr(self.bot.ws, 'send'):
                break
            await asyncio.sleep(0.5)
        if not self.bot.ws:
            print('[RPC] Could not attach interceptor - no websocket')
            return
        self._original_ws_send = self.bot.ws.send
        if not getattr(self.bot, 'ws', None):
            return
        bot_ws = self.bot.ws

        async def patched_send(data, *args, **kwargs):
            if isinstance(data, str) and '"op":3' in data:
                try:
                    payload = json.loads(data)
                    d = payload.get('d', {})
                    activities = d.get('activities', [])
                    if not activities and any((slot is not None for slot in self.rpc_slots)):
                        active = [s for s in self.rpc_slots if s is not None]
                        if active and (not self._clearing):
                            d['activities'] = active
                            payload['d'] = d
                            data = json.dumps(payload)
                except Exception as _e:
                    print(f'[rpc] ws_send patch: {_e}')
            return await self._original_ws_send(data, *args, **kwargs)
        bot_ws.send = patched_send
        self._interceptor_active = True
        print('[RPC] Presence interceptor active')

    async def _stop_presence_interceptor(self):
        if self._interceptor_active and self._original_ws_send:
            self.bot.ws.send = self._original_ws_send
            self._interceptor_active = False
            print('[RPC] Presence interceptor removed')

    @commands.Cog.listener()
    async def on_ready(self):
        await asyncio.sleep(3)
        if not self._bg_started:
            self._bg_started = True
            self.bot.loop.create_task(self.auto_refresh_presence())
            self.bot.loop.create_task(self.auto_refresh_cdn_assets())
        self._load_rpc_slots()
        await self._refresh_all_assets()
        await self._start_presence_interceptor()
        if any((a is not None for a in self.rpc_slots)):
            await self._push()
            print(f'[RPC] Restored RPC slots on startup')

    def _get_user_file(self, filename):
        uid = str(self.bot.user.id)
        path = Path(f'data/{uid}.json')
        return path

    def _save_rpc_slots(self):
        path = self._get_user_file('slots.json')
        path.parent.mkdir(exist_ok=True)
        data = []
        for slot in self.rpc_slots:
            if slot:
                clean = {k: v for k, v in slot.items() if k not in ['instance', 'flags', 'session_id', 'sync_id', 'secrets', 'party', 'metadata']}
                data.append(clean)
            else:
                data.append(None)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def _load_rpc_slots(self):
        path = self._get_user_file('slots.json')
        if not path.exists():
            return
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            for i, slot in enumerate(data[:6]):
                if slot:
                    self.rpc_slots[i] = slot
            print(f'[RPC] Loaded {sum((1 for s in self.rpc_slots if s))} saved RPC slots for {self.bot.user}')
        except Exception as e:
            print(f'[RPC] Failed to load saved RPCs: {e}')

    def _ensure_slot(self, index: int):
        if self.rpc_slots[index] is None:
            self.rpc_slots[index] = {'type': 0, 'name': 'Default', 'application_id': DEFAULT_APP_ID, 'assets': {}, 'instance': True}

    async def _refresh_cdn_url(self, url: str) -> str:
        if not url or not url.startswith('mp:'):
            return url
        try:
            headers = {'Authorization': S._get_token(self.bot), 'Content-Type': 'application/json'}
            async with aiohttp.ClientSession() as session:
                async with session.post('https://discord.com/api/v9/attachments/refresh-urls', json={'attachment_urls': [url]}, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        refreshed = data.get('refreshed_urls', [])
                        if refreshed and refreshed[0].get("refreshed"):
                            return refreshed[0]['refreshed']
        except Exception:
            pass
        return url

    async def _refresh_all_assets(self):
        try:
            for slot_idx, slot in enumerate(self.rpc_slots):
                if slot and 'assets' in slot:
                    assets = slot['assets']
                    if 'large_image' in assets and assets['large_image']:
                        if assets['large_image'].startswith('mp:'):
                            assets['large_image'] = await self._refresh_cdn_url(assets['large_image'])
                    if 'small_image' in assets and assets['small_image']:
                        if assets['small_image'].startswith('mp:'):
                            assets['small_image'] = await self._refresh_cdn_url(assets['small_image'])
            if any((a is not None for a in self.rpc_slots)):
                await self._push()
        except Exception:
            pass

    async def auto_refresh_cdn_assets(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            await asyncio.sleep(1500)
            await self._refresh_all_assets()

    async def _push(self):
        import time as _time
        now = _time.monotonic()
        if now - getattr(self, '_last_push', 0) < 1.2:
            await asyncio.sleep(1.2 - (now - self._last_push))
        self._last_push = _time.monotonic()
        active = []
        for a in self.rpc_slots:
            if not isinstance(a, dict):
                continue
            assets = a.get("assets") if isinstance(a.get("assets"), dict) else {}
            if a.get("name") or a.get("details") or a.get("state") or assets.get("large_image") or assets.get("small_image"):
                active.append(a)
        if not active:
            return
        try:
            await self._load_app_assets()
        except Exception as e:
            print(f'[RPC] asset catalog: {e}')
        default_app = int(DEFAULT_APP_ID)
        for a in active:
            slot_app = a.get("application_id") or default_app
            try:
                slot_app = int(slot_app)
            except Exception:
                slot_app = default_app
            a['application_id'] = slot_app
            assets = a.get("assets") if isinstance(a.get("assets"), dict) else {}
            new_assets = {}
            for k in ('large_image', 'small_image'):
                v = assets.get(k)
                if not v:
                    continue
                v = str(v).strip()
                if v.startswith('http://') or v.startswith('https://') or v.startswith('mp:attachments/') or 'imgur.com' in v or 'cdn.discordapp.com' in v or 'media.discordapp.net' in v:
                    a['application_id'] = default_app
                    slot_app = default_app
                    try:
                        prox = await self.upload_asset(v, app_id=default_app)
                        new_assets[k] = prox or v
                    except Exception as e:
                        print(f'[RPC] proxy {k}: {e}')
                        new_assets[k] = v
                elif v.startswith('mp:external/'):
                    new_assets[k] = v
                elif v.startswith('spotify:') or v.startswith('youtube:') or v.startswith('twitch:'):
                    new_assets[k] = v
                elif slot_app == default_app:
                    new_assets[k] = self._resolve_portal_asset(v)
                else:
                    new_assets[k] = v.lower().replace(' ', '_')
            if assets.get("large_text"):
                new_assets['large_text'] = str(assets['large_text'])[:128]
            if assets.get("small_text"):
                new_assets['small_text'] = str(assets['small_text'])[:128]
            if assets.get("large_image_text") and 'large_text' not in new_assets:
                new_assets['large_text'] = str(assets['large_image_text'])[:128]
            if assets.get("small_image_text") and 'small_text' not in new_assets:
                new_assets['small_text'] = str(assets['small_image_text'])[:128]
            a['assets'] = new_assets
            print(f'[RPC] slot app={slot_app} name={a.get("name")!r} assets={new_assets}')
        current_status = 'online'
        try:
            st = getattr(self.bot, 'status', None)
            if st is not None:
                current_status = str(getattr(st, 'value', st)).replace('Status.', '').lower()
                if current_status not in ('online', 'idle', 'dnd', 'invisible'):
                    current_status = 'online'
        except Exception:
            pass

        def _type_enum(val):
            try:
                n = int(val)
            except Exception:
                n = 0
            try:
                return discord.ActivityType(n)
            except Exception:
                return discord.ActivityType.playing

        def _build_activity(a):
            assets = a.get("assets") or {}
            app = a.get("application_id") or default_app
            try:
                app = int(app)
            except Exception:
                app = default_app
            kwargs = {'name': a.get("name") or 'RPC', 'type': _type_enum(a.get('type', 0)), 'application_id': app}
            if a.get("details"):
                kwargs['details'] = str(a['details'])[:128]
            if a.get("state"):
                kwargs['state'] = str(a['state'])[:128]
            if a.get("url") and int(a.get('type', 0) or 0) == 1:
                kwargs['url'] = a['url']
            if assets.get("large_image") or assets.get("small_image"):
                try:
                    kwargs['assets'] = discord.ActivityAssets(large_image=assets.get("large_image") or None, large_text=assets.get("large_text") or None, small_image=assets.get("small_image") or None, small_text=assets.get("small_text") or None)
                except Exception as e:
                    print(f'[RPC] ActivityAssets: {e}')
                    kwargs['assets'] = {k: v for k, v in assets.items() if v}
            if isinstance(a.get("timestamps"), dict):
                kwargs['timestamps'] = a['timestamps']
            try:
                return discord.Activity(**{k: v for k, v in kwargs.items() if v is not None})
            except Exception as e:
                print(f'[RPC] Activity build: {e}')
                return None
        activities_objs = []
        for a in active:
            obj = _build_activity(a)
            if obj is not None:
                activities_objs.append(obj)
        raw = []
        for a in active:
            app = a.get("application_id") or default_app
            entry = {'name': a.get("name") or 'RPC', 'type': int(a.get('type', 0) or 0), 'application_id': str(app)}
            if a.get("details"):
                entry['details'] = str(a['details'])[:128]
            if a.get("state"):
                entry['state'] = str(a['state'])[:128]
            if a.get("url") and int(a.get('type', 0) or 0) == 1:
                entry['url'] = a['url']
            if a.get("platform"):
                entry['platform'] = a['platform']
            assets = a.get("assets") or {}
            if assets:
                entry['assets'] = {k: v for k, v in assets.items() if v}
            if isinstance(a.get("timestamps"), dict):
                entry['timestamps'] = a['timestamps']
            if a.get("buttons"):
                btns = a['buttons']
                if isinstance(btns, list):
                    labels = []
                    for b in btns[:2]:
                        if isinstance(b, dict):
                            labels.append(str(b.get("label") or b.get("url") or '')[:32])
                        else:
                            labels.append(str(b)[:32])
                    if labels:
                        entry['buttons'] = labels
            raw.append(entry)
        status_map = {'online': 'online', 'idle': 'idle', 'dnd': 'dnd', 'invisible': 'invisible'}
        payload = {'op': 3, 'd': {'since': 0, 'activities': raw, 'status': status_map.get(current_status, 'online'), 'afk': False}}
        if activities_objs and hasattr(self.bot, 'change_presence'):
            try:
                if len(activities_objs) == 1:
                    await self.bot.change_presence(activity=activities_objs[0], status=current_status)
                else:
                    try:
                        await self.bot.change_presence(activities=activities_objs, status=current_status)
                    except TypeError:
                        pass
                print(f'[RPC] change_presence ok n={len(activities_objs)}')
            except Exception as e:
                print(f'[RPC] change_presence: {e}')
        ws = getattr(self.bot, 'ws', None)
        if ws is not None:
            try:
                send = getattr(ws, 'send_as_json', None) or getattr(ws, 'send_json', None)
                if send:
                    await send(payload)
                    print(f'[RPC] OP3 multi sent n={len(raw)} names={[r.get("name") for r in raw]}')
            except Exception as e:
                print(f'[RPC] OP3: {e}')
        else:
            print('[RPC] no ws - OP3 skipped')
        try:
            self._save_rpc_slots()
        except Exception:
            pass

    async def apply_activities(self):
        if any((a is not None for a in self.rpc_slots)):
            await self._push()

    def _parse_timestamp_value(self, value: str) -> float:
        value = value.strip()
        if ':' in value:
            parts = value.split(':')
            try:
                if len(parts) == 3:
                    return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                elif len(parts) == 2:
                    return int(parts[0]) * 60 + int(parts[1])
            except Exception:
                pass
        return float(value) * 3600

    def _set_timestamp(self, slot: int, value: str):
        now = time.time()
        total_seconds = self._parse_timestamp_value(value)
        self.rpc_slots[slot]['timestamps'] = {'start': int(now * 1000), 'end': int((now + total_seconds) * 1000)}

    def _apply_platform_preset(self, slot: int, preset_key: str) -> bool:
        off_keys = {'off', 'none', 'clear', 'normal'}
        if preset_key in off_keys:
            self._slot_platform_preset[slot] = None
            self._ensure_slot(slot)
            self.rpc_slots[slot]['application_id'] = DEFAULT_APP_ID
            self.rpc_slots[slot].pop('platform', None)
            return True
        preset = _all_presets().get(preset_key)
        if not preset:
            return False
        self._ensure_slot(slot)
        self._slot_platform_preset[slot] = preset_key
        app = preset.get("application_id")
        if app is None:
            self.rpc_slots[slot]['application_id'] = int(DEFAULT_APP_ID)
        else:
            try:
                self.rpc_slots[slot]['application_id'] = int(app)
            except Exception:
                self.rpc_slots[slot]['application_id'] = int(DEFAULT_APP_ID)
        if preset.get("platform"):
            self.rpc_slots[slot]['platform'] = preset['platform']
        else:
            self.rpc_slots[slot].pop('platform', None)
        self.rpc_slots[slot].setdefault('assets', {})
        # platform badge comes from application_id; only set image for http assets
        if preset.get("asset") and str(preset.get("asset")).startswith("http"):
            self.rpc_slots[slot]['assets']['large_image'] = preset['asset']
        if preset.get("name"):
            self.rpc_slots[slot]['name'] = preset['name']
        elif not self.rpc_slots[slot].get("name"):
            self.rpc_slots[slot]['name'] = preset_key
        if 'type' in preset and preset['type'] is not None:
            self.rpc_slots[slot]['type'] = preset['type']
        elif self.rpc_slots[slot].get("type") is None:
            self.rpc_slots[slot]['type'] = 0
        return True

    def _parse_inline(self, args: str) -> dict:
        result = {}
        words = args.split()
        positions = [(w.lower(), i) for i, w in enumerate(words) if w.lower() in INLINE_KEYS]
        for idx, (key, pos) in enumerate(positions):
            start = pos + 1
            end = positions[idx + 1][1] if idx + 1 < len(positions) else len(words)
            value = ' '.join(words[start:end]).strip()
            if value:
                result[key] = value
        return result

    async def _apply_inline(self, slot: int, parsed: dict):
        self._ensure_slot(slot)
        act = self.rpc_slots[slot]
        if 'name' in parsed:
            act['name'] = parsed['name']
        if 'details' in parsed:
            act['details'] = parsed['details']
        if 'state' in parsed:
            act['state'] = parsed['state']
        if 'type' in parsed:
            t = parsed['type'].lower()
            if t in TYPE_MAP:
                act['type'] = TYPE_MAP[t]
                if t == 'purplestream':
                    act['url'] = PURPLESTREAM_URL
                elif 'url' in act and t not in ('streaming', 'purplestream'):
                    del act['url']
        if 'timestamp' in parsed:
            val = parsed['timestamp']
            if val.lower() == 'clear':
                act.pop('timestamps', None)
            else:
                try:
                    self._set_timestamp(slot, val)
                except Exception:
                    pass
        if 'platform' in parsed:
            self._apply_platform_preset(slot, parsed['platform'].lower())
        if 'large_image_text' in parsed:
            act.setdefault('assets', {})['large_text'] = parsed['large_image_text']
        if 'large_image' in parsed:
            src = parsed['large_image']
            if isinstance(src, str) and src.startswith('http'):
                ch = getattr(self, '_last_ctx_channel', None)
                if ch is not None:
                    try:
                        cdn = await self.rehost_resized(ch, src, size=512)
                        if cdn:
                            src = cdn
                    except Exception as e:
                        print(f'[RPC] inline large resize: {e}')
            key = await self.upload_asset(src)
            if key:
                act.setdefault('assets', {})['large_image'] = key
                self._asset_urls[key] = parsed['large_image']
        if 'small_image' in parsed:
            src = parsed['small_image']
            if isinstance(src, str) and src.startswith('http'):
                ch = getattr(self, '_last_ctx_channel', None)
                if ch is not None:
                    try:
                        cdn = await self.rehost_resized(ch, src, size=512)
                        if cdn:
                            src = cdn
                    except Exception as e:
                        print(f'[RPC] inline small resize: {e}')
            key = await self.upload_asset(src)
            if key:
                act.setdefault('assets', {})['small_image'] = key
                self._asset_urls[key] = parsed['small_image']
        if 'btn1' in parsed:
            parts = parsed['btn1'].split()
            if len(parts) >= 2:
                btns = act.setdefault('buttons', [])
                entry = {'label': ' '.join(parts[:-1]), 'url': parts[-1]}
                if not btns:
                    btns.append(entry)
                else:
                    btns[0] = entry
        if 'btn2' in parsed:
            parts = parsed['btn2'].split()
            if len(parts) >= 2:
                btns = act.setdefault('buttons', [])
                while len(btns) < 2:
                    btns.append(None)
                btns[1] = {'label': ' '.join(parts[:-1]), 'url': parts[-1]}
                act['buttons'] = [b for b in btns if b]

    async def _load_app_assets(self, force: bool=False):
        if self._app_assets_loaded and (not force) and self._app_asset_map:
            return self._app_asset_map
        app_id = int(DEFAULT_APP_ID)
        token = None
        try:
            token = getattr(getattr(self.bot, 'http', None), 'token', None) or getattr(self.bot, 'token', None)
        except Exception:
            token = None
        if not token:
            try:
                from . import state as S
                token = getattr(S, 'TOKEN', None)
            except Exception:
                pass
        if token:
            token = str(token).strip().strip('"').strip("'")
        if not token:
            return self._app_asset_map
        url = f'https://discord.com/api/v9/oauth2/applications/{app_id}/assets'
        headers = {'Authorization': str(token).strip().strip('"'), 'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as r:
                    if r.status != 200:
                        body = await r.text()
                        print(f'[RPC] assets list {r.status}: {body[:150]}')
                        return self._app_asset_map
                    data = await r.json()
            mapping = {}
            if isinstance(data, list):
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    aid = str(item.get("id") or '')
                    name = str(item.get("name") or '').lower()
                    if aid:
                        mapping[aid] = aid
                    if name:
                        mapping[name] = aid
                        mapping[name.replace(' ', '_')] = aid
            self._app_asset_map = mapping
            self._app_assets_loaded = True
            print(f'[RPC] loaded {(len(data) if isinstance(data, list) else 0)} portal assets for app {app_id}')
            for k, v in list(mapping.items())[:12]:
                if k != v:
                    print(f'[RPC]   asset {k!r} -> id {v}')
        except Exception as e:
            print(f'[RPC] load assets: {e}')
        return self._app_asset_map

    def _resolve_portal_asset(self, key: str) -> str:
        if not key:
            return key
        k = str(key).strip()
        if k.startswith('http') or k.startswith('mp:') or ':' in k:
            return k
        k2 = k.lower().replace(' ', '_')
        m = self._app_asset_map or {}
        if k2 in m:
            return m[k2]
        if k in m:
            return m[k]
        return k2

    async def prepare_rpc_image(self, image_url: str, size: int=512):
        import io
        try:
            from PIL import Image
        except ImportError:
            print('[RPC] Pillow missing - pip install Pillow')
            return None
        try:
            timeout = aiohttp.ClientTimeout(total=25)
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/155.0.0.0 Safari/537.36', 'Accept': 'image/*,*/*'}
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url, headers=headers, timeout=timeout) as r:
                    if r.status != 200:
                        alts = []
                        u = image_url
                        if 'cdn.discordapp.com' in u:
                            alts.append(u.replace('cdn.discordapp.com', 'media.discordapp.net'))
                        if '?' in u:
                            alts.append(u.split('?')[0])
                        got = None
                        for alt in alts:
                            try:
                                async with session.get(alt, headers=headers, timeout=timeout) as r2:
                                    if r2.status == 200:
                                        got = await r2.read()
                                        print(f'[RPC] image download via alt {r2.status}')
                                        break
                            except Exception:
                                pass
                        if got is None:
                            print(f'[RPC] image download {r.status}')
                            return None
                        raw = got
                    else:
                        raw = await r.read()
            img = Image.open(io.BytesIO(raw))
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGBA')
            w, h = img.size
            side = min(w, h)
            left = (w - side) // 2
            top = (h - side) // 2
            img = img.crop((left, top, left + side, top + side))
            img = img.resize((size, size), getattr(Image, 'Resampling', Image).LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS)
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            buf = io.BytesIO()
            img.save(buf, format='PNG', optimize=True)
            buf.seek(0)
            print(f'[RPC] resized {w}x{h} → {size}x{size} ({buf.getbuffer().nbytes} bytes)')
            return buf
        except Exception as e:
            print(f'[RPC] prepare_rpc_image: {e}')
            return None

    async def rehost_resized(self, channel, image_url: str, size: int=512):
        buf = await self.prepare_rpc_image(image_url, size=size)
        if buf is None:
            return None
        try:
            file = discord.File(buf, filename=f'rpc_{size}.png')
            msg = await channel.send(file=file)
            if not msg.attachments:
                try:
                    await msg.delete()
                except Exception:
                    pass
                return None
            cdn = msg.attachments[0].url
            try:
                await msg.delete()
            except Exception:
                pass
            print(f'[RPC] rehosted CDN {cdn[:80]}')
            return cdn
        except Exception as e:
            print(f'[RPC] rehost: {e}')
            return None

    async def upload_asset(self, image_url: str, app_id: int | None=None):
        if not image_url:
            return None
        image_url = str(image_url).strip()
        app_id = int(app_id or DEFAULT_APP_ID)
        cache_key = f'{app_id}:{image_url}'
        if cache_key in self._asset_cache:
            return self._asset_cache[cache_key]
        if image_url in self._asset_cache and (not image_url.startswith('http')):
            return self._asset_cache[image_url]
        low = image_url.lower()
        for pref in ('spotify:', 'youtube:', 'twitch:', 'mp:external/'):
            if low.startswith(pref):
                self._asset_cache[cache_key] = image_url
                return image_url
        if low in ('spotify', 'youtube', 'twitch', 'xbox', 'playstation', 'ps5', 'ps4', 'crunchyroll', 'vrchat', 'game'):
            self._asset_cache[cache_key] = low
            return low
        if image_url.startswith('mp:external/') or image_url.startswith('external/'):
            key = image_url if image_url.startswith('mp:') else f'mp:{image_url}'
            self._asset_cache[cache_key] = key
            return key
        if not low.startswith('http://') and (not low.startswith('https://')) and (not low.startswith('mp:')):
            key = low.replace(' ', '_')
            for ext in ('.png', '.jpg', '.jpeg', '.gif', '.webp'):
                if key.endswith(ext):
                    key = key[:-len(ext)]
            try:
                await self._load_app_assets()
            except Exception:
                pass
            key = self._resolve_portal_asset(key)
            self._asset_cache[cache_key] = key
            print(f'[RPC] portal -> {key}')
            return key
        source = image_url
        if image_url.startswith('mp:attachments/'):
            source = 'https://cdn.discordapp.com/attachments/' + image_url[len('mp:attachments/'):]
        if 'cdn.discordapp.com' in source or 'media.discordapp.net' in source:
            if '?' in source:
                base = source.split('?')[0]
                source = base

        async def _parse_external(data, src):
            key = None
            if isinstance(data, list) and data:
                item = data[0]
                if isinstance(item, dict):
                    key = item.get("external_asset_path") or item.get("path")
                elif isinstance(item, str):
                    key = item
            elif isinstance(data, dict):
                key = data.get(src) or data.get(image_url)
                if isinstance(key, dict):
                    key = key.get("external_asset_path") or key.get("path")
                if not key:
                    for v in data.values():
                        if isinstance(v, dict) and (v.get("external_asset_path") or v.get("path")):
                            key = v.get("external_asset_path") or v.get("path")
                            break
                        if isinstance(v, str) and ('external' in v or v.startswith('mp:')):
                            key = v
                            break
            if not key:
                return None
            key = str(key)
            if not key.startswith('mp:'):
                key = f'mp:{key}'
            while key.startswith('mp:mp:'):
                key = key[3:]
            self._asset_cache[cache_key] = key
            self._asset_cache[image_url] = key
            print(f'[RPC] external -> {key[:80]}')
            return key
        if hasattr(self.bot, 'proxy_external_application_assets'):
            try:
                mapped = await self.bot.proxy_external_application_assets(app_id, source)
                key = await _parse_external(mapped, source)
                if key:
                    return key
            except Exception as e:
                print(f'[RPC] proxy_external_application_assets: {e}')
        if hasattr(self.bot, 'proxy_external_assets'):
            try:
                mapped = await self.bot.proxy_external_assets(app_id, [source])
                key = await _parse_external(mapped, source)
                if key:
                    return key
            except Exception as e:
                print(f'[RPC] proxy_external_assets: {e}')
        try:
            token = getattr(getattr(self.bot, 'http', None), 'token', None) or getattr(S, 'TOKEN', None)
            if token:
                token = str(token).strip().strip('"').strip("'")
                headers = {'Authorization': token, 'Content-Type': 'application/json', 'User-Agent': getattr(S, 'USER_AGENT', 'Mozilla/5.0')}
                if getattr(S, 'X_SUPER_PROPERTIES', ''):
                    headers['X-Super-Properties'] = S.X_SUPER_PROPERTIES
                async with aiohttp.ClientSession() as session:
                    async with session.post(f'https://discord.com/api/v9/applications/{app_id}/external-assets', headers=headers, json={'urls': [source]}, timeout=aiohttp.ClientTimeout(total=25)) as r:
                        body = await r.text()
                        if r.status in (200, 201):
                            try:
                                data = __import__('json').loads(body)
                            except Exception:
                                data = None
                            key = await _parse_external(data, source)
                            if key:
                                return key
                        else:
                            print(f'[RPC] external-assets {r.status}: {body[:160]}')
                            if 'cdn.discordapp.com' in source:
                                alt = source.replace('cdn.discordapp.com', 'media.discordapp.net')
                                async with session.post(f'https://discord.com/api/v9/applications/{app_id}/external-assets', headers=headers, json={'urls': [alt]}, timeout=aiohttp.ClientTimeout(total=25)) as r2:
                                    body2 = await r2.text()
                                    if r2.status in (200, 201):
                                        try:
                                            data2 = __import__('json').loads(body2)
                                        except Exception:
                                            data2 = None
                                        key = await _parse_external(data2, alt)
                                        if key:
                                            return key
        except Exception as e:
            print(f'[RPC] external-assets http: {e}')
        print(f'[RPC] fallback raw URL (library may proxy): {source[:80]}')
        self._asset_cache[cache_key] = source
        return source

    async def build_spotify(self, parts: list):
        if len(parts) < 2:
            return None
        song, artist = (parts[0], parts[1])
        album = parts[2] if len(parts) > 2 else song
        duration = float(parts[3]) if len(parts) > 3 else 3.5
        position = float(parts[4]) if len(parts) > 4 else 0.0
        current_ms = int(position * 60 * 1000)
        total_ms = int(duration * 60 * 1000)
        now = int(time.time() * 1000)
        sid = '09xhawlPUifhftf8zuie7w'
        return {'type': 2, 'name': 'Spotify', 'details': song, 'state': artist, 'timestamps': {'start': now - current_ms, 'end': now - current_ms + (total_ms - current_ms)}, 'application_id': '3201606009684', 'sync_id': sid, 'session_id': f'spotify:{sid}', 'party': {'id': f'spotify:{sid}', 'size': [1, 1]}, 'secrets': {'join': f'spotify:{sid}', 'spectate': f'spotify:{sid}', 'match': f'spotify:{sid}'}, 'instance': True, 'flags': 48, 'metadata': {'context_uri': f'spotify:album:{sid}', 'album_id': sid, 'artist_ids': ['0HPG2EIdGCP6gjXW0KzrJq', '0qc4bfxcwRFZfevTck4fOi'], 'track_id': sid}, 'assets': {'large_image': 'spotify', 'large_text': f'{album} on Spotify'}}

    async def build_youtube(self, parts: list):
        if len(parts) < 2:
            return None
        video, channel = (parts[0], parts[1])
        duration = float(parts[2]) if len(parts) > 2 else 5.0
        position = float(parts[3]) if len(parts) > 3 else 0.0
        current_ms = int(position * 60 * 1000)
        total_ms = int(duration * 60 * 1000)
        now = int(time.time() * 1000)
        return {'type': 3, 'name': 'YouTube', 'details': video, 'state': channel, 'timestamps': {'start': now - current_ms, 'end': now - current_ms + (total_ms - current_ms)}, 'application_id': '111299001912', 'assets': {'large_image': 'youtube', 'large_text': f'{video} on YouTube'}}

    async def build_xbox(self, parts: list):
        game = (parts[0] if parts else 'Xbox')[:128]
        activity = {'type': 0, 'name': game, 'application_id': 438122941302046720, 'platform': 'xbox', 'timestamps': {'start': int(time.time() * 1000)}, 'assets': {'large_text': game[:32]}}
        if len(parts) > 1 and parts[1]:
            activity['details'] = parts[1][:128]
        if len(parts) > 2 and parts[2]:
            activity['state'] = parts[2][:128]
        return activity

    async def build_playstation(self, parts: list, ps4: bool=False):
        game = (parts[0] if parts else 'PlayStation')[:128]
        return {'type': 0, 'name': game, 'application_id': 1001158269215858728, 'platform': ('ps4' if ps4 else 'ps5'), 'timestamps': {'start': int(time.time() * 1000)}, 'assets': {'large_text': game[:32]}, **({'details': parts[1][:128]} if len(parts) > 1 and parts[1] else {}), **({'state': parts[2][:128]} if len(parts) > 2 and parts[2] else {})}



    async def build_twitch(self, parts: list):
        title = (parts[0] if parts else 'Twitch')[:128]
        streamer = (parts[1] if len(parts) > 1 else title)[:128]
        return {
            'type': 1,
            'name': 'Twitch',
            'details': title,
            'state': streamer,
            'url': 'https://twitch.tv/%s' % (re.sub(r'[^a-zA-Z0-9_]', '', streamer)[:25] or 'twitch'),
            'application_id': 880988207033802783,
            'timestamps': {'start': int(time.time() * 1000)},
            'assets': {'large_text': title[:32]},
        }

    async def build_valorant(self, parts: list):
        mode = (parts[0] if parts else 'VALORANT')[:128]
        act = {
            'type': 0,
            'name': 'VALORANT',
            'details': mode,
            'application_id': 700785226400399401,
            'timestamps': {'start': int(time.time() * 1000)},
            'assets': {'large_text': mode[:32]},
        }
        if len(parts) > 1 and parts[1]:
            act['state'] = parts[1][:128]
        return act

    async def build_netflix(self, parts: list):
        title = (parts[0] if parts else 'Netflix')[:128]
        return {
            'type': 3,
            'name': 'Netflix',
            'details': title,
            'application_id': 880988207033802783,
            'timestamps': {'start': int(time.time() * 1000)},
            'assets': {'large_text': title[:32]},
            **({'state': parts[1][:128]} if len(parts) > 1 and parts[1] else {}),
        }

    async def build_vscode(self, parts: list):
        file_name = (parts[0] if parts else 'Editing')[:128]
        return {
            'type': 0,
            'name': 'Visual Studio Code',
            'details': 'Editing %s' % file_name,
            'state': (parts[1] if len(parts) > 1 else 'Workspace')[:128],
            'application_id': 383226320970055681,
            'timestamps': {'start': int(time.time() * 1000)},
            'assets': {'large_text': file_name[:32]},
        }


    async def build_league(self, parts: list):
        mode = (parts[0] if parts else 'League of Legends')[:128]
        act = {
            'type': 0,
            'name': 'League of Legends',
            'details': mode,
            'application_id': 401518684763717642,
            'timestamps': {'start': int(time.time() * 1000)},
            'assets': {'large_text': mode[:32]},
        }
        if len(parts) > 1 and parts[1]:
            act['state'] = parts[1][:128]
        if len(parts) > 2 and parts[2]:
            img = parts[2].strip()
            if img.startswith('http'):
                try:
                    key = await self.upload_asset(img)
                    if key:
                        act.setdefault('assets', {})['large_image'] = key
                except Exception:
                    act.setdefault('assets', {})['large_image'] = img
            else:
                act.setdefault('assets', {})['large_image'] = img
        return act

    async def build_roblox(self, parts: list):
        game = (parts[0] if parts else 'Roblox')[:128]
        act = {'type': 0, 'name': game, 'application_id': 963434583335854120, 'timestamps': {'start': int(time.time() * 1000)}, 'assets': {'large_text': game[:32]}}
        if len(parts) > 1 and parts[1]:
            act['details'] = parts[1][:128]
        if len(parts) > 2 and parts[2]:
            act['state'] = parts[2][:128]
        return act

    async def build_minecraft(self, parts: list):
        game = (parts[0] if parts else 'Minecraft')[:128]
        act = {'type': 0, 'name': game, 'application_id': 356875770142195712, 'timestamps': {'start': int(time.time() * 1000)}, 'assets': {'large_text': game[:32]}}
        if len(parts) > 1 and parts[1]:
            act['details'] = parts[1][:128]
        return act

    async def build_fortnite(self, parts: list):
        game = (parts[0] if parts else 'Fortnite')[:128]
        act = {'type': 0, 'name': game, 'application_id': 432980957394370572, 'timestamps': {'start': int(time.time() * 1000)}, 'assets': {'large_text': game[:32]}}
        if len(parts) > 1 and parts[1]:
            act['details'] = parts[1][:128]
        return act

    async def build_crunchyroll(self, parts: list):
        anime = (parts[0] if parts else 'Crunchyroll')[:128]
        logo = 'https://upload.wikimedia.org/wikipedia/commons/thumb/f/f6/Crunchyroll_Logo.svg/512px-Crunchyroll_Logo.svg.png'
        try:
            prox = await self.upload_asset(logo, app_id=int(DEFAULT_APP_ID))
        except Exception:
            prox = logo
        return {'type': 3, 'name': 'Crunchyroll', 'details': anime, 'application_id': int(DEFAULT_APP_ID), 'assets': {'large_image': prox or logo, 'large_text': anime[:32]}}

    async def build_vrchat(self, parts: list, image_url: str=None):
        state = parts[0] if parts else 'Exploring VRChat'
        world = parts[1] if len(parts) > 1 else 'VRChat'
        now = int(time.time() * 1000)
        large_image = None
        if image_url:
            key = await self.upload_asset(image_url)
            if key:
                large_image = key
            else:
                large_image = image_url
        else:
            large_image = 'mp:external/jxAa_-ahC78ilas-ifzE8DX6RyNTI_FV-p2F7HzGhfs/https/www.oculus.com/rich_presence/image/1856672347794301/'
        return {'type': 0, 'name': 'VRChat', 'application_id': '1498387526501535835', 'platform': 'meta_quest', 'state': state, 'timestamps': {'start': now}, 'assets': {'large_image': large_image, 'large_text': world}, 'instance': True}

    @commands.group(name='rpc1', invoke_without_command=True)
    async def rpc1(self, ctx, *, args: str=None):
        if not args:
            await ctx.send(ascii.error('Usage: .rpc1 name <text> | ...'))
            return
        try:
            self._last_ctx_channel = ctx.channel
        except Exception:
            pass
        parsed = self._parse_inline(args)
        if parsed:
            await self._apply_inline(0, parsed)
            await self.apply_activities()
            await ctx.send(ascii.success('RPC1 updated'))

    @rpc1.command(name='name')
    async def rpc1_name(self, ctx, *, name: str):
        self._ensure_slot(0)
        self.rpc_slots[0]['name'] = name
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC1 name: {name}'))

    @rpc1.command(name='details')
    async def rpc1_details(self, ctx, *, details: str=''):
        self._ensure_slot(0)
        if not details or details.strip().lower() in ('clear', 'none', '-', 'off', 'null'):
            self.rpc_slots[0].pop('details', None)
            await self.apply_activities()
            await ctx.send(ascii.success(f'RPC1 details cleared'))
            return
        self.rpc_slots[0]['details'] = details
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC1 details: {details}'))

    @rpc1.command(name='state')
    async def rpc1_state(self, ctx, *, state: str=''):
        self._ensure_slot(0)
        if not state or state.strip().lower() in ('clear', 'none', '-', 'off', 'null'):
            self.rpc_slots[0].pop('state', None)
            await self.apply_activities()
            await ctx.send(ascii.success(f'RPC1 state cleared'))
            return
        self.rpc_slots[0]['state'] = state
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC1 state: {state}'))

    @rpc1.command(name='type')
    async def rpc1_type(self, ctx, activity_type: str):
        t = activity_type.lower()
        if t not in TYPE_MAP:
            await ctx.send(ascii.error('Invalid type'))
            return
        self._ensure_slot(0)
        self.rpc_slots[0]['type'] = TYPE_MAP[t]
        if t == 'purplestream':
            self.rpc_slots[0]['url'] = PURPLESTREAM_URL
        elif 'url' in self.rpc_slots[0] and t not in ('streaming', 'purplestream'):
            del self.rpc_slots[0]['url']
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC1 type: {activity_type}'))

    @rpc1.command(name='platform')
    async def rpc1_platform(self, ctx, preset: str):
        if self._apply_platform_preset(0, preset.lower()):
            await self.apply_activities()
            await ctx.send(ascii.success(f'RPC1 platform: {preset}'))
        else:
            await ctx.send(ascii.error('Unknown platform'))

    @rpc1.command(name='large_image')
    async def rpc1_large_image(self, ctx, url: str):
        self._ensure_slot(0)
        self.rpc_slots[0]['application_id'] = int(DEFAULT_APP_ID)
        src = url
        if str(url).startswith('http'):
            try:
                ch = getattr(self, '_last_ctx_channel', ctx.channel)
                cdn = await self.rehost_resized(ch, url, size=512)
                if cdn:
                    src = cdn
            except Exception as e:
                print(f'[RPC] large resize: {e}')
        key = await self.upload_asset(src)
        if key:
            self.rpc_slots[0].setdefault('assets', {})['large_image'] = key
            await self.apply_activities()
            await ctx.send(ascii.success(f'RPC1 large → `{str(key)[:40]}`'))
        else:
            await ctx.send(ascii.error('large image failed'))

    @rpc1.command(name='small_image')
    async def rpc1_small_image(self, ctx, url: str):
        self._ensure_slot(0)
        self.rpc_slots[0]['application_id'] = int(DEFAULT_APP_ID)
        src = url
        if str(url).startswith('http'):
            try:
                ch = getattr(self, '_last_ctx_channel', ctx.channel)
                cdn = await self.rehost_resized(ch, url, size=512)
                if cdn:
                    src = cdn
            except Exception as e:
                print(f'[RPC] small resize: {e}')
        key = await self.upload_asset(src)
        if key:
            self.rpc_slots[0].setdefault('assets', {})['small_image'] = key
            await self.apply_activities()
            await ctx.send(ascii.success(f'RPC1 small → `{str(key)[:40]}`'))
        else:
            await ctx.send(ascii.error('small image failed'))

    @rpc1.command(name='timestamp')
    async def rpc1_timestamp(self, ctx, value: str):
        self._ensure_slot(0)
        if value.lower() == 'clear':
            self.rpc_slots[0].pop('timestamps', None)
            await ctx.send(ascii.info('RPC1 timestamp cleared'))
        else:
            try:
                self._set_timestamp(0, value)
                await self.apply_activities()
                await ctx.send(ascii.success(f'RPC1 timestamp: {value}'))
            except Exception:
                await ctx.send(ascii.error('Use format: 3600 or 1:00:00'))

    @rpc1.command(name='btn1')
    async def rpc1_btn1(self, ctx, label: str, url: str):
        self._ensure_slot(0)
        btns = self.rpc_slots[0].setdefault('buttons', [])
        entry = {'label': label, 'url': url}
        if not btns:
            btns.append(entry)
        else:
            btns[0] = entry
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC1 btn1: {label}'))

    @rpc1.command(name='btn2')
    async def rpc1_btn2(self, ctx, label: str, url: str):
        self._ensure_slot(0)
        btns = self.rpc_slots[0].setdefault('buttons', [])
        while len(btns) < 2:
            btns.append(None)
        btns[1] = {'label': label, 'url': url}
        self.rpc_slots[0]['buttons'] = [b for b in btns if b]
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC1 btn2: {label}'))

    @rpc1.command(name='spotify')
    async def rpc1_spotify(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['Default', 'Unknown']
        if len(parts) < 2:
            parts.append('Unknown')
        activity = await self.build_spotify(parts)
        if not activity:
            await ctx.send(ascii.error('Format: Song - Artist'))
            return
        self.rpc_slots[0] = activity
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC1 Spotify: {parts[0]}'))

    @rpc1.command(name='youtube')
    async def rpc1_youtube(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['Default Video', 'Default Channel']
        if len(parts) < 2:
            parts.append('Default Channel')
        activity = await self.build_youtube(parts)
        if not activity:
            await ctx.send(ascii.error('Format: Video - Channel'))
            return
        self.rpc_slots[0] = activity
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC1 YouTube: {parts[0]}'))

    @rpc1.command(name='xbox')
    async def rpc1_xbox(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['Xbox']
        self.rpc_slots[0] = await self.build_xbox(parts)
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC1 Xbox: {parts[0]}'))

    @rpc1.command(name='ps')
    async def rpc1_ps(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['PlayStation']
        self.rpc_slots[0] = await self.build_playstation(parts)
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC1 PS: {parts[0]}'))

    @rpc1.command(name='ps4')
    async def rpc1_ps4(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['PS4']
        self.rpc_slots[0] = await self.build_playstation(parts, ps4=True)
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC1 PS4: {parts[0]}'))

    @rpc1.command(name='crunchy')
    async def rpc1_crunchy(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['Crunchyroll']
        self.rpc_slots[0] = await self.build_crunchyroll(parts)
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC1 Crunchyroll: {parts[0]}'))

    @rpc1.command(name='clear')
    async def rpc1_clear(self, ctx):
        self.rpc_slots[0] = None
        await self.apply_activities()
        await ctx.send(ascii.info('RPC1 cleared'))

    @commands.group(name='rpc2', invoke_without_command=True)
    async def rpc2(self, ctx, *, args: str=None):
        if not args:
            await ctx.send(ascii.error('Usage: .rpc2 name <text> | ...'))
            return
        parsed = self._parse_inline(args)
        if parsed:
            await self._apply_inline(1, parsed)
            await self.apply_activities()
            await ctx.send(ascii.success('RPC2 updated'))

    @rpc2.command(name='name')
    async def rpc2_name(self, ctx, *, name: str):
        self._ensure_slot(1)
        self.rpc_slots[1]['name'] = name
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC2 name: {name}'))

    @rpc2.command(name='details')
    async def rpc2_details(self, ctx, *, details: str=''):
        self._ensure_slot(1)
        if not details or details.strip().lower() in ('clear', 'none', '-', 'off', 'null'):
            self.rpc_slots[1].pop('details', None)
            await self.apply_activities()
            await ctx.send(ascii.success(f'RPC2 details cleared'))
            return
        self.rpc_slots[1]['details'] = details
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC2 details: {details}'))

    @rpc2.command(name='state')
    async def rpc2_state(self, ctx, *, state: str=''):
        self._ensure_slot(1)
        if not state or state.strip().lower() in ('clear', 'none', '-', 'off', 'null'):
            self.rpc_slots[1].pop('state', None)
            await self.apply_activities()
            await ctx.send(ascii.success(f'RPC2 state cleared'))
            return
        self.rpc_slots[1]['state'] = state
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC2 state: {state}'))

    @rpc2.command(name='type')
    async def rpc2_type(self, ctx, activity_type: str):
        t = activity_type.lower()
        if t not in TYPE_MAP:
            await ctx.send(ascii.error('Invalid type'))
            return
        self._ensure_slot(1)
        self.rpc_slots[1]['type'] = TYPE_MAP[t]
        if t == 'purplestream':
            self.rpc_slots[1]['url'] = PURPLESTREAM_URL
        elif 'url' in self.rpc_slots[1] and t not in ('streaming', 'purplestream'):
            del self.rpc_slots[1]['url']
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC2 type: {activity_type}'))

    @rpc2.command(name='platform')
    async def rpc2_platform(self, ctx, preset: str):
        if self._apply_platform_preset(1, preset.lower()):
            await self.apply_activities()
            await ctx.send(ascii.success(f'RPC2 platform: {preset}'))
        else:
            await ctx.send(ascii.error('Unknown platform'))

    @rpc2.command(name='large_image')
    async def rpc2_large_image(self, ctx, url: str):
        key = await self.upload_asset(url)
        if key:
            self._ensure_slot(1)
            self.rpc_slots[1].setdefault('assets', {})['large_image'] = key
            await self.apply_activities()
            await ctx.send(ascii.success('RPC2 large image set'))

    @rpc2.command(name='small_image')
    async def rpc2_small_image(self, ctx, url: str):
        key = await self.upload_asset(url)
        if key:
            self._ensure_slot(1)
            self.rpc_slots[1].setdefault('assets', {})['small_image'] = key
            await self.apply_activities()
            await ctx.send(ascii.success('RPC2 small image set'))

    @rpc2.command(name='timestamp')
    async def rpc2_timestamp(self, ctx, value: str):
        self._ensure_slot(1)
        if value.lower() == 'clear':
            self.rpc_slots[1].pop('timestamps', None)
            await ctx.send(ascii.info('RPC2 timestamp cleared'))
        else:
            try:
                self._set_timestamp(1, value)
                await self.apply_activities()
                await ctx.send(ascii.success(f'RPC2 timestamp: {value}'))
            except Exception:
                await ctx.send(ascii.error('Use format: 3600 or 1:00:00'))

    @rpc2.command(name='btn1')
    async def rpc2_btn1(self, ctx, label: str, url: str):
        self._ensure_slot(1)
        btns = self.rpc_slots[1].setdefault('buttons', [])
        entry = {'label': label, 'url': url}
        if not btns:
            btns.append(entry)
        else:
            btns[0] = entry
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC2 btn1: {label}'))

    @rpc2.command(name='btn2')
    async def rpc2_btn2(self, ctx, label: str, url: str):
        self._ensure_slot(1)
        btns = self.rpc_slots[1].setdefault('buttons', [])
        while len(btns) < 2:
            btns.append(None)
        btns[1] = {'label': label, 'url': url}
        self.rpc_slots[1]['buttons'] = [b for b in btns if b]
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC2 btn2: {label}'))

    @rpc2.command(name='spotify')
    async def rpc2_spotify(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['Default', 'Unknown']
        if len(parts) < 2:
            parts.append('Unknown')
        activity = await self.build_spotify(parts)
        if not activity:
            await ctx.send(ascii.error('Format: Song - Artist'))
            return
        self.rpc_slots[1] = activity
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC2 Spotify: {parts[0]}'))

    @rpc2.command(name='youtube')
    async def rpc2_youtube(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['Default Video', 'Default Channel']
        if len(parts) < 2:
            parts.append('Default Channel')
        activity = await self.build_youtube(parts)
        if not activity:
            await ctx.send(ascii.error('Format: Video - Channel'))
            return
        self.rpc_slots[1] = activity
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC2 YouTube: {parts[0]}'))

    @rpc2.command(name='xbox')
    async def rpc2_xbox(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['Xbox']
        self.rpc_slots[1] = await self.build_xbox(parts)
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC2 Xbox: {parts[0]}'))

    @rpc2.command(name='ps')
    async def rpc2_ps(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['PlayStation']
        self.rpc_slots[1] = await self.build_playstation(parts)
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC2 PS: {parts[0]}'))

    @rpc2.command(name='ps4')
    async def rpc2_ps4(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['PS4']
        self.rpc_slots[1] = await self.build_playstation(parts, ps4=True)
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC2 PS4: {parts[0]}'))

    @rpc2.command(name='crunchy')
    async def rpc2_crunchy(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['Crunchyroll']
        self.rpc_slots[1] = await self.build_crunchyroll(parts)
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC2 Crunchyroll: {parts[0]}'))

    @rpc2.command(name='clear')
    async def rpc2_clear(self, ctx):
        self.rpc_slots[1] = None
        await self.apply_activities()
        await ctx.send(ascii.info('RPC2 cleared'))

    @commands.group(name='rpc3', invoke_without_command=True)
    async def rpc3(self, ctx, *, args: str=None):
        if not args:
            await ctx.send(ascii.error('Usage: .rpc3 name <text> | ...'))
            return
        parsed = self._parse_inline(args)
        if parsed:
            await self._apply_inline(2, parsed)
            await self.apply_activities()
            await ctx.send(ascii.success('RPC3 updated'))

    @rpc3.command(name='name')
    async def rpc3_name(self, ctx, *, name: str):
        self._ensure_slot(2)
        self.rpc_slots[2]['name'] = name
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC3 name: {name}'))

    @rpc3.command(name='details')
    async def rpc3_details(self, ctx, *, details: str=''):
        self._ensure_slot(2)
        if not details or details.strip().lower() in ('clear', 'none', '-', 'off', 'null'):
            self.rpc_slots[2].pop('details', None)
            await self.apply_activities()
            await ctx.send(ascii.success(f'RPC3 details cleared'))
            return
        self.rpc_slots[2]['details'] = details
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC3 details: {details}'))

    @rpc3.command(name='state')
    async def rpc3_state(self, ctx, *, state: str=''):
        self._ensure_slot(2)
        if not state or state.strip().lower() in ('clear', 'none', '-', 'off', 'null'):
            self.rpc_slots[2].pop('state', None)
            await self.apply_activities()
            await ctx.send(ascii.success(f'RPC3 state cleared'))
            return
        self.rpc_slots[2]['state'] = state
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC3 state: {state}'))

    @rpc3.command(name='type')
    async def rpc3_type(self, ctx, activity_type: str):
        t = activity_type.lower()
        if t not in TYPE_MAP:
            await ctx.send(ascii.error('Invalid type'))
            return
        self._ensure_slot(2)
        self.rpc_slots[2]['type'] = TYPE_MAP[t]
        if t == 'purplestream':
            self.rpc_slots[2]['url'] = PURPLESTREAM_URL
        elif 'url' in self.rpc_slots[2] and t not in ('streaming', 'purplestream'):
            del self.rpc_slots[2]['url']
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC3 type: {activity_type}'))

    @rpc3.command(name='platform')
    async def rpc3_platform(self, ctx, preset: str):
        if self._apply_platform_preset(2, preset.lower()):
            await self.apply_activities()
            await ctx.send(ascii.success(f'RPC3 platform: {preset}'))
        else:
            await ctx.send(ascii.error('Unknown platform'))

    @rpc3.command(name='large_image')
    async def rpc3_large_image(self, ctx, url: str):
        key = await self.upload_asset(url)
        if key:
            self._ensure_slot(2)
            self.rpc_slots[2].setdefault('assets', {})['large_image'] = key
            await self.apply_activities()
            await ctx.send(ascii.success('RPC3 large image set'))

    @rpc3.command(name='small_image')
    async def rpc3_small_image(self, ctx, url: str):
        key = await self.upload_asset(url)
        if key:
            self._ensure_slot(2)
            self.rpc_slots[2].setdefault('assets', {})['small_image'] = key
            await self.apply_activities()
            await ctx.send(ascii.success('RPC3 small image set'))

    @rpc3.command(name='timestamp')
    async def rpc3_timestamp(self, ctx, value: str):
        self._ensure_slot(2)
        if value.lower() == 'clear':
            self.rpc_slots[2].pop('timestamps', None)
            await ctx.send(ascii.info('RPC3 timestamp cleared'))
        else:
            try:
                self._set_timestamp(2, value)
                await self.apply_activities()
                await ctx.send(ascii.success(f'RPC3 timestamp: {value}'))
            except Exception:
                await ctx.send(ascii.error('Use format: 3600 or 1:00:00'))

    @rpc3.command(name='btn1')
    async def rpc3_btn1(self, ctx, label: str, url: str):
        self._ensure_slot(2)
        btns = self.rpc_slots[2].setdefault('buttons', [])
        entry = {'label': label, 'url': url}
        if not btns:
            btns.append(entry)
        else:
            btns[0] = entry
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC3 btn1: {label}'))

    @rpc3.command(name='btn2')
    async def rpc3_btn2(self, ctx, label: str, url: str):
        self._ensure_slot(2)
        btns = self.rpc_slots[2].setdefault('buttons', [])
        while len(btns) < 2:
            btns.append(None)
        btns[1] = {'label': label, 'url': url}
        self.rpc_slots[2]['buttons'] = [b for b in btns if b]
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC3 btn2: {label}'))

    @rpc3.command(name='spotify')
    async def rpc3_spotify(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['Default', 'Unknown']
        if len(parts) < 2:
            parts.append('Unknown')
        activity = await self.build_spotify(parts)
        if not activity:
            await ctx.send(ascii.error('Format: Song - Artist'))
            return
        self.rpc_slots[2] = activity
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC3 Spotify: {parts[0]}'))

    @rpc3.command(name='youtube')
    async def rpc3_youtube(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['Default Video', 'Default Channel']
        if len(parts) < 2:
            parts.append('Default Channel')
        activity = await self.build_youtube(parts)
        if not activity:
            await ctx.send(ascii.error('Format: Video - Channel'))
            return
        self.rpc_slots[2] = activity
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC3 YouTube: {parts[0]}'))

    @rpc3.command(name='xbox')
    async def rpc3_xbox(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['Xbox']
        self.rpc_slots[2] = await self.build_xbox(parts)
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC3 Xbox: {parts[0]}'))

    @rpc3.command(name='ps')
    async def rpc3_ps(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['PlayStation']
        self.rpc_slots[2] = await self.build_playstation(parts)
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC3 PS: {parts[0]}'))

    @rpc3.command(name='ps4')
    async def rpc3_ps4(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['PS4']
        self.rpc_slots[2] = await self.build_playstation(parts, ps4=True)
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC3 PS4: {parts[0]}'))

    @rpc3.command(name='crunchy')
    async def rpc3_crunchy(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['Crunchyroll']
        self.rpc_slots[2] = await self.build_crunchyroll(parts)
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC3 Crunchyroll: {parts[0]}'))

    @rpc3.command(name='clear')
    async def rpc3_clear(self, ctx):
        self.rpc_slots[2] = None
        await self.apply_activities()
        await ctx.send(ascii.info('RPC3 cleared'))

    @commands.group(name='rpc4', invoke_without_command=True)
    async def rpc4(self, ctx, *, args: str=None):
        if not args:
            await ctx.send(ascii.error('Usage: .rpc4 name <text> | ...'))
            return
        parsed = self._parse_inline(args)
        if parsed:
            await self._apply_inline(3, parsed)
            await self.apply_activities()
            await ctx.send(ascii.success('RPC4 updated'))

    @rpc4.command(name='name')
    async def rpc4_name(self, ctx, *, name: str):
        self._ensure_slot(3)
        self.rpc_slots[3]['name'] = name
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC4 name: {name}'))

    @rpc4.command(name='details')
    async def rpc4_details(self, ctx, *, details: str=''):
        self._ensure_slot(3)
        if not details or details.strip().lower() in ('clear', 'none', '-', 'off', 'null'):
            self.rpc_slots[3].pop('details', None)
            await self.apply_activities()
            await ctx.send(ascii.success(f'RPC4 details cleared'))
            return
        self.rpc_slots[3]['details'] = details
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC4 details: {details}'))

    @rpc4.command(name='state')
    async def rpc4_state(self, ctx, *, state: str=''):
        self._ensure_slot(3)
        if not state or state.strip().lower() in ('clear', 'none', '-', 'off', 'null'):
            self.rpc_slots[3].pop('state', None)
            await self.apply_activities()
            await ctx.send(ascii.success(f'RPC4 state cleared'))
            return
        self.rpc_slots[3]['state'] = state
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC4 state: {state}'))

    @rpc4.command(name='type')
    async def rpc4_type(self, ctx, activity_type: str):
        t = activity_type.lower()
        if t not in TYPE_MAP:
            await ctx.send(ascii.error('Invalid type'))
            return
        self._ensure_slot(3)
        self.rpc_slots[3]['type'] = TYPE_MAP[t]
        if t == 'purplestream':
            self.rpc_slots[3]['url'] = PURPLESTREAM_URL
        elif 'url' in self.rpc_slots[3] and t not in ('streaming', 'purplestream'):
            del self.rpc_slots[3]['url']
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC4 type: {activity_type}'))

    @rpc4.command(name='platform')
    async def rpc4_platform(self, ctx, preset: str):
        if self._apply_platform_preset(3, preset.lower()):
            await self.apply_activities()
            await ctx.send(ascii.success(f'RPC4 platform: {preset}'))
        else:
            await ctx.send(ascii.error('Unknown platform'))

    @rpc4.command(name='large_image')
    async def rpc4_large_image(self, ctx, url: str):
        key = await self.upload_asset(url)
        if key:
            self._ensure_slot(3)
            self.rpc_slots[3].setdefault('assets', {})['large_image'] = key
            await self.apply_activities()
            await ctx.send(ascii.success('RPC4 large image set'))

    @rpc4.command(name='small_image')
    async def rpc4_small_image(self, ctx, url: str):
        key = await self.upload_asset(url)
        if key:
            self._ensure_slot(3)
            self.rpc_slots[3].setdefault('assets', {})['small_image'] = key
            await self.apply_activities()
            await ctx.send(ascii.success('RPC4 small image set'))

    @rpc4.command(name='timestamp')
    async def rpc4_timestamp(self, ctx, value: str):
        self._ensure_slot(3)
        if value.lower() == 'clear':
            self.rpc_slots[3].pop('timestamps', None)
            await ctx.send(ascii.info('RPC4 timestamp cleared'))
        else:
            try:
                self._set_timestamp(3, value)
                await self.apply_activities()
                await ctx.send(ascii.success(f'RPC4 timestamp: {value}'))
            except Exception:
                await ctx.send(ascii.error('Use format: 3600 or 1:00:00'))

    @rpc4.command(name='btn1')
    async def rpc4_btn1(self, ctx, label: str, url: str):
        self._ensure_slot(3)
        btns = self.rpc_slots[3].setdefault('buttons', [])
        entry = {'label': label, 'url': url}
        if not btns:
            btns.append(entry)
        else:
            btns[0] = entry
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC4 btn1: {label}'))

    @rpc4.command(name='btn2')
    async def rpc4_btn2(self, ctx, label: str, url: str):
        self._ensure_slot(3)
        btns = self.rpc_slots[3].setdefault('buttons', [])
        while len(btns) < 2:
            btns.append(None)
        btns[1] = {'label': label, 'url': url}
        self.rpc_slots[3]['buttons'] = [b for b in btns if b]
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC4 btn2: {label}'))

    @rpc4.command(name='spotify')
    async def rpc4_spotify(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['Default', 'Unknown']
        if len(parts) < 2:
            parts.append('Unknown')
        activity = await self.build_spotify(parts)
        if not activity:
            await ctx.send(ascii.error('Format: Song - Artist'))
            return
        self.rpc_slots[3] = activity
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC4 Spotify: {parts[0]}'))

    @rpc4.command(name='youtube')
    async def rpc4_youtube(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['Default Video', 'Default Channel']
        if len(parts) < 2:
            parts.append('Default Channel')
        activity = await self.build_youtube(parts)
        if not activity:
            await ctx.send(ascii.error('Format: Video - Channel'))
            return
        self.rpc_slots[3] = activity
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC4 YouTube: {parts[0]}'))

    @rpc4.command(name='xbox')
    async def rpc4_xbox(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['Xbox']
        self.rpc_slots[3] = await self.build_xbox(parts)
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC4 Xbox: {parts[0]}'))

    @rpc4.command(name='ps')
    async def rpc4_ps(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['PlayStation']
        self.rpc_slots[3] = await self.build_playstation(parts)
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC4 PS: {parts[0]}'))

    @rpc4.command(name='ps4')
    async def rpc4_ps4(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['PS4']
        self.rpc_slots[3] = await self.build_playstation(parts, ps4=True)
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC4 PS4: {parts[0]}'))

    @rpc4.command(name='crunchy')
    async def rpc4_crunchy(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['Crunchyroll']
        self.rpc_slots[3] = await self.build_crunchyroll(parts)
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC4 Crunchyroll: {parts[0]}'))

    @rpc4.command(name='clear')
    async def rpc4_clear(self, ctx):
        self.rpc_slots[3] = None
        await self.apply_activities()
        await ctx.send(ascii.info('RPC4 cleared'))

    @commands.group(name='rpc5', invoke_without_command=True)
    async def rpc5(self, ctx, *, args: str=None):
        if not args:
            await ctx.send(ascii.error('Usage: .rpc5 name <text> | ...'))
            return
        parsed = self._parse_inline(args)
        if parsed:
            await self._apply_inline(4, parsed)
            await self.apply_activities()
            await ctx.send(ascii.success('RPC5 updated'))

    @rpc5.command(name='name')
    async def rpc5_name(self, ctx, *, name: str):
        self._ensure_slot(4)
        self.rpc_slots[4]['name'] = name
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC5 name: {name}'))

    @rpc5.command(name='details')
    async def rpc5_details(self, ctx, *, details: str=''):
        self._ensure_slot(4)
        if not details or details.strip().lower() in ('clear', 'none', '-', 'off', 'null'):
            self.rpc_slots[4].pop('details', None)
            await self.apply_activities()
            await ctx.send(ascii.success(f'RPC5 details cleared'))
            return
        self.rpc_slots[4]['details'] = details
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC5 details: {details}'))

    @rpc5.command(name='state')
    async def rpc5_state(self, ctx, *, state: str=''):
        self._ensure_slot(4)
        if not state or state.strip().lower() in ('clear', 'none', '-', 'off', 'null'):
            self.rpc_slots[4].pop('state', None)
            await self.apply_activities()
            await ctx.send(ascii.success(f'RPC5 state cleared'))
            return
        self.rpc_slots[4]['state'] = state
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC5 state: {state}'))

    @rpc5.command(name='type')
    async def rpc5_type(self, ctx, activity_type: str):
        t = activity_type.lower()
        if t not in TYPE_MAP:
            await ctx.send(ascii.error('Invalid type'))
            return
        self._ensure_slot(4)
        self.rpc_slots[4]['type'] = TYPE_MAP[t]
        if t == 'purplestream':
            self.rpc_slots[4]['url'] = PURPLESTREAM_URL
        elif 'url' in self.rpc_slots[4] and t not in ('streaming', 'purplestream'):
            del self.rpc_slots[4]['url']
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC5 type: {activity_type}'))

    @rpc5.command(name='platform')
    async def rpc5_platform(self, ctx, preset: str):
        if self._apply_platform_preset(4, preset.lower()):
            await self.apply_activities()
            await ctx.send(ascii.success(f'RPC5 platform: {preset}'))
        else:
            await ctx.send(ascii.error('Unknown platform'))

    @rpc5.command(name='large_image')
    async def rpc5_large_image(self, ctx, url: str):
        key = await self.upload_asset(url)
        if key:
            self._ensure_slot(4)
            self.rpc_slots[4].setdefault('assets', {})['large_image'] = key
            await self.apply_activities()
            await ctx.send(ascii.success('RPC5 large image set'))

    @rpc5.command(name='small_image')
    async def rpc5_small_image(self, ctx, url: str):
        key = await self.upload_asset(url)
        if key:
            self._ensure_slot(4)
            self.rpc_slots[4].setdefault('assets', {})['small_image'] = key
            await self.apply_activities()
            await ctx.send(ascii.success('RPC5 small image set'))

    @rpc5.command(name='timestamp')
    async def rpc5_timestamp(self, ctx, value: str):
        self._ensure_slot(4)
        if value.lower() == 'clear':
            self.rpc_slots[4].pop('timestamps', None)
            await ctx.send(ascii.info('RPC5 timestamp cleared'))
        else:
            try:
                self._set_timestamp(4, value)
                await self.apply_activities()
                await ctx.send(ascii.success(f'RPC5 timestamp: {value}'))
            except Exception:
                await ctx.send(ascii.error('Use format: 3600 or 1:00:00'))

    @rpc5.command(name='btn1')
    async def rpc5_btn1(self, ctx, label: str, url: str):
        self._ensure_slot(4)
        btns = self.rpc_slots[4].setdefault('buttons', [])
        entry = {'label': label, 'url': url}
        if not btns:
            btns.append(entry)
        else:
            btns[0] = entry
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC5 btn1: {label}'))

    @rpc5.command(name='btn2')
    async def rpc5_btn2(self, ctx, label: str, url: str):
        self._ensure_slot(4)
        btns = self.rpc_slots[4].setdefault('buttons', [])
        while len(btns) < 2:
            btns.append(None)
        btns[1] = {'label': label, 'url': url}
        self.rpc_slots[4]['buttons'] = [b for b in btns if b]
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC5 btn2: {label}'))

    @rpc5.command(name='spotify')
    async def rpc5_spotify(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['Default', 'Unknown']
        if len(parts) < 2:
            parts.append('Unknown')
        activity = await self.build_spotify(parts)
        if not activity:
            await ctx.send(ascii.error('Format: Song - Artist'))
            return
        self.rpc_slots[4] = activity
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC5 Spotify: {parts[0]}'))

    @rpc5.command(name='youtube')
    async def rpc5_youtube(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['Default Video', 'Default Channel']
        if len(parts) < 2:
            parts.append('Default Channel')
        activity = await self.build_youtube(parts)
        if not activity:
            await ctx.send(ascii.error('Format: Video - Channel'))
            return
        self.rpc_slots[4] = activity
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC5 YouTube: {parts[0]}'))

    @rpc5.command(name='xbox')
    async def rpc5_xbox(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['Xbox']
        self.rpc_slots[4] = await self.build_xbox(parts)
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC5 Xbox: {parts[0]}'))

    @rpc5.command(name='ps')
    async def rpc5_ps(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['PlayStation']
        self.rpc_slots[4] = await self.build_playstation(parts)
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC5 PS: {parts[0]}'))

    @rpc5.command(name='ps4')
    async def rpc5_ps4(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['PS4']
        self.rpc_slots[4] = await self.build_playstation(parts, ps4=True)
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC5 PS4: {parts[0]}'))

    @rpc5.command(name='crunchy')
    async def rpc5_crunchy(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['Crunchyroll']
        self.rpc_slots[4] = await self.build_crunchyroll(parts)
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC5 Crunchyroll: {parts[0]}'))

    @rpc5.command(name='clear')
    async def rpc5_clear(self, ctx):
        self.rpc_slots[4] = None
        await self.apply_activities()
        await ctx.send(ascii.info('RPC5 cleared'))

    @commands.group(name='rpc6', invoke_without_command=True)
    async def rpc6(self, ctx, *, args: str=None):
        if not args:
            await ctx.send(ascii.error('Usage: .rpc6 name <text> | ...'))
            return
        parsed = self._parse_inline(args)
        if parsed:
            await self._apply_inline(5, parsed)
            await self.apply_activities()
            await ctx.send(ascii.success('RPC6 updated'))

    @rpc6.command(name='name')
    async def rpc6_name(self, ctx, *, name: str):
        self._ensure_slot(5)
        self.rpc_slots[5]['name'] = name
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC6 name: {name}'))

    @rpc6.command(name='details')
    async def rpc6_details(self, ctx, *, details: str=''):
        self._ensure_slot(5)
        if not details or details.strip().lower() in ('clear', 'none', '-', 'off', 'null'):
            self.rpc_slots[5].pop('details', None)
            await self.apply_activities()
            await ctx.send(ascii.success(f'RPC6 details cleared'))
            return
        self.rpc_slots[5]['details'] = details
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC6 details: {details}'))

    @rpc6.command(name='state')
    async def rpc6_state(self, ctx, *, state: str=''):
        self._ensure_slot(5)
        if not state or state.strip().lower() in ('clear', 'none', '-', 'off', 'null'):
            self.rpc_slots[5].pop('state', None)
            await self.apply_activities()
            await ctx.send(ascii.success(f'RPC6 state cleared'))
            return
        self.rpc_slots[5]['state'] = state
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC6 state: {state}'))

    @rpc6.command(name='type')
    async def rpc6_type(self, ctx, activity_type: str):
        t = activity_type.lower()
        if t not in TYPE_MAP:
            await ctx.send(ascii.error('Invalid type'))
            return
        self._ensure_slot(5)
        self.rpc_slots[5]['type'] = TYPE_MAP[t]
        if t == 'purplestream':
            self.rpc_slots[5]['url'] = PURPLESTREAM_URL
        elif 'url' in self.rpc_slots[5] and t not in ('streaming', 'purplestream'):
            del self.rpc_slots[5]['url']
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC6 type: {activity_type}'))

    @rpc6.command(name='platform')
    async def rpc6_platform(self, ctx, preset: str):
        if self._apply_platform_preset(5, preset.lower()):
            await self.apply_activities()
            await ctx.send(ascii.success(f'RPC6 platform: {preset}'))
        else:
            await ctx.send(ascii.error('Unknown platform'))

    @rpc6.command(name='large_image')
    async def rpc6_large_image(self, ctx, url: str):
        key = await self.upload_asset(url)
        if key:
            self._ensure_slot(5)
            self.rpc_slots[5].setdefault('assets', {})['large_image'] = key
            await self.apply_activities()
            await ctx.send(ascii.success('RPC6 large image set'))

    @rpc6.command(name='small_image')
    async def rpc6_small_image(self, ctx, url: str):
        key = await self.upload_asset(url)
        if key:
            self._ensure_slot(5)
            self.rpc_slots[5].setdefault('assets', {})['small_image'] = key
            await self.apply_activities()
            await ctx.send(ascii.success('RPC6 small image set'))

    @rpc6.command(name='timestamp')
    async def rpc6_timestamp(self, ctx, value: str):
        self._ensure_slot(5)
        if value.lower() == 'clear':
            self.rpc_slots[5].pop('timestamps', None)
            await ctx.send(ascii.info('RPC6 timestamp cleared'))
        else:
            try:
                self._set_timestamp(5, value)
                await self.apply_activities()
                await ctx.send(ascii.success(f'RPC6 timestamp: {value}'))
            except Exception:
                await ctx.send(ascii.error('Use format: 3600 or 1:00:00'))

    @rpc6.command(name='btn1')
    async def rpc6_btn1(self, ctx, label: str, url: str):
        self._ensure_slot(5)
        btns = self.rpc_slots[5].setdefault('buttons', [])
        entry = {'label': label, 'url': url}
        if not btns:
            btns.append(entry)
        else:
            btns[0] = entry
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC6 btn1: {label}'))

    @rpc6.command(name='btn2')
    async def rpc6_btn2(self, ctx, label: str, url: str):
        self._ensure_slot(5)
        btns = self.rpc_slots[5].setdefault('buttons', [])
        while len(btns) < 2:
            btns.append(None)
        btns[1] = {'label': label, 'url': url}
        self.rpc_slots[5]['buttons'] = [b for b in btns if b]
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC6 btn2: {label}'))

    @rpc6.command(name='spotify')
    async def rpc6_spotify(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['Default', 'Unknown']
        if len(parts) < 2:
            parts.append('Unknown')
        activity = await self.build_spotify(parts)
        if not activity:
            await ctx.send(ascii.error('Format: Song - Artist'))
            return
        self.rpc_slots[5] = activity
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC6 Spotify: {parts[0]}'))

    @rpc6.command(name='youtube')
    async def rpc6_youtube(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['Default Video', 'Default Channel']
        if len(parts) < 2:
            parts.append('Default Channel')
        activity = await self.build_youtube(parts)
        if not activity:
            await ctx.send(ascii.error('Format: Video - Channel'))
            return
        self.rpc_slots[5] = activity
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC6 YouTube: {parts[0]}'))

    @rpc6.command(name='xbox')
    async def rpc6_xbox(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['Xbox']
        self.rpc_slots[5] = await self.build_xbox(parts)
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC6 Xbox: {parts[0]}'))

    @rpc6.command(name='ps')
    async def rpc6_ps(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['PlayStation']
        self.rpc_slots[5] = await self.build_playstation(parts)
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC6 PS: {parts[0]}'))

    @rpc6.command(name='ps4')
    async def rpc6_ps4(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['PS4']
        self.rpc_slots[5] = await self.build_playstation(parts, ps4=True)
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC6 PS4: {parts[0]}'))

    @rpc6.command(name='crunchy')
    async def rpc6_crunchy(self, ctx, *, args: str=None):
        parts = [p.strip() for p in args.split('-')] if args else ['Crunchyroll']
        self.rpc_slots[5] = await self.build_crunchyroll(parts)
        await self.apply_activities()
        await ctx.send(ascii.success(f'RPC6 Crunchyroll: {parts[0]}'))

    @rpc6.command(name='clear')
    async def rpc6_clear(self, ctx):
        self.rpc_slots[5] = None
        await self.apply_activities()
        await ctx.send(ascii.info('RPC6 cleared'))

    @commands.command(name='playing')
    async def playing_cmd(self, ctx, *, message=None):
        await ctx.message.delete()
        if not message:
            await ctx.send(ascii.error('Usage: .playing <text>'))
            return
        await self.bot.change_presence(activity=discord.Game(name=message))
        await ctx.send(ascii.success(f'Playing: {message}'))

    @commands.command(aliases=['listen'])
    async def listening_cmd(self, ctx, *, message=None):
        await ctx.message.delete()
        if not message:
            await ctx.send(ascii.error('Usage: .listening <text>'))
            return
        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=message))
        await ctx.send(ascii.success(f'Listening: {message}'))

    @commands.command(aliases=['watch'])
    async def watching_cmd(self, ctx, *, message=None):
        await ctx.message.delete()
        if not message:
            await ctx.send(ascii.error('Usage: .watching <text>'))
            return
        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=message))
        await ctx.send(ascii.success(f'Watching: {message}'))

    @commands.command(name='competing')
    async def competing_cmd(self, ctx, *, message=None):
        await ctx.message.delete()
        if not message:
            await ctx.send(ascii.error('Usage: .competing <text>'))
            return
        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.competing, name=message))
        await ctx.send(ascii.success(f'Competing: {message}'))

    @commands.command(name='stopactivity')
    async def stopactivity_cmd(self, ctx):
        await ctx.message.delete()
        await self.bot.change_presence(activity=None, status=discord.Status.online)
        await ctx.send(ascii.info('Activity cleared'))

    @commands.command(name='rpcstatus', aliases=['rpcs'])
    async def rpcstatus_cmd(self, ctx, status_type: str):
        await ctx.message.delete()
        status_map = {'online': discord.Status.online, 'dnd': discord.Status.dnd, 'idle': discord.Status.idle, 'invisible': discord.Status.invisible}
        if status_type.lower() in status_map:
            await self.bot.change_presence(status=status_map[status_type.lower()])
            await ctx.send(ascii.success(f'Status: {status_type}'))
        else:
            await ctx.send(ascii.error('Use: online, dnd, idle, invisible'))

    @commands.command(name='aoff')
    async def aoff_cmd(self, ctx):
        await self.bot.change_presence(activity=None)
        await ctx.message.delete()

    @commands.command(name='clear_multi_rpc')
    async def clear_multi_rpc(self, ctx):
        self._clearing = True
        self.rpc_slots = [None] * 6
        await self.bot.ws.send(json.dumps({'op': 3, 'd': {'since': 0, 'activities': [], 'status': 'online', 'afk': False}}))
        self._save_rpc_slots()
        self._clearing = False
        await ctx.send(ascii.info('Cleared all RPC slots'))

    @commands.command(name='rpc_status')
    async def rpc_status(self, ctx):
        type_names = {0: 'Playing', 1: 'Streaming', 2: 'Listening', 3: 'Watching', 5: 'Competing'}
        lines = []
        for i, act in enumerate(self.rpc_slots):
            if act is None:
                lines.append(f'\x1b[2;37mRPC{i + 1} - empty\x1b[0m')
            else:
                t = act.get('type', 0)
                label = type_names.get(t, 'Unknown')
                lines.append(f'\x1b[2;37mRPC{i + 1} [{label}] {act.get("name", "-")} | {act.get("details", "-")} | {act.get("state", "-")}\x1b[0m')
        await ctx.send(ascii.multiline(lines, raw=True))

    @commands.command(name='spotify')
    async def cmd_spotify(self, ctx, *, args: str=None):
        if not args:
            await ctx.send(ascii.error('Usage: .spotify Song - Artist [slot 1-6]'))
            return
        words = args.strip().split()
        slot = 0
        if words and words[-1] in ('1', '2', '3', '4', '5', '6'):
            slot = int(words[-1]) - 1
            args = ' '.join(words[:-1])
        parts = [p.strip() for p in args.split('-')]
        if len(parts) < 2:
            parts.append('Unknown')
        activity = await self.build_spotify(parts)
        if not activity:
            await ctx.send(ascii.error('Format: Song - Artist'))
            return
        self.rpc_slots[slot] = activity
        await self.apply_activities()
        await ctx.send(ascii.success(f'Spotify → slot {slot + 1}: {parts[0]}'))

    @commands.command(name='youtube')
    async def cmd_youtube(self, ctx, *, args: str=None):
        if not args:
            await ctx.send(ascii.error('Usage: .youtube Video - Channel [slot 1-6]'))
            return
        words = args.strip().split()
        slot = 0
        if words and words[-1] in ('1', '2', '3', '4', '5', '6'):
            slot = int(words[-1]) - 1
            args = ' '.join(words[:-1])
        parts = [p.strip() for p in args.split('-')]
        if len(parts) < 2:
            parts.append('Default Channel')
        activity = await self.build_youtube(parts)
        if not activity:
            await ctx.send(ascii.error('Format: Video - Channel'))
            return
        self.rpc_slots[slot] = activity
        await self.apply_activities()
        await ctx.send(ascii.success(f'YouTube → slot {slot + 1}: {parts[0]}'))




    def _set_activity_timer(self, slot: int, seconds: float, mode: str='elapsed'):
        self._ensure_slot(slot)
        now = time.time()
        if mode in ('elapsed', 'start'):
            self.rpc_slots[slot]['timestamps'] = {'start': int(now * 1000)}
        elif mode in ('clear', 'off'):
            self.rpc_slots[slot].pop('timestamps', None)
        else:
            self.rpc_slots[slot]['timestamps'] = {
                'start': int(now * 1000),
                'end': int((now + max(1.0, seconds)) * 1000),
            }

    def _parse_slot_duration(self, args, default_secs=3600):
        slot = 0
        secs = float(default_secs)
        items = list(args) if args else []
        if items and items[0].isdigit() and len(items[0]) == 1:
            slot = max(0, min(5, int(items[0]) - 1))
            items = items[1:]
        if items:
            raw = ''.join(items).strip().lower()
            if raw.endswith('h'):
                secs = float(raw[:-1] or 1) * 3600
            elif raw.endswith('m'):
                secs = float(raw[:-1] or 1) * 60
            elif raw.endswith('s'):
                secs = float(raw[:-1] or 1)
            elif ':' in raw:
                secs = self._parse_timestamp_value(raw)
            else:
                try:
                    secs = float(raw)
                    if secs <= 180:
                        secs = secs * 60
                except Exception:
                    secs = float(default_secs)
        return slot, max(1.0, secs)

    @commands.command(name='league', aliases=['lol', 'riot'])
    async def cmd_league(self, ctx, *, args: str=None):
        parts = [p.strip() for p in (args or "Summoner's Rift - Ranked Solo").split('-')]
        self.rpc_slots[0] = await self.build_league(parts)
        await self.apply_activities()
        await ctx.send(ascii.success('League of Legends → %s' % parts[0]))

    @commands.command(name='playtime', aliases=['rpcplay', 'playingtime'])
    async def cmd_playtime(self, ctx, *args):
        slot, secs = self._parse_slot_duration(args, default_secs=3600)
        self._ensure_slot(slot)
        self.rpc_slots[slot]['type'] = 0
        self._set_activity_timer(slot, secs, 'playing')
        await self.apply_activities()
        await ctx.send(ascii.success('play timer slot %d → %ss' % (slot + 1, int(secs))))

    @commands.command(name='watchtime', aliases=['rpcwatch', 'watchingtime'])
    async def cmd_watchtime(self, ctx, *args):
        slot, secs = self._parse_slot_duration(args, default_secs=3600)
        self._ensure_slot(slot)
        self.rpc_slots[slot]['type'] = 3
        self._set_activity_timer(slot, secs, 'watching')
        await self.apply_activities()
        await ctx.send(ascii.success('watch timer slot %d → %ss' % (slot + 1, int(secs))))

    @commands.command(name='listentime', aliases=['rpclisten', 'listeningtime'])
    async def cmd_listentime(self, ctx, *args):
        slot, secs = self._parse_slot_duration(args, default_secs=210)
        self._ensure_slot(slot)
        self.rpc_slots[slot]['type'] = 2
        self._set_activity_timer(slot, secs, 'listening')
        await self.apply_activities()
        await ctx.send(ascii.success('listen timer slot %d → %ss' % (slot + 1, int(secs))))

    @commands.command(name='rpcpreset', aliases=['preset'])
    async def cmd_rpcpreset(self, ctx, action: str=None, key: str=None, *, rest: str=None):
        action = (action or 'list').lower()
        if action in ('list', 'ls'):
            keys = sorted(_all_presets().keys())
            custom = sorted(_RUNTIME_PRESETS.keys())
            msg = 'presets (%d): %s' % (len(keys), ', '.join(keys))
            if custom:
                msg += '\ncustom: ' + ', '.join(custom)
            return await ctx.send(ascii.success(msg))
        if action in ('get', 'show') and key:
            p = _all_presets().get(key.lower())
            if not p:
                return await ctx.send(ascii.error('unknown preset'))
            return await ctx.send(ascii.success('%s → %s' % (key.lower(), json.dumps(p))))
        if action in ('del', 'rm', 'delete') and key:
            k = key.lower()
            if k in _RUNTIME_PRESETS:
                _RUNTIME_PRESETS.pop(k, None)
                _save_custom_presets()
                return await ctx.send(ascii.success('deleted custom preset %s' % k))
            return await ctx.send(ascii.error('only custom presets can be deleted'))
        if action in ('set', 'add', 'save') and key:
            k = key.lower()
            preset = {}
            blob = rest or ''
            for part in blob.split():
                if ':' in part:
                    a, b = part.split(':', 1)
                    a = a.lower()
                    if a in ('app', 'application_id', 'appid'):
                        try:
                            preset['application_id'] = int(b)
                        except Exception:
                            preset['application_id'] = b
                    elif a == 'type':
                        try:
                            preset['type'] = int(b)
                        except Exception:
                            preset['type'] = TYPE_MAP.get(b.lower(), 0)
                    elif a == 'platform':
                        preset['platform'] = b
                    elif a == 'name':
                        preset['name'] = b.replace('_', ' ')
                    elif a == 'asset':
                        preset['asset'] = b
            if 'name' not in preset:
                preset['name'] = k
            if 'type' not in preset:
                preset['type'] = 0
            _RUNTIME_PRESETS[k] = preset
            _save_custom_presets()
            return await ctx.send(ascii.success('saved preset %s → %s' % (k, json.dumps(preset))))
        return await ctx.send(ascii.error('rpcpreset list|get <k>|set <k> app:ID name:Name type:0|del <k>'))

    @commands.command(name='twitch', aliases=['ttv'])
    async def cmd_twitch(self, ctx, *, args: str=None):
        parts = [p.strip() for p in (args or 'Live - streamer').split('-')]
        act = await self.build_twitch(parts)
        self.rpc_slots[0] = act
        await self.apply_activities()
        await ctx.send(ascii.success('Twitch → %s' % (parts[0] if parts else 'Live')))

    @commands.command(name='valorant', aliases=['val'])
    async def cmd_valorant(self, ctx, *, args: str=None):
        parts = [p.strip() for p in (args or 'Competitive').split('-')]
        self.rpc_slots[0] = await self.build_valorant(parts)
        await self.apply_activities()
        await ctx.send(ascii.success('VALORANT → %s' % parts[0]))

    @commands.command(name='netflix')
    async def cmd_netflix(self, ctx, *, args: str=None):
        parts = [p.strip() for p in (args or 'Watching').split('-')]
        self.rpc_slots[0] = await self.build_netflix(parts)
        await self.apply_activities()
        await ctx.send(ascii.success('Netflix → %s' % parts[0]))

    @commands.command(name='vscode', aliases=['code', 'vsc'])
    async def cmd_vscode(self, ctx, *, args: str=None):
        parts = [p.strip() for p in (args or 'file.py - wilt').split('-')]
        self.rpc_slots[0] = await self.build_vscode(parts)
        await self.apply_activities()
        await ctx.send(ascii.success('VS Code → %s' % parts[0]))

    @commands.command(name='platforms', aliases=['rpcplatforms', 'rpcpresets'])
    async def cmd_platforms(self, ctx):
        keys = sorted(_all_presets().keys())
        await ctx.send(ascii.success('platforms: ' + ', '.join(keys)))

    @commands.command(name='roblox', aliases=['rbx'])
    async def cmd_roblox(self, ctx, *, args: str=None):
        parts = [p.strip() for p in (args or 'Roblox').split('-')]
        self.rpc_slots[0] = await self.build_roblox(parts)
        await self.apply_activities()
        await ctx.send(ascii.success('Roblox → %s' % parts[0]))

    @commands.command(name='minecraft', aliases=['mc'])
    async def cmd_minecraft(self, ctx, *, args: str=None):
        parts = [p.strip() for p in (args or 'Minecraft').split('-')]
        self.rpc_slots[0] = await self.build_minecraft(parts)
        await self.apply_activities()
        await ctx.send(ascii.success('Minecraft → %s' % parts[0]))

    @commands.command(name='fortnite', aliases=['fn'])
    async def cmd_fortnite(self, ctx, *, args: str=None):
        parts = [p.strip() for p in (args or 'Fortnite').split('-')]
        self.rpc_slots[0] = await self.build_fortnite(parts)
        await self.apply_activities()
        await ctx.send(ascii.success('Fortnite → %s' % parts[0]))

    @commands.command(name='xbox')
    async def cmd_xbox(self, ctx, *, args: str=None):
        words = args.strip().split() if args else []
        slot = 0
        if words and words[-1] in ('1', '2', '3', '4', '5', '6'):
            slot = int(words[-1]) - 1
            args = ' '.join(words[:-1]) if len(words) > 1 else None
        parts = [p.strip() for p in args.split('-')] if args else ['Xbox']
        self.rpc_slots[slot] = await self.build_xbox(parts)
        await self.apply_activities()
        await ctx.send(ascii.success(f'Xbox → slot {slot + 1}: {parts[0]}'))

    @commands.command(name='ps')
    async def cmd_ps(self, ctx, *, args: str=None):
        words = args.strip().split() if args else []
        slot = 0
        if words and words[-1] in ('1', '2', '3', '4', '5', '6'):
            slot = int(words[-1]) - 1
            args = ' '.join(words[:-1]) if len(words) > 1 else None
        parts = [p.strip() for p in args.split('-')] if args else ['PlayStation']
        self.rpc_slots[slot] = await self.build_playstation(parts)
        await self.apply_activities()
        await ctx.send(ascii.success(f'PS → slot {slot + 1}: {parts[0]}'))

    @commands.command(name='ps4')
    async def cmd_ps4(self, ctx, *, args: str=None):
        words = args.strip().split() if args else []
        slot = 0
        if words and words[-1] in ('1', '2', '3', '4', '5', '6'):
            slot = int(words[-1]) - 1
            args = ' '.join(words[:-1]) if len(words) > 1 else None
        parts = [p.strip() for p in args.split('-')] if args else ['PS4']
        self.rpc_slots[slot] = await self.build_playstation(parts, ps4=True)
        await self.apply_activities()
        await ctx.send(ascii.success(f'PS4 → slot {slot + 1}: {parts[0]}'))

    @commands.command(name='crunchy')
    async def cmd_crunchy(self, ctx, *, args: str=None):
        words = args.strip().split() if args else []
        slot = 0
        if words and words[-1] in ('1', '2', '3', '4', '5', '6'):
            slot = int(words[-1]) - 1
            args = ' '.join(words[:-1]) if len(words) > 1 else None
        parts = [p.strip() for p in args.split('-')] if args else ['Crunchyroll']
        self.rpc_slots[slot] = await self.build_crunchyroll(parts)
        await self.apply_activities()
        await ctx.send(ascii.success(f'Crunchyroll → slot {slot + 1}: {parts[0]}'))

    @commands.command(name='vrchat')
    async def cmd_vrchat(self, ctx, *, args: str=None):
        await ctx.message.delete()
        words = args.strip().split() if args else []
        slot = 0
        if words and words[-1] in ('1', '2', '3', '4', '5', '6'):
            slot = int(words[-1]) - 1
            args = ' '.join(words[:-1]) if len(words) > 1 else None
        parts = [p.strip() for p in args.split('-')] if args else ['Exploring VRChat', 'VRChat']
        activity = await self.build_vrchat(parts)
        self.rpc_slots[slot] = activity
        await self.apply_activities()
        state = parts[0] if parts else 'Exploring VRChat'
        await ctx.send(ascii.success(f'VRChat → slot {slot + 1}: {state}'))

    @commands.command(name='meta')
    async def cmd_meta(self, ctx, *, args: str=None):
        await ctx.message.delete()
        if not args:
            await ctx.send(ascii.error('Usage: .meta State - World [slot] [image_url]'))
            return
        words = args.strip().split()
        slot = 0
        image_url = None
        for i, word in enumerate(words):
            if word.startswith(('http://', 'https://')):
                image_url = word
                words = words[:i]
                break
        if words and words[-1] in ('1', '2', '3', '4', '5', '6'):
            slot = int(words[-1]) - 1
            words = words[:-1]
        args_str = ' '.join(words) if words else None
        parts = [p.strip() for p in args_str.split('-')] if args_str else ['Exploring VRChat', 'VRChat']
        activity = await self.build_vrchat(parts, image_url)
        self.rpc_slots[slot] = activity
        await self.apply_activities()
        state = parts[0] if parts else 'Exploring VRChat'
        await ctx.send(ascii.success(f'Meta Quest → slot {slot + 1}: {state}'))

    @commands.command(name='rstatus')
    async def rotate_status(self, ctx, *, statuses: str):
        await ctx.message.delete()
        status_list = [s.strip() for s in statuses.split(',')]
        if not status_list:
            await ctx.send(ascii.error('Separate statuses by commas'))
            return
        self.status_rotation_active = True
        await ctx.send(ascii.info(f'Status rotation: {len(status_list)} statuses'))
        try:
            current_index = 0
            async with aiohttp.ClientSession() as session:
                while self.status_rotation_active:
                    self.current_status = status_list[current_index]
                    json_data = {'custom_status': {'text': self.current_status, 'emoji_name': self.current_emoji}}
                    await session.patch('https://discord.com/api/v9/users/@me/settings', headers={'Authorization': S._get_token(self.bot), 'Content-Type': 'application/json'}, json=json_data)
                    await asyncio.sleep(8)
                    current_index = (current_index + 1) % len(status_list)
        finally:
            self.current_status = ''

    @commands.command(name='remoji')
    async def rotate_emoji(self, ctx, *, emojis: str):
        await ctx.message.delete()
        emoji_list = [e.strip() for e in emojis.split(',')]
        if not emoji_list:
            await ctx.send(ascii.error('Separate emojis by commas'))
            return
        self.emoji_rotation_active = True
        await ctx.send(ascii.info(f'Emoji rotation: {len(emoji_list)} emojis'))
        try:
            current_index = 0
            async with aiohttp.ClientSession() as session:
                while self.emoji_rotation_active:
                    self.current_emoji = emoji_list[current_index]
                    json_data = {'custom_status': {'text': self.current_status, 'emoji_name': self.current_emoji}}
                    await session.patch('https://discord.com/api/v9/users/@me/settings', headers={'Authorization': S._get_token(self.bot), 'Content-Type': 'application/json'}, json=json_data)
                    await asyncio.sleep(8)
                    current_index = (current_index + 1) % len(emoji_list)
        finally:
            self.current_emoji = ''

    @commands.command(name='stopstatus')
    async def stop_rotate_status(self, ctx):
        await ctx.message.delete()
        self.status_rotation_active = False
        await ctx.send(ascii.info('Status rotation stopped'))

    @commands.command(name='stopemoji')
    async def stop_rotate_emoji(self, ctx):
        await ctx.message.delete()
        self.emoji_rotation_active = False
        await ctx.send(ascii.info('Emoji rotation stopped'))

    @commands.command(name='rpcstack', aliases=['multirpc', 'rpcmulti'], brief='Xbox + Stream + PS + YouTube stack')
    async def rpcstack(self, ctx, *, text: str=''):
        import time as _time
        now = int(_time.time())
        name = 'Game'
        stream_title = 'Live'
        ps_title = 'PlayStation'
        ps_state = 'Playing'
        yt_title = 'YouTube'
        yt_state = 'Watching'
        text = (text or '').strip()
        if text:
            if ':' not in text.split()[0]:
                name = stream_title = ps_title = yt_title = text
            for part in re.findall('(\\w+):([^:]+?)(?=\\s+\\w+:|$)', text):
                k, v = (part[0].lower(), part[1].strip())
                if k in ('name', 'n', 'main', 'xbox'):
                    name = v
                elif k in ('stream', 's', 'twitch', 'live'):
                    stream_title = v
                elif k in ('ps', 'playstation', 'ps5', 'ps4'):
                    ps_title = v
                elif k in ('psstate', 'psdetails'):
                    ps_state = v
                elif k in ('yt', 'youtube', 'watch'):
                    yt_title = v
                elif k in ('ytstate', 'ytdetails'):
                    yt_state = v
        self.rpc_slots[0] = {'type': 5, 'name': name, 'details': 'Xbox', 'application_id': 438122941302046720, 'assets': {'large_image': 'xbox', 'large_text': 'Xbox'}, 'platform': 'xbox', 'timestamps': {'start': now}}
        self.rpc_slots[1] = {'type': 1, 'name': stream_title, 'url': 'https://www.twitch.tv/directory', 'application_id': int(DEFAULT_APP_ID) if str(DEFAULT_APP_ID).isdigit() else DEFAULT_APP_ID, 'assets': {'large_image': 'twitch', 'large_text': 'Streaming'}, 'timestamps': {'start': now}}
        self.rpc_slots[2] = {'type': 0, 'name': ps_title, 'details': ps_state, 'application_id': 1001158269215858728, 'assets': {'large_image': 'playstation', 'large_text': 'PlayStation'}, 'platform': 'ps5', 'timestamps': {'start': now}}
        self.rpc_slots[3] = {'type': 3, 'name': yt_title, 'details': yt_state, 'application_id': int(DEFAULT_APP_ID) if str(DEFAULT_APP_ID).isdigit() else DEFAULT_APP_ID, 'assets': {'large_image': 'youtube', 'large_text': 'YouTube'}, 'timestamps': {'start': now}}
        for i in (4, 5):
            if i < len(self.rpc_slots):
                self.rpc_slots[i] = None
        await self._push()
        await ctx.message.edit(content=S.ui_ok('rpc stack | xbox / stream / ps / yt | timers on'))

    @commands.command(name='rpcxbox', brief='Competing on Xbox + timer')
    async def rpcxbox(self, ctx, *, name: str='Xbox'):
        import time as _time
        self.rpc_slots[0] = {'type': 5, 'name': name, 'details': 'Xbox', 'application_id': 438122941302046720, 'assets': {'large_image': 'xbox', 'large_text': 'Xbox'}, 'platform': 'xbox', 'timestamps': {'start': int(_time.time())}}
        await self._push()
        await ctx.message.edit(content=S.ui_ok(f'xbox | {name}'))

    @commands.command(name='rpcps', aliases=['rpcplaystation'], brief='Playing on PlayStation + timer')
    async def rpcps(self, ctx, *, name: str='PlayStation'):
        import time as _time
        self.rpc_slots[2] = {'type': 0, 'name': name, 'details': 'PlayStation', 'application_id': 1001158269215858728, 'assets': {'large_image': 'playstation', 'large_text': 'PlayStation'}, 'platform': 'ps5', 'timestamps': {'start': int(_time.time())}}
        await self._push()
        await ctx.message.edit(content=S.ui_ok(f'ps | {name}'))

    @commands.command(name='rpcyt', aliases=['rpcyoutube'], brief='Watching YouTube + timer')
    async def rpcyt(self, ctx, *, name: str='YouTube'):
        import time as _time
        self.rpc_slots[3] = {'type': 3, 'name': name, 'details': 'YouTube', 'application_id': int(DEFAULT_APP_ID) if str(DEFAULT_APP_ID).isdigit() else DEFAULT_APP_ID, 'assets': {'large_image': 'youtube', 'large_text': 'YouTube'}, 'timestamps': {'start': int(_time.time())}}
        await self._push()
        await ctx.message.edit(content=S.ui_ok(f'youtube | {name}'))

    @commands.command(name='rpctime', aliases=['rpcelapsed'], brief='Elapsed timer on a slot')
    async def rpctime(self, ctx, slot: int=1, mode: str='start'):
        import time as _time
        idx = max(1, min(6, int(slot))) - 1
        if self.rpc_slots[idx] is None:
            return await ctx.message.edit(content=S.ui_err(f'slot {idx + 1} empty'))
        mode = (mode or 'start').lower()
        if mode in ('clear', 'off', 'none', '0'):
            self.rpc_slots[idx].pop('timestamps', None)
        elif mode in ('end', 'left', 'remain'):
            secs = 3600
            parts = (ctx.message.content or '').split()
            if len(parts) >= 4 and parts[3].isdigit():
                secs = int(parts[3])
            now = int(_time.time() * 1000)
            self.rpc_slots[idx]['timestamps'] = {'start': now, 'end': now + secs * 1000}
        else:
            self.rpc_slots[idx]['timestamps'] = {'start': int(_time.time() * 1000)}
        await self._push()
        await ctx.message.edit(content=S.ui_ok(f'slot {idx + 1} time | {mode}'))

    @commands.command(name='rpcclearfield', aliases=['rpclear', 'rpcunset'], brief='Clear one RPC field on a slot')
    async def rpcclearfield(self, ctx, slot: int=1, field: str='state'):
        idx = max(1, min(6, int(slot))) - 1
        if self.rpc_slots[idx] is None:
            return await ctx.send(ascii.error(f'slot {idx + 1} empty'))
        field = (field or 'state').lower().strip()
        act = self.rpc_slots[idx]
        if field in ('state', 'st'):
            act.pop('state', None)
        elif field in ('details', 'detail', 'd'):
            act.pop('details', None)
        elif field in ('name', 'n', 'title'):
            act['name'] = '\u200e'
        elif field in ('image', 'large', 'large_image', 'img'):
            if isinstance(act.get("assets"), dict):
                act['assets'].pop('large_image', None)
                act['assets'].pop('large_text', None)
        elif field in ('small', 'small_image'):
            if isinstance(act.get("assets"), dict):
                act['assets'].pop('small_image', None)
                act['assets'].pop('small_text', None)
        elif field in ('buttons', 'btn', 'button'):
            act.pop('buttons', None)
            if isinstance(act.get("metadata"), dict):
                act['metadata'].pop('button_urls', None)
        elif field in ('time', 'timestamps', 'timer', 'elapsed'):
            act.pop('timestamps', None)
        elif field in ('url', 'stream_url'):
            act.pop('url', None)
        elif field in ('allfields', 'fields'):
            for k in ('state', 'details', 'url', 'timestamps', 'buttons'):
                act.pop(k, None)
            if isinstance(act.get("assets"), dict):
                act['assets'] = {}
        else:
            return await ctx.send(ascii.error('fields: state details name image small buttons time url'))
        self.rpc_slots[idx] = act
        await self._push()
        await ctx.send(ascii.success(f'slot {idx + 1} cleared | {field}'))

    @commands.command(name='rpc1clearstate', aliases=['rpc1cs'], brief='Clear RPC1 state')
    async def rpc1clearstate(self, ctx):
        await ctx.invoke(self.rpcclearfield, slot=1, field='state')

    @commands.command(name='rpc1cleardetails', aliases=['rpc1cd'], brief='Clear RPC1 details')
    async def rpc1cleardetails(self, ctx):
        await ctx.invoke(self.rpcclearfield, slot=1, field='details')

    @commands.command(name='rpcasset', aliases=['rpcimg', 'rpcimage', 'setasset'], brief='Set large/small image on an RPC slot')
    async def rpcasset(self, ctx, slot: str='1', kind: str='large', *, key: str=''):
        try:
            await ctx.message.delete()
        except Exception:
            pass
        try:
            self._last_ctx_channel = ctx.channel
        except Exception:
            pass
        parts = []
        if slot and slot not in ('large', 'small', 'clear', 'none', '-', 'off'):
            if not str(slot).isdigit():
                if not key:
                    key = ' '.join((x for x in (kind if kind not in ('large', 'small') else '', slot) if x)).strip()
                    kind = 'large'
                    slot = '1'
                else:
                    key = f'{slot} {kind} {key}'.strip() if kind not in ('large', 'small') else f'{slot} {key}'.strip()
                    kind = 'large' if kind not in ('large', 'small') else kind
                    slot = '1'
            else:
                pass
        elif str(slot).lower() in ('clear', 'none', '-', 'off'):
            key = 'clear'
            kind = 'large'
            slot = '1'
        elif str(slot).lower() in ('large', 'small'):
            kind = str(slot).lower()
            slot = '1'
            if not key and kind:
                pass
        if kind not in ('large', 'small', 'l', 's'):
            if not key or key == kind:
                key = kind
            kind = 'large'
        if kind in ('l',):
            kind = 'large'
        if kind in ('s',):
            kind = 'small'
        key = (key or '').strip()
        try:
            idx = max(1, min(6, int(slot))) - 1
        except Exception:
            idx = 0
        self._ensure_slot(idx)
        act = self.rpc_slots[idx]
        if not isinstance(act.get("assets"), dict):
            act['assets'] = {}
        act['application_id'] = int(DEFAULT_APP_ID) if str(DEFAULT_APP_ID).isdigit() else DEFAULT_APP_ID
        if not key or key.lower() in ('clear', 'none', '-', 'off', 'null'):
            if kind == 'small':
                act['assets'].pop('small_image', None)
                act['assets'].pop('small_text', None)
            else:
                act['assets'].pop('large_image', None)
                act['assets'].pop('large_text', None)
            self.rpc_slots[idx] = act
            await self._push()
            return await ctx.send(ascii.success(f'slot {idx + 1} {kind} image cleared'))
        if key.startswith('http://') or key.startswith('https://'):
            try:
                note = await ctx.send(ascii.info('resizing → 512×512...'))
            except Exception:
                note = None
            try:
                cdn = await self.rehost_resized(ctx.channel, key, size=512)
                src = cdn or key
                asset_val = await self.upload_asset(src) or src
                if note:
                    try:
                        await note.delete()
                    except Exception:
                        pass
            except Exception as e:
                print(f'[RPC] rpcasset url pipeline: {e}')
                try:
                    asset_val = await self.upload_asset(key) or key
                except Exception:
                    asset_val = key
                if note:
                    try:
                        await note.edit(content=ascii.warn(f'resize skipped | {e}'))
                    except Exception:
                        pass
        else:
            asset_val = key.lower().strip().replace(' ', '_')
            for ext in ('.png', '.jpg', '.jpeg', '.gif', '.webp'):
                if asset_val.endswith(ext):
                    asset_val = asset_val[:-len(ext)]
            try:
                await self._load_app_assets()
            except Exception:
                pass
            asset_val = self._resolve_portal_asset(asset_val)
            print(f'[RPC] rpcasset portal key={asset_val} app={DEFAULT_APP_ID}')
        if kind == 'small':
            act['assets']['small_image'] = asset_val
            act['assets']['small_text'] = key if not key.startswith('http') else ' '
        else:
            act['assets']['large_image'] = asset_val
            act['assets']['large_text'] = key if not key.startswith('http') else ' '
        self.rpc_slots[idx] = act
        await self._push()
        shown = asset_val if len(str(asset_val)) < 48 else str(asset_val)[:45] + '...'
        await ctx.send(ascii.success(f'slot {idx + 1} {kind} → `{shown}` | 512×512 | app {DEFAULT_APP_ID}'))

    @commands.command(name='rpcassets', aliases=['listassets'], brief='How to use portal assets with RPC')
    async def rpcassets_help(self, ctx):
        try:
            await ctx.message.delete()
        except Exception:
            pass
        msg = f'app id | `{DEFAULT_APP_ID}`\nportal | Rich Presence → Art Assets\n.rpcasset 1 large logo\n.rpcasset 1 small icon\n.rpcasset 1 large https://cdn.../x.png\n.rpcasset 1 clear'
        await ctx.send(ascii.info(msg))

    @commands.command(name='rpcreloadassets', aliases=['rpcreload'], brief='Reload portal Art Assets catalog')
    async def rpcreloadassets(self, ctx):
        try:
            await ctx.message.delete()
        except Exception:
            pass
        self._app_assets_loaded = False
        m = await self._load_app_assets(force=True)
        names = [k for k, v in m.items() if k != v][:20]
        await ctx.send(ascii.success(f"assets | {len(names)} keys | {', '.join(names) or 'none'}"))

async def setup(bot):
    await bot.add_cog(RPCCog(bot))
