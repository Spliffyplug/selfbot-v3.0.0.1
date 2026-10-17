import json
import os
import subprocess
import sys
import urllib.request

def _pip(*args):
    cmd = [sys.executable, '-m', 'pip', 'install', '--quiet', '--no-cache-dir', *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=180)

def ensure_modifyself(log=print) -> bool:
    for name in ('modifyselfclient', 'modifyself'):
        try:
            __import__(name)
            log(f'[modifyself] already present ({name})')
            return True
        except Exception:
            pass
    if os.environ.get("SKIP_MODIFYSELF") == '1':
        log('[modifyself] SKIP_MODIFYSELF=1')
        return False
    log('[modifyself] installing deps + wheel from modifyself.com ...')
    try:
        _pip('PyNaCl', 'msgpack', 'httpx')
    except Exception as e:
        log(f'[modifyself] dep install warn: {e}')
    try:
        with urllib.request.urlopen('https://modifyself.com/get/modifyself', timeout=30) as r:
            data = json.loads(r.read().decode())
        wheel = data.get("wheel") or data.get("url")
        if not wheel:
            log(f'[modifyself] no wheel in response: {data!r}'[:200])
            return False
        log(f'[modifyself] wheel: {wheel[:80]}...')
        res = _pip('--upgrade', wheel)
        if res.returncode != 0:
            log(f"[modifyself] pip failed: {(res.stderr or res.stdout or '')[-300:]}")
            return False
    except Exception as e:
        log(f'[modifyself] skip ({e}) - use built-in spoofer')
        return False
    for name in ('modifyselfclient', 'modifyself', 'modifyself.headers'):
        try:
            __import__(name.split('.')[0])
            log(f'[modifyself] import ok after install')
            return True
        except Exception:
            continue
    try:
        from modifyself.headers import HeaderSpoofer
        log('[modifyself] HeaderSpoofer ok')
        return True
    except Exception as e:
        log(f'[modifyself] installed but import failed: {e}')
        return False
