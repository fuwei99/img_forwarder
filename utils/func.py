import json


def resolve_config() -> dict:
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    return config


def get_words() -> dict:
    with open("trigger.json", "r", encoding="utf-8") as f:
        words = json.load(f)
    return words


def mapping_cog(cog_name: str) -> str:
    return "".join(["_" + i.lower() if i.isupper() else i for i in cog_name]).lstrip(
        "_"
    )
