from discord.ext import commands
import discord


class MyCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="foo", description="bar")
    async def foo(self, ctx):
        print("yes")
        await ctx.send("bar")
