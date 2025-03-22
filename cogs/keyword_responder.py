from discord.ext import commands
import discord
import unicodedata
import random
from typing import Tuple

from utils.func import get_words
from utils.color_printer import cpr
from utils.config import config


class KeywordResponder(commands.Cog):
    def __init__(self, bot, words):
        self.bot = bot
        self.target_channel_id = config.get("target_channel_id")
        self.source_channel_id = config.get("source_channel_id")
        self.chat_channel_id = config.get("chat_channel_id")
        self.trigger_words, self.trigger_message, self.repeat_messages = (
            self.load_words(words)
        )

    def load_words(self, words) -> Tuple[dict, dict, set]:
        trigger_words = words.get("trigger_words")
        for w, k in words.get("trigger_words_rec").items():
            if trigger_words.get(k):
                trigger_words[w] = trigger_words[k]
        trigger_message = words.get("trigger_message")
        for w, k in words.get("trigger_message_rec").items():
            if trigger_message.get(k):
                trigger_message[w] = trigger_message[k]
        repeat_messages = set(words.get("repeat_messages"))
        print(cpr.info("Loaded words."))
        return trigger_words, trigger_message, repeat_messages

    def is_emoji(self, s):
        charset = unicodedata.category(s)
        return charset in ("So", "Sk", "Cf")

    def in_repeat(self, message):
        if message.content in self.repeat_messages:
            return True
        if len(message.content) == 1 and self.is_emoji(message.content):
            return True
        return False

    def in_trigger_message(self, message):
        if message.content in self.trigger_message.keys():
            return True
        return False

    def in_trigger_word(self, message):
        for w in self.trigger_words.keys():
            if w in message.content:
                return w
        return None

    async def try_auto_reply(self, message):
        if message.channel.id != self.chat_channel_id:
            return
        if self.in_trigger_message(message):
            await message.channel.send(
                random.choice(self.trigger_message(message.content))
            )
            return
        w = self.in_trigger_word(message)
        if w:
            await message.channel.send(random.choice(self.trigger_words[w]))
            return
        if self.in_repeat(message):
            await message.channel.send(message.content)
            return

    async def try_forward_images(self, message):
        if message.channel.id != self.source_channel_id:
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
                embed = discord.Embed(
                    title=f"#{i+1}",
                    color=color,
                    description=original_message_content,
                )
                embed.set_image(url=attachment.url)
                embed.set_footer(text=f"From {source_member.display_name}")
                embeds.append(embed)
            target_channel = self.bot.get_channel(self.target_channel_id)
            for embed in embeds:
                await target_channel.send(embed=embed)
            await message.add_reaction("✅")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        await self.try_forward_images(message)
        await self.try_auto_reply(message)


async def setup(
    bot: commands.Bot,
):
    words = get_words()
    await bot.add_cog(KeywordResponder(bot, words))
    print(cpr.success("Cog loaded: KeywordResponder"))
