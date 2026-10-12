import asyncio, base64, json, random, time
import discord
from discord.ext import commands
from . import state as S

def _props_from_preset(preset: dict) -> dict:
    """Build Discord identify client properties from a platform preset."""
    os_name = preset.get("os") or "Windows"
    browser = preset.get("browser") or "Discord Client"
    device = preset.get("device") or ""
    bv = preset.get("browser_version") or "1.0.9191"
    ov = preset.get("os_version") or "10"
    ua = preset.get("browser_user_agent")
    if not ua:
        if "Android" in browser or os_name == "Android":
            ua = f"Discord-Android/{bv}"
        elif "iOS" in browser or os_name == "iOS":
            ua = f"Discord/{bv} CFNetwork/1490 Darwin/23.6.0"
        elif browser == "Chrome" or "Web" in str(preset.get("label", "")):
            ua = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{bv} Safari/537.36"
        else:
            ua = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) discord/{bv} Chrome/130.0.0.0 Electron/33.0.0 Safari/537.36"
    props = {
        "os": os_name,
        "browser": browser,
        "device": device,
        "system_locale": "en-US",
        "browser_user_agent": ua,
        "browser_version": bv,
        "os_version": ov,
        "referrer": "",
        "referring_domain": "",
        "referrer_current": "",
        "referring_domain_current": "",
        "release_channel": "stable",
        "client_build_number": int(preset.get("client_build_number") or 360032) if str(preset.get("client_build_number") or "360032").isdigit() else 360032,
        "client_event_source": None,
        "has_client_mods": False,
    }
    # mobile extras
    if os_name in ("Android", "iOS"):
        props["client_version"] = bv
        if device:
            props["device"] = device
    else:
        props["client_version"] = bv
        props["os_arch"] = "x64"
        props["app_arch"] = "x64"
        props["runtime_environment"] = "native"
    return props


def _inject_identify_d(d: dict, preset: dict) -> dict:
    if not isinstance(d, dict):
        return d
    props = _props_from_preset(preset)
    d = dict(d)
    d["properties"] = props
    # also common alternate keys
    d["client_properties"] = props
    return d

try:
    from utils.ms_install import ensure_modifyself as _ensure_ms
except Exception:
    _ensure_ms = None

# Optional modifyself.com Chrome154 header/gateway payloads (https://modifyself.com)
_MS_SPOOFER = None
_MS_ERR = None
try:
    from modifyselfclient import Spoofer as _MSClient  # documented API
except Exception:
    try:
        from modifyself.headers import HeaderSpoofer as _MSClient
    except Exception:
        try:
            from modifyself import Spoofer as _MSClient
        except Exception as _e:
            _MSClient = None
            _MS_ERR = _e

def _ms_get(token: str):
    """Lazy modifyself instance for this token."""
    global _MS_SPOOFER
    if _MSClient is None:
        return None
    try:
        if _MS_SPOOFER is None or getattr(_MS_SPOOFER, "_token", None) != token:
            _MS_SPOOFER = _MSClient(token)
            try:
                _MS_SPOOFER._token = token
            except Exception:
                pass
        return _MS_SPOOFER
    except Exception:
        return None


