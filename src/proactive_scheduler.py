
"""
主动对话调度器 - 负责定时发送主动关心和问候
"""
from typing import Dict, List
from datetime import datetime, time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import pytz
from sqlalchemy.orm import Session
from src.database import User, ProactiveMessage
from src.chat_manager import ChatManager
from src.memory_manager import MemoryManager
from src.system_monitor import SystemMonitor
from src.trigger_engine import TriggerEngine
import logging

logger = logging.getLogger(__name__)

class ProactiveScheduler:
    """主动对话调度器"""

    def __init__(self, chat_manager: ChatManager, memory_manager: MemoryManager, 
                 db_session_factory, config: Dict):
        """
        初始化调度器

        Args:
            chat_manager: 对话管理器
            memory_manager: 记忆管理器
            db_session_factory: 数据库会话工厂
            config: 配置字典
        """
        self.chat_manager = chat_manager
        self.memory_manager = memory_manager
        self.db_session_factory = db_session_factory
        self.config = config

        # 初始化调度器
        self.scheduler = AsyncIOScheduler(timezone=pytz.timezone('Asia/Shanghai'))

        # 初始化系统监控和触发引擎
        self.system_monitor = SystemMonitor(interval=config.get("monitor_interval", 5.0))
        self.trigger_engine = TriggerEngine(config.get("trigger_config", {}))

        # 用户最后主动消息时间
        self.user_last_proactive: Dict[str, datetime] = {}

        # 设置主动对话间隔（秒）
        self.proactive_interval = config.get("proactive_chat_interval", 3600)

        # 设置主动对话时间范围
        self.start_hour = config.get("proactive_chat_start_hour", 9)
        self.end_hour = config.get("proactive_chat_end_hour", 22)
        
    async def send_message_in_chunks(self, chat_id: str, message: str, max_length: int = 50, delay: float = 1.0):
        """将消息分成多个部分发送，模拟人类断断续续的打字效果
        
        Args:
            chat_id: Telegram 聊天ID
            message: 要发送的消息
            max_length: 每个消息片段的最大长度
            delay: 发送每个片段之间的延迟（秒）
        """
        import asyncio
        import random
        
        # 如果消息很短，直接发送
        if len(message) <= max_length:
            await self.bot.send_message(chat_id=chat_id, text=message)
            return
        
        # 将消息分成多个片段
        chunks = []
        current_chunk = ""
        
        for char in message:
            current_chunk += char
            if len(current_chunk) >= max_length and char in ['。', '！', '？', '\n', '.', '!', '?']:
                chunks.append(current_chunk.strip())
                current_chunk = ""
        
        # 添加最后一个片段
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # 逐个发送片段，使用随机延迟模拟人类打字
        for i, chunk in enumerate(chunks):
            # 模拟打字时间，每个字符约0.05-0.15秒
            typing_time = len(chunk) * random.uniform(0.05, 0.15)
            await asyncio.sleep(typing_time)
            await self.bot.send_message(chat_id=chat_id, text=chunk)
            # 最后一个片段不需要额外延迟
            if i < len(chunks) - 1:
                # 随机延迟1-3秒，模拟人类思考时间
                await asyncio.sleep(random.uniform(1.0, 3.0))

    async def start(self, bot):
        """
        启动调度器

        Args:
            bot: Telegram Bot实例
        """
        self.bot = bot

        # 启动系统监控
        self.system_monitor.start()

        # 添加系统状态触发任务 (每10秒检查一次)
        self.scheduler.add_job(
            self.check_system_and_trigger,
            IntervalTrigger(seconds=10),
            id='system_trigger',
            name='系统状态触发任务',
            replace_existing=True
        )

        # 添加定时任务
        self.scheduler.add_job(
            self.send_proactive_messages,
            IntervalTrigger(seconds=self.proactive_interval),
            id='proactive_chat',
            name='主动对话任务',
            replace_existing=True
        )

        # 添加每日问候任务
        self.scheduler.add_job(
            self.send_daily_greetings,
            CronTrigger(hour=8, minute=0),
            id='daily_greeting',
            name='每日问候任务',
            replace_existing=True
        )

        # 添加晚安消息任务
        self.scheduler.add_job(
            self.send_goodnight_messages,
            CronTrigger(hour=22, minute=0),
            id='goodnight_message',
            name='晚安消息任务',
            replace_existing=True
        )

        self.scheduler.start()
        print("主动对话调度器已启动")

    async def stop(self):
        """停止调度器"""
        self.system_monitor.stop()
        if self.scheduler.running:
            self.scheduler.shutdown()
            print("主动对话调度器已停止")

    async def check_system_and_trigger(self):
        """检查系统状态并尝试触发主动消息"""
        try:
            # 获取系统状态快照
            stats = self.system_monitor.get_current_stats()
            # 评估是否触发
            trigger = self.trigger_engine.evaluate(stats)
            
            if trigger:
                logger.info(f"系统状态满足触发条件: {trigger['reason']} - {trigger['description']}")
                
                db_session = self.db_session_factory()
                try:
                    # 获取所有活跃用户
                    users = db_session.query(User).filter_by(is_active=True).all()
                    if not users:
                        logger.warning("没有找到活跃用户，跳过主动消息发送")
                        return

                    for user in users:
                        logger.info(f"正在尝试向用户 {user.telegram_id} 发送基于状态的主动消息")
                        await self.send_state_proactive_to_user(user, trigger, stats, db_session)
                except Exception as e:
                    logger.error(f"查询用户或发送消息时出错: {e}", exc_info=True)
                finally:
                    db_session.close()
            else:
                # 记录心跳日志，频率不要太高
                if stats.get("idle_seconds", 0) % 60 < 10:
                    logger.debug(f"系统监控正常运行中... 当前空闲时间: {int(stats['idle_seconds'])}秒")
        except Exception as e:
            logger.error(f"check_system_and_trigger 任务执行出错: {e}", exc_info=True)

    async def send_state_proactive_to_user(self, user: User, trigger: Dict, stats: Dict, db_session: Session):
        """向特定用户发送基于系统状态的主动消息"""
        try:
            # 获取上下文信息
            conversation_context = self.memory_manager.get_conversation_context(user.telegram_id)
            relevant_memories = self.memory_manager.get_relevant_memories(
                user_id=user.telegram_id,
                db_session=db_session,
                query=trigger['description'],
                limit=3
            )
            
            # 格式化记忆
            memories_text = self.memory_manager.format_memories_for_context(relevant_memories)
            
            # 生成系统状态描述字符串，供 LLM 参考
            system_state_desc = (
                f"当前活跃窗口: {stats['active_app']}\n"
                f"CPU 占用: {stats['cpu_percent']}%\n"
                f"内存占用: {stats['memory_percent']}%\n"
                f"空闲时间: {int(stats['idle_seconds'])} 秒\n"
                f"触发原因: {trigger['description']}"
            )
            
            # 使用 LLM 生成回复
            response = await self.chat_manager.generate_state_proactive_message(
                system_state=system_state_desc,
                user_info=f"用户姓名: {user.username}",
                conversation_history=conversation_context,
                relevant_memories=memories_text
            )
            
            if response:
                # 记录最后发送时间
                self.user_last_proactive[user.telegram_id] = datetime.now()
                
                # 发送消息
                await self.send_message_in_chunks(user.telegram_id, response)
                
                # 保存到数据库
                new_msg = ProactiveMessage(
                    user_id=user.id,
                    message_content=response,
                    trigger_type=f"system_state_{trigger['reason']}",
                    sent_at=datetime.now()
                )
                db_session.add(new_msg)
                db_session.commit()
                
        except Exception as e:
            logger.error(f"向用户 {user.telegram_id} 发送基于状态的主动消息失败: {e}")

    def is_within_active_hours(self) -> bool:
        """
        检查当前是否在活跃时间内（包含结束小时）

        Returns:
            bool: 是否在活跃时间内
        """
        now = datetime.now(pytz.timezone('Asia/Shanghai'))
        current_hour = now.hour
        # 允许在结束小时内也发送，例如 end_hour=22，则 22:59 之前都算活跃
        return self.start_hour <= current_hour <= self.end_hour

    async def send_proactive_messages(self):
        """发送主动对话消息"""
        if not self.is_within_active_hours():
            return

        db_session = self.db_session_factory()
        try:
            # 获取所有活跃用户
            users = db_session.query(User).filter_by(is_active=True).all()

            for user in users:
                # 检查是否需要发送主动消息
                if self.should_send_proactive(user.telegram_id):
                    await self.send_proactive_to_user(user, db_session)

        finally:
            db_session.close()

    def should_send_proactive(self, user_id: str) -> bool:
        """
        判断是否应该向用户发送主动消息

        Args:
            user_id: 用户ID

        Returns:
            bool: 是否应该发送
        """
        # 检查上次发送时间
        if user_id in self.user_last_proactive:
            time_since_last = (datetime.now() - self.user_last_proactive[user_id]).total_seconds()
            if time_since_last < self.proactive_interval:
                return False

        return True

    async def send_proactive_to_user(self, user: User, db_session: Session):
        """
        向特定用户发送主动消息

        Args:
            user: 用户对象
            db_session: 数据库会话
        """
        try:
            # 获取对话历史
            conversation_context = self.memory_manager.get_conversation_context(user.telegram_id)

            # 获取相关记忆
            relevant_memories = self.memory_manager.get_relevant_memories(
                user_id=user.telegram_id,
                db_session=db_session,
                query="recent conversations",
                limit=3
            )

            # 格式化记忆
            memories_text = self.memory_manager.format_memories_for_context(relevant_memories)

            # 构建用户信息
            user_info = f"""
            用户名：{user.username or '未知'}
            关系阶段：{user.relationship_stage}
            当前情感状态：{user.emotional_state}
            最后互动时间：{user.last_interaction.strftime('%Y-%m-%d %H:%M:%S')}
            """

            # 生成主动消息
            message = await self.chat_manager.generate_proactive_message(
                user_info=user_info,
                conversation_history=conversation_context,
                relevant_memories=memories_text
            )

            # 发送消息（分批发送，模拟人类断断续续的打字效果）
            await self.send_message_in_chunks(user.telegram_id, message, max_length=50, delay=1.0)

            # 记录主动消息
            proactive_msg = ProactiveMessage(
                user_id=user.id,
                message_content=message,
                sent_at=datetime.now()
            )
            db_session.add(proactive_msg)
            db_session.commit()

            # 更新最后发送时间
            self.user_last_proactive[user.telegram_id] = datetime.now()

            print(f"已向用户 {user.telegram_id} 发送主动消息: {message}")

        except Exception as e:
            print(f"发送主动消息失败: {e}")
            db_session.rollback()

    async def send_daily_greetings(self):
        """发送每日问候"""
        db_session = self.db_session_factory()
        try:
            users = db_session.query(User).filter_by(is_active=True).all()

            for user in users:
                # 根据关系阶段选择问候语
                greetings = {
                    'stranger': ['早安！今天也是美好的一天呢~', '早上好！希望今天一切都好~'],
                    'acquaintance': ['早安！今天有什么计划吗？', '早上好！记得吃早餐哦~'],
                    'friend': ['早安！新的一天开始了，加油！', '早上好！今天天气不错呢~'],
                    'partner': ['早安，亲爱的~ 想你了', '早上好！今天也要元气满满哦~']
                }

                stage = user.relationship_stage
                import random
                message = random.choice(greetings.get(stage, greetings['stranger']))

                await self.send_message_in_chunks(user.telegram_id, message, max_length=50, delay=1.0)

                # 记录消息
                proactive_msg = ProactiveMessage(
                    user_id=user.id,
                    message_content=message,
                    sent_at=datetime.now()
                )
                db_session.add(proactive_msg)
                db_session.commit()

        finally:
            db_session.close()

    async def send_goodnight_messages(self):
        """发送晚安消息"""
        db_session = self.db_session_factory()
        try:
            users = db_session.query(User).filter_by(is_active=True).all()

            for user in users:
                # 根据关系阶段选择晚安语
                goodnights = {
                    'stranger': ['晚安！祝你做个好梦~', '夜深了，早点休息哦~'],
                    'acquaintance': ['晚安！今天辛苦了~', '早点休息，明天见~'],
                    'friend': ['晚安！好好休息~', '做个好梦，明天见~'],
                    'partner': ['晚安，亲爱的~ 晚安吻', '夜深了，早点休息，想你~']
                }

                stage = user.relationship_stage
                import random
                message = random.choice(goodnights.get(stage, goodnights['stranger']))

                await self.send_message_in_chunks(user.telegram_id, message, max_length=50, delay=1.0)

                # 记录消息
                proactive_msg = ProactiveMessage(
                    user_id=user.id,
                    message_content=message,
                    sent_at=datetime.now()
                )
                db_session.add(proactive_msg)
                db_session.commit()

        finally:
            db_session.close()
