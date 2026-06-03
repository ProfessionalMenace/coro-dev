import discord
from discord.ext import commands, tasks
from discord.flags import Intents
from discord import app_commands
import typing

import confessions
from meta import MetaCog

from config import (
	SERVER_ID,  # pyright: ignore[reportAttributeAccessIssue]
	BOT_COLOR,  # pyright: ignore[reportAttributeAccessIssue]
	CURRENT_HOST,  # pyright: ignore[reportAttributeAccessIssue]
)

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
		super().__init__(*args, tree_cls=CommandTree, intents=Intents.all(), **kwargs)

	async def setup_hook(self):
		await self.add_cog(MetaCog(self))
		self.tree.add_command(confessions.confessions_group)

		# sync
		self.tree.copy_global_to(guild=guild)
		synced = await self.tree.sync(guild=guild)
		print([command.name for command in synced])

	async def on_ready(self):
		print(
			f"Logged in as {self.user.name} - {self.user.id}"
		)  # pyright: ignore[reportOptionalMemberAccess]
		for guild in self.guilds:
			if guild.id == SERVER_ID:
				self.CoroboCult = guild

		confessions.save_db.start()

		# set status
		activity = discord.CustomActivity(
			"Under Development | Currently Being Hosted By " + CURRENT_HOST
		)
		await self.change_presence(activity=activity, status=discord.Status.idle)
