"""
主程序入口
"""
import asyncio
import logging
from src.bot import TelegramLoveBot
from src.web_server import WebServer
from telegram.ext import Application

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def run_bot_and_server():
    """并发运行 Bot 和 Web Server"""
    # 1. 初始化组件
    bot = TelegramLoveBot()
    application = bot.run()
    web_server = WebServer(port=8080)
    
    # 2. 启动 Web Server
    # 注意：web_server.start() 是异步的，我们需要保存引用以防被 GC
    await web_server.start()
    
    # 3. 启动 Bot
    # 使用 application.run_polling() 来管理整个生命周期和信号处理
    # 但由于 web_server 已经在后台运行（aiohttp 的 start() 启动了 server），
    # 我们只需要让 run_polling 阻塞主线程即可。
    # 
    # 但是，run_polling 会创建新的 loop 如果没有当前 loop，或者使用现有的。
    # 这里我们已经在 async 函数中，说明已有 loop。
    
    logger.info("Starting Bot Polling...")
    
    # 使用 updater.start_polling() 非阻塞启动
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    logger.info("Bot and Web Server are running!")
    
    # 保持运行直到被中断
    stop_signal = asyncio.Event()
    try:
        await stop_signal.wait()
    except asyncio.CancelledError:
        pass
    finally:
        logger.info("Stopping services...")
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

def main():
    """主函数"""
    try:
        asyncio.run(run_bot_and_server())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Application stopped by user.")

if __name__ == '__main__':
    main()
