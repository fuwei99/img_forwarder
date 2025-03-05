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
BACKUP_CHANNEL_ID = config.get("backup_channel_id")
GEMINI_KEYS = config.get("gemini_keys")
NUM = len(GEMINI_KEYS)

CURRENT_GEMINI_PRO_KEY = config.get("current_gemini_pro_key")
CURRENT_GEMINI_FLASH_KEY = config.get("current_gemini_flash_key")


def get_gemini_key(model):
    if model == "gemini-2.0-pro-exp-02-05":
        CURRENT_GEMINI_PRO_KEY += 1
        CURRENT_GEMINI_PRO_KEY %= NUM
        config["current_gemini_pro_key"] = CURRENT_GEMINI_PRO_KEY
        with open("config.json", "w") as f:
            json.dump(config, f)
        return GEMINI_KEYS[CURRENT_GEMINI_PRO_KEY]
    else:
        CURRENT_GEMINI_FLASH_KEY += 1
        CURRENT_GEMINI_FLASH_KEY %= NUM
        config["current_gemini_flash_key"] = CURRENT_GEMINI_FLASH_KEY
        with open("config.json", "w") as f:
            json.dump(config, f)
        return GEMINI_KEYS[CURRENT_GEMINI_FLASH_KEY]


intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix="!", intents=intents)

available_models = {
    "pro": "gemini-2.0-pro-exp-02-05",
    "flash": "gemini-2.0-flash",
}

# def generate(prompt, model):
#     api_key = get_gemini_key(model)
#     genai.configure(api_key=api_key)
#     model = genai.get_model(available_models[model])
#     try:
#         response = model.generate(prompt)
#         return response.text, response.prompt_feedback
#     except Exception as e:
#         return str(e), None

# @bot.command(name='sync')
# @commands.has_permissions(administrator=True)
# async def sync(ctx):
#     synced = await bot.tree.sync()
#     await ctx.send(f"Synced {synced} commands")

# @bot.hybrid_command(name="start", description="Start your wonderful journey with Gemini!")
# @app_commands.describe(
#     message = "[String], try saying hello to Gemini!",
#     pro="[Boolean], whether to use Gemini 2.0 Pro",
#     system="[String], system prompt",
# )
# async def start(interaction: discord.Interaction, message, pro: bool=False, system: str=""):
#     model = "pro" if pro else "flash"
#     prompt = []
#     if system:
#         prompt.append({'role': 'user', 'parts': [system]})
#         prompt.append({'role': 'model', 'parts': ['OK']})
#     prompt.append({'role': 'user', 'parts': [message]})
#     response_text, feedback = generate(prompt, model)
#     if feedback:
#         print(feedback)
#     if response_text:
#         await interaction.response.send_message(response_text)
#         prompt.append({'role': 'model', 'parts': [response_text]})
#         interaction.extras['prompt'] = prompt
#         interaction.extras['model'] = model
#     else:
#         await interaction.response.send_message("Gemini just fell asleep, please try again later.")


@client.event
async def on_ready():
    print(f"logged in as {client.user}")


TRIGGER_WORDS = {}
TRIGGER_MESSAGE = {}
REPEAT_MESSAGES = set()


@bot.command(name="async_command")
@commands.has_permissions(administrator=True)
@app_commands.describe(message="Async slash commands.")
async def async_command(ctx):
    synced = await bot.tree.sync()
    await ctx.send(f"Synced {synced} commands")


@bot.hybrid_command(name="reload_word_list", description="Reload the word list.")
@commands.has_permissions(administrator=True)
async def reload_word_list(ctx):
    load_words()
    await ctx.send("Word list reloaded.")


# 备份命令 backup 备份聊天记录
# 通过回复消息触发
# @bot.hybrid_command(name='backup', description="Backup the message you're replying to.")
# async def backup(ctx):
#     if BACKUP_CHANNEL_ID is None or not isinstance(BACKUP_CHANNEL_ID, discord.TextChannel()):
#         await ctx.send("Backup channel does not exist or is not a text channel.", ephemeral=True)
#         return
#     if ctx.message.reference and ctx.message.message_id:
#         original_message = await ctx.fetch_message(ctx.message.reference.message_id)


def load_words():
    global TRIGGER_WORDS, TRIGGER_MESSAGE, REPEAT_MESSAGES
    with open("trigger.json", "r") as f:
        words = json.load(f)
    TRIGGER_WORDS = words.get("trigger_words")
    for w, k in words.get("trigger_words_rec"):
        if TRIGGER_WORDS.get(k):
            TRIGGER_WORDS[w] = TRIGGER_WORDS[k]
    TRIGGER_MESSAGE = words.get("trigger_message")
    for w, k in words.get("trigger_message_rec"):
        if TRIGGER_MESSAGE.get(k):
            TRIGGER_MESSAGE[w] = TRIGGER_MESSAGE[k]
    REPEAT_MESSAGES = set(words.get("repeat_messages"))


def repeat(message):
    if message.content in REPEAT_MESSAGES:
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
        target_channel = client.get_channel(TARGET_CHANNEL_ID)
        if target_channel:
            await target_channel.send(embeds=embeds, allowed_mentions=allowed_mentions)
        else:
            print(f"channel not found: {TARGET_CHANNEL_ID}")


@client.event
async def on_message(message):
    # bot do not respond to itself
    if message.author == client.user:
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
        await message.channel.send(TRIGGER_WORDS[tw])
        return


load_words()
client.run(TOKEN)
