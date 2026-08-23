"""
Alembic Environment Configuration
===================================
Configures Alembic to use our SQLAlchemy models and database settings.
Overrides the sqlalchemy.url from alembic.ini with the app's DATABASE_URL.
"""

from logging.config import fileConfig

# pyrefly: ignore [missing-import]
from sqlalchemy import create_engine, pool
from alembic import context

# ── Import our models and config ──────────────────────────────
# This import ensures all models are registered with Base.metadata
from app.models import Role, User, Store, Zone, Shelf, Product, Camera, AIJob  # noqa: F401
from app.database.database import Base, normalize_database_url
from app.core.config import get_settings

# ── Alembic Config object ────────────────────────────────────
config = context.config

# Setup logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override database URL from environment
settings = get_settings()
db_url = normalize_database_url(settings.DATABASE_URL)
# Escape '%' as '%%' for configparser interpolation (e.g. %40 in passwords)
config.set_main_option(
    "sqlalchemy.url", db_url.replace("%", "%%")
)

# Target metadata for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode — generates SQL without a live connection.
    """
    url = db_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode — connects to the database and applies changes.
    """
    connectable = create_engine(db_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
