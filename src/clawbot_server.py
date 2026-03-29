"""
ClawBot HTTP Server
实现微信 ClawBot 插件要求的 5 个 HTTP 接口
"""
import os
import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from src.database import init_db, get_session, User, Conversation
from src.memory_manager import MemoryManager
from src.chat_manager import ChatManager
from src.skill_manager import SkillManager

logger = logging.getLogger(__name__)

# 消息队列和状态管理
class MessageQueue:
    """消息队列，用于存储待发送的消息"""
    def __init__(self):
        self.messages: List[Dict] = []
        self.lock = asyncio.Lock()
    
    async def put(self, message: Dict):
        async with self.lock:
            self.messages.append(message)
    
    async def get_all(self) -> List[Dict]:
        async with self.lock:
            msgs = self.messages.copy()
            self.messages.clear()
            return msgs

message_queue = MessageQueue()

# 数据模型
class SendMessageRequest(BaseModel):
    chat_id: str
    text: Optional[str] = None
    reply_to_message_id: Optional[str] = None

class SendTypingRequest(BaseModel):
    chat_id: str
    action: str = "typing"

class Update(BaseModel):
    update_id: int
    message: Optional[Dict] = None

class ConfigResponse(BaseModel):
    webhook_url: Optional[str] = None
    max_connections: int = 40
    allowed_updates: List[str] = ["message"]

