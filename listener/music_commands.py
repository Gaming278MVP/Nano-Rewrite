import logging
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)

import asyncio
# import youtube_dl
import discord
from discord.ext import commands
from .core.music import YTDLSource, GuildVoiceState
from .core.ytpy.ytpy.youtube import YoutubeService, YoutubeVideo

ys = YoutubeService()

class Music:
    def __init__(self, bot):
        self.bot = bot
        self.guild_states = {}

    def get_guild_state(self, guild_id):
        """Gets Guild's Voice State"""

        if not guild_id in self.guild_states:
            self.guild_states[guild_id] = GuildVoiceState(client=self.bot)
        return self.guild_states[guild_id]

    async def play(self, ctx, video=None):
        """Plays song from given video"""

        state = self.get_guild_state(ctx.guild.id)
        if ctx.voice_client.is_playing():
            player = await YTDLSource.from_url(video.url, loop=self.bot.loop, stream=True)
            state.queue.append(player)
            await ctx.send('Enqueued ' + player.title)
            return

        async with ctx.typing():
            player = await YTDLSource.from_url(video.url, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else state.next())
            ctx.voice_client.source.volume = state.volume

        state.voice_client = ctx.voice_client
        state.current = player

        await ctx.send('Now playing: {}'.format(player.title))

    @commands.command(name='search', aliases=['s', 'Search', 'SEARCH'])
    async def search_(self, ctx, *args):
        """Search song by keyword"""

        # search keyword
        keyword = "".join([word+" " for word in args])
        search_result = ys.search(keyword)
        # build embed
        embed = discord.Embed(
            title='Search Keyword: ' + keyword,
            description='prefix: do. | search_limit: 7',
            color=discord.Colour(value=11735575).orange()
            )
        # fill embed
        song_list = ""
        for i, video in enumerate(search_result):
            song_list += "{}. **[{}]({})**\n".format(i + 1, video.title, video.url)
        embed.add_field(
            name='search result',
            value=song_list,
            inline=False
            )
        embed.set_thumbnail(url=search_result[0].thumbnails['high']['url'])
        await ctx.send(embed=embed)

        # wait for author response
        request_channel = ctx.message.channel
        request_author  = ctx.author
        def check(m):
            try:
                picked_entry_number = int(m.content)
                return m.channel == request_channel and m.author == request_author
            except:
                return False
        msg = await self.bot.wait_for('message', check=check)
        await request_channel.send('picked_entry_number: {}'.format(msg.content))
        await self.play(ctx=ctx, video=search_result[int(msg.content) - 1])

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """Joins a voice channel"""

        # if already connected to voice channel, then move
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)
        # if not connected yet, then connect
        await channel.connect()

    @commands.command()
    async def play_(self, ctx, *, query):
        """Plays a file from the local filesystem"""

        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(query))
        ctx.voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else None)

        await ctx.send('Now playing: {}'.format(query))

    @commands.command()
    async def yt(self, ctx, *, url):
        """Plays from a url (almost anything youtube_dl supports)"""

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop)
            ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)

        await ctx.send('Now playing: {}'.format(player.title))

    @commands.command()
    async def stream(self, ctx, *, url):
        """Streams from a url (same as yt, but doesn't predownload)"""

        state = self.get_guild_state(ctx.guild.id)
        if ctx.voice_client.is_playing():
            # add song to queue
            state.queue.append(url)
            await ctx.send(state.queue)
            return

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)

        state.voice_client = ctx.voice_client
        state.current = player
        await ctx.send('Now playing: {}'.format(player.title))

    @commands.command()
    async def volume(self, ctx, volume: int):
        """Changes the player's volume"""

        # set certains guild volume
        state = self.get_guild_state(ctx.guild.id)
        state.volume = float(volume/100)

        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        ctx.voice_client.source.volume = state.volume
        await ctx.send("Changed volume to {}%".format(volume))

    @commands.command()
    async def stop(self, ctx):
        """Stops and disconnects the bot from voice"""

        await ctx.voice_client.disconnect()
        del self.guild_states[ctx.guild.id]

    @commands.command()
    async def summon(self, ctx):
        """Force the bot to join author's voice channel"""

        self.get_guild_state(ctx.guild.id)
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            await ctx.send("You are not connected to a voice channel.")

    @commands.command(name='np', aliases=['now_play', 'nowplay', 'now_playing'])
    async def now_playing_(self, ctx):
        """Gets current playing song information"""

        state = self.get_guild_state(ctx.guild.id)
        np = "Now Playing {}".format(state.current.title)
        await ctx.send(np)

    @play_.before_invoke
    @yt.before_invoke
    @stream.before_invoke
    @search_.before_invoke
    async def ensure_voice(self, ctx):
        """Do this before do play/yt/stream/search commands"""

        self.get_guild_state(ctx.guild.id)
        # check author voice state
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
        # elif ctx.voice_client.is_playing(): # optional
            # add to queue here
            # ctx.voice_client.stop()

def setup(bot):
    bot.add_cog(Music(bot))
    print('Music is loaded')
