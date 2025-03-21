import asyncio
import concurrent.futures
import json
from typing import Iterator
import concurrent
import pytz
from datetime import datetime

WORDS = "trigger.json"
tz = pytz.timezone("Asia/Shanghai")


def get_words() -> dict:
    with open(WORDS, "r", encoding="utf-8") as f:
        words = json.load(f)
    return words


def mapping_cog(cog_name: str) -> str:
    return "".join(["_" + i.lower() if i.isupper() else i for i in cog_name]).lstrip(
        "_"
    )


def now(tz=tz, fmt="%Y-%m-%d %H:%M:%S") -> str:
    return datetime.now(tz).strftime(fmt)


def get_time(dt: datetime, tz=tz, fmt="%Y-%m-%d %H:%M:%S") -> str:
    return dt.astimezone(tz).strftime(fmt)


async def async_iter(response: Iterator):
    loop = asyncio.get_event_loop()

    def safe_next(iterator: Iterator):
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


async def async_do(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args, **kwargs)


async def async_do_thread(func, *args, **kwargs):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(func, *args, **kwargs)
        try:
            return await asyncio.wrap_future(future)
        except Exception as e:
            print(e)
