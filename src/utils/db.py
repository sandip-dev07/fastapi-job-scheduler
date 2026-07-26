from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from src.utils.configs import settings

Base = declarative_base() # Used to create database models.
engine = create_engine(url=settings.DATABASE_URL)
Session = sessionmaker(bind=engine)


def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()
        