PLATFORM_PRESETS = {
    # Desktop clients (Discord Desktop / browser)
    "desktop": {"os": "Windows", "browser": "Discord Client", "device": "", "label": "Windows Desktop",
                "browser_version": "1.0.9191", "os_version": "10.0.22631"},
    "windows": {"os": "Windows", "browser": "Discord Client", "device": "", "label": "Windows Desktop",
                "browser_version": "1.0.9191", "os_version": "10.0.22631"},
    "macos":   {"os": "Mac OS X", "browser": "Discord Client", "device": "", "label": "macOS Desktop",
                "browser_version": "1.0.9191", "os_version": "14.5.0"},
    "linux":   {"os": "Linux", "browser": "Discord Client", "device": "", "label": "Linux Desktop",
                "browser_version": "1.0.9191", "os_version": "6.8.0"},
    "web":     {"os": "Windows", "browser": "Chrome", "device": "", "label": "Web Browser",
                "browser_version": "152.0.0.0", "os_version": "10"},
    # Mobile
    "phone":   {"os": "Android", "browser": "Discord Android", "device": "Pixel 8", "label": "Android Phone",
                "browser_version": "252.15", "os_version": "14"},
    "mobile":  {"os": "Android", "browser": "Discord Android", "device": "Pixel 8", "label": "Android Phone",
                "browser_version": "252.15", "os_version": "14"},
    "android": {"os": "Android", "browser": "Discord Android", "device": "Android", "label": "Android",
                "browser_version": "252.15", "os_version": "14"},
    "ios":     {"os": "iOS", "browser": "Discord iOS", "device": "iPhone", "label": "iPhone",
                "browser_version": "252.0", "os_version": "17.5"},
    "iphone":  {"os": "iOS", "browser": "Discord iOS", "device": "iPhone", "label": "iPhone",
                "browser_version": "252.0", "os_version": "17.5"},
    "ipad":    {"os": "iOS", "browser": "Discord iOS", "device": "iPad", "label": "iPad",
                "browser_version": "252.0", "os_version": "17.5"},
    # Console / VR — Discord shows these via device field on mobile-like clients
    "console": {"os": "Windows", "browser": "Discord Client", "device": "Xbox", "label": "Console",
                "browser_version": "1.0.9191", "os_version": "10.0.22631"},
    "xbox":    {"os": "Windows", "browser": "Discord Client", "device": "Xbox Series X", "label": "Xbox",
                "browser_version": "1.0.9191", "os_version": "10.0.22631"},
    "playstation": {"os": "Windows", "browser": "Discord Client", "device": "PlayStation 5", "label": "PlayStation",
                "browser_version": "1.0.9191", "os_version": "10.0.22631"},
    "ps":      {"os": "Windows", "browser": "Discord Client", "device": "PlayStation 5", "label": "PlayStation",
                "browser_version": "1.0.9191", "os_version": "10.0.22631"},
    "vr":      {"os": "Android", "browser": "Discord Android", "device": "Quest 3", "label": "VR Headset",
                "browser_version": "252.15", "os_version": "12"},
    "quest":   {"os": "Android", "browser": "Discord Android", "device": "Quest 3", "label": "Meta Quest 3",
                "browser_version": "252.15", "os_version": "12"},
    "quest2":  {"os": "Android", "browser": "Discord Android", "device": "Quest 2", "label": "Meta Quest 2",
                "browser_version": "252.15", "os_version": "12"},
    "embedded":{"os": "Windows", "browser": "Discord Client", "device": "", "label": "Embedded",
                "browser_version": "1.0.9191", "os_version": "10.0.22631"},
}

UA_MAP = {
    ("Windows", "Discord Client"): (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) discord/1.0.9191 Chrome/134.0.6998.179 "
        "Electron/35.1.5 Safari/537.36"
    ),
    ("Mac OS X", "Discord Client"): (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) discord/1.0.9191 Chrome/134.0.6998.179 "
        "Electron/35.1.5 Safari/537.36"
    ),
    ("Linux", "Discord Client"): (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) discord/1.0.9191 Chrome/134.0.6998.179 "
        "Electron/35.1.5 Safari/537.36"
    ),
    ("Windows", "Chrome"): (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
    ),
    ("Android", "Discord Android"): (
        "Discord-Android/252.15; Android 14"
    ),
    ("iOS", "Discord iOS"): (
        "Discord/252.0.0 (iPhone; iOS 17.5; Scale/3.00)"
    ),
}

_POOL   = {"mode": "sticky", "keys": ["desktop"],
           "pool": [PLATFORM_PRESETS["desktop"]], "cursor": 0, "last": None}
_PATCH  = {"json": False, "as_json": False, "orig_json": None, "orig_as_json": None, "path": None}
_STATS  = {"identifies": 0, "reconnects": 0}
_COG    = [None]   # live cog reference


def _pick() -> dict | None:
    pool = _POOL["pool"]
    if not pool: return None
    if _POOL["mode"] == "sticky": return pool[0]
    if _POOL["mode"] == "random": return random.choice(pool)
    idx = _POOL["cursor"] % len(pool); _POOL["cursor"] = idx + 1
    return pool[idx]


def _set_pool(keys: list):
    _POOL["keys"] = [k for k in keys if k in PLATFORM_PRESETS]
    _POOL["pool"] = [PLATFORM_PRESETS[k] for k in _POOL["keys"]]
    _POOL["cursor"] = 0


