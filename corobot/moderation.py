import discord
from discord import app_commands
from discord.ext import commands
from config import MOD_ROLE_ID, LOG_CHANNEL_ID
import typing
import logging
import json

@app_commands.default_permissions(moderate_members=True)
@app_commands.checks.has_role(MOD_ROLE_ID)
class ModerationGroup(app_commands.Group):
	def __init__(self):
		super().__init__(name="mod", description="Moderation commands")
		
	async def on_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
		if isinstance(error, app_commands.errors.MissingRole):
			return await interaction.response.send_message(
				"You don't have the required role to use this command.", ephemeral=True)
		
		raise error

class ModerationCog(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.log_channel = None 
		super().__init__()
	
	@commands.Cog.listener()
	async def on_ready(self):
		await self.bot.wait_until_ready()
		self.log_channel = self.bot.get_channel(LOG_CHANNEL_ID)
		logging.log(logging.INFO, f"Moderation logging channel has been set to {self.log_channel.id}")
	
	mod_group = ModerationGroup()

	@mod_group.command(name = "log-here", description="Set the current log channel")
	async def set_log_channel(self, interaction: discord.Interaction):
		"""Set the current log channel"""
		self.log_channel = interaction.channel
		await interaction.response.send_message(
			f"Log channel updated {interaction.channel.mention}"
		)

	@mod_group.command(name = "warn", description="Send user a warning")
	@app_commands.describe(target="Discord user ID", reason="Warning Message")
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
			title = "You have been warned!",
			description = reason,
			color=discord.Color.yellow()
		)

		embed.set_footer(
			text = f"Made by CoroboCult Mod Team",
			icon_url = interaction.client.user.avatar.url
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
			embed.title = f"User: {target.display_name} has been warned!"
			embed.add_field(name = "target", value = target.mention)
			embed.add_field(name = "target id", value = target.id)
			embed.add_field(name = "moderator", value = interaction.user.mention)

			await self.log_channel.send(embed=embed)

	@commands.Cog.listener()
	async def on_message_delete(self, message):
		"""Print the edited message"""
		if message.author.bot or self.log_channel is None:
			return
		
		embed = discord.Embed(
			title=f"Message Deleted",
			description=message.content,
			timestamp=message.created_at,
		)
		embed.add_field(name = "Author:", value = message.author.mention)
		embed.add_field(name = "Channel:", value = message.channel.mention)

		await self.log_channel.send(embed=embed)

async def setup(bot):
	await bot.add_cog(ModerationCog(bot))