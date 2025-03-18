import random
import discord
from discord.ext import commands
from discord import app_commands

# import google.generativeai as genai
import json
import unicodedata


def load_config():
    with open("config.json", "r") as f:
        return json.load(f)


config = load_config()

TOKEN = config.get("token")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=".", intents=intents)


@bot.event
async def on_ready():
    print(f"logged in as {bot.user}")


# 加一个测试命令foo bar
@bot.command(name="foo", description="bar")
async def foo(ctx):
    print("yes")
    await ctx.send("bar")


bot.run(TOKEN)
