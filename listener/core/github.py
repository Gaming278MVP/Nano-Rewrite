import aiohttp
import requests
import asyncio
import pprint as pp

_TIMEOUT  = 30

_BASE_URL = 'https://api.github.com'

_METHOD_MAP = dict(
    GET='GET',
    POST='POST'
)

class AioGithub:
    """Asynchronous Github Client"""

    def __init__(self):
        self._memo = {}

    async def search_user(self, q):
        """Search user by keyword"""

        async with aiohttp.ClientSession() as session:
            url = "{}/search/users?q={}".format(_BASE_URL, q)
            async with session.get(url) as response:
                return await response.json()

    async def search(self, category="repositories", q=""):
        """Search by category & keyword.
        More flexible way to search.
        Category :
        - repositories, topics, code, commits, issues, users, text match metadata
        q : keyword
        """

        async with aiohttp.ClientSession() as session:
            url = "{}/search/{}?q={}".format(_BASE_URL, category, q)
            async with session.get(url) as response:
                return await response.json()

    async def get_user_repos(self, username):
        """Get user's repositories"""

        async with aiohttp.ClientSession() as session:
            url = "{}/users/{}/repos".format(_BASE_URL, username)
            async with session.get(url) as response:
                return await response.json()

class Github:
    def __init__(self, loop=None):
        self._memo = {}
        self.loop = loop

    async def search(self, category="repositories", q=''):
        url = "{}/search/{}?q={}".format(_BASE_URL, category, q)
        response = await self.loop.run_in_executor(None, lambda: requests.get(url))
        return response.json()
