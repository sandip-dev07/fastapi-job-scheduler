from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.utils.configs import settings

Base = declarative_base()

connect_args = (
    {"check_same_thread": False}
    if settings.DATABASE_URL.startswith("sqlite")
    else {}
)
engine = create_engine(
    url=settings.DATABASE_URL,
    pool_pre_ping=True,
    connect_args=connect_args,
)
Session = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()
