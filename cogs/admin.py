from discord.ext import commands
import discord
import os
from utils.decorator import auto_delete
from utils.func import mapping_cog
from utils.color_printer import cpr
from utils.config import config


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(
        name="sync", description="Sync hybrid commands.", hidden=True
    )
    @commands.is_owner()
    @auto_delete(delay=0)
    async def sync(self, ctx: commands.Context):
        await self.bot.tree.sync()
        await ctx.send("Synced hybrid commands.", ephemeral=True, delete_after=5)

    @commands.hybrid_command(
        name="list",
        description="List all loaded cogs.",
        hidden=True,
    )
    @commands.is_owner()
    @auto_delete(delay=0)
    async def list(self, ctx: commands.Context):
        cogs = [cog for cog in self.bot.cogs]
        await ctx.send(
            f"Loaded cogs: {', '.join(cogs)}", ephemeral=True, delete_after=5
        )

    @commands.hybrid_command(name="load", description="加载指定的cog")
    @commands.is_owner()
    @auto_delete(delay=0)
    async def load(self, ctx: commands.Context, cog: str):
        try:
            # 先发送消息
            await ctx.send(f"正在加载 cog: {cog}...", ephemeral=True, delete_after=5)
            # 然后加载cog
            await self.bot.load_extension(f"cogs.{mapping_cog(cog)}")
        except Exception as e:
            await ctx.channel.send(f"加载 {cog} 失败: {str(e)}", delete_after=5)

    @commands.hybrid_command(name="unload", description="卸载指定的cog")
    @commands.is_owner()
    @auto_delete(delay=0)
    async def unload(self, ctx: commands.Context, cog: str):
        try:
            # 先发送消息
            await ctx.send(f"正在卸载 cog: {cog}...", ephemeral=True, delete_after=5)
            # 然后卸载cog
            await self.bot.unload_extension(f"cogs.{mapping_cog(cog)}")
        except Exception as e:
            await ctx.channel.send(f"卸载 {cog} 失败: {str(e)}", delete_after=5)

    @commands.hybrid_command(name="reload", description="重新加载指定的cog")
    @commands.is_owner()
    @auto_delete(delay=0)
    async def reload(self, ctx: commands.Context, cog: str):
        try:
            # 先发送消息
            await ctx.send(f"正在重载 cog: {cog}...", ephemeral=True, delete_after=5)
            # 然后重载cog
            await self.bot.reload_extension(f"cogs.{mapping_cog(cog)}")
        except Exception as e:
            await ctx.channel.send(f"重载 {cog} 失败: {str(e)}", delete_after=5)

    @commands.hybrid_command(
        name="reload_all",
        description="重新加载所有已加载的cog",
        hidden=True,
    )
    @commands.is_owner()
    @auto_delete(delay=0)
    async def reload_all(self, ctx: commands.Context):
        success_cogs = []
        failed_cogs = []
        
        # 获取当前已加载的cog列表
        loaded_cogs = list(self.bot.cogs.keys())
        
        for cog_name in loaded_cogs:
            try:
                # 将cog名称转换为文件名格式
                file_name = mapping_cog(cog_name)
                await self.bot.reload_extension(f"cogs.{file_name}")
                success_cogs.append(cog_name)
            except Exception as e:
                failed_cogs.append(f"{cog_name} ({str(e)})")
        
        # 构建响应消息
        response = []
        if success_cogs:
            response.append(f"✅ 成功重载的cog: {', '.join(success_cogs)}")
        if failed_cogs:
            response.append(f"❌ 重载失败的cog: {', '.join(failed_cogs)}")
        
        await ctx.send("\n".join(response), ephemeral=True, delete_after=10)

    @commands.hybrid_command(
        name="nickname", description="Change nickname.", hidden=True
    )
    @commands.is_owner()
    @commands.guild_only()
    @auto_delete(delay=0)
    async def nickname(self, ctx: commands.Context, *, nickname: str):
        await ctx.guild.me.edit(nick=nickname)
        await ctx.send(f"Hola, I'm now {nickname}, どうぞよろしく！")

    @commands.hybrid_command(
        name="reload_config", description="重新加载配置文件", hidden=True
    )
    @commands.is_owner()
    @auto_delete(delay=0)
    async def reload_config(self, ctx: commands.Context):
        config.reload()
        await ctx.send("Reloaded config.", ephemeral=True, delete_after=5)

    @commands.hybrid_command(name="status", description="Change status.", hidden=True)
    @commands.is_owner()
    @auto_delete(delay=0)
    async def status(self, ctx: commands.Context, *, status: str):
        await self.bot.change_presence(activity=discord.Game(name=status))
        await ctx.send(f"Changed status to {status}.", ephemeral=True, delete_after=5)


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
    print(cpr.success("Cog loaded: Admin"))
