import discord
from discord.ext import commands, tasks
from discord.flags import Intents
from discord import app_commands
import typing

import sql, util
from config import (
	SERVER_ID, # pyright: ignore[reportAttributeAccessIssue]
	MOD_ROLE_ID, # pyright: ignore[reportAttributeAccessIssue]
	BOT_COLOR # pyright: ignore[reportAttributeAccessIssue]
) 

confessions = sql.Database("data/confessions.db")
confessions_macro_manager = sql.MacroManager("data/sql_macros.json")

@tasks.loop(minutes=5)
async def check_to_do():
	confessions.save()

confessions_group = app_commands.Group(
  name="confessions",
  description="Anonymous Confession Commands",
  guild_ids=[SERVER_ID]
)

confessions_database_group = app_commands.Group(
  name="database",
  description="Access and Modify Confession Database",
  guild_ids=[SERVER_ID]
)
confessions_group.add_command(confessions_database_group)

@confessions_database_group.command(name = "create-macro", description="Create a new macro")
@app_commands.checks.has_role(MOD_ROLE_ID)
@app_commands.describe(
	name = "Name of the macro",
	code = "Code of the macro"
)
async def confessions_database__add_macro (interaction: discord.Interaction, name: str, code: str):
	await interaction.response.defer(ephemeral=True)
	confessions_macro_manager.create_macro(name = name, author_id = interaction.user.id, code = code)
	await interaction.followup.send("Macro successfully created!")

@confessions_database__add_macro.error
async def confessions_database__add_macro__error (interaction: discord.Interaction, error: Exception):
	if isinstance(error, app_commands.MissingRole):
		return await util.send_error_message(interaction, f'<@{MOD_ROLE_ID}> Permissions Needed', ephemeral=True)
	if isinstance(error, sql.MacroError):
		return await error.send_error_message(interaction, ephemeral=True)
	await util.send_error_message(interaction, "Unexpected Failure! Please Report\n" + str(error), ephemeral=True)

@confessions_database_group.command(name = "view-macro", description="View all macros, or get data on a specific one")
@app_commands.checks.has_role(MOD_ROLE_ID)
@app_commands.describe(name = "Get info on a specific macro")
async def confessions_database__view_macros (interaction: discord.Interaction, name: typing.Optional[str] = None):
	await interaction.response.defer()
	output = ""
	macro: typing.Optional[sql.MacroData] = None
	if name is None:
		output = "\n".join(f"`{row["name"]}` - <@{row["author_id"]}>" for row in confessions_macro_manager.get_macros())
	else:
		macro = confessions_macro_manager.get_macro(name)
		output = f'`{macro["name"]}` - Created by <@{macro["author_id"]}>'
	embed = discord.Embed(
		title="Macros: " + ("all" if name is None else name),
		description = output,
		color=int(BOT_COLOR, 16)
	).set_footer(text = f"Made by CoroboCult Mod Team", icon_url = interaction.client.user.avatar.url) # pyright: ignore[reportOptionalMemberAccess]
	if name:
		embed.add_field(
			name = "Code",
			value = f"```sql\n{macro["code"]}\n```" # pyright: ignore[reportOptionalSubscript]
		)
		if macro["parameters"]: # pyright: ignore[reportOptionalSubscript]
			embed.add_field(
				name = "Parameters",
				value = ", ".join([f"`{parameter}`" for parameter in macro["parameters"]]) # pyright: ignore[reportOptionalSubscript]
			)
	await interaction.followup.send(embed=embed)

@confessions_database__view_macros.autocomplete('name')
async def command_autocomplete_view_macros(interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
	return [app_commands.Choice(name = value["name"], value = value["name"])
		for value in confessions_macro_manager.get_macros() if current in value["name"]][:25]

@confessions_database__view_macros.error
async def confessions_database__view_macros__error (interaction: discord.Interaction, error: Exception):
	if isinstance(error, app_commands.MissingRole):
		return await util.send_error_message(interaction, f'<@{MOD_ROLE_ID}> Permissions Needed', ephemeral=True)
	if isinstance(error, sql.MacroError):
		return await error.send_error_message(interaction)
	await util.send_error_message(interaction, "Unexpected Failure! Please Report\n" + str(error), ephemeral=True)

@confessions_database_group.command(name = "edit-macro", description="Edit a macro you've created")
@app_commands.checks.has_role(MOD_ROLE_ID)
@app_commands.rename(new_name = "new-name", new_code = "new-code")
@app_commands.describe(
	name = "Current macro name",
	new_name = "Rename the macro",
	new_code = "Change the code"
)
async def confessions_database__edit_macro(interaction: discord.Interaction, name: str, new_name: typing.Optional[str] = None, new_code: typing.Optional[str] = None):
	await interaction.response.defer(ephemeral=True)
	await interaction.followup.send("under construction sorry")

@confessions_database__edit_macro.error
async def confessions_database__edit_macro__error (interaction: discord.Interaction, error: Exception):
	if isinstance(error, app_commands.MissingRole):
		return await util.send_error_message(interaction, f'<@{MOD_ROLE_ID}> Permissions Needed', ephemeral=True)
	if isinstance(error, sql.MacroError):
		return await error.send_error_message(interaction, ephemeral=True)
	await util.send_error_message(interaction, "Unexpected Failure! Please Report\n" + str(error), ephemeral=True)
