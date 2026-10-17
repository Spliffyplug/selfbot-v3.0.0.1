import asyncio, os, discord
from discord.ext import commands
from . import state as S

class DownloadsCog(commands.Cog, name='downloads'):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='download', aliases=['dl'], brief='Download media via yt-dlp')
    async def download(self, ctx, url: str='', fmt: str='mp4'):
        if not url:
            return await S.safe_edit(ctx.message, S.ui_err('usage: download <url> [mp4|mp3]'))
        await S.safe_edit(ctx.message, S.ui_info(f'downloading {url}...'))
        os.makedirs('downloads', exist_ok=True)
        audio = fmt.lower() == 'mp3'
        opts = ['-x', '--audio-format', 'mp3'] if audio else ['-f', 'best']
        cmd = ['yt-dlp'] + opts + ['-o', 'downloads/%(title)s.%(ext)s', url]
        try:
            proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            _, err = await proc.communicate()
            if proc.returncode == 0:
                await S.safe_edit(ctx.message, S.ui_ok('download complete → downloads/'))
            else:
                await S.safe_edit(ctx.message, S.ui_err(f'yt-dlp error: {err.decode()[:200]}'))
        except FileNotFoundError:
            await S.safe_edit(ctx.message, S.ui_err('yt-dlp not installed'))

    @commands.command(name='yt', aliases=['youtube_dl'], brief='Download YouTube video')
    async def yt(self, ctx, url: str=''):
        if not url:
            return await S.safe_edit(ctx.message, S.ui_err('usage: yt <url>'))
        await S.safe_edit(ctx.message, S.ui_info(f'downloading {url}...'))
        os.makedirs('downloads', exist_ok=True)
        cmd = ['yt-dlp', '-f', 'best', '-o', 'downloads/%(title)s.%(ext)s', url]
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        _, err = await proc.communicate()
        if proc.returncode == 0:
            await S.safe_edit(ctx.message, S.ui_ok('downloaded → downloads/'))
        else:
            await S.safe_edit(ctx.message, S.ui_err(f'failed: {err.decode()[:200]}'))

    @commands.command(name='ytaudio', brief='Download YouTube audio as MP3')
    async def ytaudio(self, ctx, url: str=''):
        if not url:
            return await S.safe_edit(ctx.message, S.ui_err('usage: ytaudio <url>'))
        await S.safe_edit(ctx.message, S.ui_info(f'downloading audio...'))
        os.makedirs('downloads', exist_ok=True)
        cmd = ['yt-dlp', '-x', '--audio-format', 'mp3', '-o', 'downloads/%(title)s.%(ext)s', url]
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        _, err = await proc.communicate()
        if proc.returncode == 0:
            await S.safe_edit(ctx.message, S.ui_ok('MP3 saved → downloads/'))
        else:
            await S.safe_edit(ctx.message, S.ui_err(f'failed: {err.decode()[:200]}'))

    @commands.command(name='tiktok', aliases=['ttdown'], brief='Download TikTok video')
    async def tiktok(self, ctx, url: str=''):
        if not url:
            return await S.safe_edit(ctx.message, S.ui_err('usage: tiktok <url>'))
        await S.safe_edit(ctx.message, S.ui_info('downloading TikTok...'))
        os.makedirs('downloads', exist_ok=True)
        cmd = ['yt-dlp', '--no-check-certificate', '-o', 'downloads/%(id)s.%(ext)s', url]
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        _, err = await proc.communicate()
        if proc.returncode == 0:
            await S.safe_edit(ctx.message, S.ui_ok('downloaded → downloads/'))
        else:
            await S.safe_edit(ctx.message, S.ui_err(f'failed: {err.decode()[:200]}'))

    @commands.command(name='ig', aliases=['instagram'], brief='Download Instagram content')
    async def ig(self, ctx, url: str=''):
        if not url:
            return await S.safe_edit(ctx.message, S.ui_err('usage: ig <url>'))
        await S.safe_edit(ctx.message, S.ui_info('downloading Instagram...'))
        os.makedirs('downloads', exist_ok=True)
        cmd = ['yt-dlp', '--cookies-from-browser', 'chrome', '-o', 'downloads/%(id)s.%(ext)s', url]
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        _, err = await proc.communicate()
        if proc.returncode == 0:
            await S.safe_edit(ctx.message, S.ui_ok('downloaded → downloads/'))
        else:
            await S.safe_edit(ctx.message, S.ui_err(f'may need --cookies: {err.decode()[:150]}'))

async def setup(bot):
    await bot.add_cog(DownloadsCog(bot))
