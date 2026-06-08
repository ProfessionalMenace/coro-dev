import discord
from discord.ext import commands, tasks
from discord.flags import Intents
from discord import app_commands
import typing

from corobot.config import BOT_COLOR

async def send_error_message (interaction: discord.Interaction, msg: str, **kwargs: typing.Any):
	if interaction.response.is_done():
		if "ephemeral" in kwargs:
			del kwargs["ephemeral"] # not supported by followup
		await interaction.followup.send(msg, **kwargs)
	else:
		await interaction.response.send_message(msg, **kwargs)


class Paginator (discord.ui.View):
	def __init__ (self, /, user: typing.Union[discord.User, discord.Member], title: str, iterator: typing.Sequence[typing.Any], text: typing.Callable[[typing.Sequence[typing.Any]], str], items_per_page: int, known_size: typing.Optional[int] = None, timeout = 240, **kwargs: typing.Any):
		super().__init__(timeout=timeout)
		self.user = user
		self.pages: typing.List[typing.List[str]] = []
		self.title = title
		self.iterator = iterator
		self.text = text
		self.items_per_page = items_per_page
		self.known_size = known_size
		self.all_pages_generated = True if self.known_size and self.known_size / self.items_per_page <= 1 else False
		self.edit_kwargs = kwargs
		self.page_number = 0
	
	def size_found(self, size):
		self.known_size = size
		for i in range(len(self.pages)):
			self.pages[i][0] = self.title + " | Page " + str(i + 1) + " of " + str(len(self.pages))
		self.all_pages_generated = True

	def generate_page (self, page_number: int) -> str:
		if page_number < len(self.pages):
			return f"## {self.pages[page_number][0]}\n{self.pages[page_number][1]}\n-# {self.pages[page_number][2]}"
		if page_number > len(self.pages):
			self.generate_page(page_number - 1)
		content = []
		for _ in range(self.items_per_page):
			if (data := next(self.iterator, "Iterator Finished")) != "Iterator Finished": # pyright: ignore[reportArgumentType]
				content.append(data)
			else:
				self.size_found(page_number if len(content) > 0 else page_number - 1)
				break
		output = ""
		if len(content) == 0:
			output = "No content on this page"
		else:
			output = self.text(content)
		out = [
			self.title + " | Page " + str(page_number + 1) + " of " + str((self.known_size and len(self.pages)) or "?"),
			output,
			"Made by CoroboCult Mod Team"
		]
		self.pages.append(out)
		return f"## {out[0]}\n{out[1]}\n-# {out[2]}"
	
	@discord.ui.button(label = "Previous", style = discord.ButtonStyle.gray)
	async def previous (self, interaction: discord.Interaction, button: discord.ui.Button):
		if interaction.user != self.user:
			await interaction.response.send_message("Only the person who ran the command may navigate these pages", ephemeral=True)
		elif self.page_number == 0:
			await interaction.response.send_message("You are on the first page", ephemeral=True)
		else:
			self.page_number -= 1
			await interaction.response.edit_message(content = self.generate_page(self.page_number))
	
	@discord.ui.button(label = "Next", style = discord.ButtonStyle.gray)
	async def next (self, interaction: discord.Interaction, button: discord.ui.Button):
		if interaction.user != self.user:
			await interaction.response.send_message("Only the person who ran the command may navigate these pages", ephemeral=True)
		elif self.page_number + 1 == len(self.pages) and self.all_pages_generated:
			await interaction.response.send_message("You are on the last page", ephemeral=True)
		else:
			self.page_number += 1
			content = self.generate_page(self.page_number)
			if self.pages[-1][1] == "No content on this page":
				self.page_number -= 1
				self.pages.pop()
				content = self.generate_page(self.page_number)
			await interaction.response.edit_message(content = content)



async def paginator(* , interaction: discord.Interaction, title: str, followup: bool = False, known_size: typing.Optional[int] = None, iterator: typing.Sequence[typing.Any], text: typing.Callable[[typing.Sequence[typing.Any]], str], items_per_page: int, **kwargs: typing.Any):
	msg = None
	if followup:
		if "ephemeral" in kwargs:
			del kwargs["ephemeral"] # not supported by followup
		msg = await interaction.followup.send("Generating Paginator", **kwargs)
	else:
		await interaction.response.send_message("Generating Paginator", **kwargs)
		msg = await interaction.original_response()
	_paginator = Paginator(
		user = interaction.user,
		title = title,
		iterator = iterator,
		text = text,
		items_per_page = items_per_page,
		known_size = known_size,
		**kwargs
	)
	await msg.edit(content = _paginator.generate_page(0), view = _paginator, **kwargs)
	