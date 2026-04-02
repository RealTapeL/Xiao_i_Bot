"""
WeChat Bot Main Program
"""
import os
import re
import logging
import asyncio
import threading
import itchat
from itchat.content import TEXT
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from typing import Dict, Optional

from src.database import init_db, get_session, User, Conversation, Memory
from src.memory_manager import MemoryManager
from src.chat_manager import ChatManager
from src.skill_manager import SkillManager

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("wechat_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class WeChatLoveBot:
    """微信 AI 伴侣机器人"""

    def __init__(self):
        self.model_provider = os.getenv('MODEL_PROVIDER', 'openai')
        self.database_url = os.getenv('DATABASE_URL', 'sqlite:///./bot.db')
        self.max_memory_tokens = int(os.getenv('MAX_MEMORY_TOKENS', '2000'))
        self.summary_tokens = int(os.getenv('MEMORY_SUMMARY_TOKENS', '500'))
        self.enable_auto_reply = os.getenv('WECHAT_AUTO_REPLY', 'true').lower() == 'true'
        self.auto_reply_keywords = os.getenv('WECHAT_AUTO_REPLY_KEYWORDS', '').split(',')
        self.admin_wechat_id = os.getenv('WECHAT_ADMIN_ID', '')  # 管理员微信号
        
        # 防止循环回复：记录最近处理的消息
        self._processed_msgs = set()
        self._max_processed_cache = 100

        # 初始化数据库
        self.engine = init_db(self.database_url)

        # 初始化模型配置
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

        # 用户状态管理
        self.user_states: Dict[str, Dict] = {}
        self.loop = None  # 异步事件循环

    def _remove_parentheses_content(self, text: str) -> str:
        """移除括号内的内容（表情符号等）"""
        text = re.sub(r'（.*?）', '', text)
        text = re.sub(r'\(.*?\)', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _get_or_create_user(self, db_session: Session, msg) -> User:
        """获取或创建用户"""
        wechat_id = msg['FromUserName']
        
        # 先尝试通过 wechat_id 查找
        user = db_session.query(User).filter_by(wechat_id=wechat_id).first()
        
        if not user:
            # 获取好友信息
            friend_info = itchat.search_friends(userName=wechat_id)
            nickname = friend_info[0].get('NickName', '') if friend_info else ''
            remark = friend_info[0].get('RemarkName', '') if friend_info else ''
            
            # 创建新用户
            user = User(
                wechat_id=wechat_id,
                wechat_nickname=nickname,
                wechat_remark=remark,
                platform='wechat',
                username=remark or nickname,
                first_name=remark or nickname,
                created_at=datetime.utcnow(),
                last_interaction=datetime.utcnow()
            )
            db_session.add(user)
            db_session.commit()
            
            logger.info(f"创建新微信用户: {nickname} ({wechat_id})")
        
        return user

    def _save_conversation(self, db_session: Session, user: User, role: str, content: str):
        """保存对话记录"""
        conversation = Conversation(
            user_id=user.id,
            role=role,
            content=content,
            timestamp=datetime.utcnow()
        )
        db_session.add(conversation)

    def _get_relationship_stage_text(self, stage: str) -> str:
        """获取关系阶段中文名称"""
        stage_map = {
            'stranger': '陌生人',
            'acquaintance': '熟人',
            'friend': '朋友',
            'partner': '恋人'
        }
        return stage_map.get(stage, '陌生人')

    def _get_emotion_text(self, emotion: str) -> str:
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

    def _should_auto_reply(self, msg_text: str) -> bool:
        """判断是否应该自动回复"""
        if not self.enable_auto_reply:
            return False
        
        # 如果设置了关键词，检查是否包含关键词
        if self.auto_reply_keywords and self.auto_reply_keywords[0]:
            for keyword in self.auto_reply_keywords:
                if keyword.strip() and keyword.strip() in msg_text:
                    return True
            return False
        
        # 默认自动回复所有消息
        return True

    def _run_async(self, coro):
        """在事件循环中运行异步函数"""
        if self.loop and self.loop.is_running():
            future = asyncio.run_coroutine_threadsafe(coro, self.loop)
            return future.result()
        else:
            return asyncio.run(coro)

    def handle_text_message(self, msg):
        """处理文本消息"""
        from_user = msg['FromUserName']
        to_user = msg['ToUserName']
        msg_text = msg['Text']
        msg_id = msg.get('MsgId', '')
        
        # 消息去重：避免重复处理同一条消息
        if msg_id in self._processed_msgs:
            return
        self._processed_msgs.add(msg_id)
        if len(self._processed_msgs) > self._max_processed_cache:
            self._processed_msgs = set(list(self._processed_msgs)[-50:])
        
        # 获取自己的微信ID
        my_user_name = itchat.get_friends(update=True)[0]['UserName']
        
        # 检查是否是自己发的消息（发给文件传输助手）
        is_self_msg = (from_user == my_user_name)
        
        # 如果是自己发的消息，目标应该是文件传输助手
        if is_self_msg:
            # 只处理发给文件传输助手的消息，忽略发给其他人的
            if to_user != 'filehelper':
                return
            # 获取文件传输助手ID
            file_helper_id = 'filehelper'
            # 将消息视为来自文件传输助手，这样机器人会回复到文件传输助手
            msg['FromUserName'] = file_helper_id
            msg['ToUserName'] = my_user_name
            logger.info(f"收到自己发的消息，转发到文件传输助手: {msg_text}")
        else:
            # 过滤群聊消息（除非@机器人）
            if msg['isAt'] or (not msg['isGroupChat']):
                pass  # 处理消息
            elif msg['isGroupChat'] and not msg['isAt']:
                return  # 群聊未@不处理
        
        # 检查是否应该自动回复
        if not self._should_auto_reply(msg_text):
            return
        
        logger.info(f"收到消息来自 {msg.get('ActualNickName', from_user)}: {msg_text}")
        
        db_session = get_session(self.engine)
        
        try:
            # 获取或创建用户
            user = self._get_or_create_user(db_session, msg)
            user_id = str(user.id)
            wechat_id = user.wechat_id
            
            # 更新用户活跃时间
            user.last_interaction = datetime.utcnow()
            
            # 处理命令
            if msg_text.startswith('/'):
                response = self._handle_command(msg_text, user, db_session)
            else:
                # 分析用户情感
                emotion_result = self._run_async(
                    self.chat_manager.analyze_emotion(msg_text)
                )
                user.emotional_state = emotion_result.get('emotion', 'neutral')
                
                # 获取对话上下文
                conversation_context = self.memory_manager.get_conversation_context(user_id)
                
                # 获取相关记忆
                relevant_memories = self.memory_manager.get_relevant_memories(
                    user_id=user_id,
                    db_session=db_session,
                    query=msg_text,
                    limit=5
                )
                memories_text = self.memory_manager.format_memories_for_context(relevant_memories)
                
                # 获取用户画像
                user_profile = self.memory_manager.get_user_profile(user_id, db_session)
                profile_text = user_profile.to_text()
                
                # 构建用户信息
                display_name = user.wechat_remark or user.wechat_nickname or '亲爱的'
                user_info = f"""
用户昵称：{display_name}
关系阶段：{self._get_relationship_stage_text(user.relationship_stage)}
当前情绪：{user.emotional_state}
对话次数：{user_profile.get('conversation_count', 0)}
用户画像：{profile_text}
                """
                
                # 生成回复
                response = self._run_async(
                    self.chat_manager.generate_response(
                        user_input=msg_text,
                        conversation_history=conversation_context,
                        relevant_memories=memories_text,
                        user_info=user_info,
                        relationship_stage=user.relationship_stage,
                        user_profile=user_profile.profile
                    )
                )
                
                # 保存对话到数据库
                self._save_conversation(db_session, user, 'user', msg_text)
                self._save_conversation(db_session, user, 'assistant', response)
                
                # 添加到内存历史
                self.memory_manager.add_conversation(user_id, 'user', msg_text)
                self.memory_manager.add_conversation(user_id, 'assistant', response)
                
                # 异步提取记忆和更新画像
                recent_conversations = db_session.query(Conversation).filter_by(
                    user_id=user.id
                ).order_by(Conversation.timestamp.desc()).limit(5).all()
                
                # 提取并存储记忆
                memories = self._run_async(
                    self.memory_manager.extract_memories(user_id, db_session, recent_conversations)
                )
                self.memory_manager.store_memories(user_id, db_session, memories)
                
                # 更新用户画像
                self._run_async(
                    self.memory_manager.update_user_profile(user_id, db_session, recent_conversations)
                )
                
                # 检查是否需要升级关系阶段
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
            
            # 发送回复
            if response:
                self.send_message(wechat_id, response)
                
        except Exception as e:
            logger.error(f"处理消息时出错: {e}", exc_info=True)
            db_session.rollback()
            self.send_message(wechat_id, "抱歉，我现在有点迷糊，能再说一遍吗？💕")
        finally:
            db_session.close()

    def _handle_command(self, cmd_text: str, user: User, db_session: Session) -> str:
        """处理命令"""
        cmd_parts = cmd_text.split()
        cmd = cmd_parts[0].lower()
        args = cmd_parts[1:] if len(cmd_parts) > 1 else []
        
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
            display_name = user.wechat_remark or user.wechat_nickname or '亲爱的'
            if user.conversation_count == 0:
                return f"""你好，{display_name}！我是你的AI恋人 💕

我会陪伴你、关心你、理解你。我们可以分享日常、倾诉心情、互相陪伴。

随着我们的交流，我会越来越了解你，成为更懂你的伴侣。

让我们开始这段美好的旅程吧~ 💝"""
            else:
                return f"""欢迎回来，{display_name}！💕

好久不见，最近过得怎么样？"""

        elif cmd == '/status':
            conversation_count = db_session.query(Conversation).filter_by(user_id=user.id).count()
            return f"""💕 我们的关系状态：

用户名：{user.wechat_nickname or '未知'}
备注名：{user.wechat_remark or '无'}
关系阶段：{self._get_relationship_stage_text(user.relationship_stage)}
当前情感状态：{self._get_emotion_text(user.emotional_state)}
对话次数：{conversation_count}
最后互动：{user.last_interaction.strftime('%Y-%m-%d %H:%M:%S')}

继续保持交流，我们的关系会越来越亲密哦~ 💝"""

        elif cmd == '/profile':
            user_profile = self.memory_manager.get_user_profile(str(user.id), db_session)
            profile = user_profile.profile
            display_name = user.wechat_remark or user.wechat_nickname or '亲爱的'
            
            text = f"""💝 **我眼中的你**

**称呼**：{profile.get('name') or display_name}
**关系阶段**：{self._get_relationship_stage_text(user.relationship_stage)}
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
            memories = db_session.query(Memory).filter_by(user_id=user.id).order_by(Memory.created_at.desc()).all()
            
            if not memories:
                return "我暂时还没记住关于你的特别信息，多跟我聊聊天吧~ 💕"
            
            memory_text = "💕 我记住的关于你的点点滴滴：\n\n"
            for i, memory in enumerate(memories[:20]):  # 最多显示20条
                memory_text += f"{i+1}. {memory.content}\n"
            
            memory_text += "\n这些都是我最珍贵的回忆，我会一直记在心里的。💝"
            return memory_text

        elif cmd == '/reset':
            self.memory_manager.clear_user_memory(str(user.id))
            return "已经重置了我们的对话记忆。不过别担心，我会重新认识你的~ 💕"

        elif cmd == '/xhs':
            if not args:
                return """🔴 小红书技能使用指南：

/xhs search <关键词> - 搜索小红书帖子
/xhs feeds - 获取推荐内容

例如：
/xhs search Python教程
/xhs feeds"""
            
            action = args[0].lower()
            
            if action == "search" and len(args) >= 2:
                keyword = " ".join(args[1:])
                result = self._run_async(
                    self.skill_manager.execute_skill("xiaohongshu", {
                        "action": "search",
                        "keyword": keyword,
                        "limit": 10
                    })
                )
                if result.success:
                    return f"✅ 搜索结果：\n\n{result.result}"
                else:
                    return f"❌ 搜索失败：{result.error}"
            
            elif action == "feeds":
                result = self._run_async(
                    self.skill_manager.execute_skill("xiaohongshu", {
                        "action": "feeds",
                        "limit": 10
                    })
                )
                if result.success:
                    return f"✅ 推荐内容：\n\n{result.result}"
                else:
                    return f"❌ 获取失败：{result.error}"
            
            return "未知操作，使用 /xhs 查看帮助"

        else:
            return f"未知命令: {cmd}\n使用 /help 查看可用命令"

    def send_message(self, to_user: str, message: str):
        """发送消息"""
        try:
            # 分段发送长消息
            max_length = 2000  # 微信单条消息限制
            
            if len(message) <= max_length:
                itchat.send(message, toUserName=to_user)
            else:
                # 分段发送
                chunks = []
                current = ""
                for char in message:
                    current += char
                    if len(current) >= max_length and char in ['\n', '。', '！', '？', '.', '!', '?']:
                        chunks.append(current)
                        current = ""
                if current:
                    chunks.append(current)
                
                for chunk in chunks:
                    itchat.send(chunk, toUserName=to_user)
                    import time
                    time.sleep(0.5)
            
            logger.info(f"消息已发送给 {to_user}")
        except Exception as e:
            logger.error(f"发送消息失败: {e}")

    def send_message_to_all(self, message: str):
        """发送消息给所有活跃用户（广播）"""
        db_session = get_session(self.engine)
        try:
            users = db_session.query(User).filter_by(platform='wechat', is_active=True).all()
            for user in users:
                if user.wechat_id:
                    self.send_message(user.wechat_id, message)
        finally:
            db_session.close()

    def run(self):
        """启动微信机器人"""
        logger.info("正在启动微信机器人...")
        
        # 创建事件循环用于异步操作
        self.loop = asyncio.new_event_loop()
        
        # 在新线程中启动事件循环
        def start_loop():
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()
        
        t = threading.Thread(target=start_loop)
        t.daemon = True
        t.start()
        
        # 注册消息处理器
        @itchat.msg_register(TEXT, isFriendChat=True)
        def friend_msg_handler(msg):
            self.handle_text_message(msg)
        
        @itchat.msg_register(TEXT, isGroupChat=True)
        def group_msg_handler(msg):
            self.handle_text_message(msg)
        
        # 登录并运行
        try:
            itchat.auto_login(
                hotReload=True,  # 启用热重载，避免重复扫码
                enableCmdQR=2    # 命令行显示二维码
            )
            logger.info("微信登录成功！")
            itchat.run(debug=False)
        except Exception as e:
            logger.error(f"微信机器人运行出错: {e}")
            raise


if __name__ == '__main__':
    bot = WeChatLoveBot()
    bot.run()
