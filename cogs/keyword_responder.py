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
        # 移除旧的单一频道配置
        # self.target_channel_id = config.get("target_channel_id")
        # self.source_channel_id = config.get("source_channel_id")
        
        # 获取服务器配置
        self.servers_config = config.get_all_servers()
        
        # 获取所有服务器的聊天频道配置
        self.chat_channels = {}
        for server_id, server_config in self.servers_config.items():
            if "chat_channels" in server_config:
                # 将每个服务器的聊天频道合并到总的字典中
                for channel_id, channel_config in server_config["chat_channels"].items():
                    self.chat_channels[channel_id] = {
                        "preset": channel_config.get("preset", "default"),
                        "server_id": server_id  # 记录该频道属于哪个服务器
                    }
        
        # 如果仍然存在老版本的chat_channel_id配置，也添加到字典中
        chat_channel_id = config.get("chat_channel_id")
        if chat_channel_id:
            self.chat_channels[str(chat_channel_id)] = {"preset": "default", "server_id": "server_1"}
        
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
        
    def get_server_id_for_guild(self, guild_id):
        """根据Discord服务器ID查找对应的配置服务器ID"""
        # 获取所有服务器配置
        self.servers_config = config.get_all_servers()
        
        # 遍历所有服务器配置，查找匹配的guild_id
        for server_id, server_config in self.servers_config.items():
            # 直接使用配置中的discord_guild_id进行匹配
            if server_config.get("discord_guild_id") == str(guild_id):
                return server_id
            
            # 如果没有直接匹配到，尝试通过频道ID间接匹配
            for channel_id in server_config.get("chat_channels", {}):
                channel = self.bot.get_channel(int(channel_id))
                if channel and channel.guild.id == guild_id:
                    return server_id
                    
        # 默认返回第一个服务器
        return next(iter(self.servers_config.keys())) if self.servers_config else None

    async def try_auto_reply(self, message):
        # 检查消息是否来自于任何一个聊天频道
        channel_id = str(message.channel.id)
        if channel_id not in self.chat_channels:
            return
            
        if self.in_trigger_message(message):
            await message.channel.send(
                random.choice(self.trigger_message[message.content])
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
        # 获取消息所在的服务器ID
        guild_id = message.guild.id if message.guild else None
        if not guild_id:
            return  # 如果不是来自服务器的消息，忽略
            
        # 根据guild_id获取对应的服务器配置ID
        server_id = self.get_server_id_for_guild(guild_id)
        if not server_id:
            return  # 找不到对应的服务器配置
            
        # 获取该服务器的源频道ID和目标频道ID
        source_channel_id = config.get_server_value(server_id, "source_channel_id")
        target_channel_id = config.get_server_value(server_id, "target_channel_id")
        
        if not source_channel_id or not target_channel_id:
            return  # 配置不完整
            
        # 转换为整数
        try:
            source_channel_id = int(source_channel_id)
            target_channel_id = int(target_channel_id)
        except ValueError:
            print(cpr.error(f"服务器 {server_id} 的频道ID配置无效"))
            return
            
        # 检查消息是否来自源频道
        if message.channel.id != source_channel_id:
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
            target_channel = self.bot.get_channel(target_channel_id)
            if not target_channel:
                print(cpr.error(f"无法找到目标频道: {target_channel_id}"))
                return
                
            for embed in embeds:
                await target_channel.send(embed=embed)
            await message.add_reaction("✅")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        await self.try_forward_images(message)
        await self.try_auto_reply(message)


async def setup(bot: commands.Bot):
    await bot.add_cog(KeywordResponder(bot))
