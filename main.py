"""
QQ AI 伴侣机器人 - 主程序入口
基于 OpenClaw + QQBot 插件
"""
import os
import sys
import subprocess
import logging
import signal
import time
from dotenv import load_dotenv

# 先加载环境变量（从 .env 文件），再配置日志
load_dotenv()

# 从 .env 文件读取 Moonshot/Kimi API Key 并设置给 OpenClaw
moonshot_api_key = os.getenv('MOONSHOT_API_KEY')
if moonshot_api_key:
    os.environ['MOONSHOT_API_KEY'] = moonshot_api_key

# 配置国内搜索引擎（百度/必应）
os.environ['OPENCLAW_SEARCH_ENGINE'] = 'bing'  # 可选: baidu, bing
os.environ['OPENCLAW_URL_FETCH_ENABLED'] = '1'

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

# 在日志中记录 API Key 加载状态
if moonshot_api_key:
    logger.info("✅ 已从 .env 文件加载 Moonshot API Key")
else:
    logger.warning("⚠️ 未找到 MOONSHOT_API_KEY，请在 .env 文件中配置")

# 全局进程引用
gateway_process = None


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
    
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("=" * 50)
    logger.info("启动 QQ AI 伴侣机器人")
    logger.info("=" * 50)
    
    # 检查 openclaw 是否安装
    try:
        result = subprocess.run(
            ['openclaw', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        logger.info(f"OpenClaw 版本: {result.stdout.strip()}")
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.error(f"OpenClaw 未安装或无法运行: {e}")
        logger.error("请先安装 OpenClaw: sudo npm install -g openclaw")
        return 1
    
    # 配置 OpenClaw 认证（从 .env 读取 API Key）
    # 支持 Moonshot 或 DeepSeek
    try:
        import json
        auth_dir = os.path.expanduser('~/.openclaw/agents/main/agent')
        os.makedirs(auth_dir, exist_ok=True)
        auth_file = os.path.join(auth_dir, 'auth-profiles.json')
        
        # 优先使用 DeepSeek（更稳定）
        deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
        if deepseek_api_key:
            auth_config = {
                "deepseek:default": {
                    "apiKey": deepseek_api_key
                }
            }
            with open(auth_file, 'w') as f:
                json.dump(auth_config, f, indent=2)
            logger.info("✅ 已配置 DeepSeek 认证")
        elif moonshot_api_key:
            auth_config = {
                "moonshot:manual": {
                    "apiKey": moonshot_api_key
                }
            }
            with open(auth_file, 'w') as f:
                json.dump(auth_config, f, indent=2)
            logger.info("✅ 已配置 Moonshot 认证")
    except Exception as e:
        logger.warning(f"配置认证文件时出错: {e}")
    
    # 设置 DNS 为公共 DNS（解决联网搜索被阻止的问题）
    try:
        # 备份原始 DNS 配置
        if os.path.exists('/etc/resolv.conf'):
            with open('/etc/resolv.conf', 'r') as f:
                original_dns = f.read()
            if '114.114.114.114' not in original_dns and '8.8.8.8' not in original_dns:
                logger.info("配置公共 DNS 服务器...")
                # 使用国内 DNS 和 Google DNS
                dns_config = """# 公共 DNS 配置
nameserver 114.114.114.114
nameserver 223.5.5.5
nameserver 8.8.8.8
"""
                with open('/tmp/resolv.conf.new', 'w') as f:
                    f.write(dns_config + original_dns)
                # 尝试替换（可能需要 sudo）
                result = subprocess.run(
                    ['sudo', 'cp', '/tmp/resolv.conf.new', '/etc/resolv.conf'],
                    capture_output=True
                )
                if result.returncode == 0:
                    logger.info("DNS 配置已更新（使用 114.114.114.114 / 223.5.5.5 / 8.8.8.8）")
    except Exception as e:
        logger.warning(f"配置 DNS 时出错: {e}")
    
    # 设置 gateway 配置
    try:
        subprocess.run(['openclaw', 'config', 'set', 'gateway.mode', 'local'], 
                      capture_output=True, check=False)
        subprocess.run(['openclaw', 'config', 'set', 'gateway.port', '8080'],
                      capture_output=True, check=False)
        logger.info("Gateway 配置已设置")
    except Exception as e:
        logger.warning(f"设置配置时出错: {e}")
    
    # 启动 OpenClaw Gateway
    logger.info("正在启动 OpenClaw Gateway...")
    try:
        gateway_process = subprocess.Popen(
            ['openclaw', 'gateway'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        logger.info(f"Gateway 进程已启动 (PID: {gateway_process.pid})")
        logger.info("QQ 机器人正在连接，请稍候...")
        logger.info("")
        logger.info("使用方法:")
        logger.info("1. 在手机 QQ 搜索: 1903758444")
        logger.info("2. 添加机器人为好友")
        logger.info("3. 开始聊天！")
        logger.info("")
        logger.info("支持的命令: /start, /help, /status, /profile, /memories, /reset")
        logger.info("联网搜索: 支持必应/Bing 搜索（如果 DNS 配置成功）")
        logger.info("=" * 50)
        
        # 实时输出日志
        while True:
            line = gateway_process.stdout.readline()
            if not line:
                break
            line = line.strip()
            if line:
                # 过滤并输出关键日志
                if any(key in line for key in [
                    'READY', 'WebSocket connected', 'Gateway ready',
                    'qqbot', 'ERROR', 'error', '成功', '失败',
                    'Dispatch event', '机器人'
                ]):
                    logger.info(line)
                # 打印到控制台让用户看到
                print(line)
                
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"运行出错: {e}", exc_info=True)
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
    exit_code = main()
    sys.exit(exit_code)
