from discord.ext import commands
import discord
import os
from utils.decorator import auto_delete
from utils.func import mapping_cog, cpt


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(
        name="sync", description="Sync hybrid commands.", hidden=True
    )
    @commands.is_owner()
    @auto_delete()
    async def sync(self, ctx: commands.Context):
        await self.bot.tree.sync()
        await ctx.send("Synced hybrid commands.", ephemeral=True, delete_after=5)

    @commands.hybrid_command(
        name="list",
        description="List all loaded cogs.",
        hidden=True,
    )
    @commands.is_owner()
    @auto_delete()
    async def list(self, ctx: commands.Context):
        cogs = [cog for cog in self.bot.cogs]
        await ctx.send(
            f"Loaded cogs: {', '.join(cogs)}", ephemeral=True, delete_after=5
        )

    @commands.hybrid_command(name="load", description="Load a cog.", hidden=True)
    @commands.is_owner()
    @auto_delete()
    async def load(self, ctx: commands.Context, cog: str):
        await self.bot.load_extension(f"cogs.{mapping_cog(cog)}")
        await ctx.send(f"Loaded cog: {cog}", ephemeral=True, delete_after=5)

    @commands.hybrid_command(name="unload", description="Unload a cog.")
    @commands.is_owner()
    @auto_delete()
    async def unload(self, ctx: commands.Context, cog: str):
        await self.bot.unload_extension(f"cogs.{mapping_cog(cog)}")
        await ctx.send(f"Unloaded cog: {cog}", ephemeral=True, delete_after=5)

    @commands.hybrid_command(name="reload", description="Reload a cog.", hidden=True)
    @commands.is_owner()
    @auto_delete()
    async def reload(self, ctx: commands.Context, cog: str):
        await self.bot.reload_extension(f"cogs.{mapping_cog(cog)}")
        await ctx.send(f"Reloaded cog: {cog}", ephemeral=True, delete_after=5)

    @commands.hybrid_command(
        name="reload_all_loaded",
        description="Reload all cogs that are currently loaded.",
        hidden=True,
    )
    @commands.is_owner()
    @auto_delete()
    async def reload_all(self, ctx: commands.Context):
        for cog in self.bot.cogs:
            await self.bot.reload_extension(f"cogs.{mapping_cog(cog)}")
        await ctx.send("Reloaded all cogs.", ephemeral=True, delete_after=5)

    @commands.hybrid_command(
        name="reload_all",
        description="Reload all cogs in the cogs directory.",
        hidden=True,
    )
    @commands.is_owner()
    @auto_delete()
    async def reload_all(self, ctx: commands.Context):
        for file in os.listdir("cogs"):
            if file.endswith(".py"):
                await self.bot.reload_extension(f"cogs.{file[:-3]}")
        await ctx.send("Reloaded all cogs.", ephemeral=True, delete_after=5)

    @commands.hybrid_command(
        name="nickname", description="Change nickname.", hidden=True
    )
    @commands.is_owner()
    @commands.guild_only()
    @auto_delete(delay=0)
    async def nickname(self, ctx: commands.Context, *, nickname: str):
        await ctx.guild.me.edit(nick=nickname)
        await ctx.send(f"Hola, I'm now {nickname}, どうぞよろしく！")


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
    print(cpt.success("Cog loaded: Admin"))
