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


class Gemini(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        webhook: discord.Webhook,
    ):
        self.bot = bot
        self.conversations = {}
        self.apikeys = config.get("gemini_keys")
        self.current_key = config.get("current_key")
        self.num = len(self.apikeys)
        self.chat_channel_id = config.get("chat_channel_id")
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
        self.webhook = webhook
        self.context_prompter = ContextPrompter()
        self.non_gemini_model = None  # for openai model
        self.openai_api_key = config.get("openai_api_key")
        self.openai_endpoint = config.get("openai_endpoint")

        if self.openai_api_key is not None and self.openai_endpoint is not None:
            print(cpr.info("OpenAI API available."))

    def get_next_key(self):
        self.current_key = (self.current_key + 1) % self.num
        config.write("current_key", self.current_key)
        return self.apikeys[self.current_key]

    def get_random_key(self):
        return self.apikeys[random.randint(0, self.num - 1)]

    async def request_gemini(
        self,
        ctx: commands.Context,
        prompt: str,
        model_config: types.GenerateContentConfig = None,
        model="gemini-2.0-pro-exp-02-05",
        username=None,
        extra_attachment: discord.Attachment = None,
    ):
        if model_config is None:
            model_config = self.default_gemini_config
        
        # 尝试获取预设
        agent_manager = self.bot.get_cog("AgentManager")
        preset_data = None
        preset_name = "chat_preset.json"
        
        # 根据情况选择不同的预设
        if extra_attachment:
            preset_name = "attachment_preset.json"
            print(f"使用附件预设: {preset_name}")
        elif ctx.message.reference:
            preset_name = "reference_preset.json"
        
        # 获取预设内容
        if agent_manager:
            preset_data = agent_manager.get_preset_json(preset_name)
        
        if model != "gemini-2.0-pro-exp-02-05":
            key = self.get_random_key()
        else:
            key = self.get_next_key()
        client = genai.Client(api_key=key)
        
        # 处理附件 - 下载附件内容
        attachment_bytes = None
        attachment_mime_type = None
        if extra_attachment:
            msg = await ctx.send("Downloading the attachment...")
            bytes_data = await extra_attachment.read()
            attachment_bytes = bytes_data
            attachment_mime_type = extra_attachment.content_type.split(";")[0]
            await msg.edit(content="Processing the attachment...")
            print(f"附件已下载: {extra_attachment.filename} ({attachment_mime_type})")
        else:
            msg = await ctx.send("Typing...") if username is None else await self.webhook.send("Typing...", wait=True, username=username)
        
        # 如果有预设数据，使用预设构建请求
        if preset_data:
            # 首先获取变量替换所需的数据
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            bot_name = ctx.me.name
            bot_display_name = ctx.me.display_name
            user_name = ctx.author.name
            user_display_name = ctx.author.display_name
            
            # 处理上下文
            context = ""
            if hasattr(ctx, 'context') and ctx.context:
                context = ctx.context
            elif hasattr(ctx, 'history') and ctx.history:
                context = ctx.history
            else:
                # 获取历史消息作为上下文
                context = await self.context_prompter.get_context_for_prompt(ctx, self.context_length)
            
            # 确保context是字符串
            if not isinstance(context, str):
                context = str(context) if context is not None else ""
            
            # 替换预设中的变量
            first_user_message = preset_data.get("first_user_message", "")
            first_user_message = first_user_message.replace("{context}", context)
            first_user_message = first_user_message.replace("{question}", prompt)
            first_user_message = first_user_message.replace("{name}", bot_display_name)
            first_user_message = first_user_message.replace("{bot_name}", bot_name)
            first_user_message = first_user_message.replace("{current_time}", current_time)
            first_user_message = first_user_message.replace("{user_display_name}", user_display_name)
            first_user_message = first_user_message.replace("{user_name}", user_name)
            
            main_content = preset_data.get("main_content", "")
            main_content = main_content.replace("{context}", context)
            main_content = main_content.replace("{question}", prompt)
            main_content = main_content.replace("{name}", bot_display_name)
            main_content = main_content.replace("{bot_name}", bot_name)
            main_content = main_content.replace("{current_time}", current_time)
            main_content = main_content.replace("{user_display_name}", user_display_name)
            main_content = main_content.replace("{user_name}", user_name)
            
            # 如果是引用回复
            if ctx.message.reference and 'reference' in preset_name:
                reference = ctx.message.reference.resolved
                reference_time = reference.created_at.strftime("%Y-%m-%d %H:%M:%S")
                reference_user_name = reference.author.name
                reference_user_display_name = reference.author.display_name
                reference_content = reference.content
                
                main_content = main_content.replace("{reference_time}", reference_time)
                main_content = main_content.replace("{reference_user_name}", reference_user_name)
                main_content = main_content.replace("{reference_user_display_name}", reference_user_display_name)
                main_content = main_content.replace("{reference_content}", reference_content)
                first_user_message = first_user_message.replace("{reference_time}", reference_time)
                first_user_message = first_user_message.replace("{reference_user_name}", reference_user_name)
                first_user_message = first_user_message.replace("{reference_user_display_name}", reference_user_display_name)
                first_user_message = first_user_message.replace("{reference_content}", reference_content)
            
            last_user_message = preset_data.get("last_user_message", "")
            last_user_message = last_user_message.replace("{context}", context)
            last_user_message = last_user_message.replace("{question}", prompt)
            last_user_message = last_user_message.replace("{name}", bot_display_name)
            last_user_message = last_user_message.replace("{bot_name}", bot_name)
            last_user_message = last_user_message.replace("{current_time}", current_time)
            last_user_message = last_user_message.replace("{user_display_name}", user_display_name)
            last_user_message = last_user_message.replace("{user_name}", user_name)
            
            # 构建user-model-user的三个上下文
            user_parts = [types.Part.from_text(text=first_user_message)]
            model_parts = [types.Part.from_text(text=main_content)]
            last_user_parts = [types.Part.from_text(text=last_user_message)]
            
            # 如果有附件，添加到最后一个用户消息中
            if attachment_bytes:
                # 使用inline_data方式添加附件
                last_user_parts.append(
                    types.Part(
                        inline_data=types.Blob(
                            mime_type=attachment_mime_type,
                            data=attachment_bytes
                        )
                    )
                )
                print("附件已添加到用户消息中")
            
            contents = [
                types.Content(
                    role="user",
                    parts=user_parts,
                ),
                types.Content(
                    role="model",
                    parts=model_parts,
                ),
                types.Content(
                    role="user",
                    parts=last_user_parts,
                ),
            ]
            
            # 设置安全设置
            safety_settings = [
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
            ]
            
            # 获取Gemini配置
            gemini_config_data = None
            if agent_manager:
                gemini_config_data = agent_manager.get_preset_json("gemini_config.json")
            
            # 构建配置
            generate_content_config = types.GenerateContentConfig(
                temperature=gemini_config_data.get("temperature", 1.0) if gemini_config_data else 1.0,
                top_p=gemini_config_data.get("top_p", 0.95) if gemini_config_data else 0.95,
                top_k=gemini_config_data.get("top_k", 64) if gemini_config_data else 64,
                max_output_tokens=gemini_config_data.get("max_output_tokens", 8192) if gemini_config_data else 8192,
                safety_settings=safety_settings,
                response_mime_type="text/plain",
                system_instruction=[
                    types.Part.from_text(text=preset_data.get("system_prompt", "")),
                ],
            )
        else:
            # 如果没有预设，使用原有的方式
            if attachment_bytes:
                # 使用inline_data方式添加附件
                attachment_part = types.Part(
                    inline_data=types.Blob(
                        mime_type=attachment_mime_type,
                        data=attachment_bytes
                    )
                )
                contents = [prompt, attachment_part]
            else:
                contents = [prompt]
            generate_content_config = model_config
        
        full = ""
        n = config.get("gemini_chunk_per_edit")
        every_n_chunk = 1
        try:
            # 记录请求内容
            log_contents = []
            for content in contents:
                parts_text = []
                for part in content.parts:
                    if hasattr(part, "text") and part.text:
                        parts_text.append(f"Text: {part.text}")
                    elif hasattr(part, "file_data"):
                        parts_text.append("File: [attachment]")
                    else:
                        parts_text.append(f"Unknown part type: {type(part)}")
                log_contents.append(f"Role: {content.role}, Parts: {parts_text}")
            
            system_instruction = "None"
            if hasattr(generate_content_config, "system_instruction"):
                if generate_content_config.system_instruction:
                    system_instruction = generate_content_config.system_instruction[0].text if generate_content_config.system_instruction else "None"
            
            # 直接打印到控制台
            print("\n========== Gemini请求 ==========")
            print(f"模型: {model}")
            print(f"系统提示: {system_instruction}")
            print("消息内容:")
            for i, content in enumerate(log_contents):
                print(f"[{i}] {content}")
            print(f"配置: temperature={generate_content_config.temperature}, top_p={generate_content_config.top_p}, top_k={generate_content_config.top_k}, max_tokens={generate_content_config.max_output_tokens}")
            print("================================\n")
            
            # 同时记录到日志文件
            logger.info(
                "Gemini请求发送: 模型=%s, 内容=%s, 系统提示=%s, 配置=%s",
                model,
                log_contents,
                system_instruction,
                {
                    "temperature": generate_content_config.temperature,
                    "top_p": generate_content_config.top_p,
                    "top_k": generate_content_config.top_k,
                    "max_tokens": generate_content_config.max_output_tokens,
                }
            )
            
            # 使用新的请求格式
            response = client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=generate_content_config,
            )

            async for chunk in async_iter(response):
                if chunk.text:
                    full += chunk.text
                    if every_n_chunk == n:
                        await msg.edit(content=full)
                        every_n_chunk = 1
                    else:
                        every_n_chunk += 1
            await msg.edit(content=full)
        except Exception as e:
            logger.error(
                "Error when requesting gemini with key: %s, error: %s",
                key,
                e,
                exc_info=True,
            )
            if full == "":
                await msg.edit(content="Uh oh, something went wrong...")
            else:
                full += "\nUh oh, something went wrong..."
                await msg.edit(content=full)

    @commands.hybrid_command(name="hey", description="Ask a question to gemini.")
    async def hey(
        self,
        ctx: commands.Context,
        *,
        question: str,
        context_length: int = None,
    ):
        if ctx.channel.id != self.chat_channel_id:
            await ctx.send("抱歉，该命令只能在指定的聊天频道中使用", delete_after=5, ephemeral=True)
            return
        if context_length is None:
            context_length = self.context_length
        extra_attachment = None
        
        # 获取历史消息作为上下文
        history = await self.context_prompter.get_context_for_prompt(ctx, context_length)
        ctx.history = history  # 将历史消息保存到ctx对象中，供预设处理使用
        
        # 检查附件
        if ctx.message.reference:
            reference = ctx.message.reference.resolved
            # 优先查找引用消息中的附件
            if reference and reference.attachments:
                extra_attachment = reference.attachments[-1]
        
        # 检查是否需要使用预设
        agent_manager = self.bot.get_cog("AgentManager")
        use_preset = False
        preset_name = "chat_preset.json"  # 默认使用chat_preset.json
        
        if agent_manager:
            if ctx.message.reference:
                reference = ctx.message.reference.resolved
                if reference and reference.attachments:
                    preset_name = "attachment_preset.json"
                else:
                    preset_name = "reference_preset.json"
            
            preset_data = agent_manager.get_preset_json(preset_name)
            if preset_data:
                use_preset = True
        
        # 根据情况创建提示
        if use_preset:
            prompt = question
        else:
            # 否则使用传统的处理方式
            if ctx.message.reference is None:
                prompt = await self.context_prompter.chat_prompt(
                    ctx, context_length, question
                )
            else:
                reference = ctx.message.reference.resolved
                if reference.attachments:
                    prompt = await self.context_prompter.chat_prompt_with_attachment(
                        ctx, question, reference
                    )
                else:
                    prompt = await self.context_prompter.chat_prompt_with_reference(
                        ctx, context_length, 5, question, reference
                    )
        
        # 检查附件是否存在，确保传递正确
        if extra_attachment:
            print(f"处理附件: {extra_attachment.filename} ({extra_attachment.content_type})")
        
        # 发送请求
        await self.request_gemini(
            ctx,
            prompt,
            extra_attachment=extra_attachment,
        )

    @commands.hybrid_command(name="translate", description="Translate a text.")
    async def translate(
        self,
        ctx: commands.Context,
        target_language: str = None,
        context_length: int = None,
    ):
        if ctx.message.channel.id != self.chat_channel_id:
            await ctx.send("抱歉，该命令只能在指定的聊天频道中使用", delete_after=5, ephemeral=True)
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

        # 尝试获取翻译预设
        agent_manager = self.bot.get_cog("AgentManager")
        preset_data = None
        
        # 获取预设内容
        if agent_manager:
            preset_data = agent_manager.get_preset_json("translate_preset.json")
        
        # 获取被回复的消息
        reference_message = await ctx.channel.fetch_message(
            ctx.message.reference.message_id
        )
        
        if preset_data:
            # 使用预设JSON结构和原始文本
            key = self.get_next_key()
            client = genai.Client(api_key=key)
            
            # 获取变量替换所需的数据
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            bot_name = ctx.me.name
            bot_display_name = ctx.me.display_name
            user_name = ctx.author.name
            user_display_name = ctx.author.display_name
            
            # 处理上下文和引用内容
            context = ""
            if hasattr(ctx, 'context') and ctx.context:
                context = ctx.context
            elif hasattr(ctx, 'history') and ctx.history:
                context = ctx.history
            else:
                # 获取历史消息作为上下文
                context = await self.context_prompter.get_context_for_prompt(ctx, context_length)
            
            # 确保context是字符串
            if not isinstance(context, str):
                context = str(context) if context is not None else ""
            
            # 获取被引用消息的相关信息
            reference_time = reference_message.created_at.strftime("%Y-%m-%d %H:%M:%S")
            reference_user_name = reference_message.author.name
            reference_user_display_name = reference_message.author.display_name
            reference_content = reference_message.content
            
            # 替换预设中的变量
            first_user_message = preset_data.get("first_user_message", "")
            first_user_message = first_user_message.replace("{context}", context)
            first_user_message = first_user_message.replace("{target_language}", target_language)
            first_user_message = first_user_message.replace("{reference_content}", reference_content)
            first_user_message = first_user_message.replace("{reference_time}", reference_time)
            first_user_message = first_user_message.replace("{reference_user_name}", reference_user_name)
            first_user_message = first_user_message.replace("{reference_user_display_name}", reference_user_display_name)
            first_user_message = first_user_message.replace("{name}", bot_display_name)
            first_user_message = first_user_message.replace("{bot_name}", bot_name)
            first_user_message = first_user_message.replace("{current_time}", current_time)
            first_user_message = first_user_message.replace("{user_display_name}", user_display_name)
            first_user_message = first_user_message.replace("{user_name}", user_name)
            
            main_content = preset_data.get("main_content", "")
            main_content = main_content.replace("{context}", context)
            main_content = main_content.replace("{target_language}", target_language)
            main_content = main_content.replace("{reference_content}", reference_content)
            main_content = main_content.replace("{reference_time}", reference_time)
            main_content = main_content.replace("{reference_user_name}", reference_user_name)
            main_content = main_content.replace("{reference_user_display_name}", reference_user_display_name)
            main_content = main_content.replace("{name}", bot_display_name)
            main_content = main_content.replace("{bot_name}", bot_name)
            main_content = main_content.replace("{current_time}", current_time)
            main_content = main_content.replace("{user_display_name}", user_display_name)
            main_content = main_content.replace("{user_name}", user_name)
            
            last_user_message = preset_data.get("last_user_message", "")
            last_user_message = last_user_message.replace("{context}", context)
            last_user_message = last_user_message.replace("{target_language}", target_language)
            last_user_message = last_user_message.replace("{reference_content}", reference_content)
            last_user_message = last_user_message.replace("{reference_time}", reference_time)
            last_user_message = last_user_message.replace("{reference_user_name}", reference_user_name)
            last_user_message = last_user_message.replace("{reference_user_display_name}", reference_user_display_name)
            last_user_message = last_user_message.replace("{name}", bot_display_name)
            last_user_message = last_user_message.replace("{bot_name}", bot_name)
            last_user_message = last_user_message.replace("{current_time}", current_time)
            last_user_message = last_user_message.replace("{user_display_name}", user_display_name)
            last_user_message = last_user_message.replace("{user_name}", user_name)
            
            # 构建user-model-user的三个上下文
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=first_user_message),
                    ],
                ),
                types.Content(
                    role="model",
                    parts=[
                        types.Part.from_text(text=main_content),
                    ],
                ),
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=last_user_message),
                    ],
                ),
            ]
            
            # 设置安全设置
            safety_settings = [
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
            ]
            
            # 获取Gemini配置
            gemini_config_data = None
            if agent_manager:
                gemini_config_data = agent_manager.get_preset_json("gemini_config.json")
            
            # 构建配置
            generate_content_config = types.GenerateContentConfig(
                temperature=gemini_config_data.get("temperature", 1.0) if gemini_config_data else 1.0,
                top_p=gemini_config_data.get("top_p", 0.95) if gemini_config_data else 0.95,
                top_k=gemini_config_data.get("top_k", 64) if gemini_config_data else 64,
                max_output_tokens=gemini_config_data.get("max_output_tokens", 8192) if gemini_config_data else 8192,
                safety_settings=safety_settings,
                response_mime_type="text/plain",
                system_instruction=[
                    types.Part.from_text(text=preset_data.get("system_prompt", "")),
                ],
            )
            
            msg = await ctx.send("Translating...")
            full = ""
            n = config.get("gemini_chunk_per_edit")
            every_n_chunk = 1
            
            try:
                # 记录翻译请求内容
                log_contents = []
                for content in contents:
                    parts_text = []
                    for part in content.parts:
                        if hasattr(part, "text") and part.text:
                            parts_text.append(f"Text: {part.text}")
                        else:
                            parts_text.append(f"Unknown part type: {type(part)}")
                    log_contents.append(f"Role: {content.role}, Parts: {parts_text}")
                
                system_instruction = "None"
                if hasattr(generate_content_config, "system_instruction"):
                    if generate_content_config.system_instruction:
                        system_instruction = generate_content_config.system_instruction[0].text if generate_content_config.system_instruction else "None"
                
                # 直接打印到控制台
                print("\n========== Gemini翻译请求 ==========")
                print(f"模型: gemini-2.0-pro-exp-02-05")
                print(f"系统提示: {system_instruction}")
                print("消息内容:")
                for i, content in enumerate(log_contents):
                    print(f"[{i}] {content}")
                print(f"配置: temperature={generate_content_config.temperature}, top_p={generate_content_config.top_p}, top_k={generate_content_config.top_k}, max_tokens={generate_content_config.max_output_tokens}")
                print("====================================\n")
                
                # 同时记录到日志文件
                logger.info(
                    "Gemini翻译请求发送: 模型=gemini-2.0-pro-exp-02-05, 内容=%s, 系统提示=%s, 配置=%s",
                    log_contents,
                    system_instruction,
                    {
                        "temperature": generate_content_config.temperature,
                        "top_p": generate_content_config.top_p,
                        "top_k": generate_content_config.top_k,
                        "max_tokens": generate_content_config.max_output_tokens,
                    }
                )
                
                response = client.models.generate_content_stream(
                    model="gemini-2.0-pro-exp-02-05",
                    contents=contents,
                    config=generate_content_config,
                )
                
                async for chunk in async_iter(response):
                    if chunk.text:
                        full += chunk.text
                        if every_n_chunk == n:
                            await msg.edit(content=full)
                            every_n_chunk = 1
                        else:
                            every_n_chunk += 1
                await msg.edit(content=full)
            except Exception as e:
                logger.error(
                    "Error when translating with gemini, error: %s",
                    e,
                    exc_info=True,
                )
                if full == "":
                    await msg.edit(content="Uh oh, something went wrong...")
                else:
                    full += "\nUh oh, something went wrong..."
                    await msg.edit(content=full)
        else:
            # 使用原有方式
            prompt = await self.context_prompter.translate_prompt(
                ctx, context_length, target_language
            )
            await self.request_gemini(ctx, prompt)

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


