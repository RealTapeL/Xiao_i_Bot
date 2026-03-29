# 微信 AI 伴侣机器人 💕

基于微信官方 ClawBot（龙虾）插件的 AI 伴侣机器人。通过 HTTP 接口与微信对接，提供智能对话、记忆管理、关系发展等功能。

## 功能特性

- **💬 智能对话** - 基于大语言模型的自然对话，情感丰富、理解上下文
- **🧠 记忆系统** - 长期记忆存储，记住你的喜好、习惯和故事
- **👤 用户画像** - 构建完整的用户画像，包括性格、偏好、情感需求
- **💕 关系发展** - 从陌生人 → 熟人 → 朋友 → 恋人，关系逐渐深入
- **🎭 情感分析** - 实时分析你的情绪状态，提供贴心的回应

## 系统架构

```
微信客户端 ←→ ClawBot 插件 ←→ 你的 HTTP 服务 (本机器人)
                                      ↓
                                AI 对话处理
```

## 快速开始

### 1. 准备工作

#### 环境要求
- Python 3.8+
- 云服务器（需要有公网 IP）
- 微信 8.0.70+ 版本

#### 开放端口
确保服务器防火墙开放端口（默认 8080）：
```bash
# 如果是云服务器，在安全组中放行 8080 端口
# 服务器防火墙
sudo ufw allow 8080
```

### 2. 安装部署

```bash
# 克隆项目
git clone https://github.com/RealTapeL/Xiao_i_Bot.git
cd Xiao_i_Bot

# 创建虚拟环境
python -m venv bot
source bot/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，配置你的 LLM API 密钥
```

`.env` 文件示例：
```env
# LLM 配置
MODEL_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_MODEL=deepseek-chat

# 数据库
DATABASE_URL=sqlite:///./bot.db

# 记忆配置
MAX_MEMORY_TOKENS=2000
MEMORY_SUMMARY_TOKENS=500
```

### 4. 启动服务

```bash
python main.py
```

服务启动后会监听 `http://0.0.0.0:8080`

### 5. 配置 ClawBot 插件

#### 安装 ClawBot 插件

1. 更新微信到 8.0.70+ 版本
2. 打开微信 → 我 → 设置 → 插件
3. 找到「微信 ClawBot」，点击安装

#### 连接你的机器人

执行安装命令（在服务器或本地有 Node.js 的环境）：

```bash
npx -y @tencent-weixin/openclaw-weixin-cli@latest install \
  --gateway-url http://你的服务器IP:8080 \
  --gateway-type http
```

按照提示扫码登录即可。

### 6. 测试

给你的微信发送消息，机器人就会回复了！

## 命令列表

| 命令 | 说明 |
|------|------|
| `/start` | 开始对话，显示欢迎语 |
| `/help` | 查看帮助信息 |
| `/status` | 查看当前关系状态 |
| `/profile` | 查看你的用户画像 💝 |
| `/memories` | 查看机器人记住的事 |
| `/reset` | 重置对话记忆 |

## 支持的 AI 模型

| 提供商 | 环境变量 |
|--------|----------|
| OpenAI | `OPENAI_API_KEY` |
| 智谱 AI | `ZHIPUAI_API_KEY` |
| 阿里 Dashscope | `DASHSCOPE_API_KEY` |
| DeepSeek | `DEEPSEEK_API_KEY` |
| MiniMax | `MINIMAX_API_KEY`, `MINIMAX_GROUP_ID` |
| Moonshot | `MOONSHOT_API_KEY` |

## 关系阶段

机器人会根据互动情况自动发展关系：

1. **陌生人** 🤝 - 初次认识
2. **熟人** 👋 - 开始熟悉
3. **朋友** 🌟 - 建立友谊
4. **恋人** 💕 - 亲密伴侣

## 常用操作

### 查看日志
```bash
tail -f clawbot.log
```

### 后台运行
```bash
# 使用 nohup
nohup python main.py > output.log 2>&1 &

# 或使用 systemd（推荐生产环境）
```

### 重启服务
```bash
# 查找进程并杀死
ps aux | grep main.py
kill -9 <进程ID>

# 重新启动
python main.py
```

### 更新代码
```bash
git pull
pip install -r requirements.txt
# 重启服务
```

## 安全建议

1. **使用小号** - 建议使用不重要的微信小号运行，降低封号风险
2. **配置防火墙** - 只开放必要的端口
3. **使用 HTTPS** - 生产环境建议使用 HTTPS（配合 Nginx 反向代理）
4. **定期备份** - 定期备份数据库文件

## HTTPS 配置（可选）

如果你有域名，建议配置 HTTPS：

```nginx
# Nginx 配置示例
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

然后 ClawBot 连接时使用 `https://your-domain.com`

## 故障排查

### 服务启动失败
```bash
# 检查端口是否被占用
lsof -i :8080

# 检查日志
cat clawbot.log
```

### 微信收不到回复
1. 检查服务是否正常运行
2. 检查服务器防火墙/安全组
3. 检查日志是否有消息到达
4. 重新执行 ClawBot 连接命令

### 重新连接
```bash
# 断开现有连接
npx -y @tencent-weixin/openclaw-weixin-cli@latest logout

# 重新连接
npx -y @tencent-weixin/openclaw-weixin-cli@latest install \
  --gateway-url http://你的服务器IP:8080 \
  --gateway-type http
```

## 技术栈

- **Python 3.8+** - 运行环境
- **FastAPI** - HTTP 服务框架
- **Uvicorn** - ASGI 服务器
- **SQLAlchemy** - 数据库 ORM
- **LangChain** - 记忆管理

## License

MIT License

---

**Made with 💕 for AI companionship**
