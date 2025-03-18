from discord.ext import commands
import discord
import google.generativeai as genai

from utils.func import resolve_config, cpt


class Gemini(commands.Cog):
    def __init__(self, bot: commands.Bot, apikeys, current_key, chat_channel_id):
        self.bot = bot
        self.conversations = {}
        self.apikeys = apikeys
        self.current_key = current_key
        self.num = len(apikeys)
        self.chat_channel_id = chat_channel_id
        self.system_prompt = ""
        self.model = genai.GenerativeModel("gemini-2.0-pro-exp-02-05")

    def get_next_key(self):
        self.current_key = (self.current_key + 1) % self.num
        return self.apikeys[self.current_key]

    @commands.hybrid_command(name="hey", description="Ask a question to gemini.")
    async def hey(self, ctx: commands.Context, question: str, context_length: int = 20):
        if ctx.channel.id != self.chat_channel_id:
            ctx.send("I apologize, but……", delete_after=5, ephemeral=True)
            return
        key = self.get_next_key()
        # 获取当前上下文的对话
        context_msg = []
        async for msg in ctx.channel.history(limit=ctx):
            context_msg.append(f"{msg.author.name}: {msg.content}")
        context_msg.reverse()
        context = "\n".join(context_msg)
        prompt = f"\n{context}\n\nQ: {question}\n\nA:"
        genai.configure(key)
        response_stream = self.model.generate_content(prompt, stream=True)
        initial_msg = await ctx.send("Thinking...")
        async for response in response_stream:
            await initial_msg.edit(content=response)

    @commands.hybrid_command(name="set_prompt", description="Set the system prompt.")
    @commands.is_owner()
    async def set_prompt(
        self, ctx: commands.Context, system_prompt="", language="Chinese"
    ):
        if system_prompt == "":
            nickname = ctx.guild.me.nick
            if nickname is None:
                nickname = ctx.guild.me.name
            system_prompt = f"You are {nickname}, a helpful AI assistant. You are assisting a user in a chatroom. The user asks you a question, and you provide a helpful response. The user may ask you anything."
        system_prompt = (
            system_prompt
            + f"You always speak {language} unless the question specifies otherwise."
        )
        self.system_prompt = system_prompt
        self.model = genai.GenerativeModel(
            "gemini-2.0-pro-exp-02-05", system_instruction=system_prompt
        )
        await ctx.send("System prompt set.", ephemeral=True, delete_after=5)


async def setup(bot: commands.Bot):
    config = resolve_config()
    apikeys = config.get("gemini_keys")
    current_key = config.get("current_key")
    chat_channel_id = config.get("chat_channel_id")
    print(cpt.info(f"{len(apikeys)} keys loaded."))
    await bot.add_cog(Gemini(bot, apikeys, current_key, chat_channel_id))
    print(cpt.success("Cog loaded: Gemini"))
