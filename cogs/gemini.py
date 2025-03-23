from io import BytesIO
from discord.ext import commands
import discord
from google import genai
from google.genai import types
import random
from aiohttp import ClientSession
from utils.decorator import auto_delete
from utils.func import async_iter, async_do_thread
from utils.color_printer import cpr
from utils.config import config
from utils.context_prompter import ContextPrompter
from utils.logger import logger
from datetime import datetime
import PIL.Image
import base64


class Gemini(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        webhook_url: str,
        webhook: discord.Webhook,
    ):
        self.bot = bot
        self.conversations = {}
        self.apikeys = config.get("gemini_keys")
        self.current_key = config.get("current_key")
        self.num = len(self.apikeys)
        
        # 确保chat_channels中的键全部为字符串
        self.update_chat_channels()
        
        self.config = config
        self.context_length = 20
        self.target_language = config.get("target_language")
        self.default_gemini_config = types.GenerateContentConfig(
            system_instruction="",
            top_k=55,
            top_p=0.95,
            temperature=1.3,
            safety_settings=[
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY,
                    threshold=types.HarmBlockThreshold.OFF,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=types.HarmBlockThreshold.OFF,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=types.HarmBlockThreshold.OFF,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=types.HarmBlockThreshold.OFF,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=types.HarmBlockThreshold.OFF,
                ),
            ],
        )
        self.webhook_url = webhook_url
        self.webhook = webhook
        self.context_prompter = ContextPrompter()
        self.non_gemini_model = None  # for openai model
        self.openai_api_key = config.get("openai_api_key")
        self.openai_endpoint = config.get("openai_endpoint")

        if self.openai_api_key is not None and self.openai_endpoint is not None:
            print(cpr.info("OpenAI API available."))

    def update_chat_channels(self):
        """更新聊天频道配置"""
        # 获取所有服务器的聊天频道配置
        self.chat_channels = {}
        servers_config = config.get_all_servers()
        
        for server_id, server_config in servers_config.items():
            if "chat_channels" in server_config:
                # 将每个服务器的聊天频道合并到总的字典中
                for channel_id, channel_config in server_config["chat_channels"].items():
                    self.chat_channels[str(channel_id)] = {
                        "preset": channel_config.get("preset", "default"),
                        "server_id": server_id  # 记录该频道属于哪个服务器
                    }
        
        # 向后兼容：如果存在老版本的频道配置，也添加到频道列表中
        chat_channels = config.get("chat_channels", {})
        if chat_channels:
            for channel_id, channel_config in chat_channels.items():
                if channel_id not in self.chat_channels:
                    self.chat_channels[str(channel_id)] = {
                        "preset": channel_config.get("preset", "default"),
                        "server_id": "server_1"  # 假定属于server_1
                    }

    def get_next_key(self):
        self.current_key = (self.current_key + 1) % self.num
        config.write("current_key", self.current_key)
        return self.apikeys[self.current_key]

    def get_random_key(self):
        return self.apikeys[random.randint(0, self.num - 1)]

    async def request_gemini(
        self,
        prompt: str,
        msg: discord.Message = None,
        update_interval: float = 0.5,
        preset: str = None,
        session_id: str = None,
        attachment_bytes=None,
        attachment_mime_type=None,
        ctx: commands.Context = None,
        streaming: bool = True,
        use_reference: bool = False,
        reference_message: discord.Message = None,
        server_id: str = "server_1",
    ):
        response_text = ""
        attachment_model = self.vision_model
        
        history = []
        
        if attachment_bytes is not None and attachment_mime_type is not None:
            user_message = {"role": "user", "parts": [{"text": prompt}]}
            # 添加附件
            mime_type = attachment_mime_type
            if mime_type in ["image/png", "image/jpeg", "image/jpg", "image/webp"]:
                try:
                    user_message["parts"].append(
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": base64.b64encode(attachment_bytes).decode("utf-8"),
                            }
                        }
                    )
                except Exception as e:
                    logger.error(f"Error adding attachment: {e}")
        else:
                    history.append(user_message)
        else:
                logger.warning(f"Unsupported MIME type: {mime_type}")
                history.append(user_message)
        else:
            history.append({"role": "user", "parts": [{"text": prompt}]})
        
        # 获取会话
        session_id, _history = await self.get_session(session_id, ctx)
        if _history:
            # 把现有历史添加到history前面
            history = _history + history

    @commands.hybrid_command(
        name="set_context_length", description="Set the context length."
    )
    @commands.is_owner()
    @auto_delete(delay=0)
    async def set_context_length(self, ctx: commands.Context, context_length: int):
        self.context_length = context_length
        await ctx.send("Context length set.", ephemeral=True, delete_after=5)

    @commands.hybrid_command(
        name="set_target_language", description="Set the target language."
    )
    @commands.is_owner()
    @auto_delete(delay=0)
    async def set_target_language(self, ctx: commands.Context, target_language: str):
        self.target_language = target_language
        await ctx.send("Target language set.", ephemeral=True, delete_after=5)

    @commands.hybrid_command(name="set_timezone", description="Set the timezone.")
    @commands.is_owner()
    @auto_delete(delay=0)
    async def set_timezone(self, ctx: commands.Context, timezone: str):
        try:
            self.context_prompter.set_tz(timezone)
            await ctx.send(
                f"Timezone set to {timezone}.", ephemeral=True, delete_after=5
            )
        except Exception as e:
            await ctx.send(f"Invalid timezone.", ephemeral=True, delete_after=5)

    @commands.hybrid_command(name="hey", description="Ask a question to gemini.")
    async def hey(
        self,
        ctx: commands.Context,
        *,
        question: str,
        context_length: int = None,
    ):
        channel_id = str(ctx.channel.id)
        if channel_id not in self.chat_channels:
            await ctx.send("I apologize, but I cannot provide any responses in channels where chatting is not permitted. I aim to chat in permitted channels.", delete_after=5, ephemeral=True)
            return
        if context_length is None:
            context_length = self.context_length
        extra_attachment = None
        
        # 记录当前使用的服务器ID，可能在后续处理中需要
        server_id = self.chat_channels[channel_id].get("server_id", "server_1")
        
        # 获取历史消息作为上下文
        history = await self.context_prompter.get_context_for_prompt(ctx, context_length)
        ctx.history = history  # 将历史消息保存到ctx对象中，供预设处理使用
        
        # 检查附件
        if ctx.message.reference:
            reference = ctx.message.reference.resolved
            # 优先查找引用消息中的附件
            if reference and reference.attachments:
                extra_attachment = reference.attachments[-1]
        
        # 发送请求
        await self.request_gemini(
            question,  # 直接传递原始问题，预设处理在request_gemini中完成
            extra_attachment=extra_attachment,
        )

    @commands.hybrid_command(name="tr", description="Translate a text.")
    async def translate(
        self,
        ctx: commands.Context,
        target_language: str = None,
        context_length: int = None,
    ):
        channel_id = str(ctx.channel.id)
        if channel_id not in self.chat_channels:
            await ctx.send("I apologize, but I cannot provide any responses in channels where chatting is not permitted. I aim to chat in permitted channels.", delete_after=5, ephemeral=True)
            return
        if ctx.message.reference is None:
            await ctx.send(
                "Please reply to the message you want to translate.", ephemeral=True
            )
            return
        if context_length is None:
            context_length = self.context_length
        if target_language is None:
            target_language = self.target_language

        # 记录当前使用的服务器ID，可能在后续处理中需要
        server_id = self.chat_channels[channel_id].get("server_id", "server_1")

        # 尝试获取翻译预设
        agent_manager = self.bot.get_cog("AgentManager")
        preset_data = None
        
        # 获取被回复的消息
        reference_message = await ctx.channel.fetch_message(
            ctx.message.reference.message_id
        )
        
        # 检查是否有附件
        extra_attachment = None
        if reference_message and reference_message.attachments:
            extra_attachment = reference_message.attachments[-1]
        
        # 下载附件内容
        attachment_bytes = None
        attachment_mime_type = None
        if extra_attachment:
            msg = await ctx.send("Downloading the attachment...")
            bytes_data = await extra_attachment.read()
            attachment_bytes = bytes_data
            attachment_mime_type = extra_attachment.content_type.split(";")[0]
            await msg.edit(content="Processing the attachment...")
        else:
            msg = await ctx.send("Translating...")
        
        # 获取预设内容，传递guild_id
        guild_id = ctx.guild.id if ctx.guild else None
        if agent_manager:
            preset_data = agent_manager.get_preset_json("translate_preset.json", channel_id, guild_id)

    async def _on_ready(self):
        """当机器人准备好时执行"""
        # 设置agent_manager到context_prompter
        agent_manager = self.bot.get_cog("AgentManager")
            if agent_manager:
            self.context_prompter.set_agent_manager(agent_manager)

async def setup(bot: commands.Bot):
    webhook_manager = bot.get_cog("WebhookManager")
    webhook_url = config.get("webhook_url", "")
    webhook = None
    
    if webhook_manager:
        webhook = await webhook_manager.get_or_create_webhook()
    
    await bot.add_cog(Gemini(bot, webhook_url, webhook))
