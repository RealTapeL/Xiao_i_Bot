# Telegram AI Companion Bot 💕

A Telegram bot powered by large language models that provides intelligent conversation, memory management, and proactive care features. This AI companion builds emotional connections with users over time.

## Features

### Core Features
- **Intelligent Conversation** - Natural language dialogue using LLM with human-like, emotionally intelligent responses
- **Memory System** - Long-term memory storage with importance scoring and automatic extraction
- **User Profiling** - Comprehensive user profiles (`UserProfile` class) that track preferences, habits, personality traits, and shared memories
- **Proactive Care** - Scheduled check-ins and caring messages based on user profile
- **Emotion Analysis** - Analyzes user emotions in real-time for empathetic responses
- **Relationship Development** - Evolves from stranger → acquaintance → friend → partner over time with adapted conversation styles

### Advanced Features
- **System Monitoring** - Monitors computer usage patterns (CPU, memory, idle time)
- **Smart Triggers** - Initiates conversations based on user activity
- **Daily Greetings** - Morning and night automated messages
- **Web Dashboard** - Real-time logs and monitoring interface
- **Skills System** - Extensible plugin system for external integrations
- **Xiaohongshu (Little Red Book) Integration** - Search, post, and manage Xiaohongshu content

## System Architecture

```
bot/
├── src/
│   ├── __init__.py
│   ├── bot.py                    # Main Telegram bot application
│   ├── chat_manager.py           # Chat and conversation management
│   ├── memory_manager.py         # Memory extraction and retrieval
│   ├── model_manager.py          # LLM provider abstraction
│   ├── database.py               # SQLAlchemy models and utilities
│   ├── proactive_scheduler.py    # Scheduled task scheduler
│   ├── system_monitor.py         # System metrics collection
│   ├── trigger_engine.py         # Event trigger logic
│   ├── web_server.py             # Flask web server
│   └── webapp/                   # Frontend dashboard
│       ├── index.html
│       ├── main.ts
│       ├── main.js
│       ├── style.css
│       └── package.json
├── bot/                          # Bot data directory
├── requirements.txt
├── .env.example
├── main.py
├── MAC_SETUP.md                  # Mac user startup guide (for China users)
└── README.md
```

## Quick Start

> **🇨🇳 中国大陆用户注意**：如果你的服务器在中国大陆，Telegram API 可能无法直接访问。请参考 [Mac 用户启动指南](MAC_SETUP.md) 使用 SSH 隧道共享 Mac 上的 Clash 代理。

### 1. Environment Setup

```bash
# Navigate to project directory
cd /root/Xiao_i_Bot

# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
# 或使用 uv (更快)
uv pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your preferred LLM provider and API keys
```

### 3. Get Telegram Bot Token

1. Open Telegram and search for @BotFather
2. Send `/newbot` to create a new bot
3. Follow prompts to set bot name and username
4. Copy the Bot Token to your `.env` file

### 4. Configure Proxy (if needed)

If your server cannot directly access Telegram API (e.g., servers in mainland China), configure a proxy in `.env`:

```env
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890
```

**Mac 用户**：请参考 [Mac 用户启动指南](MAC_SETUP.md) 使用 SSH 隧道自动共享 Clash 代理。

### 5. Run the Bot

```bash
# Run directly
python src/bot.py

# Or use the main entry point
python main.py
```

The bot will start polling for messages. Open Telegram and send `/start` to begin!

## Command Reference

| Command | Description |
|---------|-------------|
| `/start` | Start conversation with the bot |
| `/help` | Display help information |
| `/status` | View current relationship status |
| `/profile` | View your user profile as seen by the bot |
| `/memories` | View stored long-term memories |
| `/reset` | Reset conversation memory |
| `/settings` | View/settings preferences |
| `/monitor` | View system monitoring stats |
| `/logs` | Open web dashboard |
| `/xhs` | Xiaohongshu skill operations |
| `/skills` | List all available skills |

## Configuration Guide

### Required Variables

| Variable | Description | Required |
|----------|-------------|----------|
| TELEGRAM_BOT_TOKEN | Token from @BotFather | Yes |
| MODEL_PROVIDER | LLM provider (see below) | Yes |
| API_KEY | Provider-specific API key | Yes |

### Model Providers

Supported providers: `openai`, `zhipuai`, `dashscope`, `deepseek`, `minimax`, `moonshot`

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| DATABASE_URL | SQLAlchemy database URL | `sqlite:///./bot.db` |
| MAX_MEMORY_TOKENS | Maximum conversation memory tokens | 2000 |
| MEMORY_SUMMARY_TOKENS | Summary generation token limit | 500 |
| ENABLE_PROACTIVE_CHAT | Enable scheduled messages | true |
| PROACTIVE_CHAT_INTERVAL | Seconds between proactive messages | 3600 |
| PROACTIVE_CHAT_START_HOUR | Active hours start (24h) | 9 |
| PROACTIVE_CHAT_END_HOUR | Active hours end (24h) | 22 |
| MONITOR_INTERVAL | System check interval (seconds) | 5.0 |
| TRIGGER_COOLDOWN | Trigger cooldown period (seconds) | 1800 |
| CPU_THRESHOLD | CPU alert threshold (%) | 80.0 |
| IDLE_THRESHOLD | Idle detection threshold (seconds) | 600 |
| ACTIVITY_THRESHOLD | Activity detection threshold | 100 |
| HTTP_PROXY | HTTP proxy URL | - |
| HTTPS_PROXY | HTTPS proxy URL | - |
| WEB_APP_URL | Web dashboard URL | https://your-domain.com |

