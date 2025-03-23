import os
from discord.ext import commands
import discord
from discord import app_commands
import aiofiles
import aiohttp
import glob

from utils.color_printer import cpr
from utils.config import config


# 定义自动完成函数
async def preset_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    cog = interaction.client.get_cog("AgentManager")
    if not cog:
        return []
    presets = cog._get_available_presets()
    return [
        app_commands.Choice(name=preset, value=preset)
        for preset in presets if current.lower() in preset.lower()
    ]


class AgentManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.presets_path = "agent/presets"
        
        # 获取服务器配置
        self.servers_config = config.get_all_servers()
        
        # 初始化服务器-频道预设映射
        self.server_chat_channels = {}
        self.server_main_channel_ids = {}
        
        # 重新加载所有服务器的聊天频道配置
        self.reload_chat_channels()
        
        # 注册机器人准备好时的事件
        self.bot.add_listener(self.on_ready, "on_ready")
    
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
    
    def reload_chat_channels(self):
        """重新加载所有服务器的聊天频道配置"""
        # 清空现有的配置
        self.server_chat_channels = {}
        self.server_main_channel_ids = {}
        
        # 获取所有服务器配置
        self.servers_config = config.get_all_servers()
        
        # 为每个服务器加载频道配置
        for server_id, server_config in self.servers_config.items():
            # 获取该服务器的聊天频道配置
            chat_channels = server_config.get("chat_channels", {})
            self.server_chat_channels[server_id] = {
                str(channel_id): settings for channel_id, settings in chat_channels.items()
            }
            
            # 获取该服务器的主频道ID
            main_channel_id = str(server_config.get("main_channel_id", ""))
            self.server_main_channel_ids[server_id] = main_channel_id
            
            # 确保每个服务器的聊天频道配置不为空
            if not self.server_chat_channels[server_id]:
                # 如果该服务器没有配置chat_channels，使用默认配置
                self.server_chat_channels[server_id] = {
                    main_channel_id: {
                        "preset": "default"
                    }
                }
                # 更新配置文件
                config.write_server_value(server_id, "chat_channels", self.server_chat_channels[server_id])
        
        # 向后兼容：如果存在老版本的全局频道配置，也添加到server_1
        chat_channels = config.get("chat_channels")
        main_channel_id = config.get("main_channel_id")
        if chat_channels or main_channel_id:
            if "server_1" not in self.server_chat_channels:
                self.server_chat_channels["server_1"] = {}
            if chat_channels:
                self.server_chat_channels["server_1"].update(chat_channels)
            if main_channel_id:
                self.server_main_channel_ids["server_1"] = str(main_channel_id)
    
    async def update_all_cogs_channels(self):
        """通知所有相关的cog更新频道配置"""
        # 更新Gemini cog
        gemini_cog = self.bot.get_cog("Gemini")
        if gemini_cog:
            gemini_cog.update_chat_channels()
            
        # 更新Openai cog
        openai_cog = self.bot.get_cog("Openai")
        if openai_cog:
            openai_cog.update_chat_channels()
    
    async def on_ready(self):
        """当机器人准备好后调用，用于更新头像"""
        await self._update_bot_avatar()
    
    @commands.hybrid_command(
        name="agent", description="查看和切换不同的预设模式"
    )
    @app_commands.describe(preset="选择要切换的预设")
    @app_commands.autocomplete(preset=preset_autocomplete)
    async def agent(self, ctx: commands.Context, preset: str = None):
        # 获取服务器ID
        guild_id = ctx.guild.id if ctx.guild else None
        if not guild_id:
            await ctx.send("此命令只能在服务器中使用。", ephemeral=True)
            return
            
        # 获取对应的服务器配置ID
        server_id = self.get_server_id_for_guild(guild_id)
        if not server_id:
            await ctx.send("无法找到此服务器的配置。", ephemeral=True)
            return
            
        # 检查当前频道是否在该服务器支持的聊天频道列表中
        channel_id = str(ctx.channel.id)
        if server_id not in self.server_chat_channels or channel_id not in self.server_chat_channels[server_id]:
            await ctx.send("此命令只能在指定的聊天频道中使用", ephemeral=True)
            return
            
        current_preset = self.server_chat_channels[server_id][channel_id]["preset"]
            
        if preset is None:
            # 列出所有可用的预设
            presets = self._get_available_presets()
            preset_list = "\n".join([f"- `{p}`" for p in presets])
            await ctx.send(
                f"当前频道预设: **{current_preset}**\n\n"
                f"可用预设:\n{preset_list}\n\n"
                f"使用 `/agent <预设名>` 切换预设。",
                ephemeral=True
            )
            return

        # 检查预设是否存在
        if not os.path.exists(f"{self.presets_path}/{preset}"):
            await ctx.send(
                f"预设 '{preset}' 不存在。可用预设:\n"
                f"{', '.join(self._get_available_presets())}",
                ephemeral=True
            )
            return

        # 切换当前频道的预设
        self.server_chat_channels[server_id][channel_id]["preset"] = preset
        # 更新配置文件
        config.write_server_value(server_id, "chat_channels", self.server_chat_channels[server_id])
        
        # 如果是主频道，更新机器人头像
        if channel_id == self.server_main_channel_ids.get(server_id):
            await self._update_bot_avatar(server_id)
        
        # 通知其他cog更新频道配置
        await self.update_all_cogs_channels()
        
        await ctx.send(f"已将频道 <#{channel_id}> 切换到预设: **{preset}**", ephemeral=True)
    
    async def _update_bot_avatar(self, server_id=None):
        """根据主频道预设更新机器人头像，可指定服务器ID"""
        # 确保机器人已经准备好
        if not self.bot.is_ready():
            print(cpr.warning("机器人尚未准备好，暂不更新头像"))
            return
            
        # 如果未指定服务器ID，使用第一个服务器
        if server_id is None and self.server_main_channel_ids:
            server_id = next(iter(self.server_main_channel_ids.keys()))
            
        if not server_id:
            print(cpr.warning("无法确定要使用的服务器ID，无法更新头像"))
            return
            
        # 获取服务器主频道的预设
        main_preset = "default"
        main_channel_id = self.server_main_channel_ids.get(server_id)
        
        if main_channel_id and server_id in self.server_chat_channels and main_channel_id in self.server_chat_channels[server_id]:
            main_preset = self.server_chat_channels[server_id][main_channel_id].get("preset", "default")
        else:
            print(cpr.warning(f"服务器 {server_id} 的主频道配置不完整，使用默认预设"))
            
        # 查找主频道预设目录中的avatar文件
        avatar_path = self._find_avatar_file(main_preset)
        if not avatar_path:
            print(cpr.warning(f"未找到预设 '{main_preset}' 的头像文件"))
            return
        
        try:
            # 读取头像文件
            async with aiofiles.open(avatar_path, 'rb') as image:
                avatar_data = await image.read()
                
            # 更新机器人头像
            await self.bot.user.edit(avatar=avatar_data)
            print(cpr.success(f"已更新机器人头像为预设 '{main_preset}' 的头像"))
        except discord.errors.HTTPException as e:
            if e.status == 429:  # Rate limit error
                print(cpr.warning(f"更新头像失败: 速率限制，请稍后再试"))
            else:
                print(cpr.error(f"更新头像失败: {e}"))
        except Exception as e:
            print(cpr.error(f"更新头像时发生错误: {e}"))
    
    def _find_avatar_file(self, preset_name="default"):
        """查找指定预设目录中的avatar文件"""
        preset_dir = f"{self.presets_path}/{preset_name}"
        # 查找名为avatar的文件，不限制扩展名
        avatar_files = glob.glob(f"{preset_dir}/avatar.*")
        
        if avatar_files:
            return avatar_files[0]  # 返回找到的第一个avatar文件
        return None
    
    def _get_available_presets(self):
        """获取所有可用的预设"""
        if not os.path.exists(self.presets_path):
            return ["default"]
        return [d for d in os.listdir(self.presets_path) 
                if os.path.isdir(os.path.join(self.presets_path, d))]

    def get_current_preset_path(self, channel_id=None, guild_id=None):
        """获取当前预设的路径，可指定频道ID和服务器ID"""
        server_id = None
        
        # 如果提供了guild_id，尝试获取对应的服务器配置ID
        if guild_id:
            server_id = self.get_server_id_for_guild(guild_id)
        
        # 如果提供了频道ID，尝试找到对应的预设
        if channel_id and server_id:
            channel_id = str(channel_id)
            if server_id in self.server_chat_channels and channel_id in self.server_chat_channels[server_id]:
                preset = self.server_chat_channels[server_id][channel_id].get("preset", "default")
                return f"{self.presets_path}/{preset}"
        
        # 如果只提供了频道ID，尝试在所有服务器中查找
        if channel_id and not server_id:
            channel_id = str(channel_id)
            for srv_id, channels in self.server_chat_channels.items():
                if channel_id in channels:
                    preset = channels[channel_id].get("preset", "default")
                    return f"{self.presets_path}/{preset}"
        
        # 如果没有找到匹配的预设，使用默认预设
        return f"{self.presets_path}/default"

    def get_preset_file(self, file_name, channel_id=None, guild_id=None):
        """获取预设文件的内容，可指定频道ID和服务器ID"""
        preset_path = self.get_current_preset_path(channel_id, guild_id)
        file_path = f"{preset_path}/{file_name}"
        
        if not os.path.exists(file_path):
            # 如果当前预设中没有找到文件，回退到默认预设
            file_path = f"{self.presets_path}/default/{file_name}"
        
        if not os.path.exists(file_path):
            return None
            
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    
    def get_preset_json(self, file_name, channel_id=None, guild_id=None):
        """获取预设JSON文件的内容，可指定频道ID和服务器ID"""
        import json
        preset_path = self.get_current_preset_path(channel_id, guild_id)
        file_path = f"{preset_path}/{file_name}"
        
        if not os.path.exists(file_path):
            # 如果当前预设中没有找到文件，回退到默认预设
            file_path = f"{self.presets_path}/default/{file_name}"
        
        if not os.path.exists(file_path):
            return None
            
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @commands.hybrid_command(
        name="channel_presets", description="查看所有频道的预设配置"
    )
    @commands.has_permissions(administrator=True)
    async def channel_presets(self, ctx: commands.Context):
        # 获取服务器ID
        guild_id = ctx.guild.id if ctx.guild else None
        if not guild_id:
            await ctx.send("此命令只能在服务器中使用。", ephemeral=True)
            return
            
        # 获取对应的服务器配置ID
        server_id = self.get_server_id_for_guild(guild_id)
        if not server_id:
            await ctx.send("无法找到此服务器的配置。", ephemeral=True)
            return
        
        # 重新加载配置，确保显示最新的数据
        self.reload_chat_channels()
        
        # 获取当前服务器的频道配置
        channels = self.server_chat_channels.get(server_id, {})
        if not channels:
            await ctx.send(f"服务器 {server_id} 当前没有任何频道配置", ephemeral=True)
            return
            
        message = f"**服务器 {server_id} 频道预设配置**\n\n"
        
        main_channel_id = self.server_main_channel_ids.get(server_id, "")
        
        for channel_id, config in channels.items():
            preset = config.get("preset", "default")
            channel_name = f"<#{channel_id}>"
            main_tag = "🌟 主频道" if channel_id == main_channel_id else ""
            
            message += f"• {channel_name}: **{preset}** {main_tag}\n"
            
        await ctx.send(message, ephemeral=True)
    
    @commands.hybrid_command(
        name="add-chat", description="将当前频道添加为聊天频道"
    )
    @commands.has_permissions(administrator=True)
    async def add_chat(self, ctx: commands.Context, preset: str = "default"):
        # 获取服务器ID
        guild_id = ctx.guild.id if ctx.guild else None
        if not guild_id:
            await ctx.send("此命令只能在服务器中使用。", ephemeral=True)
            return
            
        # 获取对应的服务器配置ID
        server_id = self.get_server_id_for_guild(guild_id)
        if not server_id:
            await ctx.send("无法找到此服务器的配置。", ephemeral=True)
            return
            
        channel_id = str(ctx.channel.id)
        
        # 检查预设是否存在
        if preset != "default" and not os.path.exists(f"{self.presets_path}/{preset}"):
            await ctx.send(
                f"预设 '{preset}' 不存在。可用预设:\n"
                f"{', '.join(self._get_available_presets())}",
                ephemeral=True
            )
            return
        
        # 确保服务器配置存在
        if server_id not in self.server_chat_channels:
            self.server_chat_channels[server_id] = {}
            
        # 添加频道配置
        self.server_chat_channels[server_id][channel_id] = {"preset": preset}
        
        # 更新配置文件
        config.write_server_value(server_id, "chat_channels", self.server_chat_channels[server_id])
        
        # 通知其他cog更新频道配置
        await self.update_all_cogs_channels()
        
        await ctx.send(f"已将频道 <#{channel_id}> 添加为聊天频道，使用预设: **{preset}**", ephemeral=True)
    
    @commands.hybrid_command(
        name="remove-chat", description="从聊天频道列表中移除当前频道"
    )
    @commands.has_permissions(administrator=True)
    async def remove_chat(self, ctx: commands.Context):
        # 获取服务器ID
        guild_id = ctx.guild.id if ctx.guild else None
        if not guild_id:
            await ctx.send("此命令只能在服务器中使用。", ephemeral=True)
            return
            
        # 获取对应的服务器配置ID
        server_id = self.get_server_id_for_guild(guild_id)
        if not server_id:
            await ctx.send("无法找到此服务器的配置。", ephemeral=True)
            return
            
        channel_id = str(ctx.channel.id)
        
        # 检查频道是否在聊天频道列表中
        if server_id not in self.server_chat_channels or channel_id not in self.server_chat_channels[server_id]:
            await ctx.send("此频道不在聊天频道列表中。", ephemeral=True)
            return
        
        # 检查是否是主频道
        main_channel_id = self.server_main_channel_ids.get(server_id)
        if channel_id == main_channel_id:
            await ctx.send("无法移除主频道，请先使用 `/main-chat` 命令设置其他频道为主频道。", ephemeral=True)
            return
        
        # 从配置中移除频道
        del self.server_chat_channels[server_id][channel_id]
        
        # 更新配置文件
        config.write_server_value(server_id, "chat_channels", self.server_chat_channels[server_id])
        
        # 通知其他cog更新频道配置
        await self.update_all_cogs_channels()
        
        await ctx.send(f"已从聊天频道列表中移除频道 <#{channel_id}>", ephemeral=True)
    
    @commands.hybrid_command(
        name="main-chat", description="将当前频道设置为主频道"
    )
    @commands.has_permissions(administrator=True)
    async def main_chat(self, ctx: commands.Context):
        # 获取服务器ID
        guild_id = ctx.guild.id if ctx.guild else None
        if not guild_id:
            await ctx.send("此命令只能在服务器中使用。", ephemeral=True)
            return
            
        # 获取对应的服务器配置ID
        server_id = self.get_server_id_for_guild(guild_id)
        if not server_id:
            await ctx.send("无法找到此服务器的配置。", ephemeral=True)
            return
            
        channel_id = str(ctx.channel.id)
        
        # 检查频道是否已经是聊天频道
        if server_id not in self.server_chat_channels or channel_id not in self.server_chat_channels[server_id]:
            # 自动添加为聊天频道
            if server_id not in self.server_chat_channels:
                self.server_chat_channels[server_id] = {}
            self.server_chat_channels[server_id][channel_id] = {"preset": "default"}
            config.write_server_value(server_id, "chat_channels", self.server_chat_channels[server_id])
            
        # 更新主频道ID
        self.server_main_channel_ids[server_id] = channel_id
        config.write_server_value(server_id, "main_channel_id", channel_id)
        
        # 更新机器人头像
        await self._update_bot_avatar(server_id)
        
        # 通知其他cog更新频道配置
        await self.update_all_cogs_channels()
        
        await ctx.send(f"已将频道 <#{channel_id}> 设置为主频道", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AgentManager(bot)) 