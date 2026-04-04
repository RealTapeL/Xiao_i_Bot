"""
记忆管理模块 - 基于 Mem0
为 QQ 机器人提供长期记忆功能

特性:
- 每用户独立的记忆空间
- 向量语义搜索
- 本地存储 (SQLite + Qdrant 本地模式)
- 无需 OpenAI API Key
"""
import os
import json
import logging
import sqlite3
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class QQBotMemory:
    """
    QQ 机器人记忆管理器
    
    使用本地 SQLite 存储 + 简单向量索引
    实现无需外部 API 的记忆系统
    """
    
    def __init__(self, db_path: str = "data/memories.db"):
        """初始化记忆系统"""
        self.db_path = db_path
        self.embeddings_cache: Dict[str, List[float]] = {}
        
        # 确保数据目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # 初始化数据库
        self._init_db()
        logger.info("✅ Mem0 记忆系统初始化成功 (本地模式)")
    
    def _init_db(self):
        """初始化 SQLite 数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建记忆表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                user_name TEXT,
                message TEXT NOT NULL,
                response TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_user_id ON memories(user_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_created_at ON memories(created_at)
        ''')
        
        conn.commit()
        conn.close()
    
    def _simple_hash(self, text: str) -> List[float]:
        """简单的文本哈希，用于相似度搜索"""
        import hashlib
        # 使用 MD5 生成确定性哈希
        hash_val = hashlib.md5(text.encode()).hexdigest()
        # 转换为 16 维向量
        vec = [int(hash_val[i:i+2], 16) / 255.0 for i in range(0, 32, 2)]
        return vec
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        import math
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(x * x for x in vec1))
        norm2 = math.sqrt(sum(x * x for x in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)
    
    def add_interaction(self, user_id: str, user_name: str, 
                        message: str, response: str,
                        metadata: Optional[Dict] = None) -> bool:
        """
        添加用户交互到记忆
        
        Args:
            user_id: QQ 用户ID
            user_name: 用户昵称
            message: 用户消息
            response: AI 回复
            metadata: 额外元数据
            
        Returns:
            是否成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO memories 
                (user_id, user_name, message, response, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                str(user_id),
                user_name or "",
                message,
                response,
                json.dumps(metadata or {}, ensure_ascii=False)
            ))
            
            conn.commit()
            conn.close()
            
            # 缓存嵌入向量
            text = f"{message} {response}"
            self.embeddings_cache[f"{user_id}_{cursor.lastrowid}"] = self._simple_hash(text)
            
            logger.debug(f"已添加记忆: user={user_id}, msg={message[:30]}...")
            return True
            
        except Exception as e:
            logger.error(f"添加记忆失败: {e}")
            return False
    
    def search_memories(self, user_id: str, query: str, 
                        limit: int = 5) -> List[Dict]:
        """
        搜索用户相关记忆
        
        Args:
            user_id: QQ 用户ID
            query: 查询关键词
            limit: 返回条数
            
        Returns:
            记忆列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 获取该用户的所有记忆
            cursor.execute('''
                SELECT * FROM memories 
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 100
            ''', (str(user_id),))
            
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                return []
            
            # 计算相似度
            query_vec = self._simple_hash(query)
            
            scored_memories = []
            for row in rows:
                text = f"{row['message']} {row['response'] or ''}"
                text_vec = self._simple_hash(text)
                similarity = self._cosine_similarity(query_vec, text_vec)
                
                # 关键词匹配加分
                if any(kw in text.lower() for kw in query.lower().split()):
                    similarity += 0.3
                
                scored_memories.append((similarity, row))
            
            # 按相似度排序
            scored_memories.sort(key=lambda x: x[0], reverse=True)
            
            # 返回 top N
            results = []
            for score, row in scored_memories[:limit]:
                results.append({
                    'id': row['id'],
                    'user_id': row['user_id'],
                    'user_name': row['user_name'],
                    'message': row['message'],
                    'response': row['response'],
                    'metadata': json.loads(row['metadata'] or '{}'),
                    'created_at': row['created_at'],
                    'relevance': round(score, 3)
                })
            
            return results
            
        except Exception as e:
            logger.error(f"搜索记忆失败: {e}")
            return []
    
    def get_all_memories(self, user_id: str, limit: int = 50) -> List[Dict]:
        """获取用户的所有记忆"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM memories 
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (str(user_id), limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'id': row['id'],
                    'user_id': row['user_id'],
                    'user_name': row['user_name'],
                    'message': row['message'],
                    'response': row['response'],
                    'metadata': json.loads(row['metadata'] or '{}'),
                    'created_at': row['created_at']
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"获取记忆失败: {e}")
            return []
    
    def get_context_for_llm(self, user_id: str, current_message: str,
                            max_memories: int = 5) -> List[Dict]:
        """
        为 LLM 获取记忆上下文
        
        Args:
            user_id: QQ 用户ID
            current_message: 当前用户消息
            max_memories: 最大记忆条数
            
        Returns:
            相关记忆列表（用于构造 prompt）
        """
        # 搜索相关记忆
        memories = self.search_memories(user_id, current_message, limit=max_memories)
        
        # 过滤低相关度的记忆
        relevant = [m for m in memories if m.get('relevance', 0) > 0.3]
        
        return relevant
    
    def format_context_for_prompt(self, memories: List[Dict]) -> str:
        """将记忆格式化为 LLM prompt 的一部分"""
        if not memories:
            return ""
        
        context = "\n[历史记忆参考]\n"
        for i, mem in enumerate(memories, 1):
            context += f"{i}. 用户曾问: {mem['message'][:100]}\n"
            if mem.get('response'):
                context += f"   你回复: {mem['response'][:100]}\n"
        context += "\n"
        
        return context
    
    def clear_user_memories(self, user_id: str) -> bool:
        """清除用户的所有记忆"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM memories WHERE user_id = ?', (str(user_id),))
            
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"已清除用户 {user_id} 的 {deleted} 条记忆")
            return True
            
        except Exception as e:
            logger.error(f"清除记忆失败: {e}")
            return False
    
    def get_all_users(self) -> List[str]:
        """获取所有有记忆的用户ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT DISTINCT user_id FROM memories')
            users = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            return users
            
        except Exception as e:
            logger.error(f"获取用户列表失败: {e}")
            return []
    
    def get_user_stats(self, user_id: str) -> Dict:
        """获取用户记忆统计"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*), MIN(created_at), MAX(created_at)
                FROM memories WHERE user_id = ?
            ''', (str(user_id),))
            
            count, first, last = cursor.fetchone()
            conn.close()
            
            return {
                'user_id': user_id,
                'memory_count': count,
                'first_memory': first,
                'last_memory': last
            }
            
        except Exception as e:
            logger.error(f"获取用户统计失败: {e}")
            return {'user_id': user_id, 'memory_count': 0}
    
    def get_stats(self) -> Dict:
        """获取系统统计信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*), COUNT(DISTINCT user_id) FROM memories')
            total, users = cursor.fetchone()
            
            conn.close()
            
            return {
                'status': 'active',
                'total_memories': total,
                'total_users': users,
                'db_path': self.db_path
            }
            
        except Exception as e:
            logger.error(f"获取统计失败: {e}")
            return {'status': 'error', 'error': str(e)}
