import asyncio, time, discord
from discord.ext import commands
from . import state as S
from .antid import delay, on_rate_limit, jitter

class GeneralCog(commands.Cog, name='general'):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='stats', brief='Account stats')
    async def stats(self, ctx):
        u = ctx.author
        rows = [f'  {S.DIM}tag{S.RESET}      {u}', f'  {S.DIM}id{S.RESET}       {u.id}', f'  {S.DIM}guilds{S.RESET}   {len(self.bot.guilds)}', f'  {S.DIM}latency{S.RESET}  {round(self.bot.latency * 1000)}ms']
        await S.safe_edit(ctx.message, S.ui_box('wilt stats', rows))

    @commands.command(name='clrmsgs', aliases=['clr'], brief='Delete your own messages')
    async def purge(self, ctx, amount: int=10):
        setattr(ctx, '_wilt_skip_delete', True)
        try:
            await ctx.message.delete()
        except Exception:
            pass
        deleted = 0
        async for msg in ctx.channel.history(limit=200):
            if msg.author.id == self.bot.user.id and deleted < amount:
                try:
                    await msg.delete()
                    deleted += 1
                    await delay(0.3, 0.9)
                except Exception as e:
                    if '429' in str(e):
                        await on_rate_limit(5.0)
        conf = await S.safe_send(ctx.channel, S.ui_ok(f'deleted {deleted} message(s)'))
        await asyncio.sleep(3)
        try:
            await conf.delete()
        except Exception:
            pass

    @commands.command(name='snipe', brief='Show last deleted message')
    async def snipe(self, ctx):
        entry = S._snipe_cache.get(ctx.channel.id)
        if not entry:
            return await S.safe_edit(ctx.message, S.ui_info('nothing to snipe'))
        rows = [f'  {S.DIM}author{S.RESET}  {entry.get("author", "?")}', f'  {S.DIM}content{S.RESET} {entry.get("content", "")[:200]}']
        await S.safe_edit(ctx.message, S.ui_box('snipe', rows))

    @commands.command(name='hypesquad', brief='Set HypeSquad house')
    async def hypesquad(self, ctx, house: str=''):
        import aiohttp
        house = house.lower()
        houses = {'bravery': 1, 'brilliance': 2, 'balance': 3}
        hid = houses.get(house)
        if not hid:
            return await S.safe_edit(ctx.message, S.ui_err('usage: hypesquad <bravery|brilliance|balance>'))
        h = {'Authorization': S._get_token(), 'Content-Type': 'application/json', 'User-Agent': S.USER_AGENT}
        async with aiohttp.ClientSession() as s:
            async with s.post('https://discord.com/api/v9/hypesquad/online', headers=h, json={'house_id': hid}) as r:
                if r.status in (200, 204):
                    await S.safe_edit(ctx.message, S.ui_ok(f'HypeSquad → {house.title()}'))
                else:
                    await S.safe_edit(ctx.message, S.ui_err(f'failed ({r.status})'))

    @commands.command(name='firstmessage', aliases=['fm'], brief='Jump to first message')
    async def firstmessage(self, ctx):
        async for msg in ctx.channel.history(limit=1, oldest_first=True):
            await S.safe_edit(ctx.message, msg.jump_url)

    @commands.command(name='say', brief='Send a message as yourself')
    async def say(self, ctx, *, text: str=''):
        await ctx.message.delete()
        if text:
            await S.safe_send(ctx.channel, text)

    @commands.command(name='copycat', brief='Repeat the last message in channel')
    async def copycat(self, ctx):
        async for msg in ctx.channel.history(limit=5):
            if msg.id != ctx.message.id and msg.content:
                await S.safe_edit(ctx.message, msg.content)
                return
        await S.safe_edit(ctx.message, S.ui_err('nothing to copy'))

    @commands.command(name='spam', brief='Spam message N times (main + hosted tokens)')
    async def spam(self, ctx, n: int=5, *, text: str=''):
        if not text:
            return await S.safe_edit(ctx.message, S.ui_err('usage: spam <count> <text>'))
        try:
            n = int(n)
        except (TypeError, ValueError):
            return await S.safe_edit(ctx.message, S.ui_err('usage: spam <count> <text>'))
        n = max(1, min(n, 500))
        channel_id = str(ctx.channel.id)
        try:
            await ctx.message.delete()
        except Exception:
            pass
        import aiohttp
        import asyncio as _a
        tokens = []
        main = S._get_token(self.bot)
        if main:
            tokens.append(main)
        for t in list(getattr(S, 'HOSTED_TOKENS', []) or []):
            t = str(t).strip()
            if t and t not in tokens:
                tokens.append(t)
        ua = getattr(S, 'USER_AGENT', 'Mozilla/5.0')
        sent = 0
        failed = 0
        url = f'https://discord.com/api/v9/channels/{channel_id}/messages'

        async def _send_one(session, token, content):
            headers = {'Authorization': token, 'Content-Type': 'application/json', 'User-Agent': ua}
            try:
                async with session.post(url, headers=headers, json={'content': content}) as r:
                    if r.status in (200, 201):
                        return True
                    if r.status == 429:
                        try:
                            data = await r.json()
                            await on_rate_limit(float(data.get('retry_after', 3)))
                        except Exception:
                            await on_rate_limit(3.0)
                    return False
            except Exception:
                return False
        if len(tokens) > 1:
            async with aiohttp.ClientSession() as session:
                for i in range(n):
                    token = tokens[i % len(tokens)]
                    ok = await _send_one(session, token, text)
                    if ok:
                        sent += 1
                    else:
                        failed += 1
                    await _a.sleep(jitter(0.08))
        else:

            async def _one():
                nonlocal sent, failed
                try:
                    await S.safe_send(ctx.channel, text)
                    sent += 1
                except Exception:
                    failed += 1
            wave = 6
            for start in range(0, n, wave):
                batch = [_one() for _ in range(min(wave, n - start))]
                await _a.gather(*batch)
                if start + wave < n:
                    await _a.sleep(jitter(0.05))
        conf = await ctx.channel.send(S.ui_ok(f'spam done | sent {sent}/{n} | tokens {len(tokens)} | fail {failed}'))
        await _a.sleep(4)
        try:
            await conf.delete()
        except Exception:
            pass

    @commands.command(name='spamstop', brief='Spam stop hint')
    async def spamstop(self, ctx):
        await S.safe_edit(ctx.message, S.ui_info('stop active tasks with .task clear / restart bot'))

    @commands.command(name='hostspam', aliases=['hspam'], brief='Spam only with hosted tokens')
    async def hostspam(self, ctx, n: int=5, *, text: str=''):
        if not text:
            return await S.safe_edit(ctx.message, S.ui_err('usage: hostspam <count> <text>'))
        try:
            n = int(n)
        except (TypeError, ValueError):
            return await S.safe_edit(ctx.message, S.ui_err('usage: hostspam <count> <text>'))
        n = max(1, min(n, 500))
        tokens = [str(t).strip() for t in getattr(S, 'HOSTED_TOKENS', []) or [] if str(t).strip()]
        if not tokens:
            return await S.safe_edit(ctx.message, S.ui_err('no hosted tokens - .hostadd <token>'))
        channel_id = str(ctx.channel.id)
        try:
            await ctx.message.delete()
        except Exception:
            pass
        import aiohttp
        import asyncio as _a
        ua = getattr(S, 'USER_AGENT', 'Mozilla/5.0')
        url = f'https://discord.com/api/v9/channels/{channel_id}/messages'
        sent = failed = 0
        async with aiohttp.ClientSession() as session:
            for i in range(n):
                token = tokens[i % len(tokens)]
                headers = {'Authorization': token, 'Content-Type': 'application/json', 'User-Agent': ua}
                try:
                    async with session.post(url, headers=headers, json={'content': text}) as r:
                        if r.status in (200, 201):
                            sent += 1
                        elif r.status == 429:
                            try:
                                data = await r.json()
                                await on_rate_limit(float(data.get('retry_after', 3)))
                            except Exception:
                                await on_rate_limit(3.0)
                            failed += 1
                        else:
                            failed += 1
                except Exception:
                    failed += 1
                await _a.sleep(jitter(0.08))
        conf = await ctx.channel.send(S.ui_ok(f'hostspam done | sent {sent}/{n} | hosts {len(tokens)} | fail {failed}'))
        await _a.sleep(4)
        try:
            await conf.delete()
        except Exception:
            pass

    @commands.command(name='info', brief='Bot info')
    async def info(self, ctx):
        await S.safe_edit(ctx.message, S.ui_box('wilt', [f'  {S.DIM}version{S.RESET}  {S.VERSION}', f'  {S.DIM}lib{S.RESET}      discord.py-self', f'  {S.DIM}guilds{S.RESET}   {len(self.bot.guilds)}', f'  {S.DIM}latency{S.RESET}  {round(self.bot.latency * 1000)}ms']))

    @commands.command(name='purgeall', brief='Delete ALL your messages in channel')
    async def purgeall(self, ctx):
        await ctx.message.delete()
        import asyncio as _a
        deleted = 0
        async for msg in ctx.channel.history(limit=1000):
            if msg.author.id == self.bot.user.id:
                try:
                    await msg.delete()
                    deleted += 1
                except Exception:
                    pass
                await _a.sleep(0.3)
        m = await S.safe_send(ctx.channel, S.ui_ok(f'deleted {deleted}'))
        await _a.sleep(3)
        try:
            await m.delete()
        except Exception:
            pass

    @commands.command(name='readlog', brief="Show the bot's log file tail")
    async def readlog(self, ctx, n: int=10):
        import os
        lf = getattr(S, 'LOG_FILE', 'wilt.log')
        if not os.path.exists(lf):
            return await S.safe_edit(ctx.message, S.ui_err('no log file'))
        with open(lf, 'r', errors='replace') as f:
            lines = f.readlines()
        tail = ''.join(lines[-n:])[-1900:]
        nl = chr(10)
        await S.safe_edit(ctx.message, f'```{nl}{tail}{nl}```')

    @commands.command(name='sniper', brief='Toggle nitro/giveaway sniper')
    async def sniper(self, ctx, sub: str='', toggle: str=''):
        if sub == 'nitro':
            S._nitrosniper_enabled = toggle.lower() not in ('off', 'disable') if toggle else not S._nitrosniper_enabled
            return await S.safe_edit(ctx.message, S.ui_ok(f"nitro sniper → {('on' if S._nitrosniper_enabled else 'off')}"))
        if sub == 'giveaway':
            S._giveaway_enabled = toggle.lower() not in ('off', 'disable') if toggle else not getattr(S, '_giveaway_enabled', False)
            return await S.safe_edit(ctx.message, S.ui_ok(f"giveaway sniper → {('on' if S._giveaway_enabled else 'off')}"))
        await S.safe_edit(ctx.message, S.ui_box('snipers', [f'  {S.DIM}nitro{S.RESET}    {S._nitrosniper_enabled}', f"  {S.DIM}giveaway{S.RESET} {getattr(S, '_giveaway_enabled', False)}"]))

    @commands.command(name='report', brief='Report a user via Discord API')
    async def report(self, ctx, user: discord.User=None, reason: str='spam'):
        if not user:
            return await S.safe_edit(ctx.message, S.ui_err('usage: report <@user> [spam|illegal|harassment|malware]'))
        reason_map = {'spam': 1, 'illegal': 3, 'harassment': 4, 'malware': 5, 'other': 1}
        key = (reason or 'spam').lower()
        reason_type = reason_map.get(key, 1)
        token = S._get_token(self.bot)
        headers = {'Authorization': token, 'Content-Type': 'application/json', 'User-Agent': getattr(S, 'USER_AGENT', 'Mozilla/5.0')}
        import aiohttp
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(f'https://discord.com/api/v9/users/{user.id}/report', headers=headers, json={'reason': reason_type, 'version': '1.0'}) as r:
                    if r.status in (200, 201, 204):
                        await S.safe_edit(ctx.message, S.ui_ok(f'reported {user} ({key})'))
                    elif r.status == 429:
                        await S.safe_edit(ctx.message, S.ui_err('rate limited'))
                    else:
                        await S.safe_edit(ctx.message, S.ui_err(f'report failed ({r.status})'))
        except Exception as e:
            await S.safe_edit(ctx.message, S.ui_err(str(e)[:120]))

async def setup(bot):
    await bot.add_cog(GeneralCog(bot))
