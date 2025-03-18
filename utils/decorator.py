import functools
from discord.ext import commands
import discord
import asyncio


def auto_delete(delay=5):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, ctx: commands.Context, *args, **kwargs):
            await func(self, ctx, *args, **kwargs)
            await asyncio.sleep(delay)
            try:
                await ctx.message.delete()
            except Exception as e:
                pass

        return wrapper

    return decorator
