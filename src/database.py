from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(String(50), unique=True, nullable=False)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_interaction = Column(DateTime, default=datetime.utcnow)
    relationship_stage = Column(String(50), default='stranger')  # stranger, acquaintance, friend, partner
    personality_profile = Column(Text)  # 用户性格画像
    preferences = Column(Text)  # 用户偏好设置(JSON格式)
    emotional_state = Column(String(50), default='neutral')  # 当前情感状态
    is_active = Column(Boolean, default=True)

    # 关联关系
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    memories = relationship("Memory", back_populates="user", cascade="all, delete-orphan")

class Conversation(Base):
    """对话历史模型"""
    __tablename__ = 'conversations'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    tokens = Column(Integer, default=0)
    is_summary = Column(Boolean, default=False)  # 是否为对话摘要

    # 关联关系
    user = relationship("User", back_populates="conversations")

class Memory(Base):
    """长期记忆模型"""
    __tablename__ = 'memories'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    content = Column(Text, nullable=False)
    memory_type = Column(String(50))  # 'personal_info', 'preference', 'event', 'emotion'
    importance = Column(Float, default=1.0)  # 记忆重要性评分(0-1)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    access_count = Column(Integer, default=0)

    # 关联关系
    user = relationship("User", back_populates="memories")

class ProactiveMessage(Base):
    """主动消息记录"""
    __tablename__ = 'proactive_messages'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    message_content = Column(Text, nullable=False)
    trigger_type = Column(String(50)) # system_state, timer, daily, etc.
    sent_at = Column(DateTime, default=datetime.utcnow)
    response_received = Column(Boolean, default=False)
    response_time = Column(Float)  # 用户回复时间(秒)

# 数据库初始化
def init_db(database_url):
    """初始化数据库"""
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    return engine

def get_session(engine):
    """获取数据库会话"""
    Session = sessionmaker(bind=engine)
    return Session()
