from sqlalchemy import Column, Integer, String
from src.utils.db import Base
from sqlalchemy.orm import relationship


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    password = Column(String, nullable=False)
    
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    
