from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.database import User, Memory, Conversation, Base, get_session
from src.model_manager import ModelManager
import json
import hashlib


class SimpleMemory:
    """简单的内存对话历史"""
    
    def __init__(self, max_messages: int = 20):
        self.messages: List[Dict] = []
        self.max_messages = max_messages
    
    def add_user_message(self, content: str):
        self.messages.append({"role": "user", "content": content, "time": datetime.now()})
        self._trim_if_needed()
    
    def add_ai_message(self, content: str):
        self.messages.append({"role": "assistant", "content": content, "time": datetime.now()})
        self._trim_if_needed()
    
    def _trim_if_needed(self):
        """保持消息数量在限制内"""
        if len(self.messages) > self.max_messages:
            # 保留最近的消息
            self.messages = self.messages[-self.max_messages:]
    
    def get_recent_context(self, n: int = 10) -> str:
        """获取最近 n 条对话"""
        recent = self.messages[-n:] if len(self.messages) > n else self.messages
        return "\n".join([
            f"{'你' if msg['role'] == 'user' else '我'}: {msg['content']}"
            for msg in recent
        ])
    
    def clear(self):
        self.messages = []


class UserProfile:
    """用户画像管理"""
    
    def __init__(self, user_id: str, db_session: Session):
        self.user_id = user_id
        self.db_session = db_session
        self._load_profile()
    
    def _load_profile(self):
        """从数据库加载用户画像"""
        user = self.db_session.query(User).filter_by(telegram_id=self.user_id).first()
        if user and user.personality_profile:
            try:
                self.profile = json.loads(user.personality_profile)
            except:
                self.profile = self._default_profile()
        else:
            self.profile = self._default_profile()
    
    def _default_profile(self) -> Dict:
        return {
            "name": None,                    # 用户喜欢的称呼
            "preferences": {},               # 喜好
            "habits": {},                    # 习惯
            "important_dates": {},           # 重要日期
            "personality_traits": [],        # 性格特点
            "dislikes": [],                  # 讨厌的事物
            "emotional_needs": [],           # 情感需求
            "shared_memories": [],           # 共同回忆
            "topics_discussed": [],          # 聊过的话题
            "last_emotion": "neutral",       # 上次情绪
            "conversation_count": 0,         # 对话次数
            "first_interaction": None,       # 首次互动
            "last_interaction": None,        # 上次互动
        }
    
    def update(self, key: str, value, merge: bool = False):
        """更新画像字段"""
        if merge and isinstance(self.profile.get(key), dict) and isinstance(value, dict):
            self.profile[key].update(value)
        elif merge and isinstance(self.profile.get(key), list) and isinstance(value, list):
            # 去重添加
            existing = set(self.profile[key])
            for item in value:
                if item not in existing:
                    self.profile[key].append(item)
        else:
            self.profile[key] = value
        self._save()
    
    def get(self, key: str, default=None):
        return self.profile.get(key, default)
    
    def to_text(self) -> str:
        """将画像转为文本描述"""
        parts = []
        if self.profile.get('name'):
            parts.append(f"喜欢被叫做：{self.profile['name']}")
        if self.profile.get('preferences'):
            prefs = ", ".join([f"{k}: {v}" for k, v in self.profile['preferences'].items()])
            parts.append(f"喜好：{prefs}")
        if self.profile.get('personality_traits'):
            traits = ", ".join(self.profile['personality_traits'])
            parts.append(f"性格：{traits}")
        if self.profile.get('habits'):
            habits = ", ".join([f"{k}: {v}" for k, v in self.profile['habits'].items()])
            parts.append(f"习惯：{habits}")
        
        return "；".join(parts) if parts else "还在了解中..."
    
    def _save(self):
        """保存到数据库"""
        user = self.db_session.query(User).filter_by(telegram_id=self.user_id).first()
        if user:
            user.personality_profile = json.dumps(self.profile, ensure_ascii=False)
            self.db_session.commit()


