"""Bot category — thin alias so COGS list can load cogs.bot."""
async def setup(bot):
    # botbridge may already be loaded under cogs.botbridge
    if "botbridge" in bot.cogs or "cogs.botbridge" in getattr(bot, "extensions", {}):
        return
    from .botbridge import setup as _bb_setup
    await _bb_setup(bot)
