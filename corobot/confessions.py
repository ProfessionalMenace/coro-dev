import discord
from discord.ext import commands, tasks
from discord.flags import Intents
from discord import app_commands
import typing
import json
import logging

from corobot import sql, util
from corobot.config import SERVER_ID, MOD_ROLE_ID, BOT_COLOR

logger = logging.getLogger(__name__)

with open("./config/valid_channels.json", "r") as channels:
	VALID_CHANNELS = json.load(channels)

confessions = sql.Database("./data/confessions.db")
confessions_macro_manager = sql.MacroManager("./data/sql_macros.json")

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
		try:
			await msg.edit(view = None)
		except:
			pass
	message = await channel.send(embed=embed, view=ConfessionView(_id))
	confessions.execute({"COID": _id, "MEID": message.id}, query = '''UPDATE confessions SET message_id = :MEID WHERE id = :COID''')

async def submit_reply (interaction: discord.Interaction, _id: int, content: str, attachments: typing.List[discord.Attachment]):
	data = confessions.query_single_item(parameters={"COID": _id}, query = '''SELECT * FROM confessions WHERE id = :COID''')
	if data is None:
		raise ValueError("Confession not found")
	msg = None
	for channel in await interaction.guild.fetch_channels(): # pyright: ignore[reportOptionalMemberAccess]
		if isinstance(channel, discord.TextChannel):
			try:
				msg = await channel.fetch_message(data["message_id"])
				break
			except:
				pass
	if msg is None:
		raise ValueError("Confession found in database, but not on discord")
	thread: discord.Thread = msg.thread or await msg.create_thread(name = "Replies", reason = "Confession Replies")
	confessions.execute({"COID": _id, "AUTH": interaction.user.id}, query = '''INSERT INTO replies (confession_id, author_id) VALUES (:COID, :AUTH)''')
	rid = confessions.query_single_item(query="SELECT id FROM replies ORDER BY id DESC LIMIT 1")["id"] # pyright: ignore[reportOptionalSubscript]
	params = {"REID": rid, "CONT": content, "ATCH": ""}
	embed = discord.Embed(
		title = "Reply #" + str(_id) + "-" + str(rid),
		description=content,
		color=int(BOT_COLOR, 16)
	).set_footer(text = f"Made by CoroboCult Mod Team", icon_url = interaction.client.user.avatar.url) # pyright: ignore[reportOptionalMemberAccess]
	if len(attachments) > 0:
		params["ATCH"] = attachments[0].url
		embed.set_image(url = attachments[0].url)
	confessions.execute(params, query='''INSERT INTO reply_data(id, content, attachment_id) VALUES (:REID, :CONT, :ATCH)''')
	if (_msg := thread.last_message):
		try:
			await _msg.edit(view = None)
		except:
			pass
	message = await thread.send(embed=embed, view=ReplyView(_id))
	confessions.execute({"REID": rid, "MEID": message.id}, query = '''UPDATE replies SET message_id = :MEID WHERE id = :REID''')
	
class QueryModal(discord.ui.Modal, title = "Query Database"):
	query = discord.ui.Label(text = "Query", component=discord.ui.TextInput(style=discord.TextStyle.paragraph))

	def __init__ (self, select: bool, size: int, rows: int):
		super().__init__()
		self.select = select
		self.size = size
		self.rows = rows
	
	async def on_submit(self, interaction: discord.Interaction) -> None:
		await interaction.response.defer()
		query = self.query.component.value.strip() # pyright: ignore[reportAttributeAccessIssue]
		if not self.select:
			confessions.execute(query = query)
			await interaction.followup.send("Database Updated")
		else:
			await util.paginator(
				interaction = interaction,
				title = "Query Results",
				followup=True,
				iterator = confessions.query(query = query, size = self.size), # pyright: ignore[reportCallIssue, reportArgumentType]
				known_size = self.size if self.size != -1 else None,
				text = sql.rows_to_discord,
				items_per_page = self.rows
			)

	async def on_error (self, interaction: discord.Interaction, error: Exception):
		if isinstance(error, app_commands.MissingRole):
			return await util.send_error_message(interaction, f'<@{MOD_ROLE_ID}> Permissions Needed', ephemeral=True)
		await util.send_error_message(interaction, "Unexpected Failure! Please Report (or its a sql error)\n" + str(error), ephemeral=True)
		await interaction.channel.send(f"Code\n```sql\n{self.query.component.value.strip()}```") # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]


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


