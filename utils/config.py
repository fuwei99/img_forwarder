import json

CONFIG = "config.json"


class Config:
    def __init__(self):
        self._config = {}
        self.reload()

    def get(self, key: str, default=None):
        return self._config.get(key, default)

    def write(self, key: str, value):
        self._config[key] = value
        with open(CONFIG, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=4)

    def reload(self):
        with open(CONFIG, "r", encoding="utf-8") as f:
            self._config = json.load(f)


config = Config()
