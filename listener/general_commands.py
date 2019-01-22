import discord
from discord.ext import commands

commands_string = "**Image**\n`meme` `dank` `anime` `animeme` `anime9` `waifu` `tsun` `aniwallp` `moescape` `fgo` `fgoart` `cosplay` `comic` `rwtf` `wtf` `kpop` `savage`\n"

class GeneralListener:

    def __init__(self, client):
        self.client = client

    @commands.command()
    async def help(self, ctx):
        embed = discord.Embed(
            title="Nano-bot's Commands",
            colour=discord.Colour(value=11735575).orange()
            )
        embed.add_field(
            name=":tools: **Support Dev**",
            value="Report bug, [Join Nano Support Server](https://discord.gg/Y8sB4ay)\nDon't forget to **[Vote](https://discordbots.org/bot/458298539517411328/vote)** Nano-Bot :hearts:"
            )
        embed.add_field(
            name=":books: **Commands** | Prefix: **do.**",
            value=commands_string,
            inline=False
            )
        nano_bot = await self.client.get_user_info(self.client.id)
        embed.set_thumbnail(url=nano_bot.avatar_url)
        await ctx.send(embed=embed)

    @commands.command()
    async def secret(self, ctx):
        await ctx.send(ctx.secret)

    @commands.command()
    async def ping(self, ctx):
        latency = "%.0fms" % (self.client.latency * 100)
        embed = discord.Embed(
            title="{}-bot's Latency'".format(self.client.name),
            type='rich',
            description=":hourglass_flowing_sand:" + latency,
            colour=discord.Colour(value=11735575).orange()
            )
        await ctx.send(embed=embed)

def setup(client):
    client.add_cog(GeneralListener(client))
    print('GeneralListener is Loaded')
