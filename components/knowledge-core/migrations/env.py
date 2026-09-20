from __future__ import annotations

from logging.config import fileConfig
import os

from alembic import context
from sqlalchemy import engine_from_config, pool

from knowledge_core.storage.models import Base
# Register non-core model modules in the shared SQLAlchemy metadata.
from knowledge_core.storage import control_models as _control_models  # noqa: F401
from knowledge_core.storage import deletion_models as _deletion_models  # noqa: F401
from knowledge_core.storage import generation_models as _generation_models  # noqa: F401
from knowledge_core.storage import governed_source_models as _governed_source_models  # noqa: F401
from knowledge_core.storage import identity_models as _identity_models  # noqa: F401
from knowledge_core.storage import principal_models as _principal_models  # noqa: F401
from knowledge_core.storage import repository_import_models as _repository_import_models  # noqa: F401
from knowledge_core.storage import resource_models as _resource_models  # noqa: F401
from knowledge_core.storage import retrieval_models as _retrieval_models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = os.environ.get("KNOWLEDGE_CORE_DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
