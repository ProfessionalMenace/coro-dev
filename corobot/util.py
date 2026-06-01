import discord
from discord.ext import commands, tasks
from discord.flags import Intents
from discord import app_commands
import typing

async def send_error_message (interaction: discord.Interaction, msg: str, **kwargs: typing.Any):
	if interaction.response.is_done():
		if "ephemeral" in kwargs:
			del kwargs["ephemeral"] # not supported by followup
		await interaction.followup.send(msg, **kwargs)
	else:
		await interaction.response.send_message(msg, **kwargs)
