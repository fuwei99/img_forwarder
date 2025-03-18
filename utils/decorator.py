import functools
from discord.ext import commands
import discord
import asyncio


def auto_delete(delay=5):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, ctx: commands.Context, *args, **kwargs):
            await func(self, ctx, *args, **kwargs)
            if ctx.interaction:
                await asyncio.sleep(delay)
                await ctx.delete()
            else:
                await asyncio.sleep(delay)
                await ctx.message.delete()

        return wrapper

    return decorator