class ConfessionView (discord.ui.View):
	def __init__ (self, num: int):
		super().__init__(timeout = None)
		self.num = num

	@discord.ui.button(label = "Submit a Confession")
	async def submit (self, interaction: discord.Interaction, button: discord.ui.Button):
		await interaction.response.send_modal(ConfessionModal(interaction.channel)) # pyright: ignore[reportArgumentType]
	
	@discord.ui.button(label = "Reply")
	async def reply (self, interaction: discord.Interaction, button: discord.ui.Button):
		await interaction.response.send_modal(ReplyModal(self.num))


class ConfessionModal (discord.ui.Modal, title = "Submit a Confession"):
	confession = discord.ui.Label(text = "Confession Content", component = discord.ui.TextInput(required=True, style = discord.TextStyle.paragraph))
	attachment = discord.ui.Label(text = "Confession Attachment", component = discord.ui.FileUpload(required=False, max_values=1))

	def __init__ (self, channel: discord.TextChannel):
		super().__init__()
		self.channel = channel

	async def on_submit(self, interaction: discord.Interaction) -> None:
		await submit_confession(interaction, self.channel, self.confession.component.value, self.attachment.component.values) # pyright: ignore[reportAttributeAccessIssue]
		await interaction.response.send_message(f"Confession Submitted to {self.channel.mention}\n-# Please be aware that confession data is logged for moderation purposes", ephemeral=True)


class ReplyView (discord.ui.View):
	def __init__ (self, num: int):
		super().__init__(timeout = None)
		self.num = num
	
	@discord.ui.button(label = "Reply")
	async def reply (self, interaction: discord.Interaction, button: discord.ui.Button):
		await interaction.response.send_modal(ReplyModal(self.num))


class ReplyModal (discord.ui.Modal, title = "Reply to a Confession"):
	confession = discord.ui.Label(text = "Reply Content", component = discord.ui.TextInput(required=True, style = discord.TextStyle.paragraph))
	attachment = discord.ui.Label(text = "Reply Attachment", component = discord.ui.FileUpload(required=False, max_values=1))
	number = discord.ui.Label(text = "Reply Number", component =discord.ui.TextInput(required = False, placeholder="Leave blank to reply to the most recent confession"))

	def __init__ (self, num: int):
		super().__init__()
		self.num = num

	async def on_submit(self, interaction: discord.Interaction) -> None:
		await interaction.response.defer(ephemeral = True)
		await submit_reply(interaction, int(self.number.component.value or self.num), self.confession.component.value, self.attachment.component.values) # pyright: ignore[reportAttributeAccessIssue]
		await interaction.followup.send(f"Confession Submitted to Confession #{self.number.component.value or self.num}", ephemeral=True) # pyright: ignore[reportAttributeAccessIssue]
	
	async def on_error(self, interaction: discord.Interaction, error: Exception):
		if isinstance(error, ValueError):
			await util.send_error_message(interaction, str(error), ephemeral=True)
		else:
			await util.send_error_message(interaction, "Unexpected error, please report:\n" + str(error), ephemeral=True)


