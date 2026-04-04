# QQ AI 伴侣机器人 🤖💕

基于 OpenClaw + QQBot 插件的 AI 伴侣机器人，支持智能对话、长期记忆、小红书自动化等功能。

## 功能特性

- **💬 智能对话** - 基于 DeepSeek 大语言模型
- **🧠 长期记忆** - Mem0 记忆系统，自动记住用户喜好
- **📕 小红书自动化** - 通过 MacBook Chrome 远程控制
- **👥 多用户支持** - 每用户独立记忆空间
- **🔍 联网搜索** - 支持必应/Bing 搜索

## 系统架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  手机 QQ    │────▶│  OpenClaw   │────▶│  DeepSeek   │
└─────────────┘     │  Gateway    │     │   AI 模型   │
                    └─────────────┘     └─────────────┘
                           │
                    ┌─────────────┐
                    │   Mem0 记忆  │
                    │  (SQLite)   │
                    └─────────────┘

┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  MacBook    │◀───▶│   SSH 隧道   │◀───▶│  树莓派     │
│   Chrome    │     │  (端口转发)  │     │  HTTP API   │
└─────────────┘     └─────────────┘     └─────────────┘
      │                                          │
      └────────────── 小红书网站 ◀────────────────┘
```

## 快速开始

### 1. 环境要求

- 树莓派/服务器（Debian/Ubuntu）
- Python 3.11+
- MacBook（用于运行 Chrome）
- Node.js 18+ (OpenClaw)

### 2. 安装

```bash
# 克隆项目
git clone https://github.com/RealTapeL/Xiao_i_Bot.git
cd Xiao_i_Bot

# 安装依赖
uv pip install -r requirements.txt

# 安装 OpenClaw
sudo npm install -g openclaw
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，添加 DEEPSEEK_API_KEY
```

### 4. 启动服务

```bash
# 一键启动（QQ Bot + 小红书 HTTP API）
uv run main.py
```

启动后会显示：
- QQ Bot Gateway: `ws://localhost:8080`
- 小红书控制台: `http://192.168.0.110:8082`

## 小红书自动化配置

### MacBook 端设置

**1. 启动 Chrome（开启远程调试）**

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
    --remote-debugging-port=9222 \
    --user-data-dir=/tmp/xiaohongshu-chrome \
    --no-first-run
```

**2. 建立 SSH 反向隧道**

```bash
ssh -R 9222:localhost:9222 lsy@192.168.0.110
```

**3. 登录小红书**

- 在 Chrome 中访问 https://www.xiaohongshu.com
- 用手机 APP 扫码登录

### 使用小红书功能

**Web 控制台**
- 访问 `http://树莓派IP:8082`
- 点击按钮搜索笔记、查看登录状态

**API 调用**
```bash
# 检查登录
curl http://localhost:8082/api/check-login

# 搜索笔记
curl "http://localhost:8082/api/search?keyword=旅行"

# 获取首页推荐
curl http://localhost:8082/api/feeds
```

## 端口说明

| 服务 | 端口 | 用途 |
|------|------|------|
| QQ Bot Gateway | 8080 | QQ 机器人连接 |
| 小红书 HTTP API | 8082 | Web 控制台和 API |
| MacBook Chrome | 9222 | CDP 远程调试 |

## 文件结构

```
Xiao_i_Bot/
├── main.py              # 主程序（QQ Bot + HTTP 服务）
├── manage_memory.py     # 记忆管理 CLI
├── src/
│   └── memory.py        # Mem0 记忆系统
├── XiaohongshuSkills/   # 小红书自动化技能
├── data/
│   └── memories.db      # SQLite 记忆数据库
├── .env                 # 环境变量
└── README.md
```

## 常用命令

```bash
# 启动机器人
uv run main.py

# 查看记忆状态
python manage_memory.py status

# 测试小红书 API
curl http://localhost:8082/api/check-login
```

## 故障排查

### 端口被占用
```bash
# 停止现有 Gateway
openclaw gateway stop

# 强制释放端口
lsof -i :8080 | grep LISTEN | awk '{print $2}' | xargs kill
```

### SSH 隧道断开
```bash
# 重新建立隧道
ssh -R 9222:localhost:9222 lsy@192.168.0.110
```

### Chrome 未连接
- 确保 MacBook Chrome 已启动 `--remote-debugging-port=9222`
- 确保 SSH 隧道已建立
- 在 MacBook 上测试: `curl http://localhost:9222/json`

## License

MIT License

---

**Made with 🤖 for AI companionship**
