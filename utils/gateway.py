
import base64
import json
import os
from typing import Any

def _ua() -> str:
    return os.environ.get(
        "DISCORD_USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "discord/1.0.9262 Chrome/155.0.0.0 Electron/36.0.0 Safari/537.36",
    )

def client_properties(override=None):
    props = {
        "os": "Windows",
        "browser": "Discord Client",
        "device": "",
        "system_locale": os.environ.get("SYSTEM_LOCALE", "en-US"),
        "has_client_mods": False,
        "browser_user_agent": _ua(),
        "browser_version": "1.0.9262",
        "os_version": "10.0.22631",
        "referrer": "",
        "referring_domain": "",
        "referrer_current": "",
        "referring_domain_current": "",
        "release_channel": "stable",
        "client_build_number": int(os.environ.get("CLIENT_BUILD_NUMBER", "630444") or 630444),
        "client_event_source": None,
        "client_launch_id": os.environ.get("CLIENT_LAUNCH_ID", "wilt-launch"),
        "launch_signature": os.environ.get("LAUNCH_SIGNATURE", "wilt-sig"),
        "client_heartbeat_session_id": os.environ.get("CLIENT_HB_SESSION", "wilt-hb"),
        "client_app_state": "focused",
        "os_arch": "x64",
        "app_arch": "x64",
        "native_build_number": None,
        "client_version": "1.0.9262",
    }
    if isinstance(override, dict):
        props.update(override)
    return props

def encode_super_properties(props=None) -> str:
    props = props or client_properties()
    return base64.b64encode(json.dumps(props, separators=(",", ":")).encode("utf-8")).decode("ascii")

def default_headers(token: str, props=None) -> dict:
    props = props or client_properties()
    xsp = encode_super_properties(props)
    return {
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": props.get("browser_user_agent") or _ua(),
        "X-Super-Properties": xsp,
        "X-Discord-Locale": os.environ.get("SYSTEM_LOCALE", "en-US"),
        "X-Debug-Options": "bugReporterEnabled",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://discord.com",
        "Referer": "https://discord.com/channels/@me",
        "Sec-Ch-Ua": '"Chromium";v="155", "Not_A Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }

def apply_http_headers(bot, props=None) -> bool:
    http = getattr(bot, "http", None)
    if http is None:
        return False
    props = props or client_properties()
    xsp = encode_super_properties(props)
    try:
        if hasattr(http, "headers") and isinstance(http.headers, dict):
            http.headers["User-Agent"] = props.get("browser_user_agent") or _ua()
            http.headers["X-Super-Properties"] = xsp
        for attr, val in (
            ("_super_properties", props),
            ("super_properties", props),
            ("encoded_super_properties", xsp),
            ("_super_properties_b64", xsp),
        ):
            if hasattr(http, attr):
                try:
                    setattr(http, attr, val)
                except Exception:
                    pass
        return True
    except Exception as e:
        print("[gateway] apply_http_headers:", e)
        return False

def install_ws_identify_patch(props=None) -> bool:
    props = props or client_properties()
    try:
        from discord.gateway import DiscordWebSocket as WS
    except Exception as e:
        print("[gateway] no DiscordWebSocket:", e)
        return False
    if getattr(WS, "_wilt_gw_patch", False):
        # refresh fixed props
        WS._wilt_fixed_props = props
        return True
    fixed_props = props
    WS._wilt_fixed_props = props
    for meth_name in ("send_as_json", "send_json"):
        orig = getattr(WS, meth_name, None)
        if orig is None:
            continue

        def _make(o, default_props):
            async def _wrapped(self, data, *a, **k):
                try:
                    if isinstance(data, dict) and data.get("op") in (2, "2"):
                        d = data.get("d")
                        if isinstance(d, dict):
                            d = dict(d)
                            use = getattr(type(self), "_wilt_fixed_props", None) or default_props
                            try:
                                from cogs import spoofer as _sp
                                pool = getattr(_sp, "_POOL", None)
                                if isinstance(pool, dict) and pool.get("forced_props"):
                                    use = pool["forced_props"]
                            except Exception:
                                pass
                            d["properties"] = use
                            d["client_properties"] = use
                            data = dict(data)
                            data["d"] = d
                except Exception:
                    pass
                return await o(self, data, *a, **k)
            return _wrapped

        try:
            setattr(WS, meth_name, _make(orig, fixed_props))
        except Exception as e:
            print("[gateway] patch %s: %s" % (meth_name, e))
            return False
    WS._wilt_gw_patch = True
    print("[gateway] IDENTIFY websocket patch installed")
    return True

async def probe_gateway_ws():
    try:
        import websockets
    except Exception:
        return None
    url = "wss://gateway.discord.gg/?v=9&encoding=json"
    try:
        async with websockets.connect(
            url,
            additional_headers={"User-Agent": _ua(), "Origin": "https://discord.com"},
            open_timeout=10,
            close_timeout=2,
        ) as ws:
            raw = await ws.recv()
            data = json.loads(raw)
            if data.get("op") == 10:
                return "hello hb=%s" % data.get("d", {}).get("heartbeat_interval")
            return "op=%s" % data.get("op")
    except Exception as e:
        return "probe fail: %s" % e
