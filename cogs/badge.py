
import discord
from discord.ext import commands
from . import state as S


class BadgeCog(commands.Cog, name="badge"):
    """Activity / rich presence helpers inspired by badge tools."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="playas", aliases=["gameas"], brief="Set playing activity name")
    async def playas(self, ctx, *, name: str):
        try:
            await self.bot.change_presence(activity=discord.Game(name=name[:120]))
            await ctx.send(S.ui_ok(f"playing {name[:80]}"), delete_after=8)
        except Exception as e:
            await ctx.send(S.ui_err(str(e)[:120]), delete_after=8)

    @commands.command(name="watchas", brief="Set watching activity")
    async def watchas(self, ctx, *, name: str):
        try:
            act = discord.Activity(type=discord.ActivityType.watching, name=name[:120])
            await self.bot.change_presence(activity=act)
            await ctx.send(S.ui_ok(f"watching {name[:80]}"), delete_after=8)
        except Exception as e:
            await ctx.send(S.ui_err(str(e)[:120]), delete_after=8)

    @commands.command(name="listenas", brief="Set listening activity")
    async def listenas(self, ctx, *, name: str):
        try:
            act = discord.Activity(type=discord.ActivityType.listening, name=name[:120])
            await self.bot.change_presence(activity=act)
            await ctx.send(S.ui_ok(f"listening {name[:80]}"), delete_after=8)
        except Exception as e:
            await ctx.send(S.ui_err(str(e)[:120]), delete_after=8)

    @commands.command(name="clearactivity", aliases=["clract"], brief="Clear activity")
    async def clearactivity(self, ctx):
        await self.bot.change_presence(activity=None)
        await ctx.send(S.ui_ok("activity cleared"), delete_after=6)


async def setup(bot):
    await bot.add_cog(BadgeCog(bot))
