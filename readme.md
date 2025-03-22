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

## Setup

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Configure `config.json` with your Discord token and API keys
4. Run the bot:
```bash
python main.py
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
- `.nickname <name>` - Change bot nickname
- `.reload_config` - Reload configuration
- `.status <status>` - Change bot status
- `.set_context_length <length>` - Set AI context length
- `.set_target_language <language>` - Set translation target language
- `.set_timezone <timezone>` - Set timezone
- `.set_model <model>` - Set default OpenAI model

## Configuration

The bot requires a config.json file with the following structure:
- Discord token
- Channel IDs
- API keys for Gemini and OpenAI

One possible `config.json`

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