import asyncio
import random
import time
CFG = {'batch_min': 1.2, 'batch_max': 3.8, 'burst_every': 5, 'burst_min': 4.0, 'burst_max': 9.0, 'jitter_pct': 0.25, 'typo_chance': 0.0}

def jitter(base: float, pct: float | None=None) -> float:
    p = pct if pct is not None else CFG['jitter_pct']
    return base * (1 + random.uniform(-p, p))

async def delay(min_s: float | None=None, max_s: float | None=None):
    lo = min_s if min_s is not None else CFG['batch_min']
    hi = max_s if max_s is not None else CFG['batch_max']
    await asyncio.sleep(random.uniform(lo, hi))

async def batch_delay(n: int=1):
    if n > 0 and n % CFG['burst_every'] == 0:
        await asyncio.sleep(random.uniform(CFG['burst_min'], CFG['burst_max']))
    else:
        await asyncio.sleep(random.uniform(CFG['batch_min'], CFG['batch_max']))

def shuffled(seq):
    lst = list(seq)
    random.shuffle(lst)
    return lst

async def on_rate_limit(retry_after: float):
    wait = retry_after + random.uniform(1.0, 3.0)
    print(f'[antid] rate limited - waiting {wait:.1f}s')
    await asyncio.sleep(wait)

def rand_interval(base_minutes: float) -> float:
    base_s = base_minutes * 60
    return jitter(base_s, CFG['jitter_pct'])