def _make_identify_payload(preset: dict, token: str) -> dict:
    return {
        "op": 2,
        "d": {
            "token":        token,
            "capabilities": 16381,
            "properties": {
                "os":                        preset["os"],
                "browser":                   preset["browser"],
                "device":                    preset.get("device", ""),
                "system_locale":             "en-US",
                "browser_user_agent":        UA_MAP.get((preset["os"], preset["browser"]),
                                              "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/132.0.0.0 Safari/537.36"),
                "browser_version":           "132.0.0.0",
                "os_version":                "",
                "referrer":                  "",
                "referring_domain":          "",
                "referrer_current":          "",
                "referring_domain_current":  "",
                "release_channel":           "stable",
                "client_build_number":       360032,
                "client_event_source":       None,
            },
            "compress": False,
            "client_state": {
                "guild_versions":              {},
                "highest_last_message_id":     "0",
                "read_state_version":          0,
                "user_guild_settings_version": -1,
                "user_settings_version":       -1,
                "private_channels_version":    "0",
                "api_code_version":            0,
            },
            "presence": {"status": "online", "since": 0, "activities": [], "afk": False},
        }
    }


def _find_ws_class(bot=None):
    try:
        import discord.gateway as gw
        cls = getattr(gw, "DiscordWebSocket", None)
        if cls: return cls, "discord.gateway.DiscordWebSocket"
    except Exception:
        pass
    ws = getattr(bot, "ws", None) if bot else None
    if ws: return type(ws), f"{type(ws).__module__}.{type(ws).__name__}"
    return None, None


def _install_class_patch(bot=None):
    cls, path = _find_ws_class(bot)
    if not cls:
        print("[spoofer] class not found — class patch skipped")
        return

    _PATCH["path"] = path

    def _make_interceptor(orig, method_name):
        async def interceptor(self_ws, data):
            try:
                if isinstance(data, dict) and data.get("op") == 2:
                    preset = _pick()
                    if preset:
                        d     = data.setdefault("d", {})
                        props = d.setdefault("properties", {})
                        props["os"] = preset["os"]
                        props["browser"] = preset["browser"]
                        props["device"] = preset.get("device", "")
                        if preset.get("os_version"):
                            props["os_version"] = preset["os_version"]
                        if preset.get("browser_version"):
                            props["browser_version"] = preset["browser_version"]
                        ua = UA_MAP.get((preset["os"], preset["browser"]))
                        if ua:
                            props["browser_user_agent"] = ua
                        # keep release channel stable
                        props.setdefault("release_channel", "stable")
                        props.setdefault("system_locale", "en-US")
                        _POOL["last"] = preset
                        _STATS["identifies"] += 1
                        cog = _COG[0]
                        if cog:
                            cog._last_props = dict(props)
                        print(f"[spoofer] {method_name} OP2 → {preset['label']}")
            except Exception as e:
                print(f"[spoofer] {method_name} intercept error: {e}")
            return await orig(self_ws, data)
        return interceptor

    for method in ("send_json", "send_as_json"):
        orig = getattr(cls, method, None)
        if orig and not getattr(cls, f"_spoofer_patched_{method}", False):
            setattr(cls, method, _make_interceptor(orig, method))
            setattr(cls, f"_spoofer_patched_{method}", True)
            _PATCH[method.replace("send_", "")] = True
            print(f"[spoofer] patched {path}.{method}")


def _patch_http(bot, preset: dict):
    for attr_path in ("http", "_connection.http"):
        try:
            obj = bot
            for part in attr_path.split("."):
                obj = getattr(obj, part, None)
                if obj is None: break
            if obj is None: continue
            for attr, key in [("browser","browser"),("device","device"),("os","os")]:
                if hasattr(obj, attr):
                    try: setattr(obj, attr, preset.get(key, ""))
                    except (AttributeError, TypeError): pass
            print(f"[spoofer] http patch applied via {attr_path}")
            return True
        except Exception as e:
            print(f"[spoofer] http patch ({attr_path}): {e}")
    return False


