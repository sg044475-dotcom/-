import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        
        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

@bot.event
async def on_ready():
    print(f'{bot.user} 봇이 켜졌습니다!')

@bot.event
async def on_message(message):
    print(f"메시지 받음: {message.author} - {message.content}")
    if message.author == bot.user:
        return
    await bot.process_commands(message)

@bot.command(name="실행")
async def play(ctx, url: str):
    print(f"명령어 받음: {ctx.author}가 {url} 요청")
    if not ctx.message.author.voice:
        await ctx.send("먼저 음성 채널에 입장해야 합니다.")
        return

    channel = ctx.message.author.voice.channel
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if not voice_client:
        voice_client = await channel.connect()

    async with ctx.typing():
        try:
            player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
            voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
            await ctx.send(f'재생 중: {player.title}')
        except Exception as e:
            print(f"재생 에러: {e}")
            await ctx.send(f"재생 실패: {str(e)}")

@bot.command(name="멈춰")
async def stop(ctx):
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    
    if voice_client and voice_client.is_connected():
        await voice_client.disconnect()
        await ctx.send("음악을 멈추고 봇이 퇴장했습니다.")
    else:
        await ctx.send("봇이 음성 채널에 있지 않습니다.")

bot_token = os.getenv('DISCORD_TOKEN')
if not bot_token:
    raise ValueError("DISCORD_TOKEN이 .env 파일에 설정되지 않았습니다!")
bot.run(bot_token)
