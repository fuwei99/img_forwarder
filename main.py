import discord
import os
from dotenv import load_dotenv

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
    
    # if message.attachments and any(attachment.content_type.startswith('image')for attachment in message.attachments):
    #     source_member = message.author
    #     original_message_content = message.content
    #     image_urls = [attachment.url for attachment in message.attachments if attachment.content_type.startswith('image')]
    #     forwarded_message = (
    #         f"**By** {source_member.mention}\n"
    #         f"{original_message_content}\n\n"
    #         + "\n".join(image_urls)
    #     )
    #     allowed_mentions = discord.AllowedMentions(users=True)
    #     target_channel = client.get_channel(TARGET_CHANNEL_ID)
    #     if target_channel:
    #         await target_channel.send(forwarded_message, allowed_mentions=allowed_mentions)
    #     else:
    #         print(f"channel not found: {TARGET_CHANNEL_ID}")

    # if message.attachments:
    #     basis = False
    #     for attachment in message.attachments:
    #         if attachment.content_type.startswith("image"):
    #             image_url = attachment.url
    #             if not basis:
    #                 source_member = message.author    
    #                 original_message_content = message.content
    #                 # embed = discord.Embed(
    #                 #     title=f"**By** {source_member.display_name}\n",
    #                 #     description="{source_member.mention}" + f": {original_message_content}" if original_message_content else "",
    #                 #     color=discord.Color.blue()
    #                 # )
    #                 # embed.set_image(url=image_url)
    #                 forwarded_message = (
    #                     f"**By** {source_member.mention}\n"
    #                     f"{original_message_content}\n" if original_message_content else ""
    #                     f"{image_url}"
    #                 )
    #                 basis = True
    #             else:
    #                 forwarded_message += f"\n{image_url}"
    #     allowed_mentions = discord.AllowedMentions(users=True)
    #     target_channel = client.get_channel(TARGET_CHANNEL_ID)
    #     if target_channel:
    #         await target_channel.send(forwarded_message, allowed_mentions=allowed_mentions)
    #     else:
    #         print(f"channel not found: {TARGET_CHANNEL_ID}")

client.run(TOKEN)