class SpooferCog(commands.Cog, name="spoofer"):
    def __init__(self, bot):
        self.bot         = bot
        self._last_props = None
        _COG[0] = self
        _install_class_patch(bot)

    async def cog_load(self):
        if not (_PATCH.get("json") or _PATCH.get("as_json")):
            _install_class_patch(self.bot)

    @commands.Cog.listener()
    async def on_connect(self):
        """Ensure class-level OP2 interceptor is installed. Do not replace identify."""
        if not _POOL["pool"]:
            return
        _install_class_patch(self.bot)
        preset = _pick()
        if preset:
            _patch_http(self.bot, preset)


    @commands.Cog.listener()
    async def on_ready(self):
        _install_class_patch(self.bot)

    async def _force_identify(self, preset: dict) -> bool:
        """
        DISABLED by default.
        Sending a second OP2 on a live session races the library identify/resume
        and is a common cause of discord forcing logout / token invalidation.
        Device spoof relies on the send_as_json OP2 interceptor instead.
        """
        _POOL["last"] = preset
        self._last_props = dict(preset)
        print(f"[spoofer] force_identify skipped (safe mode) → pool set to {preset.get('label')}")
        return False

    async def _reconnect(self):
        """
        Soft reconnect ONLY for explicit .spoofhard.
        Closing the gateway + wiping session_id is what logs accounts out.
        Default .spoof never calls this.
        """
        _STATS["reconnects"] += 1
        print("[spoofer] soft reconnect requested (spoofhard only)")
        try:
            ws = getattr(self.bot, "ws", None)
            if ws is not None:
                # do NOT clear session_id — allow resume so token stays valid
                for code in (1000,):
                    try:
                        close = getattr(ws, "close", None)
                        if close:
                            await close(code=code)
                            print(f"[spoofer] ws closed code={code} (resume-friendly)")
                            break
                    except Exception as e:
                        print(f"[spoofer] close: {e}")
        except Exception as e:
            print(f"[spoofer] reconnect: {e}")


    async def _apply_and_reconnect(self, preset: dict, label: str, ctx):
        """
        Safe spoof: update pool + HTTP props only.
        Does NOT close the gateway or send a second IDENTIFY (that logs accounts out).
        Device shows on the next natural reconnect/login.
        Use `.spoofhard <platform>` if you explicitly want a reconnect (risky).
        """
        _set_pool([label])
        _POOL["mode"] = "sticky"
        _POOL["last"] = preset
        _patch_http(self.bot, preset)
        try:
            await ctx.message.edit(content=S.ui_ok(
                f"spoof pool → {preset['label']}\n"
                f"os={preset.get('os')} browser={preset.get('browser')} "
                f"device={preset.get('device') or 'none'}\n"
                f"(applies on next natural reconnect — no forced logout)"))
        except Exception:
            pass

    @commands.command(name="spoof", aliases=["spoofer"], brief="Spoof platform — spoof <preset>")
    async def spoof(self, ctx, platform: str = "", sub: str = "", *, rest: str = ""):
        if not platform or platform in ("status", "info"):
            return await self._show_status(ctx)

        p = platform.lower()

        if p == "add" and sub:
            sub = sub.lower()
            if sub not in PLATFORM_PRESETS:
                return await ctx.message.edit(content=S.ui_err(f"unknown: {sub}"))
            if sub not in _POOL["keys"]:
                _POOL["keys"].append(sub); _POOL["pool"].append(PLATFORM_PRESETS[sub])
            return await ctx.message.edit(content=S.ui_ok(f"added {sub} — pool: {', '.join(_POOL['keys'])}"))

        if p == "remove" and sub:
            sub = sub.lower()
            if sub in _POOL["keys"]:
                i = _POOL["keys"].index(sub); _POOL["keys"].pop(i); _POOL["pool"].pop(i)
            return await ctx.message.edit(content=S.ui_ok(f"removed {sub}"))

        if p == "mode" and sub in ("rotate", "random", "sticky"):
            _POOL["mode"] = sub; _POOL["cursor"] = 0
            return await ctx.message.edit(content=S.ui_ok(f"mode → {sub}"))

        if p == "clear":
            _set_pool([])
            return await ctx.message.edit(content=S.ui_ok("pool cleared"))

        if p == "reset":
            preset = PLATFORM_PRESETS["desktop"]
            await self._apply_and_reconnect(preset, "desktop", ctx)
            return

        if p == "pool":
            rows = [f"  {k:<12} {PLATFORM_PRESETS[k]['label']}" for k in _POOL["keys"]]
            rows.append(f"\n  mode {_POOL['mode']}  cursor {_POOL['cursor']}")
            return await ctx.message.edit(content=S.ui_box("spoof pool", rows))

        if p not in PLATFORM_PRESETS:
            return await ctx.message.edit(
                content=S.ui_err(f"unknown: {p}  ·  valid: {', '.join(PLATFORM_PRESETS)}"))

        await self._apply_and_reconnect(PLATFORM_PRESETS[p], p, ctx)

    @commands.command(name="vr", brief="Spoof Meta Quest VR headset")
    async def vr(self, ctx):
        await self._apply_and_reconnect(PLATFORM_PRESETS["vr"], "vr", ctx)

    @commands.command(name="console", brief="Spoof console platform")
    async def console(self, ctx):
        await self._apply_and_reconnect(PLATFORM_PRESETS["console"], "console", ctx)

    @commands.command(name="spoofreset", brief="Reset spoofer to desktop")
    async def spoofreset(self, ctx):
        await self._apply_and_reconnect(PLATFORM_PRESETS["desktop"], "desktop", ctx)

    @commands.command(name="platform", brief="platform <preset>")
    async def platform_cmd(self, ctx, *, preset: str = ""):
        key = preset.strip().lower().split()[0] if preset.strip() else ""
        if not key:
            rows = [f"  {k:<14} {v['label']}" for k, v in PLATFORM_PRESETS.items()]
            return await ctx.message.edit(content=S.ui_box("platforms", rows))
        await self.spoof(ctx, key)

    @commands.command(name="spoofstatus", brief="Show current spoof status")
    async def spoofstatus(self, ctx):
        await self._show_status(ctx)

    @commands.command(name="spooferdiag", brief="Full spoofer diagnostics")
    async def spooferdiag(self, ctx):
        cls, path = _find_ws_class(self.bot)
        ws = getattr(self.bot, "ws", None)
        p  = self._last_props or {}
        patched_json    = getattr(cls, "_spoofer_patched_send_json",    False) if cls else False
        patched_as_json = getattr(cls, "_spoofer_patched_send_as_json", False) if cls else False
        ws_has_identify = hasattr(ws, "_spoof_patched_identify") if ws else False
        rows = [
            f"  {S.DIM}class found{S.RESET}         {path or 'NOT FOUND'}",
            f"  {S.DIM}send_json patched{S.RESET}   {'✓' if patched_json    else '✗'}",
            f"  {S.DIM}send_as_json patched{S.RESET}{'✓' if patched_as_json else '✗'}",
            f"  {S.DIM}instance identify{S.RESET}   {'✓' if ws_has_identify  else '✗'}",
            f"  {S.DIM}ws type{S.RESET}             {type(ws).__name__ if ws else 'None'}",
            f"  {S.DIM}has send_json{S.RESET}       {hasattr(ws, 'send_json') if ws else False}",
            f"  {S.DIM}has send_as_json{S.RESET}    {hasattr(ws, 'send_as_json') if ws else False}",
            f"  {S.DIM}has identify{S.RESET}        {hasattr(ws, 'identify') if ws else False}",
            f"  {S.DIM}has _identify{S.RESET}       {hasattr(ws, '_identify') if ws else False}",
            "",
            f"  {S.DIM}pool{S.RESET}  {', '.join(_POOL['keys']) or '—'}",
            f"  {S.DIM}mode{S.RESET}  {_POOL['mode']}",
            f"  {S.DIM}last{S.RESET}  {_POOL['last']['label'] if _POOL['last'] else '—'}",
            f"  {S.DIM}os{S.RESET}    {p.get('os','—')}",
            f"  {S.DIM}browser{S.RESET}  {p.get('browser','—')}",
            f"  {S.DIM}device{S.RESET}   {p.get('device','—') or 'none'}",
            "",
            f"  {S.DIM}identifies{S.RESET}  {_STATS['identifies']}",
            f"  {S.DIM}reconnects{S.RESET}  {_STATS['reconnects']}",
        ]
        await ctx.message.edit(content=S.ui_box("spoofer diag", rows))

    async def _show_status(self, ctx):
        preset = _POOL["last"] or {}
        p      = self._last_props or {}
        rows = [
            f"  {S.DIM}preset{S.RESET}   {preset.get('label','—')}",
            f"  {S.DIM}pool{S.RESET}     {', '.join(_POOL['keys']) or '—'}",
            f"  {S.DIM}mode{S.RESET}     {_POOL['mode']}",
            "",
            f"  {S.DIM}os{S.RESET}       {p.get('os', preset.get('os','?'))}",
            f"  {S.DIM}browser{S.RESET}  {p.get('browser', preset.get('browser','?'))}",
            f"  {S.DIM}device{S.RESET}   {p.get('device', preset.get('device','?')) or 'none'}",
            "",
            f"  {S.DIM}identifies{S.RESET} {_STATS['identifies']}",
            f"  {S.DIM}reconnects{S.RESET} {_STATS['reconnects']}",
            "",
            f"  {S.DIM}valid: {', '.join(PLATFORM_PRESETS)}{S.RESET}",
        ]
        await ctx.message.edit(content=S.ui_box("spoofer", rows))


    @commands.command(name="spoofhard", brief="Force reconnect+spoof (can log you out — use rarely)")

    async def spoofhard(self, ctx, platform: str = "desktop"):
        p = (platform or "desktop").lower()
        if p not in PLATFORM_PRESETS:
            return await ctx.message.edit(content=S.ui_err(f"unknown: {p}"))
        preset = PLATFORM_PRESETS[p]
        props = _props_from_preset(preset)
        _set_pool([p])
        _POOL["mode"] = "sticky"
        _POOL["last"] = preset
        _POOL["forced_props"] = props
        self._last_props = props
        _patch_http(self.bot, preset)
        # patch library super properties if present
        try:
            http = getattr(self.bot, "http", None)
            if http is not None:
                for attr in ("_super_properties", "super_properties"):
                    if hasattr(http, attr):
                        try:
                            setattr(http, attr, props)
                        except Exception:
                            pass
                # X-Super-Properties header
                try:
                    import base64, json as _json
                    enc = base64.b64encode(_json.dumps(props, separators=(",", ":")).encode()).decode()
                    if hasattr(http, "headers") and isinstance(http.headers, dict):
                        http.headers["X-Super-Properties"] = enc
                        http.headers["User-Agent"] = props.get("browser_user_agent") or http.headers.get("User-Agent", "")
                except Exception:
                    pass
        except Exception as e:
            print(f"[spoofer] http props: {e}")
        # ensure gateway class patches use forced_props
        try:
            cls, _path = _find_ws_class(self.bot)
            if cls is not None:
                cls._spoofer_forced_props = props
        except Exception:
            pass
        await ctx.message.edit(content=S.ui_warn(
            f"hard spoof → {preset.get('label', p)} (reconnect; may kick other sessions)"
        ))
        await self._reconnect()
        for _ in range(20):
            await asyncio.sleep(0.5)
            if _POOL.get("last"):
                break
        await ctx.channel.send(S.ui_ok(
            f"spoof active → {preset.get('label', p)} · browser={props.get('browser')} · os={props.get('os')} · device={props.get('device') or '—'}"
        ))


    @commands.command(name="msheaders", brief="Fetch modifyself.com REST headers (if installed)")
    async def msheaders(self, ctx):
        token = getattr(self.bot, "http", None) and getattr(self.bot.http, "token", None)
        token = token or getattr(self.bot, "token", None)
        if not token:
            return await ctx.message.edit(content=S.ui_err("no token on bot"))
        sp = _ms_get(token)
        if sp is None:
            return await ctx.message.edit(content=S.ui_err(
                f"modifyself not installed ({_MS_ERR}). run: curl -fsSL modifyself.com/modifyself | sh"
            ))
        try:
            headers = sp.get_headers() if hasattr(sp, "get_headers") else {}
            keys = list(headers.keys())[:12] if isinstance(headers, dict) else []
            await ctx.message.edit(content=S.ui_ok(f"modifyself headers ok · keys={keys}"))
            # apply Authorization-safe headers to http
            http = getattr(self.bot, "http", None)
            if http is not None and isinstance(headers, dict):
                for k, v in headers.items():
                    if k.lower() in ("authorization",):
                        continue
                    try:
                        if hasattr(http, "headers") and isinstance(http.headers, dict):
                            http.headers[k] = v
                    except Exception:
                        pass
        except Exception as e:
            await ctx.message.edit(content=S.ui_err(f"modifyself headers: {e}")[:180])

    @commands.command(name="msidentify", brief="Preview modifyself gateway IDENTIFY properties")
    async def msidentify(self, ctx, status: str = "online"):
        token = getattr(self.bot, "http", None) and getattr(self.bot.http, "token", None)
        token = token or getattr(self.bot, "token", None)
        sp = _ms_get(token) if token else None
        if sp is None:
            return await ctx.message.edit(content=S.ui_err("modifyself not available — install from modifyself.com"))
        try:
            if hasattr(sp, "get_gateway_identify"):
                identify = sp.get_gateway_identify(status=status)
            else:
                identify = {"note": "client has no get_gateway_identify"}
            # store for next natural identify patch
            self._ms_identify = identify
            props = (identify.get("properties") if isinstance(identify, dict) else None) or identify
            await ctx.message.edit(content=S.ui_ok(f"identify cached · props={str(props)[:120]}"))
        except Exception as e:
            await ctx.message.edit(content=S.ui_err(str(e)[:150]))

    @commands.command(name="mson", brief="Enable modifyself header patch on HTTP client")
    async def mson(self, ctx):
        token = getattr(self.bot, "http", None) and getattr(self.bot.http, "token", None)
        token = token or getattr(self.bot, "token", None)
        sp = _ms_get(token) if token else None
        if sp is None:
            return await ctx.message.edit(content=S.ui_err("install modifyself first (modifyself.com)"))
        try:
            headers = sp.get_headers() if hasattr(sp, "get_headers") else {}
            ws_h = sp.get_websocket_headers() if hasattr(sp, "get_websocket_headers") else {}
            self._ms_headers = headers if isinstance(headers, dict) else {}
            self._ms_ws_headers = ws_h if isinstance(ws_h, dict) else {}
            http = getattr(self.bot, "http", None)
            if http is not None and self._ms_headers:
                for k, v in self._ms_headers.items():
                    if k.lower() == "authorization":
                        continue
                    try:
                        if hasattr(http, "headers") and isinstance(http.headers, dict):
                            http.headers[k] = v
                    except Exception:
                        pass
            await ctx.message.edit(content=S.ui_ok("modifyself REST headers applied (no forced reconnect)"))
        except Exception as e:
            await ctx.message.edit(content=S.ui_err(str(e)[:150]))

    @commands.command(name="msoff", brief="Clear modifyself cached patches")
    async def msoff(self, ctx):
        self._ms_headers = {}
        self._ms_ws_headers = {}
        self._ms_identify = None
        global _MS_SPOOFER
        _MS_SPOOFER = None
        await ctx.message.edit(content=S.ui_ok("modifyself cleared"))

