import asyncio
import discord
from discord.ext import commands
from . import state as S

class ProfileStealCog(commands.Cog, name='profilesteal'):

    def __init__(self, bot):
        self.bot = bot

    def _target(self, ctx, user: discord.User=None, user_id: int=None):
        if user is not None:
            return user
        if user_id is not None:
            return self.bot.get_user(user_id) or discord.Object(id=user_id)
        if ctx.message.mentions:
            return ctx.message.mentions[0]
        return None

    async def _fetch_user(self, uid: int):
        u = self.bot.get_user(uid)
        if u is not None:
            return u
        try:
            return await self.bot.fetch_user(uid)
        except Exception:
            return None

    @commands.command(name='stealavatar', aliases=['copyavatar', 'sa'], brief='Steal avatar from user')
    async def stealavatar(self, ctx, user: discord.User=None, user_id: int=None):
        t = self._target(ctx, user, user_id)
        if t is None:
            return await ctx.send(S.ui_err('mention a user or pass id'), delete_after=8)
        u = await self._fetch_user(getattr(t, 'id', t))
        if u is None:
            return await ctx.send(S.ui_err('user not found'), delete_after=8)
        avatar = u.display_avatar
        if avatar is None:
            return await ctx.send(S.ui_err('no avatar'), delete_after=8)
        try:
            data = await avatar.read()
            await self.bot.user.edit(avatar=data)
            await ctx.send(S.ui_ok(f'avatar set from {u}'), delete_after=10)
        except Exception as e:
            await ctx.send(S.ui_err(str(e)[:120]), delete_after=10)

    @commands.command(name='stealbanner', aliases=['copybanner', 'sbanner'], brief='Steal banner from user')
    async def stealbanner(self, ctx, user: discord.User=None, user_id: int=None):
        t = self._target(ctx, user, user_id)
        if t is None:
            return await ctx.send(S.ui_err('mention a user or pass id'), delete_after=8)
        try:
            u = await self.bot.fetch_user(getattr(t, 'id', t))
        except Exception as e:
            return await ctx.send(S.ui_err(str(e)[:120]), delete_after=8)
        banner = getattr(u, 'banner', None)
        if banner is None:
            return await ctx.send(S.ui_err('user has no banner (or cannot see it)'), delete_after=8)
        try:
            data = await banner.read()
            await self.bot.user.edit(banner=data)
            await ctx.send(S.ui_ok(f'banner set from {u}'), delete_after=10)
        except Exception as e:
            await ctx.send(S.ui_err(str(e)[:120]), delete_after=10)

    @commands.command(name='stealprofile', aliases=['copyprofile', 'sp'], brief='Steal avatar+banner+bio if possible')
    async def stealprofile(self, ctx, user: discord.User=None, user_id: int=None):
        t = self._target(ctx, user, user_id)
        if t is None:
            return await ctx.send(S.ui_err('mention a user or pass id'), delete_after=8)
        try:
            u = await self.bot.fetch_user(getattr(t, 'id', t))
        except Exception as e:
            return await ctx.send(S.ui_err(str(e)[:120]), delete_after=8)
        done = []
        try:
            if u.display_avatar:
                await self.bot.user.edit(avatar=await u.display_avatar.read())
                done.append('avatar')
        except Exception as e:
            done.append(f'avatar-fail:{str(e)[:40]}')
        try:
            if getattr(u, 'banner', None):
                await self.bot.user.edit(banner=await u.banner.read())
                done.append('banner')
        except Exception as e:
            done.append(f'banner-fail:{str(e)[:40]}')
        try:
            profile = getattr(u, 'profile', None)
            if profile is None and hasattr(self.bot, 'http'):
                if hasattr(self.bot, 'fetch_user_profile'):
                    profile = await self.bot.fetch_user_profile(u.id)
            bio = getattr(profile, 'bio', None) if profile else None
            if bio and hasattr(self.bot.user, 'edit'):
                try:
                    await self.bot.user.edit(bio=bio)
                    done.append('bio')
                except Exception:
                    pass
        except Exception:
            pass
        await ctx.send(S.ui_ok(f"profile steal from {u}: {', '.join(done) or 'nothing'}"), delete_after=12)

    @commands.command(name='pstealstatus', aliases=['takestatus', 'copystat'], brief='Copy custom status text from member')
    async def stealstatus(self, ctx, user: discord.Member=None):
        m = user or (ctx.message.mentions[0] if ctx.message.mentions else None)
        if m is None:
            return await ctx.send(S.ui_err('mention a member in this server'), delete_after=8)
        act = None
        for a in m.activities or []:
            if str(getattr(a, 'type', '')).endswith('custom') or getattr(a, 'name', None):
                act = a
                if getattr(a, 'type', None) is not None and int(getattr(a.type, 'value', -1)) == 4:
                    break
        text = getattr(act, 'state', None) or getattr(act, 'name', None)
        if not text:
            return await ctx.send(S.ui_err('no custom status visible'), delete_after=8)
        try:
            await self.bot.change_presence(activity=discord.CustomActivity(name=text))
            await ctx.send(S.ui_ok(f'status → {text[:80]}'), delete_after=10)
        except Exception as e:
            await ctx.send(S.ui_err(str(e)[:120]), delete_after=10)

async def setup(bot):
    await bot.add_cog(ProfileStealCog(bot))
