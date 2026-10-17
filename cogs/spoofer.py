
import asyncio
import base64
import json
import random
import time

import discord
from discord.ext import commands

from . import state as S

PLATFORM_PRESETS = {
    "desktop": {
        "os": "Windows", "browser": "Discord Client", "device": "",
        "label": "Windows Desktop", "browser_version": "1.0.9191",
        "os_version": "10.0.22631", "client_build_number": 360032,
        "browser_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9191 Chrome/130.0.0.0 Electron/33.0.0 Safari/537.36",
    },
    "windows": {
        "os": "Windows", "browser": "Discord Client", "device": "",
        "label": "Windows Desktop", "browser_version": "1.0.9191",
        "os_version": "10.0.22631", "client_build_number": 360032,
        "browser_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9191 Chrome/130.0.0.0 Electron/33.0.0 Safari/537.36",
    },
    "macos": {
        "os": "Mac OS X", "browser": "Discord Client", "device": "",
        "label": "macOS Desktop", "browser_version": "1.0.9191",
        "os_version": "14.5.0", "client_build_number": 360032,
        "browser_user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9191 Chrome/130.0.0.0 Electron/33.0.0 Safari/537.36",
    },
    "linux": {
        "os": "Linux", "browser": "Discord Client", "device": "",
        "label": "Linux Desktop", "browser_version": "1.0.9191",
        "os_version": "6.8.0", "client_build_number": 360032,
        "browser_user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9191 Chrome/130.0.0.0 Electron/33.0.0 Safari/537.36",
    },
    "web": {
        "os": "Windows", "browser": "Chrome", "device": "",
        "label": "Browser", "browser_version": "131.0.0.0",
        "os_version": "10", "client_build_number": 360032,
        "browser_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    },
    "phone": {
        "os": "Android", "browser": "Discord Android", "device": "Pixel 8",
        "label": "Android Phone", "browser_version": "252.15",
        "os_version": "14", "client_build_number": 252015,
        "browser_user_agent": "Discord-Android/252.15",
    },
    "mobile": {
        "os": "Android", "browser": "Discord Android", "device": "Pixel 8",
        "label": "Android Phone", "browser_version": "252.15",
        "os_version": "14", "client_build_number": 252015,
        "browser_user_agent": "Discord-Android/252.15",
    },
    "android": {
        "os": "Android", "browser": "Discord Android", "device": "Android",
        "label": "Android", "browser_version": "252.15",
        "os_version": "14", "client_build_number": 252015,
        "browser_user_agent": "Discord-Android/252.15",
    },
    "ios": {
        "os": "iOS", "browser": "Discord iOS", "device": "iPhone",
        "label": "iPhone", "browser_version": "252.0",
        "os_version": "17.5", "client_build_number": 65200,
        "browser_user_agent": "Discord/65200 CFNetwork/1490 Darwin/23.6.0",
    },
    "iphone": {
        "os": "iOS", "browser": "Discord iOS", "device": "iPhone",
        "label": "iPhone", "browser_version": "252.0",
        "os_version": "17.5", "client_build_number": 65200,
        "browser_user_agent": "Discord/65200 CFNetwork/1490 Darwin/23.6.0",
    },
    "ipad": {
        "os": "iOS", "browser": "Discord iOS", "device": "iPad",
        "label": "iPad", "browser_version": "252.0",
        "os_version": "17.5", "client_build_number": 65200,
        "browser_user_agent": "Discord/65200 CFNetwork/1490 Darwin/23.6.0",
    },
    "vr": {
        "os": "Android", "browser": "Discord Android", "device": "Quest 3",
        "label": "Meta Quest 3", "browser_version": "252.15",
        "os_version": "12", "client_build_number": 252015,
        "browser_user_agent": "Discord-Android/252.15",
    },
    "quest": {
        "os": "Android", "browser": "Discord Android", "device": "Quest 3",
        "label": "Meta Quest 3", "browser_version": "252.15",
        "os_version": "12", "client_build_number": 252015,
        "browser_user_agent": "Discord-Android/252.15",
    },
    "quest2": {
        "os": "Android", "browser": "Discord Android", "device": "Quest 2",
        "label": "Meta Quest 2", "browser_version": "252.15",
        "os_version": "12", "client_build_number": 252015,
        "browser_user_agent": "Discord-Android/252.15",
    },
    "quest3": {
        "os": "Android", "browser": "Discord Android", "device": "Quest 3",
        "label": "Meta Quest 3", "browser_version": "252.15",
        "os_version": "12", "client_build_number": 252015,
        "browser_user_agent": "Discord-Android/252.15",
    },
    "console": {
        "os": "Windows", "browser": "Discord Client", "device": "Xbox Series X",
        "label": "Console", "browser_version": "1.0.9191",
        "os_version": "10.0.22631", "client_build_number": 360032,
        "browser_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9191 Chrome/130.0.0.0 Electron/33.0.0 Safari/537.36",
    },
    "xbox": {
        "os": "Windows", "browser": "Discord Client", "device": "Xbox Series X",
        "label": "Xbox", "browser_version": "1.0.9191",
        "os_version": "10.0.22631", "client_build_number": 360032,
        "browser_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9191 Chrome/130.0.0.0 Electron/33.0.0 Safari/537.36",
    },
    "playstation": {
        "os": "Windows", "browser": "Discord Client", "device": "PlayStation 5",
        "label": "PlayStation", "browser_version": "1.0.9191",
        "os_version": "10.0.22631", "client_build_number": 360032,
        "browser_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9191 Chrome/130.0.0.0 Electron/33.0.0 Safari/537.36",
    },
    "ps": {
        "os": "Windows", "browser": "Discord Client", "device": "PlayStation 5",
        "label": "PlayStation", "browser_version": "1.0.9191",
        "os_version": "10.0.22631", "client_build_number": 360032,
        "browser_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9191 Chrome/130.0.0.0 Electron/33.0.0 Safari/537.36",
    },
    "embedded": {
        "os": "Windows", "browser": "Discord Client", "device": "",
        "label": "Embedded", "browser_version": "1.0.9191",
        "os_version": "10.0.22631", "client_build_number": 360032,
        "browser_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9191 Chrome/130.0.0.0 Electron/33.0.0 Safari/537.36",
    },
}



_POOL = {
    "mode": "sticky",
    "keys": ["desktop"],
    "pool": [],
    "cursor": 0,
    "last": None,
    "forced_props": None,
}
_STATS = {"identifies": 0, "reconnects": 0}
_COG = [None]
_PATCH = {"path": None, "json": False, "as_json": False, "identify": False}


def _props_from_preset(preset):
    if not isinstance(preset, dict):
        preset = {}
    os_name = preset.get("os") or "Windows"
    browser = preset.get("browser") or "Discord Client"
    device = preset.get("device") or ""
    bv = str(preset.get("browser_version") or "1.0.9191")
    ov = str(preset.get("os_version") or "10")
    try:
        build = int(preset.get("client_build_number") or 360032)
    except Exception:
        build = 360032
    ua = preset.get("browser_user_agent")
    if not ua:
        if os_name == "Android" or "Android" in str(browser):
            ua = "Discord-Android/%s" % bv
        elif os_name == "iOS" or "iOS" in str(browser):
            ua = "Discord/%s CFNetwork/1490 Darwin/23.6.0" % bv
        elif browser == "Chrome":
            ua = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/%s Safari/537.36" % bv
            )
        else:
            ua = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) discord/%s Chrome/130.0.0.0 Electron/33.0.0 Safari/537.36" % bv
            )
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
        "client_build_number": build,
        "client_event_source": None,
        "has_client_mods": False,
        "client_app_state": "focused",
        "client_version": bv,
    }
    if os_name in ("Android", "iOS"):
        props["device"] = device or ("Android" if os_name == "Android" else "iPhone")
        # mobile clients must not look like desktop electron
        props.pop("os_arch", None)
        props.pop("app_arch", None)
        props.pop("runtime_environment", None)
    else:
        props["os_arch"] = "x64"
        props["app_arch"] = "x64"
        props["runtime_environment"] = "native"
    return props


