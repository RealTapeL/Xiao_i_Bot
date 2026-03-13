from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from contextlib import contextmanager

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(String(50), unique=True, nullable=False, index=True)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_interaction = Column(DateTime, default=datetime.utcnow, index=True)
    relationship_stage = Column(String(50), default='stranger')  # stranger, acquaintance, friend, partner
    personality_profile = Column(Text)  # 用户性格画像
    preferences = Column(Text)  # 用户偏好设置(JSON格式)
    emotional_state = Column(String(50), default='neutral')  # 当前情感状态
    is_active = Column(Boolean, default=True, index=True)

    # 关联关系
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    memories = relationship("Memory", back_populates="user", cascade="all, delete-orphan")

class Conversation(Base):
    """对话历史模型"""
    __tablename__ = 'conversations'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    tokens = Column(Integer, default=0)
    is_summary = Column(Boolean, default=False)  # 是否为对话摘要

    # 复合索引：用户对话历史查询
    __table_args__ = (
        Index('idx_conversation_user_timestamp', 'user_id', 'timestamp'),
    )

    # 关联关系
    user = relationship("User", back_populates="conversations")

class Memory(Base):
    """长期记忆模型"""
    __tablename__ = 'memories'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    content = Column(Text, nullable=False)
    memory_type = Column(String(50))  # 'personal_info', 'preference', 'event', 'emotion'
    importance = Column(Float, default=1.0, index=True)  # 记忆重要性评分(0-1)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.utcnow, index=True)
    access_count = Column(Integer, default=0)

    # 复合索引：记忆检索
    __table_args__ = (
        Index('idx_memory_user_importance', 'user_id', 'importance', 'last_accessed'),
    )

    # 关联关系
    user = relationship("User", back_populates="memories")

class ProactiveMessage(Base):
    """主动消息记录"""
    __tablename__ = 'proactive_messages'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    message_content = Column(Text, nullable=False)
    trigger_type = Column(String(50)) # system_state, timer, daily, etc.
    sent_at = Column(DateTime, default=datetime.utcnow, index=True)
    response_received = Column(Boolean, default=False)
    response_time = Column(Float)  # 用户回复时间(秒)

    # 复合索引
    __table_args__ = (
        Index('idx_proactive_user_sent', 'user_id', 'sent_at'),
    )

# 数据库初始化
def init_db(database_url):
    """初始化数据库"""
    engine = create_engine(
        database_url,
        pool_size=5,              # 保持的连接数
        max_overflow=10,          # 允许额外创建的连接数
        pool_pre_ping=True,       # 连接前测试连接是否有效
        pool_recycle=3600,        # 每小时回收连接
        echo=False                # 是否打印 SQL 语句
    )
    Base.metadata.create_all(engine)
    return engine

def get_session(engine):
    """获取数据库会话"""
    Session = sessionmaker(bind=engine)
    return Session()

@contextmanager
def get_session_context(engine):
    """获取数据库会话的上下文管理器
    
    使用方法:
        with get_session_context(engine) as session:
            # 执行数据库操作
            pass
    """
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
