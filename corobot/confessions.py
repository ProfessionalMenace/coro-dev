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
	#TODO: create a backup every 6 hours, max 4

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
	if isinstance(error, app_commands.CommandInvokeError):
		if isinstance(error.original, sql.MacroError):
			return await error.original.send_error_message(interaction, ephemeral=True)
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
	confessions_macro_manager.edit_macro(name = name, new_name = new_name, editor = interaction.user.id, new_code = new_code)
	await interaction.followup.send("success")

@confessions_database__edit_macro.autocomplete('name')
async def command_autocomplete_edit_macros(interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
	return [app_commands.Choice(name = value["name"], value = value["name"])
		for value in confessions_macro_manager.get_macros() if current in value["name"] and value["author_id"] == interaction.user.id][:25]
@confessions_database__edit_macro.error
async def confessions_database__edit_macro__error (interaction: discord.Interaction, error: Exception):
	if isinstance(error, app_commands.MissingRole):
		return await util.send_error_message(interaction, f'<@{MOD_ROLE_ID}> Permissions Needed', ephemeral=True)
	if isinstance(error, app_commands.CommandInvokeError):
		if isinstance(error.original, sql.MacroError):
			return await error.original.send_error_message(interaction, ephemeral=True)
	await util.send_error_message(interaction, "Unexpected Failure! Please Report\n" + str(error), ephemeral=True)

@confessions_database_group.command(name = "delete-macro", description = "Delete a macro")
@app_commands.checks.has_role(MOD_ROLE_ID)
@app_commands.describe(name = "Unwanted macro name")
async def confessions_database__delete_macro (interaction: discord.Interaction, name: str):
	await interaction.response.defer(ephemeral=True)
	confessions_macro_manager.delete_macro(name = name, editor = interaction.user.id)
	await interaction.followup.send("Success!")

@confessions_database__delete_macro.autocomplete('name')
async def command_autocomplete_delete_macros(interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
	return [app_commands.Choice(name = value["name"], value = value["name"])
		for value in confessions_macro_manager.get_macros() if current in value["name"] and value["author_id"] == interaction.user.id][:25]
@confessions_database__delete_macro.error
async def confessions_database__delete_macro__error (interaction: discord.Interaction, error: Exception):
	if isinstance(error, app_commands.MissingRole):
		return await util.send_error_message(interaction, f'<@{MOD_ROLE_ID}> Permissions Needed', ephemeral=True)
	if isinstance(error, app_commands.CommandInvokeError):
		if isinstance(error.original, sql.MacroError):
			return await error.original.send_error_message(interaction, ephemeral=True)
	await util.send_error_message(interaction, "Unexpected Failure! Please Report\n" + str(error), ephemeral=True)


@confessions_database_group.command(name = "query", description="Query the database")
@app_commands.checks.has_role(MOD_ROLE_ID)
@app_commands.describe(
	query = "SQL query to request",
	select = "Whether or not this query is a select query",
	size = "How many rows to return, only does something if select is True. Leave blank for all",
)
async def confessions_database__query (interaction: discord.Interaction, query: str, select: bool = False, size: int = -1):
	await interaction.response.defer()
	query = query.strip()
	if not select:
		confessions.execute(query = query)
		await interaction.followup.send("Database Updated")
	else:
		await util.paginator(
			interaction = interaction,
			title = "Query Results",
			followup=True,
			iterator = confessions.query(query = query, size = size), # pyright: ignore[reportCallIssue, reportArgumentType]
			known_size = size if size != -1 else None,
			text = sql.rows_to_discord,
			items_per_page = 25
		)
	
@confessions_database__query.error
async def confessions_database__query__error (interaction: discord.Interaction, error: Exception):
	if isinstance(error, app_commands.MissingRole):
		return await util.send_error_message(interaction, f'<@{MOD_ROLE_ID}> Permissions Needed', ephemeral=True)
	await util.send_error_message(interaction, "Unexpected Failure! Please Report\n" + str(error), ephemeral=True)

class ParametersModal (discord.ui.Modal, title = "Parameters"):
	def __init__ (self, select: bool, code: str, size: int, parameters: typing.Sequence[str]):
		super().__init__()
		self.select = select
		self.code = code
		self.size = size
		for parameter in parameters:
			self.add_item(discord.ui.TextInput(label = parameter, custom_id = parameter))
	
	async def on_submit(self, interaction: discord.Interaction) -> None:
		parameters = {child.custom_id: child.value for child in self.walk_children()} # pyright: ignore[reportAttributeAccessIssue]
		if not self.select:
			confessions.execute(parameters, query = self.code)
			await interaction.response.send_message("Database Updated")
		else:
			await util.paginator(
				interaction = interaction,
				title = "Query Results",
				iterator = confessions.query(query = self.code, size = self.size, parameters=parameters), # pyright: ignore[reportCallIssue, reportArgumentType]
				known_size = self.size if self.size != -1 else None,
				text = sql.rows_to_discord,
				items_per_page = 25
			)
	
async def on_error (interaction: discord.Interaction, error: Exception):
	if isinstance(error, app_commands.CommandInvokeError):
		if isinstance(error.original, sql.MacroError):
			return await error.original.send_error_message(interaction, ephemeral=True)
	await util.send_error_message(interaction, "Unexpected Failure! Please Report\n" + str(error), ephemeral=True)


@confessions_database_group.command(name = "use-macro", description="Use a macro")
@app_commands.checks.has_role(MOD_ROLE_ID)
@app_commands.describe(
	macro = "The macro to use",
	select = "Whether or not this query is a select query",
	size = "How many rows to return, only does something if select is True. Leave blank for all",
)
async def confessions_database__use_macro (interaction: discord.Interaction, macro: str, select: bool = False, size: int = -1):
	data = confessions_macro_manager.get_macro(macro)

	if data["parameters"]:
		await interaction.response.send_modal(ParametersModal(select, data["code"], size, data["parameters"]))
	else:
		if not select:
			confessions.execute(query = data["code"])
			await interaction.followup.send("Database Updated")
		else:
			await util.paginator(
				interaction = interaction,
				title = "Query Results",
				followup=True,
				iterator = confessions.query(query = data["code"], size = size), # pyright: ignore[reportCallIssue, reportArgumentType]
				known_size = size if size != -1 else None,
				text = sql.rows_to_discord,
				items_per_page = 25
			)
@confessions_database__use_macro.error
async def confessions_database__use_macro__error (interaction: discord.Interaction, error: Exception):
	if isinstance(error, app_commands.MissingRole):
		return await util.send_error_message(interaction, f'<@{MOD_ROLE_ID}> Permissions Needed', ephemeral=True)
	if isinstance(error, app_commands.CommandInvokeError):
		if isinstance(error.original, sql.MacroError):
			return await error.original.send_error_message(interaction, ephemeral=True)
	await util.send_error_message(interaction, "Unexpected Failure! Please Report\n" + str(error), ephemeral=True)
@confessions_database__use_macro.autocomplete('macro')
async def command_autocomplete_use_macro(interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
	return [app_commands.Choice(name = value["name"], value = value["name"])
		for value in confessions_macro_manager.get_macros() if current in value["name"]][:25]

async def submit_confession (interaction: discord.Interaction, channel: discord.TextChannel, content: str, attachments: typing.List[discord.Attachment]):
	confessions.execute({"AUTH": interaction.user.id}, query = '''INSERT INTO confessions(author_id) VALUES (:AUTH)''')
	_id: int = confessions.query_single_item(query = '''SELECT id from confessions ORDER BY id DESC LIMIT 1''')["id"] # pyright: ignore[reportOptionalSubscript]
	params = {"COID": _id, "CONT": content, "ATCH": ""}
	embed = discord.Embed(
		title = "Confession #" + str(_id),
		description=content,
		color=int(BOT_COLOR, 16)
	).set_footer(text = f"Made by CoroboCult Mod Team", icon_url = interaction.client.user.avatar.url) # pyright: ignore[reportOptionalMemberAccess]
	if len(attachments) > 0:
		params["ATCH"] = attachments[0].url
		embed.set_image(url = attachments[0].url)
	confessions.execute(params, query='''INSERT INTO confession_data(id, content, attachment_id) VALUES (:COID, :CONT, :ATCH)''')
	if (msg := channel.last_message):
		await msg.edit(view = None)
	message = await channel.send(embed=embed, view=ConfessionView())
	confessions.execute({"COID": _id, "MEID": message.id}, query = '''UPDATE confessions SET message_id = :MEID WHERE id = :COID''')

class ConfessionView (discord.ui.View):
	def __init__ (self):
		super().__init__(timeout = None)

	@discord.ui.button(label = "Submit a Confession")
	async def submit (self, interaction: discord.Interaction, button: discord.ui.Button):
		await interaction.response.send_modal(ConfessionModal(interaction.channel)) # pyright: ignore[reportArgumentType]

class ConfessionModal (discord.ui.Modal, title = "Submit a Confession"):
	confession = discord.ui.Label(text = "Confession Content", component = discord.ui.TextInput(required=True, style = discord.TextStyle.paragraph))
	attachment = discord.ui.Label(text = "Confession Attachment", component = discord.ui.FileUpload(required=False, max_values=1))

	def __init__ (self, channel: discord.TextChannel):
		super().__init__()
		self.channel = channel

	async def on_submit(self, interaction: discord.Interaction) -> None:
		await submit_confession(interaction, self.channel, self.confession.component.value, self.attachment.component.values) # pyright: ignore[reportAttributeAccessIssue]
		await interaction.response.send_message(f"Confession Submitted to {self.channel.mention}\n-# Please be aware that confession data is logged for moderation purposes", ephemeral=True)

@confessions_group.command(name = "confess", description = "Submit a confession")
@app_commands.describe(channel = "Channel to confess to")
# TODO: ADD CHOICES
async def confessions_group__confess (interaction: discord.Interaction, channel: typing.Optional[discord.TextChannel] = None):
	await interaction.response.send_modal(ConfessionModal(channel or interaction.channel)) # pyright: ignore[reportArgumentType]