@app_commands.default_permissions(moderate_members=True)
class ConfessionsModCog(commands.GroupCog,	name="confessmod", description="Moderation commands"):
	def __init__(self, bot):
		self.bot = bot
		super().__init__()

	# DEFAULT ERROR HANDLER
	async def cog_app_command_error(
		self,
		interaction: discord.Interaction,
		error: app_commands.AppCommandError
	):
		# INSUFFICIENT PERMISSION ROLE ERROR
		if isinstance(error, app_commands.MissingRole):
			return await util.send_error_message(interaction, f"<@{MOD_ROLE_ID}> Permissions Needed", ephemeral=True)

		# SQL RELATED ERROR
		if isinstance(error, sql.MacroError):
			return await error.send_error_message(interaction, ephemeral=True)
		
		await util.send_error_message(interaction, f"Unexpected Failure! Please Report\n{error}", ephemeral=True)
		logger.error(error)
	
	# CREATE & SAVE NEW SQL MACRO
	@app_commands.command(name = "create-macro", description="Create a new macro")
	@app_commands.describe(name = "Name of the macro", code = "Code of the macro")
	@app_commands.checks.has_role(MOD_ROLE_ID)
	async def add_macro (self, interaction: discord.Interaction, name: str, code: str):
		await interaction.response.defer(ephemeral=True)
		confessions_macro_manager.create_macro(
			name = name,
			author_id = interaction.user.id,
			code = code
		)
		await interaction.followup.send("Macro successfully created!")

	# VIEW MACROS
	@app_commands.command(name = "view-macro", description="View all macros, or get data on a specific one")
	@app_commands.describe(name = "Get info on a specific macro")
	@app_commands.checks.has_role(MOD_ROLE_ID)
	async def view_macros(self, interaction: discord.Interaction, name: typing.Optional[str] = None):
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

	@view_macros.autocomplete('name')
	async def command_autocomplete_view_macros(self, interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
		return [app_commands.Choice(name = value["name"], value = value["name"])
			for value in confessions_macro_manager.get_macros() if current in value["name"]][:25]

	# EDIT MACROS
	@app_commands.command(name = "edit-macro", description="Edit a macro you've created")
	@app_commands.rename(new_name = "new-name", new_code = "new-code")
	@app_commands.checks.has_role(MOD_ROLE_ID)
	@app_commands.describe(
		name = "Current macro name",
		new_name = "Rename the macro",
		new_code = "Change the code"
	)
	async def edit_macro(
		self,
		interaction: discord.Interaction,
		name: str,
		new_name: typing.Optional[str] = None,
		new_code: typing.Optional[str] = None
	):
		await interaction.response.defer(ephemeral=True)
		confessions_macro_manager.edit_macro(name = name, new_name = new_name, editor = interaction.user.id, new_code = new_code)
		await interaction.followup.send("success")

	@edit_macro.autocomplete('name')
	async def edit_macro_autocomplete(self, interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
		return [app_commands.Choice(name = value["name"], value = value["name"])
			for value in confessions_macro_manager.get_macros() if current in value["name"] and value["author_id"] == interaction.user.id][:25]

	# DELETE MACRO
	@app_commands.command(name = "delete-macro", description = "Delete a macro")
	@app_commands.describe(name = "Unwanted macro name")
	@app_commands.checks.has_role(MOD_ROLE_ID)
	async def delete_macro (self, interaction: discord.Interaction, name: str):
		await interaction.response.defer(ephemeral=True)
		confessions_macro_manager.delete_macro(name = name, editor = interaction.user.id)
		await interaction.followup.send("Success!")

	@delete_macro.autocomplete('name')
	async def delete_macros_autocomplete(self, interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
		return [app_commands.Choice(name = value["name"], value = value["name"])
			for value in confessions_macro_manager.get_macros() if current in value["name"] and value["author_id"] == interaction.user.id][:25]

	# QUERY DATABASE 
	@app_commands.command(name = "query", description="Query the database")
	@app_commands.checks.has_role(MOD_ROLE_ID)
	@app_commands.describe(
		query = "SQL query to request. input POP-OUT to get a paragraph input.",
		select = "Whether or not this query is a select query",
		size = "How many rows to return, only does something if select is True. Leave blank for all",
		rows = "How many rows per page, default 25"
	)
	async def query_db (self, interaction: discord.Interaction, query: str, select: bool = False, size: int = -1, rows: int = 25):
		if query == "POP-OUT":
			return await interaction.response.send_modal(QueryModal(select, size, rows))
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
				items_per_page = rows
			)
		
	# SAVE DATABASE 
	@app_commands.command(name = "save", description = "Save the database")
	@app_commands.checks.has_role(MOD_ROLE_ID)
	async def save_db (self, interaction: discord.Interaction):
		confessions.save()
		await interaction.response.send_message("Saved", ephemeral=True)
	
	# USE MACRO 
	@app_commands.command(name = "use-macro", description="Use a macro")
	@app_commands.describe(
		macro = "The macro to use",
		select = "Whether or not this query is a select query",
		size = "How many rows to return, only does something if select is True. Leave blank for all",
	)
	@app_commands.checks.has_role(MOD_ROLE_ID)
	async def use_macro (self, interaction: discord.Interaction, macro: str, select: bool = False, size: int = -1):
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

	@use_macro.autocomplete('macro')
	async def use_macro_autocomplete(self, interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
		return [app_commands.Choice(name = value["name"], value = value["name"])
			for value in confessions_macro_manager.get_macros() if current in value["name"]][:25]
	
	# ADD CHANNEL
	@app_commands.command(name = "add-channel", description = "Add a new channel to the confession channel list")
	@app_commands.describe(channel = "The wanted channel")
	@app_commands.checks.has_role(MOD_ROLE_ID)
	async def add_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
		await interaction.response.defer(ephemeral = True)
		VALID_CHANNELS[str(channel.id)] = {"id": channel.id}
		with open("./config/valid_channels.json", "w") as channels:
			json.dump(VALID_CHANNELS, channels, indent = 2)
		await interaction.followup.send(f"Added {channel.mention} successfully!")

	# REMOVE CHANNEL
	@app_commands.command(name = "remove-channel", description = "Remove a channel from the confession channel list")
	@app_commands.describe(channel = "The unwanted channel")
	@app_commands.checks.has_role(MOD_ROLE_ID)
	async def remove_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
		await interaction.response.defer(ephemeral = True)
		if str(channel.id) in VALID_CHANNELS:
			del VALID_CHANNELS[str(channel.id)]
			with open("./config/valid_channels.json", "w") as channels:
				json.dump(VALID_CHANNELS, channels, indent = 2)
			await interaction.followup.send(f"Removed {channel.mention} successfully!")
		else:
			await interaction.followup.send(f"{channel.mention} not in vaild channel list")

	@app_commands.command(name = "view-channels", description = "View confession channel list")
	@app_commands.checks.has_role(MOD_ROLE_ID)
	async def view_channels (self, interaction: discord.Interaction):
		await interaction.response.defer()
		await interaction.followup.send("## Current Confessions Channel List\n" + "\n".join(f"<#{id}>" for id in VALID_CHANNELS))


class ConfessionsUserCog(commands.GroupCog,	name="confessions", description="Anonymous Confession Commands"):
	def __init__(self, bot):
		self.bot = bot
		super().__init__()

	async def cog_load(self):
		if not self.save_db.is_running():
			self.save_db.start()

	async def cog_unload(self):
		if self.save_db.is_running():
			self.save_db.stop()

	@tasks.loop(minutes=5)
	async def save_db(self):
		logger.info("Saving confessions database")
		confessions.save()
		#TODO: create a backup every 6 hours, max 4
	
	@app_commands.command(name = "confess", description = "Submit a confession")
	@app_commands.describe(channel = "Channel to confess to")
	async def confess (self, interaction: discord.Interaction, channel: typing.Optional[str] = None):
		channel = channel or str(interaction.channel.id) # pyright: ignore[reportOptionalMemberAccess, reportAssignmentType]
		if channel not in VALID_CHANNELS: # pyright: ignore[reportOptionalMemberAccess]
			await interaction.response.send_message("This is not a valid channel", ephemeral=True)
		else:
			await interaction.response.send_modal(ConfessionModal(interaction.guild.get_channel(int(channel)))) # pyright: ignore[reportOptionalMemberAccess, reportArgumentType]

	@confess.autocomplete('channel')
	async def command_autocomplete_confess(self, interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
		return [app_commands.Choice(name = channel.name, value = str(channel.id)) # pyright: ignore[reportOptionalMemberAccess]
			for _channel in VALID_CHANNELS if current in (channel := interaction.guild.get_channel(VALID_CHANNELS[_channel]["id"])).name][:25] # pyright: ignore[reportOptionalMemberAccess]
	
	@app_commands.command(name = "reply", description = "Reply to a confession")
	@app_commands.describe(id = "Confession to reply to")
	async def reply (self, interaction: discord.Interaction, id: int):
		await interaction.response.send_modal(ReplyModal(id)) # pyright: ignore[reportOptionalMemberAccess, reportArgumentType]


async def setup(bot):
	await bot.add_cog(ConfessionsModCog(bot))
	await bot.add_cog(ConfessionsUserCog(bot))
