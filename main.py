#!/usr/bin/env python3
"""
QQ AI 伴侣机器人 - 主程序入口
基于 OpenClaw + QQBot 插件 + Mem0 记忆系统 + 小红书自动化

启动后会同时运行:
- QQ Bot Gateway (端口 8080)
- 小红书 HTTP API (端口 8082) - 用于 MacBook Chrome 远程控制
"""
import os
import sys
import subprocess
import logging
import signal
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from dotenv import load_dotenv

# 导入记忆系统
try:
    from src.memory import QQBotMemory
    MEMORY_ENABLED = True
except ImportError:
    MEMORY_ENABLED = False

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("qq_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 全局状态
gateway_process = None
memory_system = None
http_server = None
XHS_DIR = '/home/lsy/Xiao_i_Bot/XiaohongshuSkills'

# ============ 小红书 HTTP API ============

class XHSHandler(BaseHTTPRequestHandler):
    """小红书 HTTP 请求处理器"""
    
    def log_message(self, format, *args):
        logger.info(f"[XHS HTTP] {args[0]}")
    
    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
    
    def run_xhs_cmd(self, *args):
        """运行小红书 CLI 命令"""
        try:
            result = subprocess.run(
                ['python', 'scripts/cdp_publish.py', '--host', 'localhost', '--port', '9222'] + list(args),
                cwd=XHS_DIR,
                capture_output=True,
                text=True,
                timeout=60
            )
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        
        # API: 检查登录
        if path == '/api/check-login':
            result = self.run_xhs_cmd('check-login')
            self.send_json(result)
            return
        
        # API: 搜索
        if path == '/api/search':
            keyword = query.get('keyword', [''])[0]
            if not keyword:
                self.send_json({'error': 'Missing keyword'}, 400)
                return
            result = self.run_xhs_cmd('search-feeds', '--keyword', keyword)
            self.send_json(result)
            return
        
        # API: 获取首页推荐
        if path == '/api/feeds':
            result = self.run_xhs_cmd('list-feeds')
            self.send_json(result)
            return
        
        # 首页 - Web 控制台
        if path in ['/', '/index.html']:
            html = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>小红书自动化控制台</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
        h1 { color: #ff2442; }
        .section { background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .btn { 
            background: #ff2442; color: white; border: none; padding: 10px 20px; 
            border-radius: 4px; cursor: pointer; margin: 5px;
        }
        .btn:hover { background: #e02040; }
        input[type="text"] { 
            padding: 8px; width: 300px; border: 1px solid #ddd; border-radius: 4px; 
        }
        #result { 
            background: #222; color: #0f0; padding: 15px; margin-top: 20px; 
            border-radius: 4px; font-family: monospace; white-space: pre-wrap;
            max-height: 400px; overflow-y: auto; font-size: 12px;
        }
        .status-ok { color: green; }
        .status-error { color: red; }
        .info { background: #e3f2fd; padding: 10px; border-radius: 4px; margin: 10px 0; }
        code { background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }
    </style>
</head>
<body>
    <h1>📕 小红书自动化控制台</h1>
    
    <div class="info">
        <strong>使用前提：</strong><br>
        1. MacBook 上运行 Chrome: <code>--remote-debugging-port=9222</code><br>
        2. 建立 SSH 隧道: <code>ssh -R 9222:localhost:9222 lsy@192.168.0.110</code><br>
        3. 在 Chrome 中登录小红书
    </div>
    
    <div class="section">
        <h3>🔐 认证管理</h3>
        <button class="btn" onclick="apiCall('/api/check-login')">检查登录状态</button>
    </div>
    
    <div class="section">
        <h3>🔍 内容搜索</h3>
        <input type="text" id="keyword" placeholder="输入搜索关键词">
        <button class="btn" onclick="search()">搜索笔记</button>
        <button class="btn" onclick="apiCall('/api/feeds')">获取首页推荐</button>
    </div>
    
    <div class="section">
        <h3>📡 API 接口</h3>
        <ul>
            <li><code>GET /api/check-login</code> - 检查登录状态</li>
            <li><code>GET /api/search?keyword=xxx</code> - 搜索笔记</li>
            <li><code>GET /api/feeds</code> - 获取首页推荐</li>
        </ul>
    </div>
    
    <div id="result">点击按钮开始操作...</div>
    
    <script>
        async function apiCall(url) {
            document.getElementById('result').textContent = '加载中...';
            try {
                const res = await fetch(url);
                const data = await res.json();
                document.getElementById('result').textContent = JSON.stringify(data, null, 2);
            } catch (err) {
                document.getElementById('result').textContent = '错误: ' + err.message;
            }
        }
        
        function search() {
            const kw = document.getElementById('keyword').value;
            if (!kw) return alert('请输入关键词');
            apiCall('/api/search?keyword=' + encodeURIComponent(kw));
        }
    </script>
</body>
</html>'''
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode())
            return
        
        self.send_json({'error': 'Not found'}, 404)


def start_http_server(port=8082):
    """启动 HTTP 服务器"""
    try:
        server = HTTPServer(('0.0.0.0', port), XHSHandler)
        logger.info(f"🌐 小红书 HTTP 服务已启动 (端口 {port})")
        logger.info(f"   访问地址: http://localhost:{port}")
        server.serve_forever()
    except Exception as e:
        logger.error(f"HTTP 服务错误: {e}")


# ============ 主程序 ============

def init_memory():
    """初始化记忆系统"""
    global memory_system
    if MEMORY_ENABLED:
        try:
            memory_system = QQBotMemory()
            logger.info("✅ Mem0 记忆系统已启用")
            return True
        except Exception as e:
            logger.error(f"❌ 记忆系统初始化失败: {e}")
    else:
        logger.warning("⚠️ 记忆系统未启用")
    return False


def signal_handler(sig, frame):
    """处理退出信号"""
    logger.info("收到退出信号，正在停止服务...")
    if gateway_process:
        gateway_process.terminate()
        try:
            gateway_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            gateway_process.kill()
    sys.exit(0)


def main():
    """主函数"""
    global gateway_process
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("=" * 60)
    logger.info("启动 QQ AI 伴侣机器人")
    logger.info("=" * 60)
    
    # 初始化记忆系统
    init_memory()
    
    # 启动小红书 HTTP 服务（后台线程）
    http_thread = threading.Thread(target=start_http_server, args=(8082,), daemon=True)
    http_thread.start()
    
    # 检查 OpenClaw
    try:
        result = subprocess.run(['openclaw', '--version'], capture_output=True, text=True, timeout=5)
        logger.info(f"OpenClaw 版本: {result.stdout.strip()}")
    except Exception as e:
        logger.error(f"OpenClaw 未安装: {e}")
        return 1
    
    # 配置认证
    try:
        import json
        auth_dir = os.path.expanduser('~/.openclaw/agents/main/agent')
        os.makedirs(auth_dir, exist_ok=True)
        deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
        if deepseek_api_key:
            with open(os.path.join(auth_dir, 'auth-profiles.json'), 'w') as f:
                json.dump({"deepseek:default": {"apiKey": deepseek_api_key}}, f, indent=2)
            logger.info("✅ 已配置 DeepSeek 认证")
    except Exception as e:
        logger.warning(f"配置认证出错: {e}")
    
    # 配置 DNS
    try:
        if os.path.exists('/etc/resolv.conf'):
            with open('/etc/resolv.conf', 'r') as f:
                if '114.114.114.114' not in f.read():
                    subprocess.run(['sudo', 'sh', '-c', 'echo "nameserver 114.114.114.114" >> /etc/resolv.conf'], 
                                 capture_output=True)
                    logger.info("✅ DNS 配置已更新")
    except Exception as e:
        pass
    
    # 配置 Gateway
    try:
        subprocess.run(['openclaw', 'config', 'set', 'gateway.mode', 'local'], capture_output=True)
        subprocess.run(['openclaw', 'config', 'set', 'gateway.port', '8080'], capture_output=True)
        logger.info("Gateway 配置已设置")
    except Exception as e:
        logger.warning(f"Gateway 配置出错: {e}")
    
    # 启动 Gateway
    logger.info("正在启动 OpenClaw Gateway...")
    try:
        gateway_process = subprocess.Popen(
            ['openclaw', 'gateway'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        logger.info(f"Gateway 进程已启动 (PID: {gateway_process.pid})")
        logger.info("")
        logger.info("📱 使用方法:")
        logger.info("   1. 在手机 QQ 搜索: 1903758444")
        logger.info("   2. 添加机器人为好友")
        logger.info("   3. 开始聊天！")
        logger.info("")
        logger.info("🔧 支持的命令: /start, /help, /status, /memories, /reset")
        logger.info("📕 小红书控制台: http://192.168.0.110:8082")
        logger.info("=" * 60)
        
        # 实时输出日志
        while True:
            line = gateway_process.stdout.readline()
            if not line:
                break
            line = line.strip()
            if line:
                if any(k in line for k in ['READY', 'WebSocket', 'Gateway ready', 'qqbot', 'ERROR', '机器人']):
                    logger.info(line)
                print(line)
                
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"运行出错: {e}")
        return 1
    finally:
        if gateway_process:
            gateway_process.terminate()
            try:
                gateway_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                gateway_process.kill()
        logger.info("QQ 机器人已停止")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
