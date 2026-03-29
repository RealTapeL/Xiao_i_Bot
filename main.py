"""
微信机器人主程序入口
"""
import logging
from src.wechat_bot import WeChatLoveBot

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("wechat_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("启动微信 AI 伴侣机器人")
    logger.info("=" * 50)
    
    try:
        bot = WeChatLoveBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序运行出错: {e}", exc_info=True)
    finally:
        logger.info("微信机器人已停止")


if __name__ == '__main__':
    main()
