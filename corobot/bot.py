import discord
from discord.ext import commands, tasks
from discord.flags import Intents
from discord import app_commands
import typing

import confessions
from config import (
	SERVER_ID, # pyright: ignore[reportAttributeAccessIssue]
	BOT_COLOR, # pyright: ignore[reportAttributeAccessIssue]
	CURRENT_HOST, # pyright: ignore[reportAttributeAccessIssue]
)

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

	# set status
	activity = discord.CustomActivity("Under Development | Currently Being Hosted By " + CURRENT_HOST)
	await bot.change_presence(activity = activity, status = discord.Status.idle)

@bot.tree.command(name="help", description="Get a list of commands or info on a single command")
@app_commands.rename(cmd="command")
@app_commands.describe(cmd="Get info on a specific command")
@app_commands.guilds(SERVER_ID)
async def _help(interaction: discord.Interaction, cmd: typing.Optional[str] = None):
	output = ""
	cmd_list = [command for command in bot.tree.walk_commands(guild=interaction.guild)]
	if cmd is None:
		output = "List of Commands\n```"
		for command in cmd_list:
			output += "/" + command.qualified_name + " - " + command.description + "\n"
		output += "\n```"
	else:
		cmd_names = [command.qualified_name for command in cmd_list]
		if cmd not in cmd_names:
			output = "Please enter a valid cmd (use /help to find them)"
		else:
			command = [command for command in cmd_list if command.qualified_name == cmd][0]
			output = "`/" + command.qualified_name + "`\n> " + command.description + "\n"
			if isinstance(command, app_commands.commands.Group):
				output += "Sub-commands:\n```\n"
				for subcommand in command.commands:
					output += "\n- " + subcommand.name + " > " + subcommand.description
			else:
				output += "Parameters:\n```\n"
				for parameter in command.parameters:
					output += "\n- " + ("<" if parameter.required else "[") + parameter.display_name + (">" if parameter.required else "]") + " > " + parameter.description
			output += "\n```"
	embed = discord.Embed(
		title="Help: " + ("all" if cmd is None else cmd),
		description=output,
		color=int(BOT_COLOR, 16)
	).set_footer(text = f"Made by CoroboCult Mod Team", icon_url = interaction.client.user.avatar.url) # pyright: ignore[reportOptionalMemberAccess]
	await interaction.response.send_message(embed=embed)
@_help.autocomplete('cmd')
async def command_autocomplete(interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
	return [
		app_commands.Choice(name=command.qualified_name, value=command.qualified_name)
		for command in bot.tree.walk_commands(guild=interaction.guild) if current.upper() in command.qualified_name.upper()
	][:25] if len(current) > 0 else [
		app_commands.Choice(name=command.qualified_name, value=command.qualified_name)
		for command in bot.tree.walk_commands(guild=interaction.guild)
	][:25]

bot.tree.add_command(confessions.confessions_group)