def _pick():
    pool = _POOL.get("pool") or []
    if not pool:
        return _POOL.get("last")
    mode = _POOL.get("mode") or "sticky"
    if mode == "sticky":
        return pool[0]
    if mode == "random":
        return random.choice(pool)
    idx = _POOL["cursor"] % len(pool)
    _POOL["cursor"] = idx + 1
    return pool[idx]


def _set_pool(keys):
    keys = [k for k in keys if k in PLATFORM_PRESETS]
    _POOL["keys"] = keys
    _POOL["pool"] = [PLATFORM_PRESETS[k] for k in keys]
    _POOL["cursor"] = 0


def _arm_props(preset):
    props = _props_from_preset(preset)
    _POOL["last"] = preset
    _POOL["forced_props"] = props
    return props


def _apply_to_payload(data):
    if not isinstance(data, dict):
        return data
    if data.get("op") not in (2, "2"):
        return data
    props = _POOL.get("forced_props")
    if not props:
        last = _POOL.get("last")
        if last:
            props = _props_from_preset(last)
    if not props:
        return data
    d = dict(data.get("d") or {})
    d["properties"] = dict(props)
    d["client_properties"] = dict(props)
    out = dict(data)
    out["d"] = d
    _STATS["identifies"] += 1
    print(
        "[spoofer] IDENTIFY inject os=%s browser=%s device=%s"
        % (props.get("os"), props.get("browser"), props.get("device") or "-")
    )
    return out


