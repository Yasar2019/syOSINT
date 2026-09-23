import hashlib
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from alembic import command
from alembic.config import Config
from pathlib import Path

from .models import Audit


def database(url: str):
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    engine = create_engine(url, connect_args={"check_same_thread": False} if url.startswith("sqlite:") else {})
    return engine


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def record(session: Session, action: str, entity: str, entity_id: int, before=None, after=None, reason=None):
    session.add(Audit(action=action, entity=entity, entity_id=entity_id,
                      before_hash=digest(before) if before is not None else None,
                      after_hash=digest(after) if after is not None else None, reason=reason))
