import os
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_DB_PATH = PROJECT_ROOT / ".pytest_jobs.db"

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"
os.environ["DEFAULT_RETRY_BACKOFF_SECONDS"] = "1"
os.environ["LOG_LEVEL"] = "WARNING"

import pytest
from fastapi.testclient import TestClient

from main import app
from src.utils.celery import celery_app
from src.utils.db import Base, Session, engine


@pytest.fixture(scope="session", autouse=True)
def database_schema():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    TEST_DB_PATH.unlink(missing_ok=True)


@pytest.fixture(autouse=True)
def clean_tables():
    yield
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def queue_calls(monkeypatch):
    calls: list[dict[str, object]] = []

    def fake_send_task(name, args=None, task_id=None, **kwargs):
        calls.append(
            {
                "name": name,
                "args": args,
                "task_id": task_id,
            }
        )
        return SimpleNamespace(id=task_id)

    monkeypatch.setattr(celery_app, "send_task", fake_send_task)
    return calls


@pytest.fixture
def db_session():
    with Session() as session:
        yield session