async def setup(bot):
    await bot.add_cog(SpooferCog(bot))


# --- force properties on IDENTIFY (op 2) using _POOL["forced_props"] ---
def _spoofer_apply_forced_to_payload(payload):
    try:
        if not isinstance(payload, dict):
            return payload
        op = payload.get("op")
        if op not in (2, "2"):
            return payload
        props = _POOL.get("forced_props")
        if not props:
            last = _POOL.get("last")
            if isinstance(last, dict) and last.get("os"):
                props = _props_from_preset(last)
        if not props:
            return payload
        d = payload.get("d")
        if isinstance(d, dict):
            d = dict(d)
            d["properties"] = props
            payload = dict(payload)
            payload["d"] = d
        return payload
    except Exception:
        return payload



def _install_identify_wrapper():
    """Wrap DiscordWebSocket.send_as_json / send_json to inject forced props."""
    try:
        from discord.gateway import DiscordWebSocket as _WS
    except Exception:
        try:
            from discord.gateway import DiscordWebSocket as _WS
        except Exception:
            return
    if getattr(_WS, "_wilt_id_wrap", False):
        return
    for meth in ("send_as_json", "send_json"):
        orig = getattr(_WS, meth, None)
        if orig is None:
            continue
        def _make(o):
            async def _wrapped(self, data, *a, **k):
                try:
                    data = _spoofer_apply_forced_to_payload(data)
                except Exception:
                    pass
                return await o(self, data, *a, **k)
            return _wrapped
        try:
            setattr(_WS, meth, _make(orig))
        except Exception:
            pass
    _WS._wilt_id_wrap = True
    print("[spoofer] IDENTIFY property wrapper installed")

try:
    _install_identify_wrapper()
except Exception as _e:
    print(f"[spoofer] identify wrap skip: {_e}")
