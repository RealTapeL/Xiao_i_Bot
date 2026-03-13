
"""
Proactive Chat Scheduler - Sends scheduled proactive care messages
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

    def __init__(self, chat_manager: ChatManager, memory_manager: MemoryManager, 
                 db_session_factory, config: Dict):
        self.chat_manager = chat_manager
        self.memory_manager = memory_manager
        self.db_session_factory = db_session_factory
        self.config = config

        self.scheduler = AsyncIOScheduler(timezone=pytz.timezone('Asia/Shanghai'))

        self.system_monitor = SystemMonitor(interval=config.get("monitor_interval", 5.0))
        self.trigger_engine = TriggerEngine(config.get("trigger_config", {}))

        self.user_last_proactive: Dict[str, datetime] = {}

        self.proactive_interval = config.get("proactive_chat_interval", 3600)

        self.start_hour = config.get("proactive_chat_start_hour", 9)
        self.end_hour = config.get("proactive_chat_end_hour", 22)
        
    async def send_message_in_chunks(self, chat_id: str, message: str, max_length: int = 50, delay: float = 1.0):
        import asyncio
        import random
        
        if len(message) <= max_length:
            await self.bot.send_message(chat_id=chat_id, text=message)
            return
        
        chunks = []
        current_chunk = ""
        
        for char in message:
            current_chunk += char
            if len(current_chunk) >= max_length and char in ['。', '！', '？', '\n', '.', '!', '?']:
                chunks.append(current_chunk.strip())
                current_chunk = ""
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        for i, chunk in enumerate(chunks):
            typing_time = len(chunk) * random.uniform(0.05, 0.15)
            await asyncio.sleep(typing_time)
            await self.bot.send_message(chat_id=chat_id, text=chunk)
            if i < len(chunks) - 1:
                await asyncio.sleep(random.uniform(1.0, 3.0))

    async def start(self, bot):
        self.bot = bot

        self.system_monitor.start()

        self.scheduler.add_job(
            self.check_system_and_trigger,
            IntervalTrigger(seconds=10),
            id='system_trigger',
            name='System State Trigger',
            replace_existing=True
        )

        self.scheduler.add_job(
            self.send_proactive_messages,
            IntervalTrigger(seconds=self.proactive_interval),
            id='proactive_chat',
            name='Proactive Chat Task',
            replace_existing=True
        )

        self.scheduler.add_job(
            self.send_daily_greetings,
            CronTrigger(hour=8, minute=0),
            id='daily_greeting',
            name='Daily Greeting Task',
            replace_existing=True
        )

        self.scheduler.add_job(
            self.send_goodnight_messages,
            CronTrigger(hour=22, minute=0),
            id='goodnight_message',
            name='Goodnight Message Task',
            replace_existing=True
        )

        self.scheduler.start()
        print("Proactive scheduler started")

    async def stop(self):
        self.system_monitor.stop()
        if self.scheduler.running:
            self.scheduler.shutdown()
            print("Proactive scheduler stopped")

    async def check_system_and_trigger(self):
        try:
            stats = self.system_monitor.get_current_stats()
            trigger = self.trigger_engine.evaluate(stats)
            
            if trigger:
                logger.info(f"Trigger condition met: {trigger['reason']} - {trigger['description']}")
                
                db_session = self.db_session_factory()
                try:
                    users = db_session.query(User).filter_by(is_active=True).all()
                    if not users:
                        logger.warning("No active users found")
                        return

                    for user in users:
                        logger.info(f"Sending state-based message to user {user.telegram_id}")
                        await self.send_state_proactive_to_user(user, trigger, stats, db_session)
                except Exception as e:
                    logger.error(f"Error sending message: {e}", exc_info=True)
                finally:
                    db_session.close()
            else:
                if stats.get("idle_seconds", 0) % 60 < 10:
                    logger.debug(f"System monitor running... idle: {int(stats['idle_seconds'])}s")
        except Exception as e:
            logger.error(f"check_system_and_trigger error: {e}", exc_info=True)

    async def send_state_proactive_to_user(self, user: User, trigger: Dict, stats: Dict, db_session: Session):
        try:
            conversation_context = self.memory_manager.get_conversation_context(user.telegram_id)
            relevant_memories = self.memory_manager.get_relevant_memories(
                user_id=user.telegram_id,
                db_session=db_session,
                query=trigger['description'],
                limit=3
            )
            
            memories_text = self.memory_manager.format_memories_for_context(relevant_memories)
            
            system_state_desc = (
                f"Active window: {stats['active_app']}\n"
                f"CPU: {stats['cpu_percent']}%\n"
                f"Memory: {stats['memory_percent']}%\n"
                f"Idle time: {int(stats['idle_seconds'])}s\n"
                f"Trigger: {trigger['description']}"
            )
            
            response = await self.chat_manager.generate_state_proactive_message(
                system_state=system_state_desc,
                user_info=f"User: {user.username}",
                conversation_history=conversation_context,
                relevant_memories=memories_text
            )
            
            if response:
                self.user_last_proactive[user.telegram_id] = datetime.now()
                
                await self.send_message_in_chunks(user.telegram_id, response)
                
                new_msg = ProactiveMessage(
                    user_id=user.id,
                    message_content=response,
                    trigger_type=f"system_state_{trigger['reason']}",
                    sent_at=datetime.now()
                )
                db_session.add(new_msg)
                db_session.commit()
                
        except Exception as e:
            logger.error(f"Failed to send state-based message to {user.telegram_id}: {e}")

    def is_within_active_hours(self) -> bool:
        now = datetime.now(pytz.timezone('Asia/Shanghai'))
        current_hour = now.hour
        return self.start_hour <= current_hour <= self.end_hour

    async def send_proactive_messages(self):
        if not self.is_within_active_hours():
            return

        db_session = self.db_session_factory()
        try:
            users = db_session.query(User).filter_by(is_active=True).all()

            for user in users:
                if self.should_send_proactive(user.telegram_id):
                    await self.send_proactive_to_user(user, db_session)

        finally:
            db_session.close()

    def should_send_proactive(self, user_id: str) -> bool:
        if user_id in self.user_last_proactive:
            time_since_last = (datetime.now() - self.user_last_proactive[user_id]).total_seconds()
            if time_since_last < self.proactive_interval:
                return False

        return True

    async def send_proactive_to_user(self, user: User, db_session: Session):
        try:
            conversation_context = self.memory_manager.get_conversation_context(user.telegram_id)

            relevant_memories = self.memory_manager.get_relevant_memories(
                user_id=user.telegram_id,
                db_session=db_session,
                query="recent conversations",
                limit=3
            )

            memories_text = self.memory_manager.format_memories_for_context(relevant_memories)

            user_info = f"""
            Username: {user.username or 'unknown'}
            Relationship: {user.relationship_stage}
            Emotional state: {user.emotional_state}
            Last interaction: {user.last_interaction.strftime('%Y-%m-%d %H:%M:%S')}
            """

            message = await self.chat_manager.generate_proactive_message(
                user_info=user_info,
                conversation_history=conversation_context,
                relevant_memories=memories_text
            )

            await self.send_message_in_chunks(user.telegram_id, message, max_length=50, delay=1.0)

            proactive_msg = ProactiveMessage(
                user_id=user.id,
                message_content=message,
                sent_at=datetime.now()
            )
            db_session.add(proactive_msg)
            db_session.commit()

            self.user_last_proactive[user.telegram_id] = datetime.now()

            print(f"Sent proactive message to {user.telegram_id}: {message}")

        except Exception as e:
            print(f"Failed to send proactive message: {e}")
            db_session.rollback()

    async def send_daily_greetings(self):
        db_session = self.db_session_factory()
        try:
            users = db_session.query(User).filter_by(is_active=True).all()

            for user in users:
                greetings = {
                    'stranger': ['Good morning! Have a nice day~', 'Morning! Hope everything goes well~'],
                    'acquaintance': ['Good morning! Any plans today?', 'Morning! Remember to eat breakfast~'],
                    'friend': ['Good morning! New day, stay positive!', 'Morning! Nice weather today~'],
                    'partner': ['Morning darling~ Miss you', 'Morning! Stay energetic today~']
                }

                stage = user.relationship_stage
                import random
                message = random.choice(greetings.get(stage, greetings['stranger']))

                await self.send_message_in_chunks(user.telegram_id, message, max_length=50, delay=1.0)

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
        db_session = self.db_session_factory()
        try:
            users = db_session.query(User).filter_by(is_active=True).all()

            for user in users:
                goodnights = {
                    'stranger': ['Good night! Sweet dreams~', 'Late night, rest early~'],
                    'acquaintance': ['Good night! Hard work today~', 'Rest early, see you tomorrow~'],
                    'friend': ['Good night! Rest well~', 'Sweet dreams, see you tomorrow~'],
                    'partner': ['Good night darling~ Goodnight kiss', 'Late night, rest early, miss you~']
                }

                stage = user.relationship_stage
                import random
                message = random.choice(goodnights.get(stage, goodnights['stranger']))

                await self.send_message_in_chunks(user.telegram_id, message, max_length=50, delay=1.0)

                proactive_msg = ProactiveMessage(
                    user_id=user.id,
                    message_content=message,
                    sent_at=datetime.now()
                )
                db_session.add(proactive_msg)
                db_session.commit()

        finally:
            db_session.close()
