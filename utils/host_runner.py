
"""Run extra WiltBot clients for hosted tokens (multi-instance)."""
import asyncio
import logging
import traceback

logger = logging.getLogger("host_runner")

_clients = {}
_lock = asyncio.Lock()


def _mask(t: str) -> str:
    t = t or ""
    if len(t) < 16:
        return "***"
    return f"{t[:10]}…{t[-4:]}"


async def _starter(token: str, prefix: str):
    bot = None
    try:
        from selfbot import WiltBot
        bot = WiltBot()
        try:
            bot.command_prefix = prefix
        except Exception:
            pass
        if token in _clients:
            _clients[token]["bot"] = bot

        import inspect
        login = getattr(bot, "login", None)
        start = getattr(bot, "start", None)

        if login is not None:
            try:
                sig = inspect.signature(login)
                if "bot" in sig.parameters:
                    await login(token, bot=False)
                else:
                    await login(token)
            except TypeError:
                await login(token)
            await bot.connect(reconnect=True)
        elif start is not None:
            # start() blocks until close
            await start(token)
        else:
            raise RuntimeError("no login/start on WiltBot")
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error(f"hosted client {_mask(token)} died: {e}")
        traceback.print_exc()
    finally:
        info = _clients.pop(token, None)
        if bot is not None:
            try:
                await bot.close()
            except Exception:
                pass
        elif info and info.get("bot") is not None:
            try:
                await info["bot"].close()
            except Exception:
                pass


async def start_token(token: str, prefix: str = ".") -> str:
    token = (token or "").strip()
    if not token:
        return "empty token"
    async with _lock:
        if token in _clients:
            task = _clients[token].get("task")
            if task and not task.done():
                return f"already running {_mask(token)}"
            _clients.pop(token, None)
        try:
            task = asyncio.create_task(_starter(token, prefix), name=f"host-{_mask(token)}")
            _clients[token] = {"bot": None, "task": task}
            await asyncio.sleep(3.0)
            if task.done():
                exc = None
                try:
                    exc = task.exception()
                except asyncio.CancelledError:
                    pass
                _clients.pop(token, None)
                if exc:
                    return f"fail {_mask(token)}: {type(exc).__name__}: {exc}"
                return f"fail {_mask(token)}: exited early"
            return f"started {_mask(token)} (connecting…)"
        except Exception as e:
            _clients.pop(token, None)
            return f"fail {_mask(token)}: {e}"


async def stop_token(token: str) -> str:
    token = (token or "").strip()
    async with _lock:
        info = _clients.pop(token, None)
        if not info:
            return f"not running {_mask(token)}"
        task = info.get("task")
        bot = info.get("bot")
        if task and not task.done():
            task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=5)
            except Exception:
                pass
        if bot is not None:
            try:
                await bot.close()
            except Exception:
                pass
        return f"stopped {_mask(token)}"


async def stop_all() -> str:
    tokens = list(_clients.keys())
    n = 0
    for tok in tokens:
        await stop_token(tok)
        n += 1
    return f"stopped {n}"


def status() -> list:
    rows = []
    for tok, info in list(_clients.items()):
        task = info.get("task")
        bot = info.get("bot")
        state = "running" if task and not task.done() else "dead"
        user = getattr(bot, "user", None) if bot else None
        extra = f" as {user}" if user else ""
        rows.append(f"{_mask(tok)} · {state}{extra}")
    return rows


def running_count() -> int:
    return sum(1 for info in _clients.values() if info.get("task") and not info["task"].done())