### Model-Specific Settings

#### OpenAI
- `OPENAI_API_KEY`
- `OPENAI_MODEL` (default: gpt-4)
- `OPENAI_BASE_URL` (for proxy)
- `OPENAI_TEMPERATURE` (default: 0.8)

#### ZhipuAI
- `ZHIPUAI_API_KEY`
- `ZHIPUAI_MODEL` (default: chatglm3-6b)

#### Dashscope
- `DASHSCOPE_API_KEY`
- `DASHSCOPE_MODEL` (default: qwen-turbo)

#### DeepSeek
- `DEEPSEEK_API_KEY`
- `DEEPSEEK_MODEL` (default: deepseek-chat)

#### MiniMax
- `MINIMAX_API_KEY`
- `MINIMAX_GROUP_ID`
- `MINIMAX_MODEL` (default: abab5.5-chat)

#### Moonshot
- `MOONSHOT_API_KEY`
- `MOONSHOT_MODEL` (default: moonshot-v1-8k)

## Relationship Stages

The bot tracks relationship development through 4 stages:

1. **Stranger** (陌生人) - Initial state
2. **Acquaintance** (熟人) - After basic interaction
3. **Friend** (朋友) - Regular conversation
4. **Partner** (恋人) - Deep emotional connection

Relationship advances based on conversation quality and interaction frequency.

## Technology Stack

- **Python 3.8+** - Runtime environment
- **python-telegram-bot** - Telegram Bot API
- **LangChain** - Memory and prompt management
- **SQLAlchemy** - Database ORM
- **APScheduler** - Async task scheduling
- **Flask** - Web dashboard server
- **psutil** - System monitoring

## Web Dashboard

The bot includes a web-based dashboard for real-time monitoring:

- View conversation logs
- Monitor system metrics
- Track bot performance

Access via `/logs` command in Telegram (production) or open `http://localhost:PORT` locally.

## Database

Uses SQLite by default. Database schema includes:

- **users** - User profiles and states
- **conversations** - Message history
- **memories** - Extracted long-term memories
- **proactive_messages** - Scheduled message logs

### UserProfile - Intelligent User Profiling

The bot features an advanced **UserProfile** system that builds a comprehensive understanding of each user:

```python
UserProfile stores:
├── name                 # Preferred nickname/calling
├── preferences          # Likes, interests, tastes
├── habits              # Daily routines and habits
├── important_dates     # Birthdays, anniversaries
├── personality_traits  # Character characteristics
├── dislikes            # Things to avoid
├── emotional_needs     # Emotional support preferences
├── shared_memories     # Special moments together
└── conversation_count  # Total interactions
```

**How it works:**
1. **Automatic Extraction**: After each conversation, LLM analyzes dialogue to extract new information
2. **Smart Deduplication**: Prevents storing redundant or similar memories
3. **Importance Scoring**: Each memory is ranked 0-1 by significance
4. **Context Awareness**: Bot uses profile data to personalize responses

**Commands:**
- `/profile` - View your complete user profile as seen by the bot
- `/memories` - List all stored memories about you

**Relationship Evolution:**
The bot adapts its personality based on relationship stage (stranger → acquaintance → friend → partner), with conversation style becoming more intimate over time.

## Performance Optimization

The codebase includes several optimizations:

- Database indexes on frequently queried columns
- Connection pooling for database efficiency
- Async/await for non-blocking operations
- Memory summarization to reduce token usage

## Security Notes

- Keep API keys confidential
- Review proxy settings for your environment
- Regularly backup the database
- Use environment variables, never commit secrets

## Development

### Project Structure

```
src/
├── bot.py              # Entry point and command handlers
├── chat_manager.py     # Chat logic and prompt templates
├── memory_manager.py  # Memory extraction and retrieval
├── model_manager.py   # Multi-provider LLM abstraction
├── database.py        # ORM models and connection pooling
├── proactive_scheduler.py  # Scheduled task management
├── system_monitor.py  # OS metrics collection
└── trigger_engine.py   # Event trigger evaluation
```

### Adding New Features

1. Extend `ModelManager` for new LLM providers
2. Add new triggers in `TriggerEngine`
3. Create new scheduler jobs in `ProactiveScheduler`
4. Add database models in `database.py`
5. Add new skills by extending `BaseSkill` in `skill_manager.py`

## Skills System

The bot includes a extensible skills system that allows integration with external services. See [Skills Guide](skills.md) for detailed information.

### Available Skills

- **xiaohongshu** - Xiaohongshu (Little Red Book) integration

### Adding New Skills

```python
from src.skill_manager import BaseSkill, SkillResult

class MyCustomSkill(BaseSkill):
    name = "my_skill"
    description = "My custom skill"
    
    async def execute(self, params: dict) -> SkillResult:
        # Your implementation
        return SkillResult(success=True, result="Done")
```

Then register it in `SkillManager`.

## Special Guides

### For Mac Users in China

If you are using a Linux server in mainland China and need to access Telegram API, please refer to the **[Mac User Startup Guide](MAC_SETUP.md)**. This guide explains how to use SSH tunneling to share your Mac's Clash proxy with the remote server.

Key features of this solution:
- One-click startup script
- Automatic SSH tunnel management
- Proxy connectivity testing
- Clean shutdown handling

## License

MIT License

---

**Made with 💕 for AI companionship**
