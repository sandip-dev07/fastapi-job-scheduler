from sqlalchemy import Boolean, Column, Integer, String, ForeignKey
from src.utils.db import Base
from sqlalchemy.orm import relationship

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    is_completed = Column(Boolean, nullable=False, default=False)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User", back_populates="tasks")
