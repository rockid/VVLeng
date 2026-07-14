"""SQLAlchemy ORM models — shared across SQLite and PostgreSQL."""

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy import UUID as SA_UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(SA_UUID, primary_key=True, default=uuid.uuid4)
    linkedin_urn = Column(String(100), unique=True, nullable=True)
    full_name = Column(String(200))
    headline = Column(Text)
    follower_count = Column(Integer, default=0)
    connection_count = Column(Integer, default=0)
    last_activity_date = Column(Date, nullable=True)
    relevance_score = Column(Float, nullable=True)
    influence_score = Column(Float, nullable=True)
    overall_score = Column(Float, nullable=True)
    tier = Column(String(1), nullable=True)  # A / B / C
    last_seen_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    posts = relationship("Post", back_populates="author")
    actions = relationship("Action", back_populates="target_profile")


class Post(Base):
    __tablename__ = "posts"

    id = Column(SA_UUID, primary_key=True, default=uuid.uuid4)
    url = Column(Text, unique=True)
    author_profile_id = Column(SA_UUID, ForeignKey("profiles.id"), nullable=True)
    text = Column(Text)
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    posted_at = Column(DateTime, nullable=True)
    scraped_at = Column(DateTime, default=datetime.utcnow)

    author = relationship("Profile", back_populates="posts")


class Action(Base):
    __tablename__ = "actions"

    id = Column(SA_UUID, primary_key=True, default=uuid.uuid4)
    action_type = Column(String(20))  # comment | connection | visit | post
    target_url = Column(Text)
    target_profile_id = Column(SA_UUID, ForeignKey("profiles.id"), nullable=True)
    suggested_text = Column(Text, nullable=True)
    status = Column(String(20), default="suggested")  # suggested | executed | skipped | failed
    plan_date = Column(Date, nullable=True)
    executed_at = Column(DateTime, nullable=True)
    feedback = Column(JSON, nullable=True)  # {"reply_received": true, "connection_accepted": false}
    created_at = Column(DateTime, default=datetime.utcnow)

    target_profile = relationship("Profile", back_populates="actions")


class ContentIdea(Base):
    __tablename__ = "content_ideas"

    id = Column(SA_UUID, primary_key=True, default=uuid.uuid4)
    topic = Column(Text)
    hook = Column(Text)
    format = Column(String(50))
    predicted_engagement = Column(Integer, default=0)
    generated_at = Column(DateTime, default=datetime.utcnow)
    used_at = Column(DateTime, nullable=True)