
import asyncio
import base64
import json
import random
import time

import discord
from discord.ext import commands

from . import state as S

try:
    from cogs.spoofer import PLATFORM_PRESETS, _props_from_preset, _POOL, _patch_http
except Exception:
    PLATFORM_PRESETS = {}
    def _props_from_preset(p):
        return dict(p) if isinstance(p, dict) else {}
    _POOL = {}
    def _patch_http(bot, preset):
        pass

# satellite gateway sessions (extra devices on same token)
_satellites = []


def _token(bot):
    t = getattr(getattr(bot, "http", None), "token", None)
    if not t:
        t = getattr(bot, "http", None)
        t = getattr(t, "_token", None) if t else None
    if not t:
        import os
        t = os.environ.get("TOKEN") or os.environ.get("DISCORD_TOKEN")
    if not t:
        t = getattr(S, "TOKEN", None)
    return t


async def _run_satellite(token: str, props: dict, label: str, stop_event: asyncio.Event):
    """Keep a secondary gateway session alive so Discord lists another device."""
    try:
        import websockets
    except Exception as e:
        print("[multispoof] websockets missing:", e)
        return
    url = "wss://gateway.discord.gg/?v=9&encoding=json"
    ua = props.get("browser_user_agent") or "Discord-Android/252.15"
    backoff = 1.0
    while not stop_event.is_set():
        try:
            async with websockets.connect(
                url,
                additional_headers={"User-Agent": ua, "Origin": "https://discord.com"},
                open_timeout=15,
                close_timeout=3,
                max_size=8 * 1024 * 1024,
            ) as ws:
                raw = await ws.recv()
                hello = json.loads(raw)
                if hello.get("op") != 10:
                    await asyncio.sleep(2)
                    continue
                interval = float(hello.get("d", {}).get("heartbeat_interval", 41250)) / 1000.0
                # mobile/VR vs desktop capabilities differ slightly
                is_mobile = str(props.get("os", "")).lower() in ("android", "ios")
                identify = {
                    "op": 2,
                    "d": {
                        "token": token,
                        "capabilities": 8189 if is_mobile else 16381,
                        "properties": props,
                        "compress": False,
                        "presence": {
                            "status": "online",
                            "since": 0,
                            "activities": [],
                            "afk": False,
                        },
                        "client_state": {
                            "guild_versions": {},
                            "highest_last_message_id": "0",
                            "read_state_version": 0,
                            "user_guild_settings_version": -1,
                            "user_settings_version": -1,
                            "private_channels_version": "0",
                            "api_code_version": 0,
                        },
                    },
                }
                await ws.send(json.dumps(identify))
                print("[multispoof] satellite IDENTIFY sent:", label)
                backoff = 1.0
                last_hb = time.time()
                while not stop_event.is_set():
                    timeout = max(0.5, interval * 0.9 - (time.time() - last_hb))
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=timeout)
                    except asyncio.TimeoutError:
                        await ws.send(json.dumps({"op": 1, "d": None}))
                        last_hb = time.time()
                        continue
                    data = json.loads(msg)
                    op = data.get("op")
                    if op == 10:
                        interval = float(data.get("d", {}).get("heartbeat_interval", 41250)) / 1000.0
                    elif op == 1:
                        await ws.send(json.dumps({"op": 1, "d": None}))
                        last_hb = time.time()
                    elif op == 7:
                        break
                    elif op == 9:
                        # invalid session
                        await asyncio.sleep(2)
                        break
                    elif op == 0 and data.get("t") == "READY":
                        print("[multispoof] satellite READY:", label)
                    if time.time() - last_hb >= interval * 0.9:
                        await ws.send(json.dumps({"op": 1, "d": None}))
                        last_hb = time.time()
        except asyncio.CancelledError:
            return
        except Exception as e:
            print("[multispoof] satellite err %s: %s" % (label, e))
            await asyncio.sleep(backoff)
            backoff = min(30.0, backoff * 1.5)