def _stamp_connection(bot, props):
    """Write props onto library objects that identify() may read."""
    if not props:
        return
    targets = [bot]
    for name in ("_connection", "ws", "http"):
        obj = getattr(bot, name, None)
        if obj is not None:
            targets.append(obj)
    conn = getattr(bot, "_connection", None)
    if conn is not None:
        for name in ("ws", "_ws", "http"):
            obj = getattr(conn, name, None)
            if obj is not None:
                targets.append(obj)
    for obj in targets:
        for attr in (
            "_client_properties",
            "client_properties",
            "_connection_properties",
            "cached_properties",
        ):
            try:
                setattr(obj, attr, dict(props))
            except Exception:
                pass
        # some forks store under _connection._client
        try:
            setattr(obj, "_wilt_spoof_props", dict(props))
        except Exception:
            pass
    # HTTP headers
    try:
        http = getattr(bot, "http", None)
        if http is not None:
            ua = props.get("browser_user_agent")
            xsp = base64.b64encode(
                json.dumps(props, separators=(",", ":")).encode("utf-8")
            ).decode("ascii")
            if hasattr(http, "headers") and isinstance(http.headers, dict):
                if ua:
                    http.headers["User-Agent"] = ua
                http.headers["X-Super-Properties"] = xsp
            for attr, val in (
                ("_super_properties", props),
                ("super_properties", props),
                ("encoded_super_properties", xsp),
                ("_super_properties_b64", xsp),
                ("user_agent", ua),
            ):
                if hasattr(http, attr):
                    try:
                        setattr(http, attr, val)
                    except Exception:
                        pass
    except Exception as e:
        print("[spoofer] http stamp:", e)


