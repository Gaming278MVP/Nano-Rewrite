import asyncio
import discord
import youtube_dl
from random import shuffle
from async_timeout import timeout

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''

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
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = self.parse_duration(int(data.get('duration')))
        self.thumbnail = data.get('thumbnail')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        # gonna change this later
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

    @staticmethod
    def parse_duration(duration: int):
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        # Create an actual string
        duration = []
        if days > 0:
            duration.append(f'{days} days')
        if hours > 0:
            duration.append(f'{hours} hours')
        if minutes > 0:
            duration.append(f'{minutes} minutes')
        if seconds > 0:
            duration.append(f'{seconds} seconds')

        return ', '.join(duration)

class GuildVoiceState:
    def __init__(self, client):
        self.client = client
        self.current = None # current voice_entry
        self.voice_client = None
        self.queue = [] # voice entries
        self.volume = 0.25
        self.search_result = None
        self.channel = None
        self.skip_votes = set()

    def get_embedded_np(self):
        embed = self.current.create_embed()
        embed.add_field(
            name='Volume',
            value=str(self.volume * 100),
            inline=True
            )
        return embed

    def next(self):
        if self.queue != []:
            next_entry = self.queue.pop(0)
            self.voice_client.play(next_entry.player, after=lambda e: print('Player error: %s' % e) if e else self.next())
            self.voice_client.source.volume = self.volume
            self.current = next_entry
            self.client.loop.create_task(self.notify_np())
        else: # when theres no song to play.. disconnect from voice channel
            self.client.loop.create_task(self.done_playing())

    async def notify_np(self):
        embed = self.get_embedded_np()
        await self.channel.send(embed=embed)

    async def done_playing(self):
        await self.voice_client.disconnect()
        embed = discord.Embed(
            title="Done playing music, leaving the voice channel ~",
            colour=discord.Colour(value=11735575).orange()
            )
        await self.channel.send(embed=embed)

class VoiceEntry:
    def __init__(self, player=None, requester=None, video=None):
        self.player = player
        self.requester = requester
        self.video = video

    def create_embed(self):
        embed = discord.Embed(
            title=':musical_note: Now Playing :musical_note:',
            colour=discord.Colour(value=11735575).orange()
            )
        embed.add_field(
            name='Song',
            value='**{}**'.format(self.player.title),
            inline=False
            )
        embed.add_field(
            name='Requester',
            value=str(self.requester.name),
            inline=True
            )
        embed.add_field(
            name='Duration',
            value=str(self.player.duration),
            inline=True
            )
        if not self.video is None:
            embed.set_thumbnail(url=self.video.thumbnails['high']['url'])
        else:
            embed.set_thumbnail(url=self.player.thumbnail)
        return embed

class AsyncVoiceState:
    def __init__(self, client):
        self.client = client
        self.voice_client = None
        self.volume = 0.25
        self.songs = AsyncSongQueue()
        self.asyncio_event = asyncio.Event()
        self.audio_player = client.loop.create_task(self.audio_player_task())

    async def audio_player_task(self):
        while True:
            self.asyncio_event.clear()
            video = await self.songs.get()
            player = await YTDLSource.from_url(video.url, stream=True)
            player.source.volume = self.volume
            self.voice_client.play(player, loop=self.client.loop, after=self.play_next_song)
            # await player.source.channel.send("Now Playing " + player.title)
            await self.asyncio_event.wait()

    def play_next_song(self, error=None):
        fut = asyncio.run_coroutine_threadsafe(self.asyncio_event.set(), self.client.loop)
        try:
            fut.result()
        except:
            print(error + " error")
            pass

class AsyncSongQueue(asyncio.Queue):
    def shuffle(self):
        random.shuffle(self._queue)
