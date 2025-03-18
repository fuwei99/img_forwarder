import asyncio
import json
from cogs.keyword_responder import KeywordResponder
from cogs.my_commands import MyCommands
from discord.ext import commands
import discord


def resolve_config():
    with open("config.json", "r") as f:
        config = json.load(f)
    token = config.get("token")
    target_channel_id = config.get("target_channel_id")
    source_channel_id = config.get("source_channel_id")
    chat_channel_id = config.get("chat_channel_id")
    backup_channel_id = config.get("backup_channel_id")
    gemini_keys = config.get("gemini_keys")
    num = len(gemini_keys)
    current_gemini_pro_key = config.get("current_gemini_pro_key")
    current_gemini_flash_key = config.get("current_gemini_flash_key")
    return (
        token,
        target_channel_id,
        source_channel_id,
        chat_channel_id,
        backup_channel_id,
        gemini_keys,
        num,
        current_gemini_pro_key,
        current_gemini_flash_key,
    )


def load_words():
    with open("words.json", "r") as f:
        words = json.load(f)
    return words


intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=".", intents=intents)
(
    token,
    target_channel_id,
    source_channel_id,
    chat_channel_id,
    backup_channel_id,
    gemini_keys,
    num,
    current_gemini_pro_key,
    current_gemini_flash_key,
) = resolve_config()
words = load_words()


@commands.command(name="reload")
@commands.is_owner()
async def reload(ctx: commands.Context):
    # reload cogs
    for cog in bot.cogs:
        bot.remove_cog(cog)
    await main()


@commands.command(name="sync")
@commands.is_owner()
async def sync(ctx: commands.Context):
    await bot.tree.sync()
    await ctx.send("Synced tree.", ephemeral=True)


async def main():
    await bot.add_cog(MyCommands(bot, backup_channel_id))
    await bot.add_cog(
        KeywordResponder(
            bot, target_channel_id, source_channel_id, chat_channel_id, words
        )
    )
    await bot.start(token)
    print("bot started")


asyncio.run(main())
