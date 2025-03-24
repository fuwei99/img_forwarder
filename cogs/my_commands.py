from discord.ext import commands
import discord

from utils.config import config
from utils.color_printer import cpr


class MyCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = config

    def get_backup_channel(self, guild_id: str):
        """获取备份频道"""
        server_name, server_config = config.get_server_config(guild_id)
        if not server_config:
            return None
        backup_channel_id = server_config.get("backup_channel_id")
        if not backup_channel_id:
            return None
        return self.bot.get_channel(int(backup_channel_id))

    @commands.hybrid_command(name="ping", description="检查机器人延迟。")
    async def ping(self, ctx: commands.Context):
        await ctx.send(f"延迟: {round(self.bot.latency * 1000)}ms")

    @commands.hybrid_command(name="backup", description="备份一条消息。")
    async def backup(self, ctx: commands.Context):
        if ctx.message.reference is None:
            await ctx.send("你必须回复一条消息来备份它。", ephemeral=True)
            return
        if ctx.message.reference.resolved is None:
            await ctx.send("无法解析你回复的消息。", ephemeral=True)
            return
        if not isinstance(ctx.message.reference.resolved, discord.Message):
            await ctx.send("你回复的不是一条消息。", ephemeral=True)
            return
            
        # 检查是否已经备份过
        for reaction in ctx.message.reference.resolved.reactions:
            if reaction.emoji == "📨" and reaction.me:
                await ctx.send(
                    "这条消息已经备份过了。",
                    delete_after=5,
                    ephemeral=True,
                )
                return

        # 获取备份频道
        backup_channel = self.get_backup_channel(str(ctx.guild.id))
        if backup_channel is None:
            await ctx.send("找不到备份频道。", ephemeral=True)
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
            name="原始消息",
            value=f"[跳转]({original_message.jump_url})",
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

        if embeds or files:
            await backup_channel.send(embeds=embeds, files=files)
        await original_message.add_reaction("📨")


async def setup(bot: commands.Bot):
    await bot.add_cog(MyCommands(bot))
    print(cpr.success("Cog loaded: MyCommands"))
