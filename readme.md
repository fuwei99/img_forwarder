# Img Forwarder (图片转发机器人)

## 最新更新

- **多服务支持**：现在支持多个Discord服务器的配置管理
- **网络配置**：增加了网络端口5000的配置功能，通过Web界面可更方便地管理机器人

## [中文版]

这是一个功能丰富的 Discord 机器人，最初设计用于将图片从一个频道转发到图库频道，但现已演变为包含多种 AI 集成和实用功能的综合工具。

### 功能特性

- **图片转发**：自动将源频道的图片转发到目标图库频道
- **消息备份**：使用 `.backup` 命令备份消息
- **AI 集成**：
  - 通过 `.hey` 命令集成 Google Gemini
  - 通过 `.yo` 和 `.yoo` 命令集成 OpenAI
  - 使用 `.translate` 命令实现翻译功能
- **关键词响应**：自动回复配置的触发词
- **管理命令**：提供多种机器人管理的管理员命令
- **Web 界面**：提供直观的配置和预设管理界面
- **多服务器支持**：支持在多个Discord服务器上同时工作

### 安装设置

1. 克隆仓库
2. 安装依赖：
```bash
pip install -r requirements.txt
```
3. 创建配置文件：
   - 将 `config.example.json` 复制为 `config.json`
   - 在 `config.json` 中填入你的 Discord 令牌和 API 密钥
4. 运行机器人：
```bash
python main.py
```
或者使用批处理文件：
```bash
./start.bat
```

### GitHub 部署

如果你是从 GitHub 克隆此项目：

1. 克隆仓库：
```bash
git clone https://github.com/YOUR_USERNAME/img_forwarder.git
cd img_forwarder
```

2. 创建配置文件：
```bash
cp config.example.json config.json
```

3. 使用你喜欢的编辑器编辑配置文件，填入你的令牌和 API 密钥：
```bash
nano config.json  # 或使用任何文本编辑器
```

4. 安装依赖并启动机器人：
```bash
pip install -r requirements.txt
python main.py  # 或 ./start.bat
```

### 命令

#### 用户命令
- `.ping` - 检查机器人延迟
- `.backup` - 备份消息（必须作为回复使用）
- `.hey <问题>` - 向 Google Gemini 提问
- `.translate [目标语言]` - 翻译消息（必须作为回复使用）
- `.yo <模型> <问题>` - 与特定 OpenAI 模型聊天
- `.yoo <问题>` - 与默认 OpenAI 模型聊天

#### 管理员命令
- `.sync` - 同步混合命令
- `.list` - 列出所有已加载的 cogs
- `.load <cog>` - 加载一个 cog
- `.unload <cog>` - 卸载一个 cog
- `.reload <cog>` - 重新加载一个 cog
- `.reload_all` - 重新加载所有 cogs
- `.nickname <名称>` - 更改机器人昵称
- `.reload_config` - 重新加载配置
- `.status <状态>` - 更改机器人状态
- `.set_context_length <长度>` - 设置 AI 上下文长度
- `.set_target_language <语言>` - 设置翻译目标语言
- `.set_timezone <时区>` - 设置时区
- `.set_model <模型>` - 设置默认 OpenAI 模型

### Web 界面

启动机器人后，可通过 http://127.0.0.1:5000 访问 Web 管理界面：
- `/` - 主页
- `/config` - 配置设置页面，支持多服务器配置和网络端口设置
- `/presets` - 预设管理页面

#### 多服务器配置
在Web界面中，您可以管理多个Discord服务器的配置：
- 添加新服务器：在配置页面中添加新的服务器配置
- 编辑现有服务器：修改服务器名称、ID和频道设置
- 删除服务器：移除不再需要的服务器配置

#### 网络设置
机器人默认使用5000端口运行Web界面。您可以通过修改源代码中的端口配置进行自定义：
- 主机地址：默认为127.0.0.1（本地访问）
- 端口：默认为5000

### 配置

