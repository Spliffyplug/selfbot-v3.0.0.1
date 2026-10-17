import asyncio, discord
from discord.ext import commands
from . import state as S
from .antid import jitter
_typing_tasks: dict = {}

async def _typing_loop(channel_id: int, token: str, user_agent: str):
    import aiohttp, random
    url = f'https://discord.com/api/v9/channels/{channel_id}/typing'
    h = {'Authorization': token, 'User-Agent': user_agent}
    async with aiohttp.ClientSession() as s:
        while True:
            try:
                async with s.post(url, headers=h) as r:
                    pass
            except asyncio.CancelledError:
                raise
            except Exception as e:
                print(f'[typing] {e}')
            interval = jitter(8.0)
            if random.random() < 0.08:
                interval += random.uniform(4.0, 12.0)
            await asyncio.sleep(interval)

class UtilityCog(commands.Cog, name='utility'):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='typing', brief='Start typing indicator')
    async def typing_start(self, ctx):
        cid = ctx.channel.id
        if cid in _typing_tasks and (not _typing_tasks[cid].done()):
            return await S.safe_edit(ctx.message, S.ui_info('already typing here'))
        await ctx.message.delete()
        _typing_tasks[cid] = asyncio.create_task(_typing_loop(cid, S.TOKEN, S.USER_AGENT))

    @commands.command(name='typingstop', brief='Stop typing indicator')
    async def typing_stop(self, ctx):
        t = _typing_tasks.pop(ctx.channel.id, None)
        if t and (not t.done()):
            t.cancel()
        await S.safe_edit(ctx.message, S.ui_ok('typing stopped'))

    @commands.command(name='uwuify', brief='UwU-ify text')
    async def uwuify(self, ctx, *, text: str=''):
        if not text:
            return await S.safe_edit(ctx.message, S.ui_err('usage: uwuify <text>'))
        result = text.replace('r', 'w').replace('R', 'W').replace('l', 'w').replace('L', 'W')
        await S.safe_edit(ctx.message, result)

    @commands.command(name='owoify', brief='OwO-ify text')
    async def owoify(self, ctx, *, text: str=''):
        if not text:
            return await S.safe_edit(ctx.message, S.ui_err('usage: owoify <text>'))
        result = text.replace('r', 'w').replace('l', 'w').replace('R', 'W').replace('L', 'W')
        await S.safe_edit(ctx.message, result + ' owo')

    @commands.command(name='mock', brief='Mock text')
    async def mock(self, ctx, *, text: str=''):
        if not text:
            return await S.safe_edit(ctx.message, S.ui_err('usage: mock <text>'))
        result = ''.join((c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(text)))
        await S.safe_edit(ctx.message, result)

    @commands.command(name='reverse', brief='Reverse text')
    async def reverse(self, ctx, *, text: str=''):
        await S.safe_edit(ctx.message, text[::-1] if text else '')

    @commands.command(name='clap', brief='Clap between words')
    async def clap(self, ctx, *, text: str=''):
        await S.safe_edit(ctx.message, ' 👏 '.join(text.split()) if text else '')

    @commands.command(name='aesthetic', brief='Aesthetic text')
    async def aesthetic(self, ctx, *, text: str=''):
        result = ' '.join(text) if text else ''
        await S.safe_edit(ctx.message, result)

    @commands.command(name='ghostping', brief='Ghost ping a user')
    async def ghostping(self, ctx, user: discord.User=None):
        if not user:
            return await S.safe_edit(ctx.message, S.ui_err('usage: ghostping <@user>'))
        await ctx.message.delete()
        m = await ctx.channel.send(user.mention)
        await asyncio.sleep(0.4)
        await m.delete()

    @commands.command(name='trl', aliases=['translatecmd'], brief='Translate text')
    async def translate(self, ctx, lang: str='en', *, text: str=''):
        if not text:
            return await S.safe_edit(ctx.message, S.ui_err('usage: translate <lang> <text>'))
        try:
            from deep_translator import GoogleTranslator
            result = GoogleTranslator(source='auto', target=lang).translate(text)
            await S.safe_edit(ctx.message, f'```\n{result}\n```')
        except ImportError:
            await S.safe_edit(ctx.message, S.ui_err('deep-translator not installed'))
        except Exception as e:
            await S.safe_edit(ctx.message, S.ui_err(str(e)))

    @commands.command(name='pin', brief='Pin the replied-to message')
    @commands.guild_only()
    async def pin(self, ctx):
        ref = ctx.message.reference
        if not ref:
            return await S.safe_edit(ctx.message, S.ui_err('reply to a message to pin it'))
        try:
            msg = await ctx.channel.fetch_message(ref.message_id)
            await msg.pin()
            await S.safe_edit(ctx.message, S.ui_ok('message pinned'))
        except Exception as e:
            await S.safe_edit(ctx.message, S.ui_err(str(e)))

    @commands.command(name='unpin', brief='Unpin the replied-to message')
    @commands.guild_only()
    async def unpin(self, ctx):
        ref = ctx.message.reference
        if not ref:
            return await S.safe_edit(ctx.message, S.ui_err('reply to a message to unpin it'))
        try:
            msg = await ctx.channel.fetch_message(ref.message_id)
            await msg.unpin()
            await S.safe_edit(ctx.message, S.ui_ok('message unpinned'))
        except Exception as e:
            await S.safe_edit(ctx.message, S.ui_err(str(e)))

    @commands.command(name='animatetype', brief='Animate text character by character')
    async def animatetype(self, ctx, *, text: str=''):
        if not text:
            return await S.safe_edit(ctx.message, S.ui_err('usage: animatetype <text>'))
        import asyncio
        for i in range(1, len(text) + 1):
            await S.safe_edit(ctx.message, text[:i])
            await asyncio.sleep(jitter(0.08))

    @commands.command(name='ragebait', brief='Post a random ragebait message')
    async def ragebait(self, ctx):
        import random
        baits = ['pineapple on pizza is actually good', 'tabs are objectively better than spaces', 'the moon landing was faked', 'anime is better than cartoons', 'cats are better than dogs', 'mint chocolate chip is the worst flavor', 'water is wet', 'a hot dog is a sandwich']
        await S.safe_edit(ctx.message, random.choice(baits))

    @commands.command(name='therapy', brief='Send a supportive message')
    async def therapy(self, ctx):
        import random
        messages = ['you got this 💪', "take a deep breath. you're doing great.", 'one step at a time ✨', "it's okay to rest. progress is not linear.", 'you are not your mistakes.', 'your feelings are valid.', 'tomorrow is a new day 🌅']
        await S.safe_edit(ctx.message, random.choice(messages))

    async def _start_bg(self):
        if not getattr(self, '_need_bg', False):
            return
        self._need_bg = False

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            await self._start_bg()
        except Exception:
            pass

    def cog_unload(self):
        for t in _typing_tasks.values():
            if t and (not t.done()):
                t.cancel()
        _typing_tasks.clear()

async def setup(bot):
    await bot.add_cog(UtilityCog(bot))
