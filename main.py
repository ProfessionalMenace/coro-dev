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

with open("./config/config.json", "r") as config:
	config_data = json.loads(config.read())
	BOT_COLOR = config_data["BOT COLOR"]
	SERVER_ID = config_data["SERVER ID"]
  SERVER_ID = int(config_data["SERVER ID"])
  MOD_ROLE_ID = int(config_data["MOD ROLE ID"])

with open("./config/secrets.json", "r") as secrets:
	TOKEN = json.loads(secrets.read())["BOT TOKEN"]

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

@tasks.loop(minutes=5)
async def check_to_do():
	confessions.save()

@bot.event
async def on_ready():
	print(f'Logged in as {bot.user.name} - {bot.user.id}') # pyright: ignore[reportOptionalMemberAccess]
	for guild in bot.guilds:
		if guild.id == SERVER_ID:
			bot.CoroboCult = guild

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
	).set_footer(text = f"Made by CoroboCult Mod Team", icon_url = bot.user.avatar.url) # pyright: ignore[reportOptionalMemberAccess]
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

confessions_group = app_commands.Group(name="confessions", description="Anonymous Confession Commands", guild_ids=[SERVER_ID])
bot.tree.add_command(confessions_group)

confessions_database_group = app_commands.Group(name="database", description="Access and Mofidy Confession Database", guild_ids=[SERVER_ID])
confessions_group.add_command(confessions_database_group)

@confessions_database_group.command(name = "create-macro", description="Create a new macro")
@app_commands.checks.has_role(MOD_ROLE_ID)
@app_commands.describe(
	name = "Name of the macro, max 20 characters",
	code = "Code of the macro"
)
async def confessions_database__add_macro (interaction: discord.Interaction, name: str, code: str):
	await interaction.response.defer(ephemeral=True)
	if len(name) >= 20:
		return await interaction.followup.send("Name must be at most 20 characters")
	if confessions.query(size = 1, query = "SELECT name FROM macros WHERE name = ?;", parameters = (name,)):
		return await interaction.followup.send("Name is already in use")
	confessions.create_macro(name = name, author_id = interaction.user.id, code = code)
	await interaction.followup.send("Macro successfully created!")

@confessions_database_group.command(name = "view-macro", description="View all macros, or get data on a specific one")
@app_commands.checks.has_role(MOD_ROLE_ID)
@app_commands.describe(name = "Get info on a specific macro")
async def confessions_database__view_macros (interaction: discord.Interaction, name: typing.Optional[str] = None):
	await interaction.response.defer(ephemeral=True)
	if name is None:
		output = []
		for row in confessions.query(query = 'SELECT name, author_id FROM macros;'): # pyright: ignore[reportOptionalIterable]
			output.append(f"`{row["name"]:>20}` - <@{row["author_id"]}>")
		embed = discord.Embed(
			title="Macros: " + ("all" if name is None else name),
			description="\n".join(output),
			color=int(BOT_COLOR, 16)
		).set_footer(text = f"Made by CoroboCult Mod Team", icon_url = bot.user.avatar.url) # pyright: ignore[reportOptionalMemberAccess]
		await interaction.followup.send(embed = embed)
	else:
		pass
@confessions_database__view_macros.autocomplete('name')
async def command_autocomplete_view_macros(interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
	return [app_commands.Choice(name = value["name"], value = value["name"])
				 for value in confessions.query(parameters = (f"%{current}%",), size = 25, query = '''
																		SELECT name
																		FROM macros
																		WHERE name LIKE ?;
				 ''')]

if __name__ == "__main__":
	bot.run(TOKEN)
