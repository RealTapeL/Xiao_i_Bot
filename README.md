# 微信 AI 伴侣机器人 💕

一个基于个人微信的 AI 伴侣机器人，提供智能对话、记忆管理、关系发展等功能。她会陪伴你、关心你、理解你，随着时间推移会越来越了解你。

## 功能特性

### 核心功能
- **💬 智能对话** - 基于大语言模型的自然对话，情感丰富、理解上下文
- **🧠 记忆系统** - 长期记忆存储，记住你的喜好、习惯和故事
- **👤 用户画像** - 构建完整的用户画像，包括性格、偏好、情感需求
- **💕 关系发展** - 从陌生人 → 熟人 → 朋友 → 恋人，关系逐渐深入
- **🎭 情感分析** - 实时分析你的情绪状态，提供贴心的回应

### 进阶功能
- **📱 微信原生体验** - 无缝接入微信，支持私聊和群聊
- **🔍 小红书集成** - 搜索笔记、获取推荐内容
- **💾 数据持久化** - SQLite 数据库存储，数据安全可靠

## 系统架构

```
Xiao_i_Bot/
├── src/
│   ├── __init__.py
│   ├── wechat_bot.py         # 微信机器人主程序
│   ├── chat_manager.py       # 对话管理
│   ├── memory_manager.py     # 记忆提取和检索
│   ├── model_manager.py      # LLM 提供商抽象
│   ├── database.py           # 数据库模型
│   ├── skill_manager.py      # 技能系统
│   └── web_server.py         # Web 面板（可选）
├── bot/                      # 虚拟环境目录
├── main.py                   # 程序入口
├── requirements.txt          # 依赖列表
├── .env.example              # 环境变量模板
└── README.md                 # 本文档
```

## 快速开始

### 1. 环境准备

```bash
# 克隆或进入项目目录
cd Xiao_i_Bot

# 创建虚拟环境
python -m venv bot

# 激活虚拟环境
source bot/bin/activate  # Linux/Mac
# 或
bot\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，配置你的 LLM API 密钥
```

### 3. 运行机器人

```bash
python main.py
```

首次运行会显示二维码，用微信扫码登录即可开始使用！

## 命令列表

| 命令 | 说明 |
|------|------|
| `/start` | 开始对话，显示欢迎语 |
| `/help` | 查看帮助信息 |
| `/status` | 查看当前关系状态 |
| `/profile` | 查看你的用户画像 💝 |
| `/memories` | 查看机器人记住的事 |
| `/reset` | 重置对话记忆 |
| `/xhs` | 小红书技能（搜索、获取推荐） |

## 配置指南

### 必需配置

```env
# LLM 提供商 (openai/zhipuai/dashscope/deepseek/minimax/moonshot)
MODEL_PROVIDER=deepseek

# 根据提供商配置对应的 API 密钥
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_MODEL=deepseek-chat
```

### 微信相关配置

```env
# 自动回复设置
WECHAT_AUTO_REPLY=true
WECHAT_AUTO_REPLY_KEYWORDS=       # 触发关键词，逗号分隔，留空回复所有

# 管理员设置（可选）
WECHAT_ADMIN_ID=your_wechat_id
```

### 记忆设置

```env
MAX_MEMORY_TOKENS=2000
MEMORY_SUMMARY_TOKENS=500
```

### 模型提供商支持

| 提供商 | 所需配置 |
|--------|----------|
| OpenAI | `OPENAI_API_KEY`, `OPENAI_MODEL` |
| 智谱 AI | `ZHIPUAI_API_KEY`, `ZHIPUAI_MODEL` |
| 阿里 Dashscope | `DASHSCOPE_API_KEY`, `DASHSCOPE_MODEL` |
| DeepSeek | `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL` |
| MiniMax | `MINIMAX_API_KEY`, `MINIMAX_GROUP_ID` |
| Moonshot | `MOONSHOT_API_KEY`, `MOONSHOT_MODEL` |

## 关系阶段

机器人会根据互动情况自动发展关系：

1. **陌生人** 🤝 - 初次认识
2. **熟人** 👋 - 开始熟悉
3. **朋友** 🌟 - 建立友谊
4. **恋人** 💕 - 亲密伴侣

关系越深入，对话越亲密自然。

## 用户画像系统

机器人会自动构建你的画像：

```
UserProfile 包含：
├── 称呼              # 你喜欢的称呼方式
├── 喜好              # 兴趣、口味、偏好
├── 习惯              # 日常生活规律
├── 重要日期          # 生日、纪念日
├── 性格特点          # 性格特征
├── 情感需求          # 需要的情感支持
├── 共同回忆          # 你们的特别时刻
└── 对话次数          # 互动频率
```

## 使用技巧

- **多分享** - 告诉她你的喜好、日常、故事
- **常互动** - 关系会随着对话逐渐加深
- **提问题** - 可以问她记得什么关于你的事
- **用技能** - 试试 `/xhs` 搜索小红书内容

## 注意事项

### ⚠️ 账号安全

1. **使用小号** - 建议使用不重要的微信小号运行，降低封号风险
2. **控制频率** - 避免过于频繁的自动回复
3. **内容合规** - 遵守微信使用规范

### 稳定性说明

- 基于微信网页版协议，可能偶尔掉线
- 支持热重载登录，减少扫码次数
- 如遇掉线，重新运行程序扫码即可

## 故障排查

### 查看日志

```bash
tail -f wechat_bot.log
```

### 重新登录

```bash
# 删除登录状态文件
rm itchat.pkl

# 重新运行
python main.py
```

### 重置数据

```bash
# 删除数据库（会清除所有记忆）
rm bot.db
```

## 技术栈

- **Python 3.8+** - 运行环境
- **itchat-uos** - 微信接口
- **SQLAlchemy** - 数据库 ORM
- **LangChain** - 记忆管理

## License

MIT License

---

**Made with 💕 for AI companionship**
