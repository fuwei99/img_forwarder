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
        
        # 初始化多频道预设配置
        self.reload_chat_channels()
        
        # 注册机器人准备好时的事件
        self.bot.add_listener(self.on_ready, "on_ready")
    
    def reload_chat_channels(self):
        """重新加载聊天频道配置"""
        chat_channels = config.get("chat_channels", {})
        self.chat_channels = {str(channel_id): settings for channel_id, settings in chat_channels.items()}
        
        if not self.chat_channels:
            # 如果没有配置chat_channels，创建默认配置
            main_channel_id = "1350642349000233180"
            self.chat_channels = {
                main_channel_id: {
                    "preset": "default"
                }
            }
            config.write("chat_channels", self.chat_channels)
            config.write("main_channel_id", main_channel_id)
        
        # 获取主频道ID
        self.main_channel_id = str(config.get("main_channel_id", "1350642349000233180"))
    
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
        # 检查当前频道是否在支持的聊天频道列表中
        channel_id = str(ctx.channel.id)
        if channel_id not in self.chat_channels:
            await ctx.send("此命令只能在指定的聊天频道中使用", ephemeral=True)
            return
            
        current_preset = self.chat_channels[channel_id]["preset"]
            
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
        self.chat_channels[channel_id]["preset"] = preset
        config.write("chat_channels", self.chat_channels)
        
        # 如果是主频道，更新机器人头像
        if channel_id == self.main_channel_id:
            await self._update_bot_avatar()
        
        # 通知其他cog更新频道配置
        await self.update_all_cogs_channels()
        
        await ctx.send(f"已将频道 <#{channel_id}> 切换到预设: **{preset}**", ephemeral=True)
    
    async def _update_bot_avatar(self):
        """根据主频道预设更新机器人头像"""
        # 确保机器人已经准备好
        if not self.bot.is_ready():
            print(cpr.warning("机器人尚未准备好，暂不更新头像"))
            return
            
        # 获取主频道的预设
        main_preset = "default"
        if self.main_channel_id in self.chat_channels:
            main_preset = self.chat_channels[self.main_channel_id].get("preset", "default")
        else:
            print(cpr.warning(f"配置中的主频道 {self.main_channel_id} 不存在于chat_channels中，使用默认预设"))
            
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

    def get_current_preset_path(self, channel_id=None):
        """获取当前预设的路径，可指定频道ID"""
        if channel_id:
            channel_id = str(channel_id)
            if channel_id in self.chat_channels:
                preset = self.chat_channels[channel_id].get("preset", "default")
                return f"{self.presets_path}/{preset}"
        
        # 如果没有指定频道或频道不存在配置，使用默认预设
        return f"{self.presets_path}/default"

    def get_preset_file(self, file_name, channel_id=None):
        """获取预设文件的内容，可指定频道ID"""
        preset_path = self.get_current_preset_path(channel_id)
        file_path = f"{preset_path}/{file_name}"
        
        if not os.path.exists(file_path):
            # 如果当前预设中没有找到文件，回退到默认预设
            file_path = f"{self.presets_path}/default/{file_name}"
        
        if not os.path.exists(file_path):
            return None
            
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    
    def get_preset_json(self, file_name, channel_id=None):
        """获取预设JSON文件的内容，可指定频道ID"""
        import json
        preset_path = self.get_current_preset_path(channel_id)
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
        # 重新加载配置，确保显示最新的数据
        self.reload_chat_channels()
        
        if len(self.chat_channels) == 0:
            await ctx.send("当前没有任何频道配置", ephemeral=True)
            return
            
        message = "**频道预设配置**\n\n"
        
        for channel_id, config in self.chat_channels.items():
            preset = config.get("preset", "default")
            channel_name = f"<#{channel_id}>"
            main_tag = "🌟 主频道" if channel_id == self.main_channel_id else ""
            
            message += f"• {channel_name}: **{preset}** {main_tag}\n"
            
        await ctx.send(message, ephemeral=True)
    
    @commands.hybrid_command(
        name="add-chat", description="将当前频道添加为聊天频道"
    )
    @commands.has_permissions(administrator=True)
    async def add_chat(self, ctx: commands.Context, preset: str = "default"):
        channel_id = str(ctx.channel.id)
        
        # 检查预设是否存在
        if preset != "default" and not os.path.exists(f"{self.presets_path}/{preset}"):
            await ctx.send(
                f"预设 '{preset}' 不存在。可用预设:\n"
                f"{', '.join(self._get_available_presets())}",
                ephemeral=True
            )
            return
            
        # 检查频道是否已存在
        if channel_id in self.chat_channels:
            current_preset = self.chat_channels[channel_id]["preset"]
            await ctx.send(
                f"此频道已是聊天频道，当前使用预设: **{current_preset}**\n"
                f"若要更改预设，请使用 `/agent {preset}` 命令",
                ephemeral=True
            )
            return
        
        # 添加频道到聊天频道列表
        self.chat_channels[channel_id] = {
            "preset": preset
        }
        
        # 保存配置
        config.write("chat_channels", self.chat_channels)
        
        # 通知其他cog更新频道配置
        await self.update_all_cogs_channels()
        
        await ctx.send(f"已将频道 <#{channel_id}> 添加为聊天频道，使用预设: **{preset}**", ephemeral=True)
        print(cpr.success(f"已添加频道 {channel_id} 为聊天频道，使用预设: {preset}"))
    
    @commands.hybrid_command(
        name="remove-chat", description="从聊天频道列表中移除当前频道"
    )
    @commands.has_permissions(administrator=True)
    async def remove_chat(self, ctx: commands.Context):
        channel_id = str(ctx.channel.id)
        
        # 检查频道是否存在于列表中
        if channel_id not in self.chat_channels:
            await ctx.send("此频道不在聊天频道列表中", ephemeral=True)
            return
        
        # 检查是否为主频道
        if channel_id == self.main_channel_id:
            await ctx.send("无法移除主频道。请先使用 `/main-chat` 设置其他频道为主频道，再移除此频道", ephemeral=True)
            return
        
        # 从列表中移除频道
        del self.chat_channels[channel_id]
        
        # 保存配置
        config.write("chat_channels", self.chat_channels)
        
        # 通知其他cog更新频道配置
        await self.update_all_cogs_channels()
        
        await ctx.send(f"已将频道 <#{channel_id}> 从聊天频道列表中移除", ephemeral=True)
        print(cpr.warning(f"已从聊天频道列表中移除频道 {channel_id}"))
    
    @commands.hybrid_command(
        name="main-chat", description="将当前频道设置为主频道"
    )
    @commands.has_permissions(administrator=True)
    async def main_chat(self, ctx: commands.Context):
        channel_id = str(ctx.channel.id)
        
        # 检查频道是否存在于列表中
        if channel_id not in self.chat_channels:
            # 如果频道不存在于列表中，自动添加为聊天频道
            self.chat_channels[channel_id] = {
                "preset": "default"
            }
        
        # 更新主频道ID
        old_main_channel_id = self.main_channel_id
        self.main_channel_id = channel_id
        
        # 保存配置
        config.write("main_channel_id", channel_id)
        config.write("chat_channels", self.chat_channels)
        
        # 通知其他cog更新频道配置
        await self.update_all_cogs_channels()
        
        # 更新机器人头像
        await self._update_bot_avatar()
        
        await ctx.send(
            f"已将频道 <#{channel_id}> 设置为主频道\n"
            f"之前的主频道为 <#{old_main_channel_id}>",
            ephemeral=True
        )
        print(cpr.success(f"已将频道 {channel_id} 设置为主频道，之前的主频道为 {old_main_channel_id}"))


async def setup(bot: commands.Bot):
    cog = AgentManager(bot)
    await bot.add_cog(cog)
    # 不再这里更新头像，而是等待on_ready事件
    print(cpr.success("Cog loaded: AgentManager")) 