机器人需要一个 config.json 文件，结构如下：
- Discord 令牌
- 频道 ID
- Gemini 和 OpenAI 的 API 密钥

可能的 `config.json` 示例：

```json
{
    "token": "你的机器人令牌", 
    "servers": {
        "server_1": {
            "name": "主服务器",
            "discord_guild_id": "服务器ID",
            "target_channel_id": 123456789, // 图库频道
            "source_channel_id": 123456789, // 图片分享频道
            "main_channel_id": 123456789, // 自动回复、备份和 AI 功能工作的频道
            "backup_channel_id": 123456789,
            "chat_channels": {
                "频道ID": {
                    "preset": "default"
                }
            }
        },
        "server_2": {
            "name": "副服务器",
            "discord_guild_id": "服务器ID",
            "target_channel_id": 123456789,
            "source_channel_id": 123456789,
            "main_channel_id": 123456789,
            "backup_channel_id": 123456789,
            "chat_channels": {
                "频道ID": {
                    "preset": "default"
                }
            }
        }
    },
    "gemini_keys": [
        "你的_GEMINI_密钥",
        "你的_GEMINI_密钥",
        "你的_GEMINI_密钥",
    ],
    "gemini_chunk_per_edit": 2, // 推荐设置为 2，3 也可以
    "current_key": -1, // 设置为任何数字都可以，用于状态记录
    "target_language": "Chinese", // AI 翻译的默认目标语言
    "webhook_url": "你的_WEBHOOK_URL", // 为聊天频道设置的 webhook，用于 AI 功能
    "openai_key": "OPENAI_密钥",
    "openai_endpoint": "OPENAI_端点", // 你的 OpenAI 端点，应以 `/v1` 结尾，允许使用任何 OpenAI 格式的模型
    "openai_models": {
        "grok": {
            "id": "grok/grok-3",
            "chunk_per_edit": 10
        },
        "claude": {
            "id": "cursor/claude-3.7-sonnet",
            "chunk_per_edit": 10
        },
        "gpt": {
            "id": "cursor/gpt-4o",
            "chunk_per_edit": 10
        },
        "AI_名称": {
            "id": "模型列表中的模型名称",
            "chunk_per_edit": 10
        }
    }
}
```

### 系统要求

- Python 3.11+
- discord.py 2.5.2+
- Google Genai 库
- requirements.txt 中列出的其他库

---

## [English Version]

# Img Forwarder

## Latest Updates

- **Multi-server Support**: Now supports configuration management for multiple Discord servers
- **Network Configuration**: Added network port 5000 configuration functionality, making bot management more convenient through the Web interface

This Discord bot was initially created for forwarding images from one channel to a gallery, but has evolved to include multiple AI integration and utility functions.

## Features

- **Image Forwarding**: Automatically forwards images from a source channel to a target gallery channel
- **Message Backup**: Backup messages with `.backup` command
- **AI Integration**:
  - Google Gemini integration with `.hey` command
  - OpenAI integration with `.yo` and `.yoo` commands
  - Translation capabilities with `.translate` command
- **Keyword Response**: Automatically responds to configured trigger words
- **Admin Commands**: Various administrative commands for bot management
- **Web Interface**: Intuitive configuration and preset management interface
- **Multi-server Support**: Support working on multiple Discord servers

## Setup

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Create configuration file:
   - Copy `config.example.json` to `config.json`
   - Fill in your Discord token and API keys in `config.json`
4. Run the bot:
```bash
python main.py
```
Or use the batch file:
```bash
./start.bat
```

## GitHub Deployment

