import json
from discord.ext import commands
import discord
from aiohttp import ClientSession
import asyncio
import os

from utils.color_printer import cpr
from utils.config import config
from utils.decorator import auto_delete
from utils.context_prompter import ContextPrompter
from utils.logger import logger


class Openai(commands.Cog):
    def __init__(self, bot: commands.Bot, webhook_url: str):
        self.bot = bot
        self.webhook_url = webhook_url
        self.key = config.get("openai_key")
        self.endpoint = config.get("openai_endpoint")
        self.models: dict[str, str] = config.get("openai_models")
        self.context_prompter = ContextPrompter()
        
        # 确保chat_channels中的键全部为字符串
        self.update_chat_channels()
        
        # 从配置文件读取默认模型，如果没有则使用第一个模型
        self.model = config.get("default_openai_model")
        if not self.model or self.model not in self.models:
            self.model = list(self.models.keys())[0]
            config.write("default_openai_model", self.model)
        
        self.context_length = 20

    async def cog_load(self):
        """当cog被加载时调用，这是一个异步上下文"""
        # 注册on_ready事件来设置context_prompter
        self.bot.add_listener(self._on_ready, "on_ready")

    async def _on_ready(self):
        """当机器人准备好时执行"""
        # 设置agent_manager到context_prompter
        agent_manager = self.bot.get_cog("AgentManager")
        if agent_manager:
            self.context_prompter.set_agent_manager(agent_manager)
            print(f"OpenAI cog: AgentManager 已设置到 ContextPrompter")

    def update_chat_channels(self):
        """更新聊天频道配置"""
        # 获取所有服务器配置
        self.servers = config.get("servers", {})
        print(f"OpenAI cog 已更新服务器配置")
    
    def get_channel_config(self, guild_id: str, channel_id: str):
        """获取频道配置"""
        server_name, server_config = config.get_server_config(guild_id)
        if not server_config:
            return None
        return server_config.get("chat_channels", {}).get(channel_id)

    async def request_openai(self, model: str, prompt: str, username: str, guild_id=None, channel_id=None) -> str:
        url = f"{self.endpoint}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.key}",
        }
        
        # 尝试从Agent Manager获取配置
        openai_config = {}
        preset = None
        
        if hasattr(self.bot, "get_cog"):
            agent_manager = self.bot.get_cog("AgentManager")
            if agent_manager:
                # 获取OpenAI配置
                config_from_preset = agent_manager.get_preset_json("openai_config.json", channel_id, guild_id)
                if config_from_preset:
                    openai_config = config_from_preset
                
                # 根据当前的使用场景选择预设
                # 这里根据prompt内容判断使用哪种预设
                if "<reference>" in prompt and "<attachment>" in prompt:
                    preset = agent_manager.get_preset_json("attachment_preset.json", channel_id, guild_id)
                elif "<reference>" in prompt:
                    preset = agent_manager.get_preset_json("reference_preset.json", channel_id, guild_id)
                else:
                    preset = agent_manager.get_preset_json("chat_preset.json", channel_id, guild_id)
        
        # 构建消息
        messages = []
        
        # 如果未获取到预设，直接使用原始格式
        if not preset:
            messages = [{"role": "user", "content": prompt}]
        else:
            # 构建符合预设格式的消息数组
            if preset.get("system_prompt"):
                messages.append({
                    "role": "system", 
                    "content": preset["system_prompt"]
                })
            
            messages.append({
                "role": "user", 
                "content": preset.get("first_user_message", "历史消息如下")
            })
            
            messages.append({
                "role": "assistant", 
                "content": prompt  # 这里是原始prompt，它已经包含了main_content的格式
            })
            
            messages.append({
                "role": "user", 
                "content": preset.get("last_user_message", "Your reply:")
            })
        
        data = {
            "model": self.models[model]["id"],
            "messages": messages,
            "top_p": openai_config.get("top_p", 0.95),
            "top_k": openai_config.get("top_k", 55),
            "temperature": openai_config.get("temperature", 1.0),
            "stream": False,
        }
        
        # 记录API请求数据
        logger.info(f"OpenAI API 请求数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        try:
            # 创建新的ClientSession用于API请求
            async with ClientSession() as session:
                # 使用会话进行API请求
                async with session.post(url, headers=headers, json=data) as resp:
                    resp.raise_for_status()
                    response_data = await resp.json()
                    
                    # 从响应中提取回复内容
                    if "choices" in response_data and len(response_data["choices"]) > 0:
                        content = response_data["choices"][0]["message"]["content"]
                        if not content or content.strip() == "":
                            raise ValueError("API返回了空响应")
                        return content
                    else:
                        raise ValueError("API返回的响应格式不正确")
        except Exception as e:
            logger.error(f"OpenAI API请求失败: {str(e)}")
            raise ValueError(f"OpenAI API请求失败: {str(e)}")

    @commands.hybrid_command(name="yo", description="Chat with OpenAI models.")
    async def yo(
        self,
        ctx: commands.Context,
        model: str,
        *,
        question: str,
        context_length: int = None,
    ):
        # 获取服务器和频道配置
        guild_id = str(ctx.guild.id)
        channel_id = str(ctx.channel.id)
        channel_config = self.get_channel_config(guild_id, channel_id)
        
        if not channel_config:
            await ctx.send("此频道未配置为聊天频道", ephemeral=True)
            return
            
        if context_length is None:
            context_length = self.context_length
        
        # 模型名称作为用户名
        username = model
        
        if ctx.message.reference is None:
            prompt = await self.context_prompter.chat_prompt(
                ctx, context_length, question, name=username
            )
        else:
            message = ctx.message.reference.resolved
            prompt = await self.context_prompter.chat_prompt_with_reference(
                ctx, context_length, 5, question, message, name=username
            )
            
        try:
            # 使用webhook发送消息，这样可以自定义名称
            webhook = await self.get_or_create_webhook(ctx.channel)
            
            # 根据频道类型选择正确的发送方式
            if isinstance(ctx.channel, discord.Thread):
                # 发送初始消息到线程中
                typing_msg = await webhook.send(
                    content="typing...", 
                    username=username, 
                    wait=True,
                    thread=ctx.channel
                )
            else:
                # 发送到普通文字频道
                typing_msg = await webhook.send(
                    content="typing...", 
                    username=username, 
                    wait=True
                )
            
            # 使用流式生成并更新消息
            await self.stream_openai_response(model, prompt, username, typing_msg, channel_id, guild_id, webhook)
        except Exception as e:
            logger.error(f"OpenAI请求失败: {e}")
            await ctx.send(f"请求失败：{str(e)}", ephemeral=True)

    @commands.hybrid_command(name="yoo", description="Chat with default OpenAI model.")
    async def yoo(
        self, ctx: commands.Context, *, question: str, context_length: int = None
    ):
        # 获取服务器和频道配置
        guild_id = str(ctx.guild.id)
        channel_id = str(ctx.channel.id)
        channel_config = self.get_channel_config(guild_id, channel_id)
        
        if not channel_config:
            await ctx.send("此频道未配置为聊天频道", ephemeral=True)
            return
            
        if context_length is None:
            context_length = self.context_length
        
        # 使用默认模型
        model = self.model
        username = model
        
        if ctx.message.reference is None:
            prompt = await self.context_prompter.chat_prompt(
                ctx, context_length, question, name=username
            )
        else:
            message = ctx.message.reference.resolved
            prompt = await self.context_prompter.chat_prompt_with_reference(
                ctx, context_length, 5, question, message, name=username
            )
            
        try:
            # 使用webhook发送消息，这样可以自定义名称
            webhook = await self.get_or_create_webhook(ctx.channel)
            
            # 根据频道类型选择正确的发送方式
            if isinstance(ctx.channel, discord.Thread):
                # 发送初始消息到线程中
                typing_msg = await webhook.send(
                    content="typing...", 
                    username=username, 
                    wait=True,
                    thread=ctx.channel
                )
            else:
                # 发送到普通文字频道
                typing_msg = await webhook.send(
                    content="typing...", 
                    username=username, 
                    wait=True
                )
            
            # 使用流式生成并更新消息
            await self.stream_openai_response(model, prompt, username, typing_msg, channel_id, guild_id, webhook)
        except Exception as e:
            logger.error(f"OpenAI请求失败: {e}")
            await ctx.send(f"请求失败：{str(e)}", ephemeral=True)
            
    async def get_or_create_webhook(self, channel):
        """获取或创建用于发送消息的webhook"""
        # 如果是线程，获取父频道
        if isinstance(channel, discord.Thread):
            channel = channel.parent
        
        # 检查现有的webhook
        webhooks = await channel.webhooks()
        for webhook in webhooks:
            if webhook.url == self.webhook_url:
                return webhook
        
        # 如果没有找到，创建新的webhook
        return await channel.create_webhook(name="OpenAI Bot")
    
    async def stream_openai_response(self, model: str, prompt: str, username: str, message: discord.Message, channel_id=None, guild_id=None, webhook=None):
        """流式生成并更新OpenAI响应"""
        try:
            # 获取完整响应
            response = await self.request_openai(model, prompt, username, guild_id, channel_id)
            
            # 检查响应是否为空
            if not response or response.strip() == "":
                response = "抱歉，我现在无法生成回复。请稍后再试。"
            
            # 更新消息
            if webhook and isinstance(message, discord.WebhookMessage):
                # 不再传递avatar_url，使用默认头像
                await message.edit(content=response)
            else:
                await message.edit(content=response)
                
        except Exception as e:
            error_msg = f"生成响应时发生错误: {str(e)}"
            logger.error(error_msg)
            if webhook and isinstance(message, discord.WebhookMessage):
                await message.edit(content=error_msg)
            else:
                await message.edit(content=error_msg)

    @commands.hybrid_command(name="list_models", description="列出所有可用的OpenAI模型")
    async def list_models(self, ctx: commands.Context):
        """列出所有可用的OpenAI模型"""
        model_list = []
        for model_name in self.models.keys():
            if model_name == self.model:
                model_list.append(f"**{model_name}** (当前默认)")
            else:
                model_list.append(model_name)
        
        embed = discord.Embed(
            title="可用的OpenAI模型",
            description="\n".join(model_list),
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="set_default_model", description="设置默认的OpenAI模型")
    @commands.has_permissions(administrator=True)
    async def set_default_model(self, ctx: commands.Context, model: str):
        """设置默认的OpenAI模型
        
        参数:
            model: 模型名称，可以使用 /list_models 查看所有可用模型
        """
        if model not in self.models:
            available_models = "\n".join(self.models.keys())
            await ctx.send(f"错误：找不到模型 '{model}'。可用的模型有：\n{available_models}", ephemeral=True)
            return
        
        self.model = model
        config.write("default_openai_model", model)
        await ctx.send(f"默认模型已设置为：{model}", ephemeral=True)

    @set_default_model.error
    async def set_default_model_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("错误：只有管理员可以更改默认模型", ephemeral=True)


async def setup(bot: commands.Bot):
    openai_key = config.get("openai_key", "")
    if not openai_key or openai_key == "YOUR_OPENAI_API_KEY":
        print(cpr.warning("OpenAI API key not set, skipping OpenAI setup"))
        return

    webhook_url = config.get("webhook_url")
    if not webhook_url:
        print(cpr.error("Webhook URL not set, cannot setup OpenAI"))
        return

    await bot.add_cog(Openai(bot, webhook_url))
    print(cpr.success("Cog loaded: Openai"))
