from __future__ import annotations

from config.settings import Settings

from .base import BaseDatabase
from .mysql_client import MysqlDatabase
from .sqlite_client import SqliteDatabase


def create_database(settings: Settings) -> BaseDatabase:
    if settings.db_backend == "sqlite":
        return SqliteDatabase(settings.sqlite_db_path, settings.project_root)
    if settings.db_backend == "mysql":
        return MysqlDatabase(
            project_root=settings.project_root,
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            database=settings.mysql_database,
            charset=settings.mysql_charset,
            connect_timeout=settings.mysql_connect_timeout,
        )
    raise ValueError(f"Unsupported database backend: {settings.db_backend}")