class ClawBotServer:
    """ClawBot HTTP 服务器"""
    
    def __init__(self, host: str = None, port: int = None):
        self.host = host or os.getenv('SERVER_HOST', '0.0.0.0')
        self.port = port or int(os.getenv('SERVER_PORT', '8080'))
        self.engine = None
        self.memory_manager = None
        self.chat_manager = None
        self.skill_manager = None
        self.update_id = 0
        
        # 加载配置
        self.model_provider = os.getenv('MODEL_PROVIDER', 'openai')
        self.database_url = os.getenv('DATABASE_URL', 'sqlite:///./bot.db')
        self.max_memory_tokens = int(os.getenv('MAX_MEMORY_TOKENS', '2000'))
        self.summary_tokens = int(os.getenv('MEMORY_SUMMARY_TOKENS', '500'))
        
        # 初始化 FastAPI
        self.app = FastAPI(
            title="Xiao_i Bot - ClawBot Adapter",
            description="微信 ClawBot 适配器 - AI 伴侣机器人",
            version="1.0.0"
        )
        self.setup_routes()
    
    def init_components(self):
        """初始化组件"""
        # 初始化数据库
        self.engine = init_db(self.database_url)
        
        # 模型配置
        model_config = {
            "provider": self.model_provider,
            "max_memory_tokens": self.max_memory_tokens,
            "summary_tokens": self.summary_tokens
        }
        
        # 根据提供商配置
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
        
        logger.info("ClawBot 组件初始化完成")
    
    def setup_routes(self):
        """设置路由"""
        
        @self.app.get("/health")
        async def health_check():
            """健康检查"""
            return {"status": "ok", "service": "xiao-i-bot"}
        
        @self.app.post("/ilink/bot/getupdates")
        async def get_updates(offset: Optional[int] = None, limit: int = 100):
            """
            长轮询获取新消息
            ClawBot 会定期调用此接口拉取消息
            """
            try:
                # 获取队列中的消息
                messages = await message_queue.get_all()
                
                updates = []
                for msg in messages:
                    self.update_id += 1
                    updates.append({
                        "update_id": self.update_id,
                        "message": msg
                    })
                
                return {"ok": True, "result": updates}
            except Exception as e:
                logger.error(f"get_updates error: {e}")
                return {"ok": False, "error": str(e)}
        
        @self.app.post("/ilink/bot/sendmessage")
        async def send_message(request: SendMessageRequest):
            """
            发送消息给用户
            这里只是把消息存入队列，实际不会直接发给微信
            （微信会自己处理发送）
            """
            logger.info(f"收到发送消息请求: chat_id={request.chat_id}, text={request.text}")
            return {
                "ok": True,
                "result": {
                    "message_id": f"msg_{datetime.utcnow().timestamp()}",
                    "chat": {"id": request.chat_id},
                    "text": request.text,
                    "date": int(datetime.utcnow().timestamp())
                }
            }
        
        @self.app.post("/ilink/bot/sendtyping")
        async def send_typing(request: SendTypingRequest):
            """发送正在输入状态"""
            logger.info(f"发送 typing 状态: chat_id={request.chat_id}")
            return {"ok": True}
        
        @self.app.get("/ilink/bot/getconfig")
        async def get_config():
            """获取机器人配置"""
            return {
                "ok": True,
                "result": {
                    "webhook_url": None,  # 使用长轮询，不设置 webhook
                    "max_connections": 40,
                    "allowed_updates": ["message"]
                }
            }
        
        @self.app.post("/ilink/bot/getuploadurl")
        async def get_upload_url():
            """获取媒体文件上传地址"""
            return {
                "ok": True,
                "result": {
                    "upload_url": None,
                    "expires_in": 3600
                }
            }
        
        @self.app.post("/webhook")
        async def receive_webhook(message: Dict):
            """
            接收微信消息的 Webhook
            ClawBot 会把收到的微信消息转发到这里
            """
            logger.info(f"收到微信消息: {message}")
            
            # 后台处理消息
            asyncio.create_task(self.handle_message(message))
            
            return {"ok": True}
    
    async def handle_message(self, message: Dict):
        """处理收到的消息"""
        try:
            # 提取消息信息
            chat = message.get("chat", {})
            from_user = message.get("from", {})
            text = message.get("text", "")
            
            chat_id = str(chat.get("id", ""))
            user_id = str(from_user.get("id", ""))
            user_name = from_user.get("first_name", "") or from_user.get("username", "亲爱的")
            
            if not text:
                return
            
            # 处理消息并生成回复
            response_text = await self.process_message(user_id, user_name, text)
            
            if response_text:
                # 构建回复消息
                reply_message = {
                    "message_id": f"reply_{datetime.utcnow().timestamp()}",
                    "from": {"id": 0, "is_bot": True, "first_name": "小i"},
                    "chat": chat,
                    "date": int(datetime.utcnow().timestamp()),
                    "text": response_text
                }
                
                # 添加到消息队列
                await message_queue.put(reply_message)
                logger.info(f"回复已加入队列: {response_text[:50]}...")
                
        except Exception as e:
            logger.error(f"处理消息时出错: {e}", exc_info=True)
    
    async def process_message(self, user_id: str, user_name: str, text: str) -> str:
        """处理用户消息，生成回复"""
        db_session = get_session(self.engine)
        
        try:
            # 获取或创建用户
            user = db_session.query(User).filter_by(wechat_id=user_id).first()
            
            if not user:
                user = User(
                    wechat_id=user_id,
                    platform='wechat',
                    username=user_name,
                    first_name=user_name,
                    created_at=datetime.utcnow(),
                    last_interaction=datetime.utcnow()
                )
                db_session.add(user)
                db_session.commit()
            
            user_db_id = str(user.id)
            
            # 更新活跃时间
            user.last_interaction = datetime.utcnow()
            
            # 处理命令
            if text.startswith('/'):
                response = self.handle_command(text, user, db_session)
            else:
                # 分析情感
                emotion_result = await self.chat_manager.analyze_emotion(text)
                user.emotional_state = emotion_result.get('emotion', 'neutral')
                
                # 获取对话上下文
                conversation_context = self.memory_manager.get_conversation_context(user_db_id)
                
                # 获取相关记忆
                relevant_memories = self.memory_manager.get_relevant_memories(
                    user_id=user_db_id,
                    db_session=db_session,
                    query=text,
                    limit=5
                )
                memories_text = self.memory_manager.format_memories_for_context(relevant_memories)
                
                # 获取用户画像
                user_profile = self.memory_manager.get_user_profile(user_db_id, db_session)
                profile_text = user_profile.to_text()
                
                # 构建用户信息
                user_info = f"""
用户昵称：{user_name}
关系阶段：{self.get_relationship_stage_text(user.relationship_stage)}
当前情绪：{user.emotional_state}
对话次数：{user_profile.get('conversation_count', 0)}
用户画像：{profile_text}
                """
                
                # 生成回复
                response = await self.chat_manager.generate_response(
                    user_input=text,
                    conversation_history=conversation_context,
                    relevant_memories=memories_text,
                    user_info=user_info,
                    relationship_stage=user.relationship_stage,
                    user_profile=user_profile.profile
                )
                
                # 保存对话
                self.save_conversation(db_session, user, 'user', text)
                self.save_conversation(db_session, user, 'assistant', response)
                
                # 更新内存历史
                self.memory_manager.add_conversation(user_db_id, 'user', text)
                self.memory_manager.add_conversation(user_db_id, 'assistant', response)
                
                # 提取记忆和更新画像
                recent_conversations = db_session.query(Conversation).filter_by(
                    user_id=user.id
                ).order_by(Conversation.timestamp.desc()).limit(5).all()
                
                memories = await self.memory_manager.extract_memories(user_db_id, db_session, recent_conversations)
                self.memory_manager.store_memories(user_db_id, db_session, memories)
                await self.memory_manager.update_user_profile(user_db_id, db_session, recent_conversations)
                
                # 检查关系升级
                new_stage = self.chat_manager.update_relationship_stage(
                    user.relationship_stage,
                    user_profile.get('conversation_count', 0),
                    0.5,
                    (datetime.utcnow() - user.created_at).days if user.created_at else 0
                )
                if new_stage != user.relationship_stage:
                    user.relationship_stage = new_stage
                    logger.info(f"用户 {user_id} 关系阶段升级到: {new_stage}")
            
            db_session.commit()
            return response
            
        except Exception as e:
            logger.error(f"处理消息时出错: {e}", exc_info=True)
            db_session.rollback()
            return "抱歉，我现在有点迷糊，能再说一遍吗？💕"
        finally:
            db_session.close()
    
    def handle_command(self, cmd_text: str, user: User, db_session) -> str:
        """处理命令"""
        cmd_parts = cmd_text.split()
        cmd = cmd_parts[0].lower()
        
        if cmd == '/help':
            return """💕 **使用指南** 💕

**基础命令：**
/start - 开始对话
/help - 查看帮助
/status - 查看当前关系状态
/profile - 查看我眼中的你 💝
/memories - 查看我记住的事

**系统命令：**
/reset - 重置对话记忆

想我了就随时找我聊天哦～"""

        elif cmd == '/start':
            name = user.first_name or '亲爱的'
            if user.conversation_count == 0:
                return f"""你好，{name}！我是你的AI恋人 💕

我会陪伴你、关心你、理解你。我们可以分享日常、倾诉心情、互相陪伴。

随着我们的交流，我会越来越了解你，成为更懂你的伴侣。

让我们开始这段美好的旅程吧~ 💝"""
            else:
                return f"""欢迎回来，{name}！💕

好久不见，最近过得怎么样？"""

        elif cmd == '/status':
            conversation_count = db_session.query(Conversation).filter_by(user_id=user.id).count()
            return f"""💕 我们的关系状态：

用户名：{user.username or '未知'}
关系阶段：{self.get_relationship_stage_text(user.relationship_stage)}
当前情感状态：{self.get_emotion_text(user.emotional_state)}
对话次数：{conversation_count}
最后互动：{user.last_interaction.strftime('%Y-%m-%d %H:%M:%S')}

继续保持交流，我们的关系会越来越亲密哦~ 💝"""

        elif cmd == '/profile':
            user_profile = self.memory_manager.get_user_profile(str(user.id), db_session)
            profile = user_profile.profile
            name = user.first_name or '亲爱的'
            
            text = f"""💝 **我眼中的你**

**称呼**：{profile.get('name') or name}
**关系阶段**：{self.get_relationship_stage_text(user.relationship_stage)}
**对话次数**：{profile.get('conversation_count', 0)} 次

**📝 你的画像**：
"""
            
            if profile.get('preferences'):
                prefs = profile['preferences']
                if isinstance(prefs, dict):
                    text += "\n**喜好**：\n"
                    for k, v in prefs.items():
                        text += f"  • {k}: {v}\n"
                else:
                    text += f"\n**喜好**：{prefs}\n"
            
            if profile.get('habits'):
                habits = profile['habits']
                if isinstance(habits, dict):
                    text += "\n**习惯**：\n"
                    for k, v in habits.items():
                        text += f"  • {k}: {v}\n"
                else:
                    text += f"\n**习惯**：{habits}\n"
            
            if profile.get('personality_traits'):
                traits = ", ".join(profile['personality_traits'])
                text += f"\n**性格**：{traits}\n"
            
            if profile.get('emotional_needs'):
                needs = ", ".join(profile['emotional_needs'])
                text += f"\n**情感需求**：{needs}\n"
            
            if profile.get('shared_memories'):
                text += "\n**我们的回忆**：\n"
                for mem in profile['shared_memories'][:3]:
                    text += f"  • {mem}\n"
            
            if not any([profile.get('preferences'), profile.get('habits'), 
                       profile.get('personality_traits')]):
                text += "\n_我还在努力了解你呢，多跟我聊聊天吧~_ 💕"
            else:
                text += "\n_我会继续记住关于你的一切_ 💕"
            
            return text

        elif cmd == '/memories':
            from src.database import Memory
            memories = db_session.query(Memory).filter_by(user_id=user.id).order_by(Memory.created_at.desc()).all()
            
            if not memories:
                return "我暂时还没记住关于你的特别信息，多跟我聊聊天吧~ 💕"
            
            memory_text = "💕 我记住的关于你的点点滴滴：\n\n"
            for i, memory in enumerate(memories[:20]):
                memory_text += f"{i+1}. {memory.content}\n"
            
            memory_text += "\n这些都是我最珍贵的回忆，我会一直记在心里的。💝"
            return memory_text

        elif cmd == '/reset':
            self.memory_manager.clear_user_memory(str(user.id))
            return "已经重置了我们的对话记忆。不过别担心，我会重新认识你的~ 💕"

        else:
            return f"未知命令: {cmd}\n使用 /help 查看可用命令"
    
    def save_conversation(self, db_session, user: User, role: str, content: str):
        """保存对话记录"""
        conversation = Conversation(
            user_id=user.id,
            role=role,
            content=content,
            timestamp=datetime.utcnow()
        )
        db_session.add(conversation)
    
    def get_relationship_stage_text(self, stage: str) -> str:
        """获取关系阶段中文名称"""
        stage_map = {
            'stranger': '陌生人',
            'acquaintance': '熟人',
            'friend': '朋友',
            'partner': '恋人'
        }
        return stage_map.get(stage, '陌生人')
    
    def get_emotion_text(self, emotion: str) -> str:
        """获取情感状态中文名称"""
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
    
    def run(self):
        """启动服务器"""
        # 初始化组件
        self.init_components()
        
        logger.info(f"启动 ClawBot HTTP 服务: http://{self.host}:{self.port}")
        uvicorn.run(self.app, host=self.host, port=self.port, log_level="info")


if __name__ == "__main__":
    server = ClawBotServer()
    server.run()
