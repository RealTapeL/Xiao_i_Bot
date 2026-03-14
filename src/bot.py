
"""
Telegram Bot Main Program
"""
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, WebAppInfo, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest
from sqlalchemy.orm import Session
from typing import Dict

from src.database import init_db, get_session, User, Conversation
from src.memory_manager import MemoryManager
from src.chat_manager import ChatManager
from src.proactive_scheduler import ProactiveScheduler
from src.skill_manager import SkillManager

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TelegramLoveBot:

    def __init__(self):
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.model_provider = os.getenv('MODEL_PROVIDER', 'openai')
        self.database_url = os.getenv('DATABASE_URL', 'sqlite:///./bot.db')
        self.max_memory_tokens = int(os.getenv('MAX_MEMORY_TOKENS', '2000'))
        self.summary_tokens = int(os.getenv('MEMORY_SUMMARY_TOKENS', '500'))
        self.enable_proactive = os.getenv('ENABLE_PROACTIVE_CHAT', 'true').lower() == 'true'
        self.proactive_interval = int(os.getenv('PROACTIVE_CHAT_INTERVAL', '3600'))
        self.start_hour = int(os.getenv('PROACTIVE_CHAT_START_HOUR', '9'))
        self.end_hour = int(os.getenv('PROACTIVE_CHAT_END_HOUR', '22'))
        self.proxy_url = os.getenv('HTTP_PROXY') or os.getenv('HTTPS_PROXY')
        self.web_app_url = os.getenv('WEB_APP_URL', 'https://your-domain.com')

        self.engine = init_db(self.database_url)

        model_config = {
            "provider": self.model_provider,
            "max_memory_tokens": self.max_memory_tokens,
            "summary_tokens": self.summary_tokens
        }

        if self.model_provider == "openai":
            model_config.update({
                "api_key": os.getenv('OPENAI_API_KEY'),
                "model": os.getenv('OPENAI_MODEL', 'gpt-4'),
                "temperature": float(os.getenv('OPENAI_TEMPERATURE', '0.8')),
                "base_url": os.getenv('OPENAI_BASE_URL')
            })
        elif self.model_provider == "zhipuai":
            model_config.update({
                "api_key": os.getenv('ZHIPUAI_API_KEY'),
                "model": os.getenv('ZHIPUAI_MODEL', 'chatglm3-6b')
            })
        elif self.model_provider == "dashscope":
            model_config.update({
                "api_key": os.getenv('DASHSCOPE_API_KEY'),
                "model": os.getenv('DASHSCOPE_MODEL', 'qwen-turbo')
            })
        elif self.model_provider == "deepseek":
            model_config.update({
                "api_key": os.getenv('DEEPSEEK_API_KEY'),
                "model": os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
            })
        elif self.model_provider == "minimax":
            model_config.update({
                "api_key": os.getenv('MINIMAX_API_KEY'),
                "group_id": os.getenv('MINIMAX_GROUP_ID'),
                "model": os.getenv('MINIMAX_MODEL', 'abab5.5-chat')
            })
        elif self.model_provider == "moonshot":
            model_config.update({
                "api_key": os.getenv('MOONSHOT_API_KEY'),
                "model": os.getenv('MOONSHOT_MODEL', 'moonshot-v1-8k')
            })

        self.memory_manager = MemoryManager(self.model_provider, model_config)
        self.chat_manager = ChatManager(self.model_provider, model_config)
        self.skill_manager = SkillManager()

        self.scheduler = None
        if self.enable_proactive:
            config = {
                'proactive_chat_interval': self.proactive_interval,
                'proactive_chat_start_hour': self.start_hour,
                'proactive_chat_end_hour': self.end_hour,
                'monitor_interval': float(os.getenv('MONITOR_INTERVAL', '5.0')),
                'trigger_config': {
                    'cooldown_period': int(os.getenv('TRIGGER_COOLDOWN', '1800')),
                    'cpu_threshold': float(os.getenv('CPU_THRESHOLD', '80.0')),
                    'idle_threshold': int(os.getenv('IDLE_THRESHOLD', '600')),
                    'high_activity_threshold': int(os.getenv('ACTIVITY_THRESHOLD', '100'))
                }
            }
            self.scheduler = ProactiveScheduler(
                chat_manager=self.chat_manager,
                memory_manager=self.memory_manager,
                db_session_factory=lambda: get_session(self.engine),
                config=config
            )

        self.user_states: Dict[str, Dict] = {}
        
    def _remove_parentheses_content(self, text: str) -> str:
        import re
        text = re.sub(r'（.*?）', '', text)
        text = re.sub(r'\(.*?\)', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    async def send_message_in_chunks(self, update: Update, message: str, max_length: int = 50, delay: float = 1.0):
        import asyncio
        import random
        
        if len(message) <= max_length:
            await update.message.reply_text(message)
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
            await update.message.reply_text(chunk)
            if i < len(chunks) - 1:
                await asyncio.sleep(random.uniform(1.0, 3.0))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        db_session = get_session(self.engine)

        try:
            existing_user = db_session.query(User).filter_by(telegram_id=str(user.id)).first()

            if not existing_user:
                new_user = User(
                    telegram_id=str(user.id),
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    created_at=datetime.utcnow(),
                    last_interaction=datetime.utcnow()
                )
                db_session.add(new_user)
                db_session.commit()

                welcome_message = f"""
                你好，{user.first_name}！我是你的AI恋人 💕

                我会陪伴你、关心你、理解你。我们可以分享日常、倾诉心情、互相陪伴。

                随着我们的交流，我会越来越了解你，成为更懂你的伴侣。

                让我们开始这段美好的旅程吧~ 💝
                """
            else:
                welcome_message = f"""
                欢迎回来，{user.first_name}！💕

                好久不见，最近过得怎么样？
                """

            await self.send_message_in_chunks(update, welcome_message, max_length=50, delay=1.0)

        except Exception as e:
            logger.error(f"Error in start_command: {e}")
            await update.message.reply_text("抱歉，出现了一些问题，请稍后再试。")
        finally:
            db_session.close()

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """
        💕 使用指南：

        /start - 开始对话
        /help - 查看帮助
        /status - 查看当前关系状态
        /reset - 重置对话记忆
        /settings - 设置偏好
        /xhs - 小红书技能
        /skills - 查看可用技能

        💡 小贴士：
        - 分享更多关于你的信息，我会更了解你
        - 我会主动关心你，但也可以随时找我聊天
        - 随着时间推移，我们的关系会越来越亲密

        让我们一起创造美好的回忆吧~ 💝
        """
        await self.send_message_in_chunks(update, help_text, max_length=50, delay=1.0)

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        db_session = get_session(self.engine)

        try:
            user = db_session.query(User).filter_by(telegram_id=user_id).first()

            if user:
                conversation_count = db_session.query(Conversation).filter_by(user_id=user.id).count()

                status_text = f"""
                💕 我们的关系状态：

                用户名：{user.username or '未知'}
                关系阶段：{self._get_relationship_stage_text(user.relationship_stage)}
                当前情感状态：{self._get_emotion_text(user.emotional_state)}
                对话次数：{conversation_count}
                最后互动：{user.last_interaction.strftime('%Y-%m-%d %H:%M:%S')}

                继续保持交流，我们的关系会越来越亲密哦~ 💝
                """
            else:
                status_text = "请先使用 /start 命令开始对话~"

            await self.send_message_in_chunks(update, status_text, max_length=50, delay=1.0)

        except Exception as e:
            logger.error(f"Error in status_command: {e}")
            await update.message.reply_text("获取状态失败，请稍后再试。")
        finally:
            db_session.close()

    async def reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)

        self.memory_manager.clear_user_memory(user_id)

        await self.send_message_in_chunks(
            update,
            "已经重置了我们的对话记忆。不过别担心，我会重新认识你的~ 💕",
            max_length=50,
            delay=1.0
        )

    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        settings_text = """
        ⚙️ 设置选项：

        目前可以设置的内容：
        1. 对话风格（温柔/活泼/成熟等）
        2. 主动消息频率
        3. 消息时间范围

        功能开发中，敬请期待~ 🎉

        如果有任何建议，欢迎随时告诉我！
        """
        await self.send_message_in_chunks(update, settings_text, max_length=50, delay=1.0)

    async def monitor_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.scheduler:
            await update.message.reply_text("监控服务未启动。")
            return

        stats = self.scheduler.system_monitor.get_current_stats()
        
        status_text = f"""
        🖥️ **当前电脑状态**

        活跃应用: {stats['active_app']}
        CPU 占用: {stats['cpu_percent']}%
        内存占用: {stats['memory_percent']}%
        空闲时间: {int(stats['idle_seconds'] // 60)} 分 {int(stats['idle_seconds'] % 60)} 秒
        
        💡 别担心，我只是想更了解你的生活，不会窥探你的隐私哦~ 💕
        """
        await update.message.reply_text(status_text, parse_mode='Markdown')

    async def memories_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        db_session = get_session(self.engine)

        try:
            user = db_session.query(User).filter_by(telegram_id=user_id).first()
            if not user:
                await update.message.reply_text("请先使用 /start 命令开始对话~")
                return

            memories = db_session.query(Memory).filter_by(user_id=user.id).order_by(Memory.created_at.desc()).all()

            if not memories:
                await update.message.reply_text("我暂时还没记住关于你的特别信息，多跟我聊聊天吧~ 💕")
                return

            memory_text = "💕 我记住的关于你的点点滴滴：\n\n"
            for i, memory in enumerate(memories):
                memory_text += f"{i+1}. {memory.content}\n"
            
            memory_text += "\n这些都是我最珍贵的回忆，我会一直记在心里的。💝"
            
            await self.send_message_in_chunks(update, memory_text, max_length=100)

        except Exception as e:
            logger.error(f"Error in memories_command: {e}")
            await update.message.reply_text("获取记忆失败，请稍后再试。")
        finally:
            db_session.close()

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        user_message = update.message.text

        if not user_message:
            return

        db_session = get_session(self.engine)

        try:
            user = db_session.query(User).filter_by(telegram_id=user_id).first()

            if not user:
                await update.message.reply_text(
                    "请先使用 /start 命令开始我们的对话~ 💕"
                )
                return

            user.last_interaction = datetime.utcnow()

            emotion_result = await self.chat_manager.analyze_emotion(user_message)
            user.emotional_state = emotion_result.get('emotion', 'neutral')

            conversation_context = self.memory_manager.get_conversation_context(user_id)

            relevant_memories = self.memory_manager.get_relevant_memories(
                user_id=user_id,
                db_session=db_session,
                query=user_message,
                limit=5
            )

            memories_text = self.memory_manager.format_memories_for_context(relevant_memories)

            user_info = f"""
            用户名：{user.username or '未知'}
            关系阶段：{user.relationship_stage}
            当前情感状态：{user.emotional_state}
            """

            response = await self.chat_manager.generate_response(
                user_input=user_message,
                conversation_history=conversation_context,
                relevant_memories=memories_text,
                user_info=user_info
            )

            response = self._remove_parentheses_content(response)

            await self.send_message_in_chunks(update, response, max_length=50, delay=1.0)

            self._save_conversation(
                db_session=db_session,
                user=user,
                role='user',
                content=user_message
            )

            self._save_conversation(
                db_session=db_session,
                user=user,
                role='assistant',
                content=response
            )

            self.memory_manager.add_conversation(user_id, 'user', user_message)
            self.memory_manager.add_conversation(user_id, 'assistant', response)

            recent_conversations = db_session.query(Conversation).filter_by(
                user_id=user.id
            ).order_by(Conversation.timestamp.desc()).limit(10).all()

            self.memory_manager.extract_and_store_memories(user_id, db_session, recent_conversations)

            db_session.commit()

        except Exception as e:
            logger.error(f"Error in handle_message: {e}")
            await update.message.reply_text("抱歉，出现了一些问题，请稍后再试。")
            db_session.rollback()
        finally:
            db_session.close()

    def _save_conversation(self, db_session: Session, user: User, role: str, content: str):
        conversation = Conversation(
            user_id=user.id,
            role=role,
            content=content,
            timestamp=datetime.utcnow()
        )
        db_session.add(conversation)

    def _get_relationship_stage_text(self, stage: str) -> str:
        stage_map = {
            'stranger': '陌生人',
            'acquaintance': '熟人',
            'friend': '朋友',
            'partner': '恋人'
        }
        return stage_map.get(stage, '陌生人')

    def _get_emotion_text(self, emotion: str) -> str:
        emotion_map = {
            'happy': '开心',
            'sad': '难过',
            'angry': '生气',
            'anxious': '焦虑',
            'neutral': '平静',
            'excited': '兴奋',
            'tired': '疲惫'
        }
        return emotion_map.get(emotion, '平静')

    async def logs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        web_app_url = self.web_app_url.rstrip('/')
        
        is_local = any(x in web_app_url for x in ['localhost', '127.0.0.1', '0.0.0.0'])
        
        if is_local:
            await update.message.reply_text(
                f"🚀 **本地控制面板已就绪**\n\n请在浏览器中打开以下链接：\n`{web_app_url}`\n\n(Telegram 不支持直接点击 localhost 链接，请复制或手动打开)",
                parse_mode='Markdown'
            )
        else:
            web_app = WebAppInfo(url=web_app_url)
            keyboard = [
                [KeyboardButton("📊 打开控制面板 (Web App)", web_app=web_app)]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await update.message.reply_text(
                "点击下方按钮在 Telegram 内打开控制面板 ✨",
                reply_markup=reply_markup
            )

    async def xhs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /xhs command for Xiaohongshu operations"""
        if not context.args:
            help_text = """
🔴 小红书技能使用指南：

/xhs search <关键词> - 搜索小红书帖子
/xhs feeds - 获取推荐内容
/xhs usernote - 查看我的笔记
/xhs note <笔记ID> - 查看笔记详情

例如：
/xhs search Python教程
/xhs feeds
            """
            await update.message.reply_text(help_text)
            return
        
        action = context.args[0].lower()
        
        if action == "search":
            if len(context.args) < 2:
                await update.message.reply_text("请提供搜索关键词，例如：/xhs search Python教程")
                return
            keyword = " ".join(context.args[1:])
            await update.message.reply_text(f"🔍 正在搜索：「{keyword}」...")
            
            result = await self.skill_manager.execute_skill("xiaohongshu", {
                "action": "search",
                "keyword": keyword,
                "limit": 10
            })
            
            if result.success:
                await update.message.reply_text(f"✅ 搜索结果：\n\n{result.result}")
            else:
                await update.message.reply_text(f"❌ 搜索失败：{result.error}")
        
        elif action == "feeds":
            await update.message.reply_text("📡 正在获取推荐内容...")
            
            result = await self.skill_manager.execute_skill("xiaohongshu", {
                "action": "feeds",
                "limit": 10
            })
            
            if result.success:
                await update.message.reply_text(f"✅ 推荐内容：\n\n{result.result}")
            else:
                await update.message.reply_text(f"❌ 获取失败：{result.error}")
        
        elif action == "usernote":
            await update.message.reply_text("👤 正在获取你的笔记...")
            
            result = await self.skill_manager.execute_skill("xiaohongshu", {
                "action": "user_notes",
                "limit": 10
            })
            
            if result.success:
                await update.message.reply_text(f"✅ 你的笔记：\n\n{result.result}")
            else:
                await update.message.reply_text(f"❌ 获取失败：{result.error}")
        
        elif action == "note":
            if len(context.args) < 2:
                await update.message.reply_text("请提供笔记ID，例如：/xhs note 12345678")
                return
            note_id = context.args[1]
            await update.message.reply_text(f"📝 正在获取笔记详情...")
            
            result = await self.skill_manager.execute_skill("xiaohongshu", {
                "action": "note_detail",
                "note_id": note_id
            })
            
            if result.success:
                await update.message.reply_text(f"✅ 笔记详情：\n\n{result.result}")
            else:
                await update.message.reply_text(f"❌ 获取失败：{result.error}")
        
        else:
            await update.message.reply_text(f"未知操作：{action}\n使用 /xhs 查看帮助")

    async def skills_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List all available skills"""
        skills = self.skill_manager.list_skills()
        
        text = "🎯 可用技能列表：\n\n"
        for skill in skills:
            text += f"• {skill['name']}: {skill['description']}\n"
        
        await update.message.reply_text(text)

    def run(self):
        builder = Application.builder().token(self.telegram_token)
        
        if self.proxy_url:
            logger.info(f"使用代理服务器: {self.proxy_url}")
            request = HTTPXRequest(
                proxy=self.proxy_url, 
                connect_timeout=60.0, 
                read_timeout=60.0,
                write_timeout=60.0,
                pool_timeout=60.0
            )
            builder.request(request)
        else:
            request = HTTPXRequest(
                connect_timeout=60.0, 
                read_timeout=60.0,
                write_timeout=60.0,
                pool_timeout=60.0
            )
            builder.request(request)
            
        application = builder.build()

        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("status", self.status_command))
        application.add_handler(CommandHandler("reset", self.reset_command))
        application.add_handler(CommandHandler("settings", self.settings_command))
        application.add_handler(CommandHandler("monitor", self.monitor_command))
        application.add_handler(CommandHandler("memories", self.memories_command))
        application.add_handler(CommandHandler("logs", self.logs_command))
        application.add_handler(CommandHandler("xhs", self.xhs_command))
        application.add_handler(CommandHandler("skills", self.skills_command))

        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        if self.scheduler:
            async def post_init(application: Application):
                await self.scheduler.start(application.bot)
            
            application.post_init = post_init
            
            async def post_shutdown(application: Application):
                try:
                    await self.scheduler.stop()
                except Exception as e:
                    logger.error(f"停止调度器时出错: {e}")
            
            application.post_shutdown = post_shutdown
            
        return application

if __name__ == '__main__':
    bot = TelegramLoveBot()
    application = bot.run()
    logger.info("Bot is running...")
    application.run_polling()
