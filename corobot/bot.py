import discord
from discord.ext import commands
from discord.flags import Intents
from discord import app_commands
import typing
import logging
from corobot.config import SERVER_ID, CURRENT_HOST

logger = logging.getLogger(__name__)
guild = discord.Object(id=SERVER_ID)


class CommandTree(app_commands.CommandTree):
	def __init__(self, client, *, fallback_to_global: bool = True):
		super().__init__(
			client,
			fallback_to_global=fallback_to_global,
			allowed_contexts=app_commands.AppCommandContext(
				guild=True, dm_channel=False, private_channel=False
			),
		)


class Corobot(commands.Bot):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

	async def setup_hook(self):
		await self.load_extension("corobot.meta")
		await self.load_extension("corobot.moderation")
		await self.load_extension("corobot.confessions")

		# sync
		self.tree.copy_global_to(guild=guild)
		synced = await self.tree.sync(guild=guild)
		logger.info([command.name for command in synced])

	async def on_ready(self):
		logger.info(f"Logged in as {self.user.name} - {self.user.id}")
		for guild in self.guilds:
			if guild.id == SERVER_ID:
				self.CoroboCult = guild

		# set status
		activity = discord.CustomActivity(f"Currently Being Hosted By {CURRENT_HOST}")
		await self.change_presence(activity=activity, status=discord.Status.idle)

def run_bot(TOKEN: typing.Optional[str]):
	bot = Corobot(
		command_prefix="!",
		tree_cls=CommandTree,
		intents=Intents.all()
	)
	bot.run(TOKEN, log_handler=None)
