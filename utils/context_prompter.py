import discord
import pytz
from discord.ext import commands
from utils.func import get_time, now


class ContextPrompter:
    def __init__(self):
        self.tz = pytz.timezone("Asia/Shanghai")

    def set_tz(self, tz: str):
        try:
            self.tz = pytz.timezone(tz)
        except Exception as e:
            print(e)

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

    async def chat_prompt(
        self, ctx: commands.Context, context_length: int, question: str
    ):
        context = await self.get_context_for_prompt(ctx, context_length)
        prompt = f"""
        <context>
        {context}
        </context>
        <instruction>
        You are {ctx.me.display_name} ({ctx.me.name}), chatting in a discord server.
        Speak naturally like a human who talks, and don't use phrases like 'according to the context' since humans never talk like that. Remember the Language is Chinese unless the user specifies otherwise! Avoid explicitly mentioning someone's name. If you have to mention someone (try to avoid this case), use their display name (the name that appears outside the parentheses).
        </instruction>
        <question>
        {question}
        </question>
        Now is {now(tz=self.tz)}.
        {ctx.author.display_name} ({ctx.author.name}) is asking you a question (refer to `<question>`) under the context (refer to `<context>`).
        Refer to `<instruction>` and reply now.
        """
        return prompt

    async def chat_prompt_with_reference(
        self,
        ctx: commands.Context,
        context_length: int,
        after_message_context_length: int,
        question: str,
        reference: discord.Message,
    ):
        context = await self.get_context_for_prompt(
            ctx,
            context_length,
            before_message=reference,
            after_message=reference,
            after_message_context_length=after_message_context_length,
        )
        prompt = f"""
        <context>
        {context}
        </context>
        <instruction>
        You are {ctx.me.display_name} ({ctx.me.name}), chatting in a discord server.
        Speak naturally like a human who talks, and don't use phrases like 'according to the context' since humans never talk like that. Remember the Language is Chinese unless the user specifies otherwise! Avoid explicitly mentioning someone's name. If you have to mention someone (try to avoid this case), use their display name (the name that appears outside the parentheses).
        </instruction>
        <question>
        {question}
        </question>
        <reference>
        {reference.author.display_name} ({reference.author.name}) ({self.get_msg_time(reference)}): {reference.content}
        </reference>
        Now is {now(tz=self.tz)}.
        {ctx.author.display_name} ({ctx.author.name}) is asking you a question (refer to `<question>`) about the message above (refer to `<reference>`) under the context (refer to `<context>`).
        Refer to `<instruction>` and reply now.
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
        context = await self.get_context_for_prompt(
            ctx,
            context_length,
            after_message=reference,
            after_message_context_length=after_message_context_length,
        )

        prompt = f"""
        <context>
        {context}
        </context>
        <instruction>
        You are a skilled muti-lingual translator, currently doing a translation job in a discord server. You'll get a message which you need to translate into {target_language} with context. You only need to supply the translation according to the context without any additional information. Don't act like a machine, talk smoothly like a human without being too informal.
        </instruction>
        <reference>
        {reference.author.display_name} ({reference.author.name}) ({self.get_msg_time(reference)}): {reference.content}
        </reference>
        Now is {now(tz=self.tz)}.
        {ctx.author.display_name} ({ctx.author.name}) is asking you to translate the message above (refer to `<reference>`) into {target_language} under the context (refer to `<context>`).
        Refer to `<instruction>` and reply now.
        Your translation should not include the author's name and the time.
        """
        return prompt
