import json
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