class MultiSpoofCog(commands.Cog, name="multispoof"):
    def __init__(self, bot):
        self.bot = bot
        self._pool = []
        self._cursor = 0
        self._mode = "multi"
        self._stop = asyncio.Event()
        self._tasks = []

    def cog_unload(self):
        self._stop_all()

    def _stop_all(self):
        self._stop.set()
        for t in list(self._tasks):
            if t and not t.done():
                t.cancel()
        self._tasks.clear()
        self._stop = asyncio.Event()

    async def _start_multi(self, keys):
        self._stop_all()
        token = _token(self.bot)
        if not token:
            raise RuntimeError("no token")
        self._pool = [k for k in keys if k in PLATFORM_PRESETS]
        if not self._pool:
            raise RuntimeError("empty pool")
        # first platform forces main session
        first = self._pool[0]
        preset = PLATFORM_PRESETS[first]
        props = _props_from_preset(preset)
        try:
            _POOL["forced_props"] = props
            _POOL["last"] = preset
            _POOL["mode"] = "sticky"
            _POOL["keys"] = [first]
            _POOL["pool"] = [preset]
        except Exception:
            pass
        try:
            _patch_http(self.bot, preset)
        except Exception:
            pass
        # try force main reconnect via spoofer cog
        sp = self.bot.get_cog("spoofer") or self.bot.get_cog("SpooferCog")
        if sp is not None and hasattr(sp, "_apply_and_reconnect"):
            # apply without message context - call internals
            try:
                await sp._force_identify(preset)
                await sp._reconnect()
            except Exception as e:
                print("[multispoof] main reconnect:", e)
        # satellites for remaining platforms
        for key in self._pool[1:]:
            preset = PLATFORM_PRESETS[key]
            props = _props_from_preset(preset)
            t = asyncio.create_task(
                _run_satellite(token, props, preset.get("label") or key, self._stop)
            )
            self._tasks.append(t)
        return [PLATFORM_PRESETS[k].get("label", k) for k in self._pool]

    @commands.group(name="multispoof", aliases=["mspoof", "ms"], invoke_without_command=True)
    async def multispoof(self, ctx, *args):
        if not args:
            rows = [
                "  mode multi (parallel gateway devices)",
                "  pool %s" % (", ".join(self._pool) or "-"),
                "  sats %d" % len([t for t in self._tasks if t and not t.done()]),
                "  cmds: multi | set | stop | status | list",
            ]
            return await S.safe_edit(ctx.message, S.ui_box("multispoof", rows))

        sub = args[0].lower()
        rest = [a.lower() for a in args[1:]]

        if sub == "list":
            keys = sorted(PLATFORM_PRESETS.keys())
            return await S.safe_edit(
                ctx.message, S.ui_ok("platforms: " + ", ".join(keys))
            )

        if sub == "status":
            rows = [
                "  pool %s" % (", ".join(self._pool) or "-"),
                "  live sats %d" % len([t for t in self._tasks if t and not t.done()]),
            ]
            return await S.safe_edit(ctx.message, S.ui_box("multispoof status", rows))

        if sub == "stop":
            self._stop_all()
            return await S.safe_edit(ctx.message, S.ui_ok("multispoof stopped"))

        if sub in ("multi", "set", "start", "all"):
            platforms = rest
            if not platforms:
                platforms = ["desktop", "mobile", "web"]
            bad = [p for p in platforms if p not in PLATFORM_PRESETS]
            if bad:
                return await S.safe_edit(
                    ctx.message, S.ui_err("unknown: %s" % ", ".join(bad))
                )
            await S.safe_edit(ctx.message, S.ui_info("starting multi-gateway devices..."))
            try:
                labels = await self._start_multi(platforms)
            except Exception as e:
                return await S.safe_send(ctx.channel, S.ui_err(str(e)[:150]))
            return await S.safe_send(
                ctx.channel,
                S.ui_ok(
                    "multi devices: %s  (check Discord Settings → Devices)"
                    % ", ".join(labels)
                ),
            )

        # treat args as platform list
        platforms = [a.lower() for a in args]
        bad = [p for p in platforms if p not in PLATFORM_PRESETS]
        if bad:
            return await S.safe_edit(
                ctx.message,
                S.ui_err("subs: multi | set | stop | status | list  or platforms"),
            )
        await S.safe_edit(ctx.message, S.ui_info("starting multi-gateway devices..."))
        try:
            labels = await self._start_multi(platforms)
        except Exception as e:
            return await S.safe_send(ctx.channel, S.ui_err(str(e)[:150]))
        return await S.safe_send(
            ctx.channel, S.ui_ok("multi devices: %s" % ", ".join(labels))
        )

    @multispoof.command(name="multi")
    async def multi_cmd(self, ctx, *platforms):
        await self.multispoof(ctx, "multi", *platforms)

    @multispoof.command(name="stop")
    async def stop_cmd(self, ctx):
        await self.multispoof(ctx, "stop")

    @multispoof.command(name="status")
    async def status_cmd(self, ctx):
        await self.multispoof(ctx, "status")

    @multispoof.command(name="list")
    async def list_cmd(self, ctx):
        await self.multispoof(ctx, "list")


async def setup(bot):
    if "multispoof" in bot.cogs:
        await bot.remove_cog("multispoof")
    await bot.add_cog(MultiSpoofCog(bot))