async def setup(bot: commands.Bot):
    apikeys = config.get("gemini_keys")
    print(cpr.info(f"{len(apikeys)} keys loaded."))
    webhook = discord.Webhook.from_url(
        config.get("webhook_url"), session=ClientSession()
    )
    cog = Gemini(bot, webhook)
    
    # 设置AgentManager
    try:
        agent_manager = bot.get_cog("AgentManager")
        if agent_manager:
            cog.context_prompter.set_agent_manager(agent_manager)
            # 加载Gemini配置
            gemini_config = agent_manager.get_preset_json("gemini_config.json")
            if gemini_config:
                # 将JSON配置转换为Gemini配置对象
                safety_settings = []
                for setting in gemini_config.get("safety_settings", []):
                    category = getattr(types.HarmCategory, setting["category"])
                    threshold = getattr(types.HarmBlockThreshold, setting["threshold"])
                    safety_settings.append(types.SafetySetting(
                        category=category,
                        threshold=threshold
                    ))
                
                cog.default_gemini_config = types.GenerateContentConfig(
                    system_instruction=gemini_config.get("system_instruction", ""),
                    top_k=gemini_config.get("top_k", 55),
                    top_p=gemini_config.get("top_p", 0.95),
                    temperature=gemini_config.get("temperature", 1.3),
                    safety_settings=safety_settings
                )
    except Exception as e:
        print(f"Error loading Gemini config: {e}")
    
    await bot.add_cog(cog)
    print(cpr.success("Cog loaded: Gemini"))
