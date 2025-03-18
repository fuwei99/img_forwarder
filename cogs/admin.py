from discord.ext import commands
import discord


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="sync", description="Sync hybrid commands.")
    @commands.is_owner()
    async def sync(self, ctx: commands.Context):
        self.bot.sync_all_commands()
        await ctx.send("Synced hybrid commands.", ephemeral=True, delete_after=5)
