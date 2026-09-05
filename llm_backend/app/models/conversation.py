from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum
from app.core.logger import get_logger

logger = get_logger(service="conversation")

class DialogueType(enum.Enum):
    NORMAL = "General Chat"
    DEEP_THINKING = "Deep Thinking"
    WEB_SEARCH = "Web Search"
    RAG = "Knowledge Base Q&A"

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, default=1)
    title = Column(String(100), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    status = Column(String(20), default="ongoing")
    dialogue_type = Column(Enum(DialogueType), nullable=False)
    
    # relationship
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan") 
