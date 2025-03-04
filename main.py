import random
import discord
from discord.ext import commands
from discord import app_commands
# import google.generativeai as genai
import json
import unicodedata

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)
    
config = load_config()

TOKEN = config.get("token")
TARGET_CHANNEL_ID = config.get("target_channel_id")
SOURCE_CHANNEL_ID = config.get("source_channel_id")
GEMINI_KEYS = config.get("gemini_keys")
NUM = len(GEMINI_KEYS)

CURRENT_GEMINI_PRO_KEY = config.get("current_gemini_pro_key")
CURRENT_GEMINI_FLASH_KEY = config.get("current_gemini_flash_key")

# def get_gemini_key(model):
#     if model == "gemini-2.0-pro-exp-02-05":
#         CURRENT_GEMINI_PRO_KEY += 1
#         CURRENT_GEMINI_PRO_KEY %= NUM
#         config["current_gemini_pro_key"] = CURRENT_GEMINI_PRO_KEY
#         with open('config.json', 'w') as f:
#             json.dump(config, f)
#         return GEMINI_KEYS[CURRENT_GEMINI_PRO_KEY]
#     else:
#         CURRENT_GEMINI_FLASH_KEY += 1
#         CURRENT_GEMINI_FLASH_KEY %= NUM
#         config["current_gemini_flash_key"] = CURRENT_GEMINI_FLASH_KEY
#         with open('config.json', 'w') as f:
#             json.dump(config, f)
#         return GEMINI_KEYS[CURRENT_GEMINI_FLASH_KEY]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)
# bot = commands.Bot(command_prefix='!', intents=intents)

# available_models = {
#     "pro": "gemini-2.0-pro-exp-02-05",
#     "flash": "gemini-2.0-flash",
# }

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

TRIGGER_WORDS = ["春同", "蠢"]
TRIGGER_MESSAGE = ["春"]
REPLY_WORDS = ["春", "春同", "春同一根", "春同一根捏", "不会给春同很多很好的评价"]

def update_words():
    for word in REPLY_WORDS:
        REPLY_WORDS.append(word.replace("春", "蠢"))

REPEAT_CHARACTERS = ["？", "?", "……"]

def repeat(message):
    if any(word == message.content for word in REPEAT_CHARACTERS):
        return True
    elif len(message.content) > 1:
        return
    else:
        char = message.content[0]
        charset = unicodedata.category(char)
        if charset in ("So", "Sk", "Cf"):
            return True
    
def trigger(message):
    if any(word in message.content for word in TRIGGER_WORDS) or any(word == message.content for word in TRIGGER_MESSAGE):
        return True
    return False

async def forward_images(message):
    if message.channel.id != SOURCE_CHANNEL_ID:
        return

    if message.attachments and any(attachment.content_type.startswith('image') for attachment in message.attachments):
        source_member = message.author
        original_message_content = message.content
        embeds = []
        color = discord.Color.random()
        for i, attachment in enumerate(message.attachments):
            if attachment.content_type.startswith('image'):
                if i==0:
                    embed = discord.Embed(
                        title=f"**By** {source_member.display_name}\n",
                        description=f"{source_member.mention}" + (f": {original_message_content}" if original_message_content else ""),
                        color=color
                    )
                    embed.set_image(url=attachment.url)
                    embeds.append(embed)
                else:
                    embed = discord.Embed(
                        color=color
                    )
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
    if message.author == client.user:
        return

    if repeat(message):
        source_channel = client.get_channel(message.channel.id)
        if source_channel:
            await source_channel.send(message.content)
            return
    
    if trigger(message):
        source_channel = client.get_channel(message.channel.id)
        if source_channel:
            await source_channel.send(random.choice(REPLY_WORDS))
            return
    
    await forward_images(message)


update_words()
client.run(TOKEN)