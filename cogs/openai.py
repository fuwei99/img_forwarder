import json
from discord.ext import commands
import discord
from aiohttp import ClientSession

from utils.color_printer import cpr
from utils.config import config
from utils.decorator import auto_delete
from utils.context_prompter import ContextPrompter


class Openai(commands.Cog):
    def __init__(self, bot: commands.Bot, webhook: discord.Webhook):
        self.bot = bot
        self.webhook = webhook
        self.key = config.get("openai_key")
        self.endpoint = config.get("openai_endpoint")
        self.models: dict[str, str] = config.get("openai_models")
        self.context_prompter = ContextPrompter()
        self.chat_channel_id = config.get("chat_channel_id")
        self.model = list(self.models.keys())[0]
        self.context_length = 20

    async def request_openai(self, model: str, prompt: str, username: str) -> str:
        url = f"{self.endpoint}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.key}",
        }
        data = {
            "model": self.models[model]["id"],
            "messages": [
                {"role": "user", "content": prompt},
            ],
            "top_p": 0.95,
            "tok_k": 55,
            "temperature": 1.0,
            "stream": True,
        }
        initial_message = await self.webhook.send(
            "Typing...", username=username, wait=True
        )
        full = ""
        every_n_chunk = 1
        n = self.models[model]["chunk_per_edit"]
        async with ClientSession() as session:
            async with session.post(url, json=data, headers=headers) as response:
                async for line in response.content:
                    line = line.decode("utf-8").strip()
                    if line:
                        line = line.removeprefix("data:").strip()
                        data = json.loads(line)
                        choices = data.get("choices")
                        if choices:
                            delta = choices[0].get("delta").get("content")
                            if delta:
                                full += delta
                                if every_n_chunk == n:
                                    await initial_message.edit(content=full)
                                    every_n_chunk = 1
                                else:
                                    every_n_chunk += 1
                            if choices[0].get("finish_reason"):
                                break
        await initial_message.edit(content=full)

    @commands.hybrid_command(name="yo", description="Chat with OpenAI models.")
    async def yo(
        self,
        ctx: commands.Context,
        model: str,
        *,
        question: str,
        context_length: int = None,
    ):
        if ctx.channel.id != self.chat_channel_id:
            await ctx.send("I apologize, but……", delete_after=5, ephemeral=True)
            return
        if context_length is None:
            context_length = self.context_length
        if ctx.message.reference is None:
            prompt = await self.context_prompter.chat_prompt(
                ctx, context_length, question
            )
        else:
            message = ctx.message.reference.resolved
            prompt = await self.context_prompter.chat_prompt_with_reference(
                ctx, context_length, 5, question, message
            )
        username = model + "🤖"
        await self.request_openai(model, prompt, username)

    @commands.hybrid_command(name="yoo", description="Chat with default OpenAI model.")
    async def yoo(
        self, ctx: commands.Context, *, question: str, context_length: int = None
    ):
        if ctx.channel.id != self.chat_channel_id:
            await ctx.send("I apologize, but……", delete_after=5, ephemeral=True)
            return
        if context_length is None:
            context_length = self.context_length
        if ctx.message.reference is None:
            prompt = await self.context_prompter.chat_prompt(
                ctx, context_length, question
            )
        else:
            message = ctx.message.reference.resolved
            prompt = await self.context_prompter.chat_prompt_with_reference(
                ctx, context_length, 5, question, message
            )
        username = self.model + "🤖"
        await self.request_openai(self.model, prompt, username)

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


async def setup(bot):
    webhook = discord.Webhook.from_url(
        config.get("webhook_url"), session=ClientSession()
    )
    await bot.add_cog(Openai(bot, webhook))
    print(cpr.success("Cog loaded: Openai"))
