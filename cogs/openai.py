import json
from discord.ext import commands
import discord
from aiohttp import ClientSession

from utils.color_printer import cpr
from utils.config import config
from utils.decorator import auto_delete
from utils.context_prompter import ContextPrompter
from utils.logger import logger


class Openai(commands.Cog):
    def __init__(self, bot: commands.Bot, webhook: discord.Webhook):
        self.bot = bot
        self.webhook = webhook
        self.key = config.get("openai_key")
        self.endpoint = config.get("openai_endpoint")
        self.models: dict[str, str] = config.get("openai_models")
        self.context_prompter = ContextPrompter()
        
        # 确保chat_channels中的键全部为字符串
        self.update_chat_channels()
        
        self.model = list(self.models.keys())[0]
        self.context_length = 20

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
        if hasattr(self.bot, "get_cog"):
            agent_manager = self.bot.get_cog("AgentManager")
            if agent_manager:
                config_from_preset = agent_manager.get_preset_json("openai_config.json", channel_id)
                if config_from_preset:
                    openai_config = config_from_preset
        
        data = {
            "model": self.models[model]["id"],
            "messages": [
                {"role": "user", "content": prompt},
            ],
            "top_p": openai_config.get("top_p", 0.95),
            "top_k": openai_config.get("top_k", 55),
            "temperature": openai_config.get("temperature", 1.0),
            "stream": True,
        }
        msg = await self.webhook.send("Typing...", username=username, wait=True)
        full = ""
        every_n_chunk = 1
        n = self.models[model]["chunk_per_edit"]
        async with ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as resp:
                resp.raise_for_status()
                async for line in resp.content:
                    if not line:
                        continue
                    sline = line.decode("utf-8").strip()
                    if sline == "data: [DONE]":
                        break
                    if not sline.startswith("data: "):
                        continue
                    try:
                        ss = sline[6:]
                        data = json.loads(ss)
                        dt = data["choices"][0]["delta"].get("content", "")
                        full += dt
                        if (every_n_chunk % n) == 0:
                            await msg.edit(content=full)
                        every_n_chunk += 1
                    except Exception as e:
                        logger.error(e)
        await msg.edit(content=full)
        return full

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
            await ctx.send("抱歉，该命令只能在指定的聊天频道中使用", delete_after=5, ephemeral=True)
            return
        if context_length is None:
            context_length = self.context_length
        username = model + "🤖"
        if ctx.message.reference is None:
            prompt = await self.context_prompter.chat_prompt(
                ctx, context_length, question, name=username
            )
        else:
            message = ctx.message.reference.resolved
            prompt = await self.context_prompter.chat_prompt_with_reference(
                ctx, context_length, 5, question, message, name=username
            )
        await self.request_openai(model, prompt, username, channel_id)

    @commands.hybrid_command(name="yoo", description="Chat with default OpenAI model.")
    async def yoo(
        self, ctx: commands.Context, *, question: str, context_length: int = None
    ):
        await self.yo(ctx, self.model, question=question, context_length=context_length)

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

    async with ClientSession() as session:
        webhook = discord.Webhook.from_url(webhook_url, session=session)
        await bot.add_cog(Openai(bot, webhook))
        print(cpr.success("Cog loaded: Openai"))
