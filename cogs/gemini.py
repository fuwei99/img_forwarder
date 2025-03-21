import asyncio
from typing import Iterator
from discord.ext import commands
import discord
from google import genai
from google.genai import types
import pytz
import random
from aiohttp import ClientSession
from utils.decorator import auto_delete

from utils.color_printer import cpr
from utils.config import config
from utils.context_prompter import ContextPrompter


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
                yield item
        except Exception as e:
            print(e)

    async def request_gemini(
        self,
        ctx: commands.Context,
        prompt: str,
        model_config: types.GenerateContentConfig = None,
        model="gemini-2.0-pro-exp-02-05",
        username=None,
        extra_url=None,
    ):
        if model_config is None:
            model_config = self.default_gemini_config
        if model != "gemini-2.0-pro-exp-02-05":
            key = self.get_random_key()
        else:
            key = self.get_next_key()
        client = genai.Client(api_key=key)
        if username is None:
            msg = await ctx.send("Typing...")
        else:
            msg = await self.webhook.send("Typing...", wait=True, username=username)
        full = ""
        every_three_chunk = 1
        contents: list[types.Part] = [types.Part.from_text(prompt)]
        if extra_url:
            for url in extra_url:
                contents.append(types.Part.from_url(url))
        try:
            response = client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=self.default_gemini_config,
            )

            async for chunk in self.stream_generator(response):
                if chunk.text:
                    full += chunk.text
                    if every_three_chunk == 3:
                        await msg.edit(content=full)
                        every_three_chunk = 1
                    else:
                        every_three_chunk += 1
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
        extra_url = None
        if ctx.message.reference is None:
            prompt = await self.context_prompter.chat_prompt(
                ctx, context_length, question
            )
        else:
            reference = ctx.message.reference.resolved
            if reference.attachments:
                extra_url: list[str] = []
                for attachment in reference.attachments:
                    extra_url.append(attachment.url)
                prompt = await self.context_prompter.chat_prompt_with_attachment(
                    ctx, question, reference
                )
            else:
                prompt = await self.context_prompter.chat_prompt_with_reference(
                    ctx, context_length, 5, question, reference
                )
        await self.request_gemini(ctx, prompt, extra_url=extra_url)

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
        prompt = await self.context_prompter.translate_prompt(
            ctx, context_length, message, 5, target_language
        )
        username = ctx.me.display_name + " (Translator🔤)"
        await self.request_gemini(
            ctx, prompt, model="gemini-2.0-flash", username=username
        )

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
    await bot.add_cog(Gemini(bot, webhook))
    print(cpr.success("Cog loaded: Gemini"))
