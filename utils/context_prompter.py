import discord
import pytz
import re
from discord.ext import commands
from utils.func import get_time, now


class ContextPrompter:
    def __init__(self):
        self.tz = pytz.timezone("Asia/Shanghai")
        self.agent_manager = None

    def set_agent_manager(self, agent_manager):
        self.agent_manager = agent_manager

    def set_tz(self, tz: str):
        try:
            self.tz = pytz.timezone(tz)
        except Exception as e:
            print(e)

    def maltose_regex(self, context: str) -> str:
        """
        使用正则表达式预处理上下文内容，删除命令触发词
        例如: .hey, .yo claude, .yoo 等，这些只是触发词对机器人理解没有用处
        """
        # 匹配并删除命令触发词
        # 1. 匹配 .hey, .yo, .yoo 后跟空格和可能的参数
        pattern1 = r'\.hey\s+|\.yo\s+[a-zA-Z]+\s+|\.yoo\s+'
        # 2. 匹配独立的命令 .hey, .yo, .yoo (行首或前面有空格，后面是行尾或空格)
        pattern2 = r'(^|\s)\.hey($|\s)|(^|\s)\.yo($|\s)|(^|\s)\.yoo($|\s)'
        
        # 应用正则替换
        context = re.sub(pattern1, '', context)
        context = re.sub(pattern2, '', context)
        
        return context.strip()

    def get_msg_time(self, msg: discord.Message) -> str:
        time = msg.created_at if msg.edited_at is None else msg.edited_at
        return get_time(time, tz=self.tz)

    async def get_context_for_prompt(
        self,
        ctx: commands.Context,
        context_length: int,
        before_message=None,
        after_message=None,
        after_message_context_length=0,
    ):
        context_msg = []
        if before_message is not None and after_message is not None:
            async for msg in ctx.channel.history(
                limit=context_length + 1, before=before_message
            ):
                context_msg.append(
                    f"{msg.author.display_name} ({msg.author.name}) ({self.get_msg_time(msg)}): {msg.content}"
                )
            context_msg.reverse()
            context_msg.append(
                f"{after_message.author.display_name} ({after_message.author.name}) ({self.get_msg_time(after_message)}): {after_message.content}"
            )
            async for msg in ctx.channel.history(
                limit=after_message_context_length + 1, after=after_message
            ):
                context_msg.append(
                    f"{msg.author.display_name} ({msg.author.name}) ({self.get_msg_time(msg)}): {msg.content}"
                )
        elif before_message is not None:
            async for msg in ctx.channel.history(
                limit=context_length + 1, before=before_message
            ):
                context_msg.append(
                    f"{msg.author.display_name} ({msg.author.name}) ({self.get_msg_time(msg)}): {msg.content}"
                )
            context_msg.reverse()
        elif after_message is not None:
            async for msg in ctx.channel.history(
                limit=context_length + 1, after=after_message
            ):
                context_msg.append(
                    f"{msg.author.display_name} ({msg.author.name}) ({self.get_msg_time(msg)}): {msg.content}"
                )
        else:
            async for msg in ctx.channel.history(
                limit=context_length + 1, before=ctx.message
            ):
                context_msg.append(
                    f"{msg.author.display_name} ({msg.author.name}) ({self.get_msg_time(msg)}): {msg.content}"
                )
            context_msg.reverse()
        return "\n".join(context_msg)

    def _get_template(self, template_name, channel_id=None):
        """获取模板内容"""
        if self.agent_manager:
            return self.agent_manager.get_preset_file(template_name, channel_id)
        else:
            # 如果没有设置agent_manager，返回默认模板
            return None

    async def chat_prompt(
        self,
        ctx: commands.Context,
        context_length: int,
        question: str,
        name: str = None,
    ):
        context = await self.get_context_for_prompt(ctx, context_length)
        # 应用正则预处理
        context = self.maltose_regex(context)
        name = name if name else ctx.me.display_name
        
        # 获取预设模板
        if self.agent_manager:
            # 获取预设JSON
            preset = self.agent_manager.get_preset_json("chat_preset.json", ctx.channel.id)
            if preset and "main_content" in preset:
                # 使用预设中的main_content，并替换其中的模板变量
                main_content = preset["main_content"]
                return main_content.format(
                    context=context,
                    question=question,
                    name=name,
                    bot_name=ctx.me.name,
                    current_time=now(tz=self.tz),
                    user_display_name=ctx.author.display_name,
                    user_name=ctx.author.name
                )
        
        # 回退到原始模板
        prompt = f"""
        <context>
        {context}
        </context>
        <question>
        {question}
        </question>
        You are {name} ({ctx.me.name}), chatting in a discord server.
        Speak naturally like a human who talks, and don't use phrases like 'according to the context' since humans never talk like that. Remember the Language is Chinese unless the user specifies otherwise! Avoid explicitly mentioning someone's name. If you have to mention someone (try to avoid this case), use their display name (the name that appears outside the parentheses).
        Now is {now(tz=self.tz)}.
        {ctx.author.display_name} ({ctx.author.name}) is asking you a question (refer to `<question>`).
        Consider the context in `<context>` and reply now. 
        Avoid using ellipsis!
        Your reply:
        """
        return prompt

    async def chat_prompt_with_reference(
        self,
        ctx: commands.Context,
        context_length: int,
        after_message_context_length: int,
        question: str,
        reference: discord.Message,
        name: str = None,
    ):
        context = await self.get_context_for_prompt(
            ctx, context_length, reference, after_message_context_length=after_message_context_length
        )
        # 应用正则预处理
        context = self.maltose_regex(context)
        name = name if name else ctx.me.display_name
        
        # 获取预设模板
        if self.agent_manager:
            # 获取预设JSON
            preset = self.agent_manager.get_preset_json("reference_preset.json", ctx.channel.id)
            if preset and "main_content" in preset:
                # 使用预设中的main_content，并替换其中的模板变量
                main_content = preset["main_content"]
                return main_content.format(
                    context=context,
                    question=question,
                    name=name,
                    bot_name=ctx.me.name,
                    current_time=now(tz=self.tz),
                    user_display_name=ctx.author.display_name,
                    user_name=ctx.author.name,
                    reference_user_display_name=reference.author.display_name,
                    reference_user_name=reference.author.name,
                    reference_time=self.get_msg_time(reference),
                    reference_content=reference.content
                )
        
        # 回退到原始模板
        prompt = f"""
        <context>
        {context}
        </context>
        <question>
        {question}
        </question>
        <reference>
        {reference.author.display_name} ({reference.author.name}) ({self.get_msg_time(reference)}): {reference.content}
        </reference>
        You are {name} ({ctx.me.name}), chatting in a discord server.
        Speak naturally like a human who talks, and don't use phrases like 'according to the context' since humans never talk like that. Remember the Language is Chinese unless the user specifies otherwise! Avoid explicitly mentioning someone's name. If you have to mention someone (try to avoid this case), use their display name (the name that appears outside the parentheses).
        Now is {now(tz=self.tz)}.
        {ctx.author.display_name} ({ctx.author.name}) is asking you a question (refer to `<question>`) about the message above (refer to `<reference>`).
        Consider the context in `<context>` and reply now.
        Avoid using ellipsis!
        Your reply:
        """
        return prompt

    async def chat_prompt_with_attachment(
        self,
        ctx: commands.Context,
        question: str,
        reference: discord.Message,
    ):
        content = reference.content
        if content == "":
            content = "[No content, only attachments]"
            
        # 使用模板
        template = self._get_template("chat_prompt_with_attachment.txt", ctx.channel.id)
        if template:
            return template.format(
                question=question,
                name=ctx.me.display_name,
                bot_name=ctx.me.name,
                current_time=now(tz=self.tz),
                user_display_name=ctx.author.display_name,
                user_name=ctx.author.name,
                reference_user_display_name=reference.author.display_name,
                reference_user_name=reference.author.name,
                reference_time=self.get_msg_time(reference),
                reference_content=content
            )
            
        # 回退到原始模板
        prompt: str = f"""
        <question>
        {question}
        </question>
        <reference>
        {reference.author.display_name} ({reference.author.name}) ({self.get_msg_time(reference)}): {content}
        </reference>
        You are {ctx.me.display_name} ({ctx.me.name}), chatting in a discord server.
        Speak naturally like a human who talks, and don't use phrases like 'according to the context' since humans never talk like that. Remember the Language is Chinese unless the user specifies otherwise! Avoid explicitly mentioning someone's name. If you have to mention someone (try to avoid this case), use their display name (the name that appears outside the parentheses).
        Now is {now(tz=self.tz)}.
        {ctx.author.display_name} ({ctx.author.name}) is asking you a question (refer to `<question>`) about the message (refer to `<reference>`) with the ATTACHMENT FILE.
        Analyze the attachment file and reply now.
        Avoid using ellipsis!
        Your reply:
        """
        return prompt

    async def translate_prompt(
        self,
        ctx: commands.Context,
        context_length: int,
        reference: discord.Message,
        after_message_context_length: int,
        target_language: str,
    ):
        # 获取上下文内容
        context = await self.get_context_for_prompt(
            ctx, context_length, reference, after_message_context_length=after_message_context_length
        )
        # 应用正则预处理
        context = self.maltose_regex(context)
        
        # 使用模板
        template = self._get_template("translate_prompt.txt", ctx.channel.id)
        if template:
            return template.format(
                context=context,
                target_language=target_language,
                reference_content=reference.content,
                bot_name=ctx.me.name,
                current_time=now(tz=self.tz),
                user_display_name=ctx.author.display_name,
                user_name=ctx.author.name,
                reference_user_display_name=reference.author.display_name,
                reference_user_name=reference.author.name,
                reference_time=self.get_msg_time(reference)
            )

        # 回退到原始模板
        prompt = f"""
        <context>
        {context}
        </context>
        `<reference>` is the message you need to translate.
        <reference>
        {reference.content}
        </reference>
        This message is from `<author>`.
        <author>
        {reference.author.display_name} ({reference.author.name}) ({self.get_msg_time(reference)})
        </author>
        You are a skilled muti-lingual translator, currently doing a translation job in a discord server. You'll get a message which you need to translate into {target_language} with context. You only need to supply the translation according to the context without any additional information. Don't act like a machine, translate smoothly like a human without being too informal. 
        Your translation should not include the author's name and the time.
        Now is {now(tz=self.tz)}.
        {ctx.author.display_name} ({ctx.author.name}) is asking you to translate the message in `<reference>` into {target_language} under the context (refer to <context>). The message is from `<author>`, so consider the context and try to understand the message before translating.
        Your translation:
        """
        return prompt
