import discord
from discord.ext import commands, tasks
from discord.flags import Intents
from discord import app_commands
import typing
import asyncio
import tracemalloc
import json

from sql import Database

#start error logging
tracemalloc.start()
config = open("./config/config.json", "r")
config_data = json.loads(config.read())
config.close()

TOKEN = json.loads(open("./config/secrets.json", "r").read())["BOT TOKEN"]
BOT_COLOR = config_data["BOT COLOR"]
SERVER_ID = config_data["SERVER ID"]

confessions = Database("config/confessions.db")

guild = discord.Object(id=SERVER_ID)
class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.CoroboCult: typing.Optional[discord.Guild] = None # CoroboCult Server
        self.tree = app_commands.CommandTree(self, allowed_contexts=app_commands.AppCommandContext(guild=True,dm_channel=False,private_channel=False))
    async def setup_hook(self):
        print([command.name for command in await self.tree.sync(guild=guild)])
        print([command.name for command in await self.tree.sync()])

intents = Intents.all()
bot = MyClient(intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} - {bot.user.id}') # pyright: ignore[reportOptionalMemberAccess]
    for guild in bot.guilds:
        if guild.id == SERVER_ID:
            bot.CoroboCult = guild
            
