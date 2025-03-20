import json

CONFIG = "config.json"

class Config:
    def __init__(self):
        with open(CONFIG, "r", encoding="utf-8") as f:
            self._config: dict = json.load(f)
    
    def get(self, key: str):
        return self._config.get(key)
    
    def write(self, key: str, value):
        self._config[key] = value
        with open(CONFIG, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=4)
            
config = Config()