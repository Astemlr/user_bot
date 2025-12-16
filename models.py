"""Модели базы данных."""
from sqlalchemy import Column, Integer, String, Boolean, Text, BigInteger, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    """Модель пользователя."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    target_chat_id = Column(BigInteger, nullable=True)

    filters = relationship("Filter", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")


class Filter(Base):
    """Модель фильтра."""
    __tablename__ = "filters"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    keywords = Column(Text, nullable=True)
    topics = Column(Text, nullable=True)
    use_semantic = Column(Boolean, default=False)

    user = relationship("User", back_populates="filters")


class Subscription(Base):
    """Модель подписки на канал/чат."""
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    chat_id = Column(BigInteger, nullable=False)
    chat_title = Column(String, nullable=True)
    chat_type = Column(String, nullable=True)

    user = relationship("User", back_populates="subscriptions")



