import discord
from discord import app_commands
from discord.ext import commands, tasks
from corobot.config import MOD_ROLE_ID, LOG_CHANNEL_ID
import typing
import logging
import sqlite3
import datetime

logger = logging.getLogger(__name__)
DB_PATH = "data/moderation.db"


@app_commands.default_permissions(moderate_members=True)
@app_commands.checks.has_role(MOD_ROLE_ID)
class ModerationGroup(app_commands.Group):
	def __init__(self):
		super().__init__(name="mod", description="Moderation commands")

	async def on_error(
		self, interaction: discord.Interaction, error: app_commands.AppCommandError
	):
		if isinstance(error, app_commands.errors.MissingRole):
			return await interaction.response.send_message(
				"You don't have the required role to use this command.", ephemeral=True
			)

		raise error


class ModerationDBManager():
	def __init__(self, db_path) -> None:
		self.db_path = db_path

		with sqlite3.connect(self.db_path) as conn:
			cursor = conn.cursor()
			cursor.execute("""
				CREATE TABLE IF NOT EXISTS mod_actions (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					action_time TIMESTAMP,
					target_id INTEGER,
					moderator_id INTEGER,
					action_type CHAR(20),
					reason TEXT
				)
			""")
			conn.commit()
	
	def log_mod_action(self, target_id: int, moderator_id: int, mod_action_type: str, reason: str):
		with sqlite3.connect(self.db_path) as conn:
			cursor = conn.cursor()
			cursor.execute(
				"""
				INSERT INTO mod_actions (action_time, target_id, moderator_id, action_type, reason)
					VALUES (?, ?, ?, ?, ?)
				""",
				(
					int(datetime.datetime.now().timestamp()),
					target_id,
					moderator_id,
					mod_action_type,
					reason
				)
			)
			conn.commit()


class MessageLogDBManager():
	def __init__(self, db_path):
		self.db_path = db_path

		with sqlite3.connect(self.db_path) as conn:
			cursor = conn.cursor()
			cursor.execute("""
				CREATE TABLE IF NOT EXISTS message_log (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					detection_time TIMESTAMP,
					author_id INTEGER,
					message_content TEXT
				)
			""")
			conn.commit()
	
	def log_message(self, author_id: int, message_content: int):
		with sqlite3.connect(self.db_path) as conn:
			cursor = conn.cursor()
			cursor.execute(
				"""
				INSERT INTO message_log (detection_time, author_id, message_content)
					VALUES (?, ?, ?)
				""",
				(
					int(datetime.datetime.now().timestamp()),
					author_id,
					message_content
				)
			)
			conn.commit()
	
	def delete_older_than(self, timestamp: int):
		with sqlite3.connect(self.db_path) as conn:
			cursor = conn.cursor()
			cursor.execute(
				f"""
				DELETE FROM message_log WHERE detection_time < ?;
				""",
				(timestamp,)
			)
			conn.commit()
	

class ModerationCog(commands.Cog, ModerationDBManager):
	mod_group = ModerationGroup()

	def __init__(self, bot, db_path, log_channel_id):
		self.bot = bot
		self.log_channel = None
		self.log_channel_id = log_channel_id 
		commands.Cog.__init__(self)
		ModerationDBManager.__init__(self, db_path)

	@commands.Cog.listener()
	async def on_ready(self):
		self.log_channel = self.bot.get_channel(self.log_channel_id)
		if self.log_channel:
			logger.info(f"Moderation logging channel has been set to {self.log_channel.id}")
		else:
			logger.warning("Moderation logging channel could not be set!")

	@mod_group.command(name="log-here", description="Set the current log channel")
	async def set_log_channel(self, interaction: discord.Interaction):
		"""Set the current log channel"""
		self.log_channel = interaction.channel
		await interaction.response.send_message(
			f"Log channel updated {interaction.channel.mention}"
		)

	@mod_group.command(name="warn", description="Send user a warning")
	@app_commands.describe(target="Discord user", reason="Warning Message")
	async def warn(
		self,
		interaction: discord.Interaction,
		target: discord.User,
		reason: typing.Optional[str] = None,
	):
		"""Anonymous warning command (logged)"""
		await interaction.response.defer(ephemeral=True)

		if self.log_channel is None:
			return await interaction.followup.send(
				"No logging channel!", ephemeral=True
			)

		if not reason:
			return await interaction.followup.send(
				"Remember to provide a reason!", ephemeral=True
			)

		embed = discord.Embed(
			title="You have been warned!",
			description=reason,
			color=discord.Color.yellow(),
			timestamp=interaction.created_at,
		)

		embed.set_footer(
			text=f"Made by CoroboCult Mod Team",
			icon_url=interaction.client.user.avatar.url,
		)

		try:
			await target.send(embed=embed)

			await interaction.followup.send(
				f"User {target.mention} has been warned!", ephemeral=True
			)

		except:
			await interaction.followup.send(
				"Message could not be delivered!", ephemeral=True
			)

		finally:
			# log database
			self.log_mod_action(
				target_id=target.id,
				moderator_id=interaction.user.id,
				mod_action_type="WARN",
				reason=reason
			)
			
			# log mod channel
			embed.title = f"User: {target.display_name} has been warned!"
			embed.add_field(name="target", value=target.mention)
			embed.add_field(name="moderator", value=interaction.user.mention)
			await self.log_channel.send(embed=embed)


class MessageLoggerCog(commands.Cog, MessageLogDBManager):
	def __init__(self, bot, db_path):
		self.bot = bot
		self.prune_db.start()
		commands.Cog.__init__(self)
		MessageLogDBManager.__init__(self, db_path)
	
	@tasks.loop(minutes=720)
	async def prune_db(self):
		"""Periodically delete old messages"""
		cutoff = datetime.datetime.now() - datetime.timedelta(hours=12)
		self.delete_older_than(int(cutoff.timestamp()))
		logger.info(f"Prunning database entries older than {cutoff}")
	
	@commands.Cog.listener()
	async def on_message_delete(self, message: discord.Message):
		"""Log deleted messages"""
		self.log_message(message.author.id, message.content)

	@commands.Cog.listener()
	async def on_message_edit(self, before: discord.Message, after: discord.Message):
		"""Log edited messages"""
		if len(before.content) != 0 and before.content != after.content:
			self.log_message(before.author.id, before.content)

async def setup(bot):
	await bot.add_cog(ModerationCog(bot, DB_PATH, LOG_CHANNEL_ID))
	await bot.add_cog(MessageLoggerCog(bot, DB_PATH))
