from discord.ext import commands
import discord


class MyCommands(commands.Cog):
    def __init__(self, bot, backup_channel_id):
        self.bot = bot
        self.backup_channel_id = backup_channel_id

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

        original_message = ctx.message.reference.resolved

        embed = discord.Embed(
            description=original_message.content,
            color=original_message.author.color,
            timestamp=original_message.created_at,
        )
        embed.set_author(
            name=original_message.author.display_name,
            icon_url=original_message.author.avatar_url,
        )
        embed.add_field(
            name="Original message",
            value=f"[Jump!]({original_message.jump_url})",
            inline=True,
        )

        if original_message.attachments:
            embed.set_image(url=original_message.attachments[0].url)

        backup_channel = self.bot.get_channel(self.backup_channel_id)
        if backup_channel is None:
            await ctx.send("The backup channel could not be found.")
            return
        await backup_channel.send(embed=embed)
        # 加一个备份符号
        await original_message.add_reaction("📨")
