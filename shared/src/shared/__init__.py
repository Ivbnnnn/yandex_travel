"""Common HTTP infrastructure. Import Kafka/outbox from their own modules."""

from .config import BaseConfig
from .database import Database
from .db.base import Base
from .db.repository import BaseRepository
from .fastapi.factory import create_app

__all__ = ["Base", "BaseConfig", "BaseRepository", "Database", "create_app"]
