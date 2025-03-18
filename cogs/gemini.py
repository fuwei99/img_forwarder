from discord.ext import commands
import discord
from google import genai
from google.genai import types
from utils.decorator import auto_delete

from utils.func import resolve_config, write_config, cpt


class Gemini(commands.Cog):
    def __init__(
        self, bot: commands.Bot, apikeys, current_key, chat_channel_id, config
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

    def get_next_key(self):
        self.current_key = (self.current_key + 1) % self.num
        self.config["current_key"] = self.current_key
        write_config(self.config)
        return self.apikeys[self.current_key]

    @commands.hybrid_command(name="hey", description="Ask a question to gemini.")
    async def hey(
        self,
        ctx: commands.Context,
        *,
        question: str,
        context_length: int = None,
    ):
        if context_length is None:
            context_length = self.context_length
        if self.system_prompt == "":
            nickname = ctx.guild.me.nick
            if nickname is None:
                nickname = ctx.guild.me.name
            self.system_prompt = f"You are {nickname}, a helpful AI assistant. You are assisting a user in a discord server. The user asks you a question, and you provide a helpful response. The user may ask you anything. You always speak Chinese unless the question specifies otherwise."
        if ctx.channel.id != self.chat_channel_id:
            ctx.send("I apologize, but……", delete_after=5, ephemeral=True)
            return
        key = self.get_next_key()
        context_msg = []
        async for msg in ctx.channel.history(limit=context_length):
            context_msg.append(f"{msg.author.name}: {msg.content}")
        context_msg.reverse()
        context = "\n".join(context_msg)
        prompt = f"Chat context: \n{{{context}}} \nQuestion: {question}\n Answer:"
        client = genai.Client(api_key=key)
        msg = await ctx.send("Thinking...")
        full = ""
        every_two_chunk = False
        try:
            response = client.models.generate_content_stream(
                model="gemini-2.0-pro-exp-02-05",
                contents=[prompt],
                config=types.GenerateContentConfig(
                    system_instruction=self.system_prompt,
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
                ),
            )
            for chunk in response:
                if chunk.text:
                    print(chunk.text)
                    full += chunk.text
                    if every_two_chunk:
                        await msg.edit(content=full)
                        every_two_chunk = False
                    else:
                        every_two_chunk = True
            await msg.edit(content=full)
        except Exception as e:
            print(e)

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
    async def set_prompt(self, ctx: commands.Context, context_length: int):
        self.context_length = context_length
        await ctx.send("Context length set.", ephemeral=True, delete_after=5)


async def setup(bot: commands.Bot):
    config = resolve_config()
    apikeys = config.get("gemini_keys")
    current_key = config.get("current_key")
    chat_channel_id = config.get("chat_channel_id")
    print(cpt.info(f"{len(apikeys)} keys loaded."))
    await bot.add_cog(Gemini(bot, apikeys, current_key, chat_channel_id, config))
    print(cpt.success("Cog loaded: Gemini"))
