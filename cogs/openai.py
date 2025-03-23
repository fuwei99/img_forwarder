import json
from discord.ext import commands
import discord
from aiohttp import ClientSession
import asyncio

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
        
        self.model = list(self.models.keys())[0]
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
        chat_channels = config.get("chat_channels", {})
        self.chat_channels = {str(channel_id): settings for channel_id, settings in chat_channels.items()}
        print(f"OpenAI cog 已更新频道配置: {list(self.chat_channels.keys())}")

    async def request_openai(self, model: str, prompt: str, username: str, channel_id=None) -> str:
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
                config_from_preset = agent_manager.get_preset_json("openai_config.json", channel_id)
                if config_from_preset:
                    openai_config = config_from_preset
                
                # 根据当前的使用场景选择预设
                # 这里根据prompt内容判断使用哪种预设
                if "<reference>" in prompt and "<attachment>" in prompt:
                    preset = agent_manager.get_preset_json("attachment_preset.json", channel_id)
                elif "<reference>" in prompt:
                    preset = agent_manager.get_preset_json("reference_preset.json", channel_id)
                else:
                    preset = agent_manager.get_preset_json("chat_preset.json", channel_id)
        
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
        
        # 创建新的ClientSession用于API请求
        async with ClientSession() as session:
            # 使用会话进行API请求
            async with session.post(url, headers=headers, json=data) as resp:
                resp.raise_for_status()
                response_data = await resp.json()
                
                # 从响应中提取回复内容
                if "choices" in response_data and len(response_data["choices"]) > 0:
                    return response_data["choices"][0]["message"]["content"]
                else:
                    raise ValueError("API返回的响应格式不正确")

    @commands.hybrid_command(name="yo", description="Chat with OpenAI models.")
    async def yo(
        self,
        ctx: commands.Context,
        model: str,
        *,
        question: str,
        context_length: int = None,
    ):
        channel_id = ctx.channel.id
        if str(channel_id) not in self.chat_channels:
            await ctx.send("I apologize, but I cannot provide any responses in channels where chatting is not permitted. I aim to chat in permitted channels.", delete_after=5, ephemeral=True)
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
            
            # 获取对应预设的头像URL（如果有）
            avatar_url = await self.get_model_avatar_url(model, channel_id)
            
            # 根据频道类型选择正确的发送方式
            if isinstance(ctx.channel, discord.Thread):
                # 发送初始消息到线程中
                typing_msg = await webhook.send(
                    content="正在输入...", 
                    username=username, 
                    avatar_url=avatar_url, 
                    wait=True,
                    thread=ctx.channel
                )
            else:
                # 发送到普通文字频道
                typing_msg = await webhook.send(
                    content="正在输入...", 
                    username=username, 
                    avatar_url=avatar_url, 
                    wait=True
                )
            
            # 使用流式生成并更新消息
            await self.stream_openai_response(model, prompt, username, typing_msg, channel_id, webhook)
        except Exception as e:
            logger.error(f"OpenAI请求失败: {e}")
            await ctx.send(f"请求失败：{str(e)}", ephemeral=True)

    @commands.hybrid_command(name="yoo", description="Chat with default OpenAI model.")
    async def yoo(
        self, ctx: commands.Context, *, question: str, context_length: int = None
    ):
        channel_id = ctx.channel.id
        if str(channel_id) not in self.chat_channels:
            await ctx.send("I apologize, but I cannot provide any responses in channels where chatting is not permitted. I aim to chat in permitted channels.", delete_after=5, ephemeral=True)
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
            
            # 获取对应预设的头像URL（如果有）
            avatar_url = await self.get_model_avatar_url(model, channel_id)
            
            # 根据频道类型选择正确的发送方式
            if isinstance(ctx.channel, discord.Thread):
                # 发送初始消息到线程中
                typing_msg = await webhook.send(
                    content="正在输入...", 
                    username=username, 
                    avatar_url=avatar_url, 
                    wait=True,
                    thread=ctx.channel
                )
            else:
                # 发送到普通文字频道
                typing_msg = await webhook.send(
                    content="正在输入...", 
                    username=username, 
                    avatar_url=avatar_url, 
                    wait=True
                )
            
            # 使用流式生成并更新消息
            await self.stream_openai_response(model, prompt, username, typing_msg, channel_id, webhook)
        except Exception as e:
            logger.error(f"OpenAI请求失败: {e}")
            await ctx.send(f"请求失败：{str(e)}", ephemeral=True)
            
    async def get_or_create_webhook(self, channel):
        """获取或创建用于发送消息的webhook"""
        # 如果是线程，获取父频道
        if isinstance(channel, discord.Thread):
            parent_channel = channel.parent
            # 尝试查找现有的webhook
            webhooks = await parent_channel.webhooks()
            for webhook in webhooks:
                if webhook.user == self.bot.user:
                    return webhook
                    
            # 如果没有找到，创建一个新的webhook
            return await parent_channel.create_webhook(name=f"{self.bot.user.name} Webhook")
        else:
            # 处理普通文字频道
            webhooks = await channel.webhooks()
            for webhook in webhooks:
                if webhook.user == self.bot.user:
                    return webhook
                    
            # 如果没有找到，创建一个新的webhook
            return await channel.create_webhook(name=f"{self.bot.user.name} Webhook")
        
    async def get_model_avatar_url(self, model: str, channel_id=None):
        """获取模型对应的头像URL"""
        # 尝试从Agent Manager获取预设信息
        if hasattr(self.bot, "get_cog"):
            agent_manager = self.bot.get_cog("AgentManager")
            if agent_manager:
                # 获取当前频道的预设
                preset_path = agent_manager.get_current_preset_path(channel_id)
                # 预设目录下可能有avatar文件
                import os
                import glob
                
                avatar_files = glob.glob(f"{preset_path}/avatar.*")
                if avatar_files:
                    # 构建discord CDN URL
                    avatar_file = avatar_files[0]
                    # 使用bot的默认头像，不用找avatar文件
                    return self.bot.user.display_avatar.url
                    
        # 默认使用bot头像
        return self.bot.user.display_avatar.url

    async def stream_openai_response(self, model: str, prompt: str, username: str, message: discord.Message, channel_id=None, webhook=None):
        """使用真正的流式传输处理OpenAI响应并更新Discord消息"""
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
                config_from_preset = agent_manager.get_preset_json("openai_config.json", channel_id)
                if config_from_preset:
                    openai_config = config_from_preset
                
                # 根据当前的使用场景选择预设
                if "<reference>" in prompt and "<attachment>" in prompt:
                    preset = agent_manager.get_preset_json("attachment_preset.json", channel_id)
                elif "<reference>" in prompt:
                    preset = agent_manager.get_preset_json("reference_preset.json", channel_id)
                else:
                    preset = agent_manager.get_preset_json("chat_preset.json", channel_id)
        
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
            "stream": True,  # 启用流式传输
        }
        
        # 记录API请求数据
        logger.info(f"OpenAI API 请求数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        # 创建新的ClientSession用于API请求
        full_response = ""
        update_counter = 0
        last_update_time = asyncio.get_event_loop().time()
        chunk_per_edit = self.models[model].get("chunk_per_edit", 10)  # 每10个数据块更新一次消息
        
        try:
            async with ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as resp:
                    resp.raise_for_status()
                    
                    # 处理流式响应
                    async for line in resp.content:
                        if not line:
                            continue
                        
                        line_text = line.decode('utf-8').strip()
                        if line_text == "data: [DONE]":
                            break
                        
                        if line_text.startswith('data: '):
                            json_data = json.loads(line_text[6:])
                            
                            # 提取增量内容
                            if 'choices' in json_data and len(json_data['choices']) > 0:
                                delta = json_data['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    content = delta['content']
                                    full_response += content
                                    update_counter += 1
                                    
                                    # 每chunk_per_edit个片段更新一次或超过0.5秒未更新
                                    current_time = asyncio.get_event_loop().time()
                                    if update_counter % chunk_per_edit == 0 or (current_time - last_update_time) > 0.5:
                                        try:
                                            # 使用webhook编辑消息，保持自定义用户名
                                            await message.edit(content=full_response)
                                            last_update_time = current_time
                                        except Exception as edit_error:
                                            logger.error(f"编辑消息失败: {edit_error}")
            
            # 最终更新，确保显示完整回复
            if full_response:
                try:
                    await message.edit(content=full_response)
                except Exception as final_edit_error:
                    logger.error(f"最终编辑消息失败: {final_edit_error}")
                
        except Exception as e:
            logger.error(f"处理流式响应时出错: {e}")
            # 如果已经有部分响应，则保留并标明错误
            if full_response:
                try:
                    await message.edit(content=f"{full_response}\n\n*[处理过程中出现错误]*")
                except Exception as error_edit:
                    logger.error(f"编辑错误消息失败: {error_edit}")
            else:
                try:
                    await message.edit(content="抱歉，请求处理过程中出现错误。")
                except Exception as error_edit:
                    logger.error(f"编辑错误消息失败: {error_edit}")
            raise

    @commands.hybrid_command(name="models", description="List available OpenAI models.")
    @auto_delete(delay=0)
    async def models(self, ctx: commands.Context):
        await ctx.send("\n".join(self.models.keys()), ephemeral=True, delete_after=5)

    @commands.hybrid_command(
        name="set_model", description="Set the default OpenAI model."
    )
    @commands.is_owner()
    @auto_delete(delay=0)
    async def set_model(self, ctx: commands.Context, model: str):
        if model not in self.models.keys():
            await ctx.send("Model not found.", ephemeral=True, delete_after=5)
            return
        self.model = model
        await ctx.send("Model set.", ephemeral=True, delete_after=5)

    @commands.hybrid_command(
        name="set_openai_context_length",
        description="Set the context length for OpenAI models.",
    )
    @commands.is_owner()
    @auto_delete(delay=0)
    async def set_openai_context_length(
        self, ctx: commands.Context, context_length: int
    ):
        self.context_length = context_length
        await ctx.send("Context length set.", ephemeral=True, delete_after=5)

    @commands.hybrid_command(
        name="set_openai_timezone", description="Set the timezone for OpenAI models."
    )
    @commands.is_owner()
    @auto_delete(delay=0)
    async def set_openai_timezone(self, ctx: commands.Context, timezone: str):
        try:
            self.context_prompter.set_tz(timezone)
            await ctx.send(
                f"Timezone set to {timezone}.", ephemeral=True, delete_after=5
            )
        except Exception as e:
            await ctx.send(f"Invalid timezone.", ephemeral=True, delete_after=5)


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
