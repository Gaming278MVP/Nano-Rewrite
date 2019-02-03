import discord
from discord.ext import commands

from .core.github import AioGithub

class GithubOwner:
    """Represents 'Github's owner data."""

    def __init__(self):
        self.raw = None

class GithubListener:
    """Github commands listener cogs"""

    def __init__(self, client):
        self.client = client
        self.git_client = AioGithub()

    @commands.command(name='git')
    def _git(self, ctx):
        return

def setup(bot):
    bot.load_extension(GithubListener(bot))
    print("GithubListener is loaded")
