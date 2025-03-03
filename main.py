import discord
import os
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

load_dotenv()

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
TARGET_CHANNEL_ID = int(os.environ.get("TARGET_CHANNEL_ID"))
SOURCE_CHANNEL_ID = int(os.environ.get("SOURCE_CHANNEL_ID"))

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
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

app = Flask('')
@app.route('/')
def home():
    return "I'm alive"
def run():
    app.run(host='0.0.0.0', port=8080)
def keep_alive():
    server = Thread(target=run)
    server.start()

keep_alive()

client.run(TOKEN)