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

    def get_server_config(self, server_id: str, default=None):
        """获取指定服务器的配置"""
        servers = self._config.get("servers", {})
        return servers.get(server_id, default)

    def get_server_value(self, server_id: str, key: str, default=None):
        """获取指定服务器的特定配置项"""
        server_config = self.get_server_config(server_id)
        if server_config:
            return server_config.get(key, default)
        return default

    def write_server_value(self, server_id: str, key: str, value):
        """更新指定服务器的特定配置项"""
        servers = self._config.get("servers", {})
        if server_id not in servers:
            servers[server_id] = {}
        servers[server_id][key] = value
        self._config["servers"] = servers
        with open(CONFIG, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=4)

    def get_all_servers(self):
        """获取所有服务器配置"""
        return self._config.get("servers", {})

    def add_server(self, server_id: str, server_config: dict):
        """添加新服务器配置"""
        servers = self._config.get("servers", {})
        servers[server_id] = server_config
        self._config["servers"] = servers
        with open(CONFIG, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=4)

    def reload(self):
        with open(CONFIG, "r", encoding="utf-8") as f:
            self._config = json.load(f)


config = Config()