class MemoryManager:
    """增强的记忆管理器"""

    def __init__(self, provider: str = "openai", config: Dict = None):
        self.model_manager = ModelManager(provider, config)
        self.provider = provider
        self.config = config or {}
        self.max_memory_tokens = config.get("max_memory_tokens", 2000) if config else 2000
        
        # 内存中的对话历史
        self.user_memories: Dict[str, SimpleMemory] = {}
        # 用户画像缓存
        self.user_profiles: Dict[str, UserProfile] = {}

    def get_user_memory(self, user_id: str) -> SimpleMemory:
        """获取用户的内存对话历史"""
        if user_id not in self.user_memories:
            self.user_memories[user_id] = SimpleMemory()
        return self.user_memories[user_id]

    def get_user_profile(self, user_id: str, db_session: Session) -> UserProfile:
        """获取用户画像"""
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = UserProfile(user_id, db_session)
        return self.user_profiles[user_id]

    def add_conversation(self, user_id: str, role: str, content: str):
        """添加对话到内存历史"""
        memory = self.get_user_memory(user_id)
        if role == 'user':
            memory.add_user_message(content)
        else:
            memory.add_ai_message(content)

    def get_conversation_context(self, user_id: str) -> str:
        """获取最近的对话上下文"""
        memory = self.get_user_memory(user_id)
        return memory.get_recent_context(n=10)

    async def extract_memories(self, user_id: str, db_session: Session, 
                              new_conversations: List[Conversation]) -> List[Dict]:
        """使用 LLM 从对话中提取记忆"""
        if not new_conversations:
            return []
        
        # 构建对话文本
        conversation_text = "\n".join([
            f"{'用户' if c.role == 'user' else 'AI'}: {c.content}"
            for c in new_conversations[-5:]  # 只分析最近5条
        ])
        
        # 获取现有记忆避免重复
        existing_memories = self.get_all_memories_text(user_id, db_session)
        
        prompt = f"""从以下对话中提取重要信息作为长期记忆。

已有记忆（避免重复提取）：
{existing_memories}

新对话：
{conversation_text}

请提取以下类型的信息（JSON格式）：
[
  {{
    "type": "personal_info",
    "content": "用户的姓名/年龄/职业等",
    "importance": 0.9
  }},
  {{
    "type": "preference", 
    "content": "用户的喜好、口味、兴趣",
    "importance": 0.8
  }},
  {{
    "type": "habit",
    "content": "用户的生活习惯",
    "importance": 0.7
  }},
  {{
    "type": "emotion",
    "content": "用户的情感状态或需求",
    "importance": 0.6
  }},
  {{
    "type": "event",
    "content": "重要事件或约定",
    "importance": 0.8
  }},
  {{
    "type": "shared",
    "content": "你们之间的互动或回忆",
    "importance": 0.7
  }}
]

规则：
1. 只提取新的、重要的信息
2. 用简洁的一句话描述
3. importance 0-1，越重要越高
4. 如果没有新信息，返回空数组 []
5. 只返回 JSON 数组，不要有其他文字"""

        try:
            import asyncio
            response = await asyncio.to_thread(
                self.model_manager.generate,
                [{"role": "user", "content": prompt}]
            )
            
            # 清理响应
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()
            
            memories = json.loads(response)
            
            # 过滤掉重复或相似的记忆
            filtered_memories = self._filter_duplicate_memories(user_id, db_session, memories)
            
            return filtered_memories
            
        except Exception as e:
            print(f"提取记忆失败: {e}")
            return []

    def _filter_duplicate_memories(self, user_id: str, db_session: Session, 
                                   new_memories: List[Dict]) -> List[Dict]:
        """过滤掉与现有记忆重复的内容"""
        existing = db_session.query(Memory).filter(
            Memory.user_id == db_session.query(User.id).filter_by(telegram_id=user_id).scalar_subquery()
        ).all()
        
        existing_contents = [m.content.lower() for m in existing]
        filtered = []
        
        for mem in new_memories:
            content = mem.get('content', '').lower()
            # 检查是否已存在相似内容
            is_duplicate = any(
                self._similarity(content, existing) > 0.7 
                for existing in existing_contents
            )
            if not is_duplicate:
                filtered.append(mem)
        
        return filtered

    def _similarity(self, s1: str, s2: str) -> float:
        """简单计算两个字符串的相似度"""
        if not s1 or not s2:
            return 0.0
        # 使用简单的字符集合交集
        set1 = set(s1)
        set2 = set(s2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0

    def store_memories(self, user_id: str, db_session: Session, memories: List[Dict]):
        """存储记忆到数据库"""
        if not memories:
            return
        
        user = db_session.query(User).filter_by(telegram_id=user_id).first()
        if not user:
            return
        
        for mem_data in memories:
            memory = Memory(
                user_id=user.id,
                content=mem_data['content'],
                memory_type=mem_data.get('type', 'general'),
                importance=mem_data.get('importance', 0.7),
                created_at=datetime.utcnow(),
                last_accessed=datetime.utcnow(),
                access_count=0
            )
            db_session.add(memory)
        
        db_session.commit()
        print(f"已存储 {len(memories)} 条新记忆")

    async def update_user_profile(self, user_id: str, db_session: Session,
                                  new_conversations: List[Conversation]):
        """更新用户画像"""
        if not new_conversations:
            return
        
        profile = self.get_user_profile(user_id, db_session)
        
        # 构建对话文本
        conversation_text = "\n".join([
            f"{'用户' if c.role == 'user' else 'AI'}: {c.content}"
            for c in new_conversations[-3:]
        ])
        
        prompt = f"""从以下对话中提取用户画像信息。

当前画像：{json.dumps(profile.profile, ensure_ascii=False)}

新对话：
{conversation_text}

请返回需要更新或添加的字段（JSON格式）：
{{
  "name": "用户喜欢的称呼（如果有提到）",
  "preferences": {{"喜好类型": "具体内容"}},
  "habits": {{"习惯类型": "具体内容"}},
  "personality_traits": ["性格特点1", "性格特点2"],
  "emotional_needs": ["情感需求"]
}}

如果没有新信息，返回空对象 {{}}。"""

        try:
            import asyncio
            response = await asyncio.to_thread(
                self.model_manager.generate,
                [{"role": "user", "content": prompt}]
            )
            
            updates = json.loads(response.strip())
            
            # 更新画像
            for key, value in updates.items():
                if value:
                    if isinstance(value, dict):
                        profile.update(key, value, merge=True)
                    elif isinstance(value, list):
                        profile.update(key, value, merge=True)
                    else:
                        profile.update(key, value)
            
            # 更新统计
            profile.update('conversation_count', profile.get('conversation_count', 0) + len(new_conversations))
            profile.update('last_interaction', datetime.now().isoformat())
            
        except Exception as e:
            print(f"更新用户画像失败: {e}")

    def get_relevant_memories(self, user_id: str, db_session: Session, 
                             query: str = None, limit: int = 5) -> List[Memory]:
        """获取相关记忆"""
        user = db_session.query(User).filter_by(telegram_id=user_id).first()
        if not user:
            return []

        # 按重要性和最近访问排序
        memories = db_session.query(Memory).filter_by(
            user_id=user.id
        ).order_by(
            Memory.importance.desc(),
            Memory.last_accessed.desc()
        ).limit(limit * 2).all()  # 先获取多一些
        
        # 更新访问记录
        for memory in memories[:limit]:
            memory.last_accessed = datetime.utcnow()
            memory.access_count = (memory.access_count or 0) + 1
        
        db_session.commit()
        return memories[:limit]

    def get_all_memories_text(self, user_id: str, db_session: Session) -> str:
        """获取所有记忆的文本表示"""
        memories = self.get_relevant_memories(user_id, db_session, limit=20)
        if not memories:
            return "暂无记忆"
        return "\n".join([f"- {m.content}" for m in memories])

    def format_memories_for_context(self, memories: List[Memory]) -> str:
        """格式化记忆用于上下文"""
        if not memories:
            return ""
        
        # 按类型分组
        by_type = {}
        for m in memories:
            t = m.memory_type or 'general'
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(m.content)
        
        parts = []
        type_names = {
            'personal_info': '关于你',
            'preference': '你的喜好',
            'habit': '你的习惯', 
            'emotion': '你的情绪',
            'event': '重要的事',
            'shared': '我们的回忆'
        }
        
        for t, contents in by_type.items():
            name = type_names.get(t, t)
            parts.append(f"{name}：{'; '.join(contents[:3])}")
        
        return "\n".join(parts)

    def get_important_memories(self, user_id: str, db_session: Session, 
                              min_importance: float = 0.8) -> List[Memory]:
        """获取重要记忆"""
        user = db_session.query(User).filter_by(telegram_id=user_id).first()
        if not user:
            return []
        
        return db_session.query(Memory).filter(
            Memory.user_id == user.id,
            Memory.importance >= min_importance
        ).order_by(Memory.importance.desc()).all()

    def clear_user_memory(self, user_id: str):
        """清理用户内存缓存"""
        if user_id in self.user_memories:
            del self.user_memories[user_id]
        if user_id in self.user_profiles:
            del self.user_profiles[user_id]
