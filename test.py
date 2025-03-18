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

TARGET_CHANNEL_ID = config.get("target_channel_id")
SOURCE_CHANNEL_ID = config.get("source_channel_id")
CHAT_CHANNEL_ID = config.get("chat_channel_id")

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


def load_words():
    global TRIGGER_WORDS, TRIGGER_MESSAGE, REPEAT_MESSAGES
    with open("trigger.json", "r", encoding="utf-8") as f:
        words = json.load(f)
    TRIGGER_WORDS = words.get("trigger_words")
    # 字典

    for w, k in words.get("trigger_words_rec").items():
        if TRIGGER_WORDS.get(k):
            TRIGGER_WORDS[w] = TRIGGER_WORDS[k]
    TRIGGER_MESSAGE = words.get("trigger_message")
    for w, k in words.get("trigger_message_rec").items():
        if TRIGGER_MESSAGE.get(k):
            TRIGGER_MESSAGE[w] = TRIGGER_MESSAGE[k]
    REPEAT_MESSAGES = set(words.get("repeat_messages"))


def is_emoji(s):
    charset = unicodedata.category(s)
    return charset in ("So", "Sk", "Cf")


def repeat(message):
    if message.content in REPEAT_MESSAGES:
        return True
    splitted = message.content.split("\n")
    if all(len(s) == 1 and is_emoji(s) for s in splitted):
        return True
    return False


def trigger_message(message):
    if message.content in TRIGGER_MESSAGE.keys():
        return True
    return False


# 查找触发词
def trigger_word(message):
    for w in TRIGGER_WORDS.keys():
        if w in message.content:
            return w
    return None


async def try_forward_images(message):
    if message.channel.id != SOURCE_CHANNEL_ID:
        return

    if message.attachments and any(
        attachment.content_type.startswith("image")
        for attachment in message.attachments
    ):
        source_member = message.author
        original_message_content = message.content
        embeds = []
        color = discord.Color.random()
        for i, attachment in enumerate(message.attachments):
            if attachment.content_type.startswith("image"):
                if i == 0:
                    embed = discord.Embed(
                        title=f"**By** {source_member.display_name}\n",
                        description=f"{source_member.mention}"
                        + (
                            f": {original_message_content}"
                            if original_message_content
                            else ""
                        ),
                        color=color,
                    )
                    embed.set_image(url=attachment.url)
                    embeds.append(embed)
                else:
                    embed = discord.Embed(color=color)
                    embed.set_image(url=attachment.url)
                    embeds.append(embed)
        allowed_mentions = discord.AllowedMentions(users=True)
        target_channel = bot.get_channel(TARGET_CHANNEL_ID)
        if target_channel:
            await target_channel.send(embeds=embeds, allowed_mentions=allowed_mentions)
        else:
            print(f"channel not found: {TARGET_CHANNEL_ID}")


@bot.event
async def on_message(message):
    # bot do not respond to itself
    if message.author == bot.user:
        return

    await try_forward_images(message)

    if CHAT_CHANNEL_ID is None or message.channel.id != CHAT_CHANNEL_ID:
        return

    if repeat(message):
        await message.channel.send(message.content)
        return

    if trigger_message(message):
        await message.channel.send(random.choice(TRIGGER_MESSAGE[message.content]))
        return

    tw = trigger_word(message)
    if tw is not None:
        await message.channel.send(random.choice(TRIGGER_WORDS[tw]))
        return


load_words()


bot.run(TOKEN)
