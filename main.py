"""
主程序入口 - ClawBot 版本
启动 HTTP 服务，接收微信 ClawBot 插件的消息
"""
import logging
from src.clawbot_server import ClawBotServer

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("clawbot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("启动微信 AI 伴侣机器人 - ClawBot 版本")
    logger.info("=" * 50)
    
    try:
        # 创建并启动 ClawBot HTTP 服务
        server = ClawBotServer(host="0.0.0.0", port=8080)
        server.run()
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序运行出错: {e}", exc_info=True)
    finally:
        logger.info("微信机器人已停止")


if __name__ == '__main__':
    main()
