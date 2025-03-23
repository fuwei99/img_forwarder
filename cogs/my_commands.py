from discord.ext import commands
import discord

from utils.config import config
from utils.color_printer import cpr


class MyCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 不再直接使用单一备份频道
        # self.backup_channel_id = config.get("backup_channel_id")
        # 获取服务器配置
        self.servers_config = config.get_all_servers()

    @commands.hybrid_command(name="ping", description="Check the bot's latency.")
    async def ping(self, ctx: commands.Context):
        await ctx.send(f"Pong! {round(self.bot.latency * 1000)}ms")
        
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

    @commands.hybrid_command(name="backup", description="Back up a message.")
    async def backup(self, ctx: commands.Context):
        if ctx.message.reference is None:
            await ctx.send("You must reply to a message to back it up.")
            return
        if ctx.message.reference.resolved is None:
            await ctx.send("The message you replied to could not be resolved.")
            return
        if not isinstance(ctx.message.reference.resolved, discord.Message):
            await ctx.send("The message you replied to is not a message.")
            return
        for reaction in ctx.message.reference.resolved.reactions:
            if reaction.emoji == "📨" and reaction.me:
                await ctx.send(
                    "This message has already been backed up.",
                    delete_after=5,
                    ephemeral=True,
                )
                return

        # 获取消息所在的服务器ID
        guild_id = ctx.guild.id if ctx.guild else None
        if not guild_id:
            await ctx.send("此命令只能在服务器中使用。", ephemeral=True)
            return
            
        # 根据guild_id获取对应的服务器配置ID
        server_id = self.get_server_id_for_guild(guild_id)
        if not server_id:
            await ctx.send("无法找到此服务器的配置。", ephemeral=True)
            return
            
        # 获取该服务器的备份频道ID
        backup_channel_id = config.get_server_value(server_id, "backup_channel_id")
        if not backup_channel_id:
            await ctx.send("此服务器没有配置备份频道。", ephemeral=True)
            return
            
        # 转换为整数
        try:
            backup_channel_id = int(backup_channel_id)
        except ValueError:
            await ctx.send("备份频道ID配置无效。", ephemeral=True)
            return

        original_message = ctx.message.reference.resolved

        embed = discord.Embed(
            description=original_message.content,
            color=original_message.author.color,
            timestamp=original_message.created_at,
        )
        embed.set_author(
            name=original_message.author.display_name,
            icon_url=original_message.author.avatar,
        )
        embed.add_field(
            name="Original message",
            value=f"[Jump!]({original_message.jump_url})",
            inline=True,
        )

        embeds = [embed]
        files = []
        for attachment in original_message.attachments:
            if attachment.content_type.startswith("image"):
                new_embed = discord.Embed()
                new_embed.set_image(url=attachment.url)
                embeds.append(new_embed)
            else:
                file = await attachment.to_file()
                files.append(file)

        backup_channel = self.bot.get_channel(backup_channel_id)
        if backup_channel is None:
            await ctx.send("The backup channel could not be found.")
            return
        if embeds or files:
            await backup_channel.send(embeds=embeds, files=files)
        await original_message.add_reaction("📨")


async def setup(bot: commands.Bot):
    await bot.add_cog(MyCommands(bot))
