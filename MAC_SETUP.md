# Mac 用户启动指南

本指南适用于在 **Linux 服务器** 上运行 Xiao_i_Bot，但需要通过 **Mac 本地的 Clash 代理** 访问 Telegram API 的用户。

## 原理说明

由于服务器位于中国大陆，无法直接访问 Telegram API。本方案通过 **SSH 反向隧道** 将 Mac 上的 Clash 代理共享给远程服务器使用：

```
[Linux 服务器] ←──SSH 隧道──→ [Mac 本地] ←──→ [Clash Party] ←──→ [Telegram API]
     47.97.87.209              127.0.0.1          代理端口:7890
```

## 前置要求

1. **Mac 电脑** 已安装并运行 [Clash Party](https://github.com/pompurin404/ClashParty) 或其他 Clash 客户端
2. **Linux 服务器** 已部署 Xiao_i_Bot（位于 `/root/Xiao_i_Bot`）
3. Mac 与服务器之间可通过 SSH 连接
4. 服务器公网 IP: `47.97.87.209`

## 快速开始

### 第一步：配置 SSH 免密登录（只需一次）

在 Mac 终端运行：

```bash
ssh-copy-id root@47.97.87.209
```

按提示输入服务器密码，完成后测试：

```bash
ssh root@47.97.87.209 "echo 连接成功"
```

### 第二步：创建启动脚本

在 Mac 终端运行以下命令，创建一键启动脚本：

```bash
cat > ~/Desktop/start_xiao_bot.sh << 'EOF'
#!/bin/bash

# ============================================
# Xiao_i_Bot 一键启动脚本（Mac → Linux 服务器）
# 功能：自动建立 SSH 隧道，共享 Mac 的 Clash 代理给服务器
# ============================================

# 配置变量
SERVER_IP="47.97.87.209"         # 服务器公网 IP
SERVER_USER="root"               # 服务器用户名
LOCAL_PROXY_PORT="7890"          # Mac 上 Clash 的端口
REMOTE_PROXY_PORT="7890"         # 服务器上映射的端口
BOT_DIR="/root/Xiao_i_Bot"       # 服务器上 Bot 的目录

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}      ${GREEN}🤖 Xiao_i_Bot 启动器${NC}                      ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}      通过 SSH 隧道共享 Clash 代理               ${BLUE}║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# 步骤 1: 检查 Clash 是否运行
echo -e "${YELLOW}[1/5] 📡 检查 Clash Party 代理...${NC}"
if ! lsof -i :$LOCAL_PROXY_PORT | grep -q LISTEN; then
    echo -e "${RED}❌ Clash 未在端口 $LOCAL_PROXY_PORT 运行${NC}"
    echo ""
    echo "请确认："
    echo "  1. Clash Party 已启动"
    echo "  2. 端口是 $LOCAL_PROXY_PORT（可在 Clash 设置中查看）"
    echo ""
    echo "如果端口不同，请修改本脚本的 LOCAL_PROXY_PORT 变量"
    exit 1
fi
echo -e "${GREEN}✅ Clash 代理运行正常 (端口: $LOCAL_PROXY_PORT)${NC}"
echo ""

# 步骤 2: 检查 SSH 连接
echo -e "${YELLOW}[2/5] 🔑 检查 SSH 连接...${NC}"
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes $SERVER_USER@$SERVER_IP "echo OK" 2>/dev/null | grep -q OK; then
    echo -e "${RED}❌ SSH 连接失败${NC}"
    echo ""
    echo "请确认："
    echo "  1. 服务器 IP 正确: $SERVER_IP"
    echo "  2. 已配置 SSH 免密登录"
    echo ""
    echo "配置免密登录命令："
    echo "  ssh-copy-id $SERVER_USER@$SERVER_IP"
    exit 1
fi
echo -e "${GREEN}✅ SSH 连接正常 ($SERVER_USER@$SERVER_IP)${NC}"
echo ""

# 步骤 3: 建立 SSH 隧道
echo -e "${YELLOW}[3/5] 🔄 建立 SSH 反向隧道...${NC}"
echo "      服务器:$REMOTE_PROXY_PORT → Mac:$LOCAL_PROXY_PORT"

# 先关闭可能已存在的隧道
ssh -O exit $SERVER_USER@$SERVER_IP 2>/dev/null
sleep 1

# 建立新的隧道
ssh -f -N -R $REMOTE_PROXY_PORT:127.0.0.1:$LOCAL_PROXY_PORT -o ServerAliveInterval=60 -o ServerAliveCountMax=3 $SERVER_USER@$SERVER_IP

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ SSH 隧道建立成功${NC}"
else
    echo -e "${RED}❌ SSH 隧道建立失败${NC}"
    exit 1
fi
sleep 2
echo ""

# 步骤 4: 验证代理
echo -e "${YELLOW}[4/5] 🧪 测试代理连通性...${NC}"
HTTP_CODE=$(ssh $SERVER_USER@$SERVER_IP "curl -s -o /dev/null -w '%{http_code}' --max-time 10 -x http://127.0.0.1:$REMOTE_PROXY_PORT https://api.telegram.org" 2>/dev/null)

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "301" ] || [ "$HTTP_CODE" = "302" ]; then
    echo -e "${GREEN}✅ Telegram API 可访问 (HTTP $HTTP_CODE)${NC}"
else
    echo -e "${YELLOW}⚠️ 代理测试返回 HTTP $HTTP_CODE，继续尝试启动...${NC}"
fi
echo ""

# 步骤 5: 启动 Bot
echo -e "${YELLOW}[5/5] 🤖 启动 Xiao_i_Bot...${NC}"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 使用 ssh -t 分配伪终端，支持 Ctrl+C 正常退出
ssh -t $SERVER_USER@$SERVER_IP "cd $BOT_DIR && source .venv/bin/activate && python main.py"

# Bot 停止后的清理
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}🛑 Bot 已停止，正在清理 SSH 隧道...${NC}"

# 关闭隧道
ssh -O exit $SERVER_USER@$SERVER_IP 2>/dev/null

# 备用清理：直接杀掉相关进程
PIDS=$(ps aux | grep "ssh -f -N -R $REMOTE_PROXY_PORT" | grep -v grep | awk '{print $2}')
if [ ! -z "$PIDS" ]; then
    kill $PIDS 2>/dev/null
fi

echo -e "${GREEN}✅ 清理完成${NC}"
echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}            ${GREEN}👋 感谢使用 Xiao_i_Bot${NC}              ${BLUE}║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════╝${NC}"
EOF

chmod +x ~/Desktop/start_xiao_bot.sh
```

### 第三步：启动 Bot

1. **确保 Clash Party 已启动**
   - 打开 Clash Party 应用
   - 确认系统代理已开启

2. **运行启动脚本**
   ```bash
   ~/Desktop/start_xiao_bot.sh
   ```

3. **在 Telegram 中测试**
   - 找到你的 Bot
   - 发送 `/start` 命令
   - 应该能收到回复！

4. **停止 Bot**
   - 在终端按 `Ctrl+C`
   - 脚本会自动清理 SSH 隧道

## 脚本功能说明

| 步骤 | 功能 | 说明 |
|------|------|------|
| 1️⃣ | 检查 Clash | 确认 Clash Party 在端口 7890 运行 |
| 2️⃣ | 检查 SSH | 确认可以免密登录服务器 |
| 3️⃣ | 建立隧道 | 将服务器的 7890 端口转发到 Mac 的 7890 端口 |
| 4️⃣ | 测试代理 | 验证 Telegram API 可访问 |
| 5️⃣ | 启动 Bot | 在服务器上启动 Xiao_i_Bot |

## 常见问题

### Q1: 提示 "Clash 未在端口 7890 运行"

**原因**：Clash Party 的端口可能不是 7890

**解决**：
1. 打开 Clash Party 设置，查看 HTTP 端口
2. 编辑脚本，修改 `LOCAL_PROXY_PORT` 为实际端口号：
   ```bash
   LOCAL_PROXY_PORT="你的端口号"
   ```

### Q2: 提示 "SSH 连接失败"

**原因**：未配置 SSH 免密登录

**解决**：
```bash
ssh-copy-id root@47.97.87.209
```

### Q3: Bot 启动后无响应

**原因**：SSH 隧道可能断开

**解决**：
1. 检查 Mac 与服务器之间的网络连接
2. 重新运行启动脚本
3. 检查 Clash Party 是否正常运行

### Q4: 如何修改服务器配置？

编辑脚本中的以下变量：
```bash
SERVER_IP="你的服务器IP"         # 修改服务器地址
SERVER_USER="root"               # 修改用户名
LOCAL_PROXY_PORT="7890"          # 修改 Clash 端口
BOT_DIR="/root/Xiao_i_Bot"       # 修改 Bot 目录
```

## 注意事项

1. **保持 Mac 终端开启**：关闭终端会断开 SSH 隧道，导致 Bot 无法访问 Telegram
2. **保持 Clash 运行**：Clash Party 必须在脚本运行期间保持开启
3. **网络切换时需重启**：如果 Mac 切换了 WiFi 网络，需要重新运行脚本

## 替代方案

如果 SSH 隧道方案不适合你，还可以考虑：

### 方案 A：在服务器上安装代理
在 Linux 服务器上直接安装 Clash 或 V2Ray，无需依赖 Mac。

### 方案 B：部署到海外服务器
使用 AWS、Vultr 等海外服务器，无需代理即可访问 Telegram。

### 方案 C：使用 Webhook 模式
通过 Cloudflare Tunnel 等工具，将 Bot 的 webhook 暴露到公网。

---

**提示**：本脚本专为 Mac + Linux 服务器场景设计。如有其他需求，请参考项目文档或提交 Issue。
