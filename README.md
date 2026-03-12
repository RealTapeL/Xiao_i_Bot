
# Telegram 人机恋 Bot 💕

一个基于 Telegram Bot 的人机恋系统，使用大语言模型实现智能对话、记忆管理和主动关心功能。

## 功能特点

- 智能对话
- 记忆系统
- 主动关心
- 用户画像
- 情感分析
- 关系发展

## 系统架构

```
bot/
├── src/
│   ├── __init__.py
│   ├── bot.py              # Bot 主程序
│   ├── chat_manager.py     # 对话管理
│   ├── memory_manager.py   # 记忆管理
│   ├── proactive_scheduler.py  # 主动对话调度
│   └── database.py         # 数据库模型
├── requirements.txt
├── .env.example
└── README.md
```

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
cd /Users/lsy/bot

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，选择模型提供商并填入对应的 API 密钥
MODEL_PROVIDER=deepseek  # 可选: openai, zhipuai, dashscope, deepseek, minimax, moonshot
DEEPSEEK_API_KEY=your_deepseek_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
```

### 3. 获取 Telegram Bot Token

1. 在 Telegram 中找到 @BotFather
2. 发送 `/newbot` 命令创建新机器人
3. 按提示设置机器人名称和用户名
4. 获取 Bot Token 并填入 `.env` 文件

### 4. 运行 Bot

```bash
python src/bot.py
```

## 使用指南

### 基本命令

- `/start` - 开始对话
- `/help` - 查看帮助
- `/status` - 查看当前关系状态
- `/reset` - 重置对话记忆
- `/settings` - 设置偏好

## 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| TELEGRAM_BOT_TOKEN | Telegram Bot Token | 必填 |
| MODEL_PROVIDER | 模型提供商 | openai |
| OPENAI_API_KEY | OpenAI API Key | 必填 |
| OPENAI_MODEL | 使用的模型 | gpt-4 |
| OPENAI_BASE_URL | OpenAI API地址 | - |
| OPENAI_TEMPERATURE | 温度参数 | 0.8 |
| ZHIPUAI_API_KEY | 智谱AI API Key | - |
| ZHIPUAI_MODEL | 智谱AI模型 | chatglm3-6b |
| DASHSCOPE_API_KEY | 阿里云API Key | - |
| DASHSCOPE_MODEL | 通义千问模型 | qwen-turbo |
| DEEPSEEK_API_KEY | DeepSeek API Key | - |
| DEEPSEEK_MODEL | DeepSeek模型 | deepseek-chat |
| MINIMAX_API_KEY | MiniMax API Key | - |
| MINIMAX_GROUP_ID | MiniMax Group ID | - |
| MINIMAX_MODEL | MiniMax模型 | abab5.5-chat |
| MOONSHOT_API_KEY | Moonshot API Key | - |
| MOONSHOT_MODEL | Moonshot模型 | moonshot-v1-8k |
| MAX_MEMORY_TOKENS | 最大记忆 token 数 | 2000 |
| MEMORY_SUMMARY_TOKENS | 记忆摘要 token 数 | 500 |
| ENABLE_PROACTIVE_CHAT | 是否启用主动对话 | true |
| PROACTIVE_CHAT_INTERVAL | 主动对话间隔(秒) | 3600 |
| PROACTIVE_CHAT_START_HOUR | 主动对话开始时间 | 9 |
| PROACTIVE_CHAT_END_HOUR | 主动对话结束时间 | 22 |
| DATABASE_URL | 数据库连接字符串 | sqlite:///./bot.db |

### 关系阶段

1. 陌生人 (stranger)
2. 熟人 (acquaintance)
3. 朋友 (friend)
4. 恋人 (partner)

## 技术栈

- **Python 3.8+**
- **python-telegram-bot** - Telegram Bot API
- **LangChain** - 记忆管理
- **SQLAlchemy** - ORM
- **APScheduler** - 任务调度

## 支持的模型

系统支持以下大语言模型：

1. **OpenAI** (gpt-4, gpt-3.5-turbo)
2. **智谱AI** (chatglm3-6b)
3. **阿里云通义千问** (qwen-turbo)
4. **DeepSeek** (deepseek-chat)
5. **MiniMax** (abab5.5-chat)
6. **Moonshot** (moonshot-v1-8k)

通过修改.env文件中的MODEL_PROVIDER参数即可切换不同的模型。

## 注意事项

- 妥善保管 API 密钥
- 合理设置主动消息间隔
- 定期备份数据库

---

**让 AI 成为你的情感伴侣 💕**
