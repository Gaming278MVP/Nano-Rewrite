import logging
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)

import asyncio
# import youtube_dl
import discord
from discord.ext import commands
from .core.music import YTDLSource, GuildVoiceState, VoiceEntry
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

        if ctx.voice_client is None:
            ctx.voice_client.connect()

        state = self.get_guild_state(ctx.guild.id)
        if ctx.voice_client.is_playing():
            player = await YTDLSource.from_url(video.url, loop=self.bot.loop, stream=True)
            entry = VoiceEntry(
                player = player,
                requester = ctx.message.author,
                video = video
                )
            state.queue.append(entry)
            await ctx.send('Enqueued ' + player.title)
            return

        async with ctx.typing():
            player = await YTDLSource.from_url(video.url, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else state.next())
            ctx.voice_client.source.volume = state.volume

        entry = VoiceEntry(
            player = player,
            requester = ctx.message.author,
            video = video
            )
        state.current = entry
        state.voice_client = ctx.voice_client
        state.channel = ctx.message.channel

        await ctx.send(embed=state.get_embedded_np())

    async def handle_url(self, ctx, url):
        """Handle input url, play from given url"""

        try:
            player = await YTDLSource.from_url(
                url,
                loop=self.bot.loop,
                stream=True
                )
        except:
            await ctx.send(':x: | Cannot extract data from given url, make sure it is a valid url.')
            return
        entry = VoiceEntry(
            player = player,
            requester = ctx.message.author,
            video = None
            )

        state = self.get_guild_state(ctx.guild.id)
        if ctx.voice_client.is_playing():
            state.queue.append(entry)
            await ctx.send('Enqueued ' + player.title)
            return

        async with ctx.typing():
            ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else state.next())
            ctx.voice_client.source.volume = state.volume

        state.voice_client = ctx.voice_client
        state.current = entry
        state.channel = ctx.message.channel

        await ctx.send(embed=state.get_embedded_np())
        return

    @commands.command(name='search', aliases=['s', 'Search', 'SEARCH', 'play', 'p'])
    async def search_(self, ctx, *args):
        """Search song by keyword and do start song selection"""

        # get keyword from args
        keyword = "".join([word+" " for word in args])

        # check if inpuy keyword is url
        if 'www' in keyword or 'youtu' in keyword:
            # handle url
            await self.handle_url(ctx, keyword)
            return

        # search video by keyword
        search_result = ys.search(keyword)

        # build embed
        embed = discord.Embed(
            title='Song Selection | Reply the song number to continue',
            description='prefix: do. | search_limit: 7',
            color=discord.Colour(value=11735575).orange()
            )

        # Converts search_result into a string
        song_list = "".join(["{}. **[{}]({})**\n".format(i + 1, video.title, video.url) for i, video in enumerate(search_result)])

        # fill embed
        embed.add_field(
            name='search result for ' + keyword,
            value=song_list,
            inline=False
            )
        embed.set_thumbnail(url=search_result[0].thumbnails['high']['url'])
        embed.set_footer(text='Song selection | Type the entry number to continue')
        embedded_list = await ctx.send(embed=embed)

        # wait for author response
        request_channel = ctx.message.channel
        request_author  = ctx.author
        def check(m):
            try: # '/^*[0-9][0-9 ]*$/'
                picked_entry_number = int(m.content)
                return m.channel == request_channel and m.author == request_author
            except:
                return False
        try:
            msg = await self.bot.wait_for('message', check=check, timeout=10.0)
        except:
            # TIMEOUT ERROR EXCEPTION
            await embedded_list.delete()
            return
        # await request_channel.send('picked_entry_number: {}'.format(msg.content))
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
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            video = ys.search(url)[0]
            entry = VoiceEntry(
                player = player,
                requester = ctx.message.author,
                video = video
                )
            state.queue.append(entry)
            await ctx.send('Enqueued ' + player.title)
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
        state.volume = float(volume/100.0)

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

        state = self.get_guild_state(ctx.guild.id)
        if ctx.author.voice:
            state.voice_client = await ctx.author.voice.channel.connect()
        else:
            await ctx.send("You are not connected to a voice channel.")

    @commands.command(name='np', aliases=['now_play', 'nowplay', 'now_playing'])
    async def now_playing_(self, ctx):
        """Gets current playing song information"""

        state = self.get_guild_state(ctx.guild.id)
        embed = state.get_embedded_np()
        # np = "Now Playing {}".format(state.current.title)
        await ctx.send(embed=embed)

    @commands.command(name='skip')
    async def skip_(self, ctx):
        """Vote to skip a song.
        Requester can automatically skip.
        3 skip votes are needed to skip the song.
        """

        # if not connected to voice channel or voice client is not playing any song
        if ctx.voice_client is None or not ctx.voice_client.is_playing():
            await ctx.send("Not playing any music.")
            return

        state = self.get_guild_state(ctx.guild.id)
        if state.current.requester == ctx.message.author:
            # do skip song
            state.voice_client.stop()
            await ctx.message.add_reaction('⏭')
            return
        elif ctx.author.id not in state.skip_votes:
            # increment voters
            state.skip_votes.add(ctx.author.id)
            total_votes = len(state.skip_votes)
            # check voters
            if total_votes >= 3:
                await ctx.message.add_reaction('⏭')
                state.voice_client.stop()
            else:
                await ctx.send("⏭ | Current skip votes **{}/3**".format(total_votes))

    @commands.command(name='pause')
    async def pause_(self, ctx):
        """Pause current playing song"""

        state = self.get_guild_state(ctx.guild.id)
        if state.voice_client is None or not state.voice_client.is_playing():
            await ctx.send('Not playing any song.')
        state.voice_client.pause()

    @commands.command(name='resume')
    async def resume_(self, ctx):
        """Resumes paused song"""

        state = self.get_guild_state(ctx.guild.id)
        if state.voice_client is None or state.voice_client.is_playing():
            await ctx.send('Nothing to resume.')
        if not state.current is None:
            state.voice_client.resume()

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
    print('MusicListener is loaded')
