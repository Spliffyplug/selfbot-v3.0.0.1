async def setup(bot):
    if 'botbridge' in bot.cogs or 'cogs.botbridge' in getattr(bot, 'extensions', {}):
        return
    from .botbridge import setup as _bb_setup
    await _bb_setup(bot)