If you're cloning this project from GitHub:

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/img_forwarder.git
cd img_forwarder
```

2. Create your configuration file:
```bash
cp config.example.json config.json
```

3. Edit the configuration file with your favorite editor to add your tokens and API keys:
```bash
nano config.json  # or any text editor
```

4. Install dependencies and start the bot:
```bash
pip install -r requirements.txt
python main.py  # or ./start.bat
```

## Commands

### User Commands
- `.ping` - Check bot latency
- `.backup` - Backup a message (must be used as a reply)
- `.hey <question>` - Ask Google Gemini a question
- `.translate [target_language]` - Translate a message (must be used as a reply)
- `.yo <model> <question>` - Chat with specific OpenAI model
- `.yoo <question>` - Chat with default OpenAI model

### Admin Commands
- `.sync` - Sync hybrid commands
- `.list` - List all loaded cogs
- `.load <cog>` - Load a cog
- `.unload <cog>` - Unload a cog
- `.reload <cog>` - Reload a cog
- `.reload_all` - Reload all cogs
- `.nickname <n>` - Change bot nickname
- `.reload_config` - Reload configuration
- `.status <status>` - Change bot status
- `.set_context_length <length>` - Set AI context length
- `.set_target_language <language>` - Set translation target language
- `.set_timezone <timezone>` - Set timezone
- `.set_model <model>` - Set default OpenAI model

## Web Interface

After starting the bot, access the web management interface at http://127.0.0.1:5000:
- `/` - Home page
- `/config` - Configuration settings page, supports multi-server configuration and network port settings
- `/presets` - Preset management page

### Multi-server Configuration
In the Web interface, you can manage configurations for multiple Discord servers:
- Add new servers: Add new server configurations in the configuration page
- Edit existing servers: Modify server names, IDs, and channel settings
- Delete servers: Remove server configurations that are no longer needed

### Network Settings
The bot runs the Web interface on port 5000 by default. You can customize this by modifying the port configuration in the source code:
- Host address: Default is 127.0.0.1 (local access)
- Port: Default is 5000

## Configuration

The bot requires a config.json file with the following structure:
```json
{
    "token": "YOUR_BOT_TOKEN", 
    "servers": {
        "server_1": {
            "name": "Main Server",
            "discord_guild_id": "SERVER_ID",
            "target_channel_id": 123456789, // gallery channel
            "source_channel_id": 123456789, // image sharing channel
            "main_channel_id": 123456789, // channel for auto-responses, backups, and AI features
            "backup_channel_id": 123456789,
            "chat_channels": {
                "CHANNEL_ID": {
                    "preset": "default"
                }
            }
        },
        "server_2": {
            "name": "Secondary Server",
            "discord_guild_id": "SERVER_ID",
            "target_channel_id": 123456789,
            "source_channel_id": 123456789,
            "main_channel_id": 123456789,
            "backup_channel_id": 123456789,
            "chat_channels": {
                "CHANNEL_ID": {
                    "preset": "default"
                }
            }
        }
    },
    "gemini_keys": [
        "YOUR_GEMINI_KEY",
        "YOUR_GEMINI_KEY",
        "YOUR_GEMINI_KEY",
    ],
    "gemini_chunk_per_edit": 2, // recommended to set to 2, 3 is also fine
    "current_key": -1, // can be set to any number, used for state tracking
    "target_language": "English", // default target language for AI translation
    "webhook_url": "YOUR_WEBHOOK_URL", // webhook set up for chat channel, used for AI features
    "openai_key": "OPENAI_KEY",
    "openai_endpoint": "OPENAI_ENDPOINT", // your OpenAI endpoint, should end with `/v1`, allows use of any OpenAI format model
    "openai_models": {
        "grok": {
            "id": "grok/grok-3",
            "chunk_per_edit": 10
        },
        "claude": {
            "id": "cursor/claude-3.7-sonnet",
            "chunk_per_edit": 10
        },
        "gpt": {
            "id": "cursor/gpt-4o",
            "chunk_per_edit": 10
        },
        "AI_NAME": {
            "id": "MODEL_NAME_FROM_LIST",
            "chunk_per_edit": 10
        }
    }
}
```

## Requirements

- Python 3.11+
- discord.py 2.5.2+
- Google Genai library
- Additional libraries listed in requirements.txt