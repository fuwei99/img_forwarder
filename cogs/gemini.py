import asyncio
from typing import Iterator
from discord.ext import commands
import discord
from google import genai
from google.genai import types
import pytz
import random
from datetime import datetime
from utils.decorator import auto_delete

from utils.func import resolve_config, write_config, cpt


class Gemini(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        apikeys,
        current_key,
        chat_channel_id,
        config,
        openai_api_key=None,
        openai_endpoint=None,
    ):
        self.bot = bot
        self.conversations = {}
        self.apikeys = apikeys
        self.current_key = current_key
        self.num = len(apikeys)
        self.chat_channel_id = chat_channel_id
        self.system_prompt = ""
        self.config = config
        self.context_length = 20
        self.target_language = "Chinese"
        self.default_gemini_config = types.GenerateContentConfig(
            system_instruction="",
            top_k=55,
            top_p=0.95,
            temperature=1,
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
        self.tz = pytz.timezone("Asia/Shanghai")
        self.non_gemini_model = None  # for openai model
        self.openai_api_key = openai_api_key
        self.openai_endpoint = openai_endpoint

    def get_time(self):
        return datetime.now(self.tz).strftime("%Y-%m-%d %H:%M:%S")

    def get_next_key(self):
        self.current_key = (self.current_key + 1) % self.num
        self.config["current_key"] = self.current_key
        write_config(self.config)
        return self.apikeys[self.current_key]

    def get_msg_time(self, msg: discord.Message) -> str:
        return (
            self.get_time(msg.edited_at)
            if msg.edited_at is not None
            else self.get_time(msg.created_at)
        )

    def get_random_key(self):
        return self.apikeys[random.randint(0, self.num - 1)]

    async def get_context_for_prompt(
        self,
        ctx: commands.Context,
        context_length: int,
        before_message=None,
        after_message=None,
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
                limit=context_length, after=after_message
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

    async def stream_generator(self, response: Iterator[types.GenerateContentResponse]):
        loop = asyncio.get_event_loop()

        def safe_next(iterator: Iterator[types.GenerateContentResponse]):
            try:
                return next(iterator), False
            except StopIteration:
                return None, True

        try:
            iterator = iter(response)
            while True:
                item, done = await loop.run_in_executor(None, safe_next, iterator)
                if done:
                    break
                print(item)
                yield item
        except Exception as e:
            print(e)

    async def request_gemini(
        self,
        ctx: commands.Context,
        prompt: str,
        model_config: types.GenerateContentConfig = None,
        model="gemini-2.0-pro-exp-02-05",
    ):
        if model_config is None:
            model_config = self.default_gemini_config
        if model != "gemini-2.0-pro-exp-02-05":
            key = self.get_random_key()
        else:
            key = self.get_next_key()
        client = genai.Client(api_key=key)
        msg = await ctx.send("Typing...")
        full = ""
        every_two_chunk = False
        try:
            response = client.models.generate_content_stream(
                model=model,
                contents=[prompt],
                config=self.default_gemini_config,
            )

            async for chunk in self.stream_generator(response):
                if chunk.text:
                    full += chunk.text
                    if every_two_chunk:
                        await msg.edit(content=full)
                        every_two_chunk = False
                    else:
                        every_two_chunk = True
            await msg.edit(content=full)
        except Exception as e:
            print(e)

    @commands.hybrid_command(name="hey", description="Ask a question to gemini.")
    async def hey(
        self,
        ctx: commands.Context,
        *,
        question: str,
        context_length: int = None,
    ):
        if ctx.channel.id != self.chat_channel_id:
            await ctx.send("I apologize, but……", delete_after=5, ephemeral=True)
            return
        if context_length is None:
            context_length = self.context_length
        if self.system_prompt == "":
            nickname = ctx.guild.me.nick
            if nickname is None:
                nickname = ctx.guild.me.name
            self.system_prompt = f"You are {nickname}, a helpful AI assistant. You are assisting a user in a discord server. The user asks you a question, and you provide a helpful response. The user may ask you anything. You always speak Chinese unless the question specifies otherwise."
        system_prompt = self.system_prompt
        if ctx.message.reference is not None:
            message = ctx.message.reference.resolved
            context = await self.get_context_for_prompt(
                ctx, context_length, before_message=message
            )
        else:
            context = await self.get_context_for_prompt(ctx, context_length)
        model_config = self.default_gemini_config.model_copy()
        model_config.system_instruction = system_prompt
        instructions = f"You are {ctx.me.display_name} ({ctx.me.name}). Now answer the question naturally like a human who talks, don't use phrases like 'according to the context' since humans never talk like that. Remember the Language is Chinese unless the user specifies otherwise!"
        time = self.get_time()
        prompt = f"Chat context: {{\n{context}\n}}"
        if ctx.message.reference is not None:
            prompt += f"\n\nQuestion directly related to message: {{\n{message.author.display_name} ({message.author.name}): {message.content}\n}}"
        prompt += f"\n\nQuestion from {ctx.message.author.display_name} ({ctx.message.author.name}): {question}"
        prompt += f"\n\nCurrent time: {time}"
        prompt += f"\n\nAdditional instructions: {instructions}"
        prompt += f"\n\nAnswer to {ctx.message.author.display_name} ({ctx.message.author.name}):"
        await self.request_gemini(ctx, prompt, model_config)

    @commands.hybrid_command(name="translate", description="Translate a text.")
    async def translate(
        self,
        ctx: commands.Context,
        target_language: str = None,
        context_length: int = None,
    ):
        if ctx.message.channel.id != self.chat_channel_id:
            await ctx.send("I apologize, but……", delete_after=5, ephemeral=True)
            return
        if ctx.message.reference is None:
            await ctx.send(
                "Please reply to the message you want to translate.", ephemeral=True
            )
            return
        message = ctx.message.reference.resolved
        if context_length is None:
            context_length = self.context_length
        if target_language is None:
            target_language = self.target_language
        system_prompt = f"You are a skilled muti-lingual translator, currently doing a translation job in a discord server. You'll get a message which you need to translate into {target_language} with context. You only need to supply the translation according to the context without any additional information. Don't act like a machine, talk smoothly like a human without being too informal."
        model_config = self.default_gemini_config.model_copy()
        model_config.system_instruction = system_prompt
        context = await self.get_context_for_prompt(
            ctx, 10, before_message=message, after_message=message
        )
        time = self.get_time()
        instructions = "Remember, you only need to supply the translation which fits the context in a suitable tone, don't give any additional information!"
        prompt = f"Chat context: {{\n{context}\n}}"
        prompt += f"\n\nMessage to translate: {{\n{message.author.display_name} ({message.author.name}): {message.content}\n}}"
        prompt += f"\n\nCurrent time: {time}"
        prompt += f"\n\nAdditional instructions: {instructions}"
        prompt += f"\n\n{target_language} translation for {ctx.message.author.display_name} ({ctx.message.author.name}):"
        await self.request_gemini(ctx, prompt, model_config, model="gemini-2.0-flash")

    @commands.hybrid_command(name="set_prompt", description="Set the system prompt.")
    @commands.is_owner()
    @auto_delete(delay=0)
    async def set_prompt(
        self, ctx: commands.Context, system_prompt="", language="Chinese"
    ):
        if system_prompt == "":
            nickname = ctx.guild.me.nick
            if nickname is None:
                nickname = ctx.guild.me.name
            system_prompt = f"You are {nickname}, a helpful AI assistant. You are assisting a user in a discord server. The user asks you a question, and you provide a helpful response. The user may ask you anything."
        system_prompt = (
            system_prompt
            + f"You always speak {language} unless the question specifies otherwise."
        )
        self.system_prompt = system_prompt
        await ctx.send("System prompt set.", ephemeral=True, delete_after=5)

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


async def setup(bot: commands.Bot):
    config = resolve_config()
    apikeys = config.get("gemini_keys")
    print(cpt.info(f"{len(apikeys)} keys loaded."))
    current_key = config.get("current_key")
    chat_channel_id = config.get("chat_channel_id")
    openai_api_key = config.get("openai_api_key")
    openai_endpoint = config.get("openai_endpoint")
    if openai_api_key is not None and openai_endpoint is not None:
        await bot.add_cog(
            Gemini(
                bot,
                apikeys,
                current_key,
                chat_channel_id,
                config,
                openai_api_key,
                openai_endpoint,
            )
        )
        print(cpt.success("Cog loaded: Gemini, with OpenAI model"))
    else:
        await bot.add_cog(Gemini(bot, apikeys, current_key, chat_channel_id, config))
        print(cpt.success("Cog loaded: Gemini"))
