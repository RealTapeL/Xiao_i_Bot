from typing import List, Dict, Optional
from datetime import datetime
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from sqlalchemy.orm import Session
from src.database import User, Memory, Conversation
from src.model_manager import ModelManager


class MemoryManager:

    def __init__(self, provider: str = "openai", config: Dict = None):
        self.model_manager = ModelManager(provider, config)
        self.provider = provider
        self.config = config or {}
        self.max_memory_tokens = config.get("max_memory_tokens", 2000) if config else 2000
        self.summary_tokens = config.get("summary_tokens", 500) if config else 500
        self.user_memories: Dict[str, ConversationBufferMemory] = {}

        self.summarization_prompt = PromptTemplate.from_template("""
        请将以下对话历史总结为一段简短的文字（不超过200字），保留所有关键信息（如提到的姓名、爱好、重要约定或情感转折点）。
        这个总结将作为后续对话的背景。

        对话历史：
        {history}

        总结：
        """)

        self.memory_extraction_prompt = PromptTemplate.from_template("""
        从以下对话中提取重要信息，包括：
        1. 用户个人信息（姓名、年龄、职业等）
        2. 用户偏好和兴趣
        3. 重要事件和经历
        4. 用户当前情感状态

        对话内容：
        {conversation}

        请以JSON数组格式返回提取的信息，每个信息包含type（类型）、content（内容）、importance（重要性0-1）字段。
        示例格式：[{{"type": "personal", "content": "用户姓名是张三", "importance": 0.9}}]
        注意：只返回JSON数组，不要包含任何其他文字说明。
        如果没有提取到任何信息，返回空数组：[]
        """)

    def get_user_memory(self, user_id: str) -> ConversationBufferMemory:
        if user_id not in self.user_memories:
            self.user_memories[user_id] = ConversationBufferMemory(
                return_messages=False
            )
        return self.user_memories[user_id]

    def add_conversation(self, user_id: str, role: str, content: str):
        memory = self.get_user_memory(user_id)
        if role == 'user':
            memory.chat_memory.add_user_message(content)
        else:
            memory.chat_memory.add_ai_message(content)

    def get_conversation_context(self, user_id: str) -> str:
        memory = self.get_user_memory(user_id)
        history = memory.load_memory_variables({}).get('history', '')
        
        # 如果历史记录太长，进行总结
        if len(history) > 2000:
            summary = self.summarize_history(history)
            # 重置内存并只保留总结
            memory.clear()
            memory.chat_memory.add_ai_message(f"这是我们之前的对话总结：{summary}")
            return f"对话总结：{summary}"
            
        return history

    def extract_and_store_memories(self, user_id: str, db_session: Session, recent_conversations: List[Conversation]):
        """
        从对话中提取重要记忆并存储到数据库

        Args:
            user_id: 用户ID
            db_session: 数据库会话
            recent_conversations: 最近的对话列表
        """
        # 构建对话文本
        conversation_text = "\n".join([
            f"{c.role}: {c.content}"
            for c in recent_conversations
        ])

        # 使用LLM提取记忆
        prompt = self.memory_extraction_prompt.format(conversation=conversation_text)
        response = self.model_manager.generate([{"role": "user", "content": prompt}])

        # 解析并存储记忆
        try:
            import json
            import re

            print(f"LLM response for memory extraction: {response}")

            # 尝试从响应中提取 JSON 数组
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                response = json_match.group(0)

            memories_data = json.loads(response)
            user = db_session.query(User).filter_by(telegram_id=user_id).first()

            for mem_data in memories_data:
                memory = Memory(
                    user_id=user.id,
                    content=mem_data['content'],
                    memory_type=mem_data.get('type', 'general'),
                    importance=mem_data.get('importance', 0.7),
                    created_at=datetime.utcnow()
                )
                db_session.add(memory)

            db_session.commit()
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            print(f"Response was: {response}")
            db_session.rollback()
        except Exception as e:
            print(f"Error storing memories: {e}")
            print(f"Response was: {response}")
            db_session.rollback()

    def get_relevant_memories(self, user_id: str, db_session: Session, query: str, limit: int = 5) -> List[Memory]:
        """
        获取与查询相关的记忆

        Args:
            user_id: 用户ID
            db_session: 数据库会话
            query: 查询文本
            limit: 返回记忆数量限制

        Returns:
            相关记忆列表
        """
        user = db_session.query(User).filter_by(telegram_id=user_id).first()
        if not user:
            return []

        # 简单实现：按重要性和最近访问时间排序
        memories = db_session.query(Memory).filter_by(
            user_id=user.id
        ).order_by(
            Memory.importance.desc(),
            Memory.last_accessed.desc()
        ).limit(limit).all()

        # 更新访问时间
        for memory in memories:
            memory.last_accessed = datetime.utcnow()
            memory.access_count += 1

        db_session.commit()
        return memories

    def format_memories_for_context(self, memories: List[Memory]) -> str:
        """
        将记忆格式化为上下文字符串

        Args:
            memories: 记忆列表

        Returns:
            格式化的记忆文本
        """
        if not memories:
            return "暂无相关记忆"

        formatted = "关于用户的重要信息：\n"
        for memory in memories:
            formatted += f"- {memory.content}\n"

        return formatted

    def clear_user_memory(self, user_id: str):
        """
        清除用户的短期记忆

        Args:
            user_id: 用户ID
        """
        if user_id in self.user_memories:
            del self.user_memories[user_id]

    def summarize_history(self, history: str) -> str:
        """
        使用LLM总结对话历史
        """
        if not history or len(history) < 200:
            return history
            
        prompt = self.summarization_prompt.format(history=history)
        return self.model_manager.generate([{"role": "user", "content": prompt}])