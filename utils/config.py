import json

CONFIG = "config.json"


class Config:
    def __init__(self):
        self._config = {}
        self.reload()

    def get(self, key: str, default=None):
        """获取配置值，支持多层级访问，如 'servers.main.chat_channels'"""
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        return value

    def write(self, key: str, value):
        """写入配置值，支持多层级写入，如 'servers.main.chat_channels'"""
        keys = key.split('.')
        current = self._config
        
        # 遍历到最后一个key之前
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        # 设置最后一个key的值
        current[keys[-1]] = value
        
        # 保存到文件
        with open(CONFIG, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=4, ensure_ascii=False)

    def reload(self):
        with open(CONFIG, "r", encoding="utf-8") as f:
            self._config = json.load(f)

    def get_server_config(self, guild_id: str):
        """获取指定服务器的配置"""
        for server_name, server_config in self._config.get("servers", {}).items():
            if server_config.get("guild_id") == guild_id:
                return server_name, server_config
        return None, None


config = Config()
