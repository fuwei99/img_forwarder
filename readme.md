---
title: Img Forwarder (图片转发机器人)
emoji: 🖼️
colorFrom: indigo
colorTo: blue
sdk: docker
pinned: false
---

# Img Forwarder (图片转发机器人)

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

### Hugging Face Space 部署

本项目可以在 Hugging Face Space 上部署：

[![Deploy to Hugging Face](https://img.shields.io/badge/Deploy%20to-Hugging%20Face-blue)](https://huggingface.co/spaces/fuwei99/img_forwarder)

1. 在 Hugging Face 上创建一个新的 Space，选择 Docker 作为 SDK
2. 上传项目代码到 Space
3. 修改 `config.json` 文件，填入你的 Discord 令牌和 API 密钥
4. Space 将自动构建并启动机器人
5. 你可以通过 Space 的 Web 界面访问机器人的配置界面

**注意**：项目已经内置了自动保活功能，会定期自我请求以保持 Space 活跃。

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
- `/config` - 配置设置页面
- `/presets` - 预设管理页面

### 配置

机器人需要一个 config.json 文件，结构如下：
- Discord 令牌
- 频道 ID
- Gemini 和 OpenAI 的 API 密钥

可能的 `config.json` 示例：

```json
{
    "token": "你的机器人令牌", 
    "target_channel_id": 123, // 图库频道
    "source_channel_id": 123, // 图片分享频道
    "chat_channel_id": 123, // 自动回复、备份和 AI 功能工作的频道
    "backup_channel_id": 123, 
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

## Hugging Face Space Deployment

This project can be deployed on Hugging Face Space:

[![Deploy to Hugging Face](https://img.shields.io/badge/Deploy%20to-Hugging%20Face-blue)](https://huggingface.co/spaces/fuwei99/img_forwarder)

1. Create a new Space on Hugging Face and select Docker as the SDK
2. Upload the project code to Space
3. Modify the `config.json` file to fill in your Discord token and API keys
4. Space will automatically build and start the bot
5. You can access the bot's configuration interface through Space's Web interface

**Note**: The project has built-in auto-alive functionality, which periodically self-requests to keep Space active.

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
- `/config` - Configuration settings page
- `/presets` - Preset management page

## Configuration

The bot requires a config.json file with the following structure:
- Discord token
- Channel IDs
- API keys for Gemini and OpenAI

One possible `config.json`:

```json
{
    "token": "YOUR_BOT_TOKEN", 
    "target_channel_id": 123, // the gallery channel
    "source_channel_id": 123, // the img-sharing channel
    "chat_channel_id": 123, // auto-responding, backup and ai functions are working for this channel
    "backup_channel_id": 123, 
    "gemini_keys": [
        "YOUR_GEMINI_KEY",
        "YOUR_GEMINI_KEY",
        "YOUR_GEMINI_KEY",
    ],
    "gemini_chunk_per_edit": 2, // 2 is recommended, 3 is ok
    "current_key": -1, // set to any number will work, it's used for status recording
    "target_language": "Chinese", // the default target language for ai translation
    "webhook_url": "YOUR_WEB_HOOK_URL", // set up a webhook for the chat channel and this's used for the ai functions
    "openai_key": "OPENAI_KEY",
    "openai_endpoint": "OPENAI_ENDPOINT", // your openai endpoint, and it should end with `/v1`. thus, this allows you to use any other models with an openai format
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
            "id": "YOUR_MODEL_NAME_IN_THE_MODEL_LIST",
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