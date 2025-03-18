import asyncio
import json
from discord.ext import commands
import discord
import os
from utils.func import resolve_config

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=".", intents=intents)


async def main():
    config = resolve_config()
    token = config.get("token")
    for file in os.listdir("cogs"):
        if file.endswith(".py"):
            bot.load_extension(f"cogs.{file[:-3]}")
    await bot.start(token)


asyncio.run(main())
