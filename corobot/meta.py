import discord
from discord import app_commands
from discord.ext import commands
import typing
from corobot.config import BOT_COLOR


class MetaCog(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@app_commands.command(name="ping", description="pong")
	async def ping(self, interaction: discord.Interaction):
		await interaction.response.send_message("pong")

	@app_commands.command(
		name="help", description="Get a list of commands or info on a single command"
	)
	@app_commands.rename(cmd="command")
	@app_commands.describe(cmd="Get info on a specific command")
	async def _help(
		self, interaction: discord.Interaction, cmd: typing.Optional[str] = None
	):
		output = ""
		cmd_list = [
			command for command in self.bot.tree.walk_commands(guild=interaction.guild)
		]
		if cmd is None:
			output = "List of Commands\n```"
			for command in cmd_list:
				output += (
					"/" + command.qualified_name + " - " + command.description + "\n"
				)
			output += "\n```"
		else:
			cmd_names = [command.qualified_name for command in cmd_list]
			if cmd not in cmd_names:
				output = "Please enter a valid cmd (use /help to find them)"
			else:
				command = [
					command for command in cmd_list if command.qualified_name == cmd
				][0]
				output = (
					"`/" + command.qualified_name + "`\n> " + command.description + "\n"
				)
				if isinstance(command, app_commands.commands.Group):
					output += "Sub-commands:\n```\n"
					for subcommand in command.commands:
						output += (
							"\n- " + subcommand.name + " > " + subcommand.description
						)
				else:
					output += "Parameters:\n```\n"
					for parameter in command.parameters:
						output += (
							"\n- "
							+ ("<" if parameter.required else "[")
							+ parameter.display_name
							+ (">" if parameter.required else "]")
							+ " > "
							+ parameter.description
						)
				output += "\n```"
		embed = discord.Embed(
			title="Help: " + ("all" if cmd is None else cmd),
			description=output,
			color=int(BOT_COLOR, 16),
		).set_footer(
			text=f"Made by CoroboCult Mod Team",
			icon_url=interaction.client.user.avatar.url,
		)  # pyright: ignore[reportOptionalMemberAccess]
		await interaction.response.send_message(embed=embed)

	@_help.autocomplete("cmd")
	async def command_autocomplete(
		self, interaction: discord.Interaction, current: str
	) -> typing.List[app_commands.Choice[str]]:
		return (
			[
				app_commands.Choice(
					name=command.qualified_name, value=command.qualified_name
				)
				for command in self.bot.tree.walk_commands(guild=interaction.guild)
				if current.upper() in command.qualified_name.upper()
			][:25]
			if len(current) > 0
			else [
				app_commands.Choice(
					name=command.qualified_name, value=command.qualified_name
				)
				for command in self.bot.tree.walk_commands(guild=interaction.guild)
			][:25]
		)
