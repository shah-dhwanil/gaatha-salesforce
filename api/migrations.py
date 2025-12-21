"""
Database migration manager using yoyo-migrations.

This module provides utilities to apply, rollback, and manage database migrations
using yoyo-migrations. It integrates with the application's configuration and
database settings.
"""

from typing import Optional

import structlog
from yoyo import get_backend, read_migrations
from yoyo.backends import DatabaseBackend

from api.settings.database import DatabaseConfig

logger = structlog.get_logger(__name__)


class MigrationManager:
    """
    Manages database migrations using yoyo-migrations.

    This class handles migration application, rollback, and status checking
    with proper error handling and logging.
    """

    def __init__(
        self,
        config: DatabaseConfig,
        migrations_dir: Optional[str] = None,
    ) -> None:
        """
        Initialize the migration manager.

        Args:
            migrations_dir: Path to migrations directory. Defaults to ./migrations
            database_url: Database connection URL. If not provided, builds from settings
        """
        self.migrations_dir = migrations_dir
        self.database_url = config.get_database_url("postgresql+psycopg")

        self._backend: Optional[DatabaseBackend] = None

    def _get_backend(self, migration_schema: str) -> Optional[DatabaseBackend]:
        """
        Get or create the yoyo database backend.

        Returns:
            DatabaseBackend instance

        Raises:
            Exception: If backend creation fails
        """
        if self._backend is None:
            database_url = (
                self.database_url + f"?options=-csearch_path={migration_schema}"
            )
            try:
                logger.info("Creating yoyo database backend", url=self.database_url)
                self._backend = get_backend(database_url)
                logger.info("Database backend created successfully")
                return self._backend
            except Exception as e:
                logger.error("Failed to create database backend", error=str(e))
                raise

    def apply(self, migration_schema: str):
        """
        Apply all pending migrations.

        Raises:
            Exception: If migration application fails
        """
        try:
            backend = self._get_backend(migration_schema)
            backend
            if backend is None:
                raise Exception("Database backend is not initialized")
        except Exception as e:
            logger.error("Failed to apply migrations", error=str(e))
            raise
        migrations = backend.to_apply(read_migrations(self.migrations_dir))
        for migration in migrations:
            try:
                logger.info("Applying migration", migration=migration)
                backend.apply_one(migration)
                logger.info("Migration applied successfully", migration=migration)
            except Exception as e:
                logger.error(
                    "Failed to apply migrations", migration=migration, error=str(e)
                )
                raise

    @classmethod
    def apply_main_migrations(
        cls, config: DatabaseConfig, migrations_dir: Optional[str] = None
    ):
        """
        Apply main migrations using the MigrationManager.

        Args:
            config: Database configuration
            migrations_dir: Path to migrations directory. Defaults to ./migrations

        Raises:
            Exception: If migration application fails
        """
        manager = cls(config, migrations_dir or "./migrations")
        manager.apply("salesforce")

    @classmethod
    def apply_company_migrations(
        cls,
        config: DatabaseConfig,
        schema_name: str,
        migrations_dir: Optional[str] = None,
    ):
        """
        Apply company-specific migrations using the MigrationManager.

        Args:
            config: Database configuration
            migrations_dir: Path to migrations directory. Defaults to ./migrations/company
        Raises:
            Exception: If migration application fails
        """
        manager = cls(config, "./migrations/company/")
        manager.apply(schema_name)