def _install_patches():
    try:
        from discord.gateway import DiscordWebSocket as WS
    except Exception as e:
        print("[spoofer] no DiscordWebSocket:", e)
        return False

    # send_as_json / send_json
    for meth in ("send_as_json", "send_json"):
        flag = "_wilt_spoof_%s" % meth
        if getattr(WS, flag, False):
            continue
        orig = getattr(WS, meth, None)
        if orig is None:
            continue

        def _make(o):
            async def _wrapped(self, data, *a, **k):
                try:
                    data = _apply_to_payload(data)
                except Exception as e:
                    print("[spoofer] payload patch:", e)
                return await o(self, data, *a, **k)

            return _wrapped

        try:
            setattr(WS, meth, _make(orig))
            setattr(WS, flag, True)
            print("[spoofer] patched WS.%s" % meth)
        except Exception as e:
            print("[spoofer] patch %s fail: %s" % (meth, e))

    # identify() — rewrite after original builds payload if we can wrap it
    if not getattr(WS, "_wilt_spoof_identify", False):
        orig_id = getattr(WS, "identify", None)
        if orig_id is not None:

            async def _identify_wrapped(self, *a, **k):
                # stamp props on self before identify runs
                props = _POOL.get("forced_props")
                if props:
                    for attr in (
                        "_client_properties",
                        "client_properties",
                        "_connection_properties",
                    ):
                        try:
                            setattr(self, attr, dict(props))
                        except Exception:
                            pass
                    conn = getattr(self, "_connection", None)
                    if conn is not None:
                        for attr in ("_client_properties", "client_properties"):
                            try:
                                setattr(conn, attr, dict(props))
                            except Exception:
                                pass
                return await orig_id(self, *a, **k)

            try:
                WS.identify = _identify_wrapped
                WS._wilt_spoof_identify = True
                print("[spoofer] patched WS.identify")
            except Exception as e:
                print("[spoofer] identify patch fail:", e)

    return True


def _wipe_resume_state(bot):
    targets = []
    for name in ("ws", "_connection"):
        obj = getattr(bot, name, None)
        if obj is not None:
            targets.append(obj)
    conn = getattr(bot, "_connection", None)
    if conn is not None:
        targets.append(conn)
        for sub in ("ws", "_ws", "gateway"):
            inner = getattr(conn, sub, None)
            if inner is not None:
                targets.append(inner)
    for obj in targets:
        for attr in (
            "session_id",
            "_session_id",
            "sessionID",
            "sequence",
            "_sequence",
            "seq",
            "resume_gateway_url",
            "_resume_gateway_url",
        ):
            if hasattr(obj, attr):
                try:
                    setattr(obj, attr, None)
                except Exception:
                    pass


class SpooferCog(commands.Cog, name="spoofer"):
    def __init__(self, bot):
        self.bot = bot
        self._last_props = None
        _COG[0] = self
        if not _POOL["pool"] and "desktop" in PLATFORM_PRESETS:
            _set_pool(["desktop"])
        _install_patches()

    @commands.Cog.listener()
    async def on_ready(self):
        _install_patches()
        # if we have forced props, re-stamp every ready
        props = _POOL.get("forced_props")
        if props:
            _stamp_connection(self.bot, props)
            print(
                "[spoofer] on_ready armed os=%s device=%s"
                % (props.get("os"), props.get("device") or "-")
            )

    @commands.Cog.listener()
    async def on_resumed(self):
        # resume does NOT send new properties — force hard reconnect if spoof armed
        props = _POOL.get("forced_props")
        if not props:
            return
        print("[spoofer] RESUMED with spoof armed — forcing full IDENTIFY")
        await self._hard_reconnect()

    async def _hard_reconnect(self):
        _STATS["reconnects"] += 1
        bot = self.bot
        props = _POOL.get("forced_props")
        if props:
            _stamp_connection(bot, props)
        _install_patches()
        _wipe_resume_state(bot)
        closed = False
        targets = []
        ws = getattr(bot, "ws", None)
        if ws is not None:
            targets.append(ws)
        conn = getattr(bot, "_connection", None)
        if conn is not None:
            for sub in ("ws", "_ws"):
                inner = getattr(conn, sub, None)
                if inner is not None:
                    targets.append(inner)
        for obj in targets:
            close = getattr(obj, "close", None)
            if close is None:
                continue
            try:
                res = close(code=4000)
                if asyncio.iscoroutine(res):
                    await res
                print("[spoofer] ws closed 4000 (no resume)")
                closed = True
                break
            except TypeError:
                try:
                    res = close()
                    if asyncio.iscoroutine(res):
                        await res
                    print("[spoofer] ws closed")
                    closed = True
                    break
                except Exception as e:
                    print("[spoofer] close:", e)
            except Exception as e:
                print("[spoofer] close:", e)
        await asyncio.sleep(0.6)
        _install_patches()
        if props:
            _stamp_connection(bot, props)
        if not closed:
            print("[spoofer] no ws close handle — props armed for next identify")
        # second pass: library may recreate ws quickly with resume — wipe again
        await asyncio.sleep(0.4)
        _wipe_resume_state(bot)
        if props:
            _stamp_connection(bot, props)
        _install_patches()

    async def _apply(self, key, ctx=None):
        key = (key or "").lower().strip()
        # aliases
        aliases = {
            "vr": "quest3" if "quest3" in PLATFORM_PRESETS else "vr",
            "quest": "quest3" if "quest3" in PLATFORM_PRESETS else "quest",
            "q3": "quest3" if "quest3" in PLATFORM_PRESETS else "quest",
            "q2": "quest2",
            "phone": "mobile",
            "android": "android" if "android" in PLATFORM_PRESETS else "mobile",
            "iphone": "ios",
            "pc": "desktop",
            "win": "desktop",
            "windows": "windows" if "windows" in PLATFORM_PRESETS else "desktop",
            "mac": "macos",
            "browser": "web",
            "chrome": "web",
            "ps5": "playstation",
            "ps4": "playstation",
            "playstation": "playstation",
            "ps": "ps" if "ps" in PLATFORM_PRESETS else "playstation",
        }
        key = aliases.get(key, key)
        if key not in PLATFORM_PRESETS:
            return False, "unknown platform: %s" % key
        preset = PLATFORM_PRESETS[key]
        props = _arm_props(preset)
        _set_pool([key])
        _POOL["mode"] = "sticky"
        self._last_props = props
        _stamp_connection(self.bot, props)
        _install_patches()
        await self._hard_reconnect()
        label = preset.get("label") or key
        return True, "%s | os=%s browser=%s device=%s" % (
            label,
            props.get("os"),
            props.get("browser"),
            props.get("device") or "-",
        )

    @commands.command(name="spoof", aliases=["spoofer", "device"])
    async def spoof(self, ctx, platform: str = "", sub: str = ""):
        p = (platform or "").lower().strip()
        if not p or p in ("status", "info"):
            props = _POOL.get("forced_props") or self._last_props or {}
            last = _POOL.get("last") or {}
            rows = [
                "  last %s" % (last.get("label") or "-"),
                "  os %s" % (props.get("os") or "-"),
                "  browser %s" % (props.get("browser") or "-"),
                "  device %s" % (props.get("device") or "-"),
                "  identifies %d" % _STATS["identifies"],
                "  reconnects %d" % _STATS["reconnects"],
                "  valid %s" % ", ".join(sorted(PLATFORM_PRESETS.keys())),
            ]
            return await S.safe_edit(ctx.message, S.ui_box("spoof status", rows))
        if p == "list":
            return await S.safe_edit(
                ctx.message, S.ui_ok(", ".join(sorted(PLATFORM_PRESETS.keys())))
            )
        if p == "reset":
            p = "desktop"
        ok, msg = await self._apply(p, ctx)
        if not ok:
            return await S.safe_edit(ctx.message, S.ui_err(msg))
        try:
            await S.safe_edit(ctx.message, S.ui_ok("spoof FORCED → %s\nreconnecting..." % msg))
        except Exception:
            await S.safe_send(ctx.channel, S.ui_ok("spoof → %s" % msg))

    @commands.command(name="vr", brief="Spoof Meta Quest (Android)")
    async def vr(self, ctx):
        key = "quest3" if "quest3" in PLATFORM_PRESETS else "vr"
        ok, msg = await self._apply(key, ctx)
        await S.safe_edit(ctx.message, S.ui_ok(msg) if ok else S.ui_err(msg))

    @commands.command(name="spoofmobile", aliases=["spoofphone"])
    async def spoofmobile(self, ctx):
        ok, msg = await self._apply("mobile", ctx)
        await S.safe_edit(ctx.message, S.ui_ok(msg) if ok else S.ui_err(msg))

    @commands.command(name="spoofios")
    async def spoofios(self, ctx):
        ok, msg = await self._apply("ios", ctx)
        await S.safe_edit(ctx.message, S.ui_ok(msg) if ok else S.ui_err(msg))



    @commands.command(name='spoofdesktop', aliases=['spoofpc', 'spoofwin'])
    async def spoofdesktop(self, ctx):
        ok, msg = await self._apply('desktop', ctx)
        await S.safe_edit(ctx.message, S.ui_ok(msg) if ok else S.ui_err(msg))

    @commands.command(name='spoofweb', aliases=['spoofbrowser'])
    async def spoofweb(self, ctx):
        ok, msg = await self._apply('web', ctx)
        await S.safe_edit(ctx.message, S.ui_ok(msg) if ok else S.ui_err(msg))

    @commands.command(name='spoofmacos', aliases=['spoofmac'])
    async def spoofmacos(self, ctx):
        ok, msg = await self._apply('macos', ctx)
        await S.safe_edit(ctx.message, S.ui_ok(msg) if ok else S.ui_err(msg))

    @commands.command(name='spooflinux')
    async def spooflinux(self, ctx):
        ok, msg = await self._apply('linux', ctx)
        await S.safe_edit(ctx.message, S.ui_ok(msg) if ok else S.ui_err(msg))

    @commands.command(name='spoofandroid')
    async def spoofandroid(self, ctx):
        ok, msg = await self._apply('android', ctx)
        await S.safe_edit(ctx.message, S.ui_ok(msg) if ok else S.ui_err(msg))

    @commands.command(name='spoofipad')
    async def spoofipad(self, ctx):
        ok, msg = await self._apply('ipad', ctx)
        await S.safe_edit(ctx.message, S.ui_ok(msg) if ok else S.ui_err(msg))

    @commands.command(name='spoofquest', aliases=['spoofquest3'])
    async def spoofquest(self, ctx):
        key = 'quest3' if 'quest3' in PLATFORM_PRESETS else 'quest'
        ok, msg = await self._apply(key, ctx)
        await S.safe_edit(ctx.message, S.ui_ok(msg) if ok else S.ui_err(msg))

    @commands.command(name='spoofquest2')
    async def spoofquest2(self, ctx):
        ok, msg = await self._apply('quest2', ctx)
        await S.safe_edit(ctx.message, S.ui_ok(msg) if ok else S.ui_err(msg))

    @commands.command(name='spoofconsole')
    async def spoofconsole(self, ctx):
        ok, msg = await self._apply('console', ctx)
        await S.safe_edit(ctx.message, S.ui_ok(msg) if ok else S.ui_err(msg))

    @commands.command(name='spoofxbox')
    async def spoofxbox(self, ctx):
        ok, msg = await self._apply('xbox', ctx)
        await S.safe_edit(ctx.message, S.ui_ok(msg) if ok else S.ui_err(msg))

    @commands.command(name='spoofps', aliases=['spoofplaystation'])
    async def spoofps(self, ctx):
        ok, msg = await self._apply('playstation', ctx)
        await S.safe_edit(ctx.message, S.ui_ok(msg) if ok else S.ui_err(msg))

    @commands.command(name='spoofhard')
    async def spoofhard(self, ctx, platform: str = 'mobile'):
        # same path as .spoof — explicit name for force
        ok, msg = await self._apply(platform, ctx)
        await S.safe_edit(ctx.message, S.ui_ok('HARD ' + msg) if ok else S.ui_err(msg))


async def setup(bot):
    if "spoofer" in bot.cogs:
        await bot.remove_cog("spoofer")
    await bot.add_cog(SpooferCog(bot))
    _install_patches()
