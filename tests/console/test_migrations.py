"""Regression tests for the Alembic migration chain (Issue #109).

The chain previously assumed ``Base.metadata.create_all`` had already created
``audit_logs`` and other tables, so ``alembic upgrade head`` on a fresh
database failed with ``no such table: audit_logs`` and left a partially
applied schema. These tests pin the fresh-DB, legacy-DB and roundtrip paths.
"""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from database import Base
import models.ai_setting  # noqa: F401
import models.audit_log  # noqa: F401
import models.consent  # noqa: F401
import models.document  # noqa: F401
import models.m365_setting  # noqa: F401
import models.organization  # noqa: F401
import models.retention_policy  # noqa: F401
import models.user  # noqa: F401


_BACKEND_DIR = Path(__file__).parents[2] / "src" / "console" / "backend"


# The migration tests operate on their own temporary SQLite databases and must
# not depend on (or contend with) the shared test_console.db used by the app
# test fixtures. Shadow the package-level autouse fixtures from conftest.py.
@pytest.fixture(autouse=True, scope="module")
def _override_db():
    yield


@pytest.fixture(autouse=True)
def setup_db():
    yield


def _alembic_config(url: str) -> Config:
    cfg = Config(str(_BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def _tables(url: str) -> dict[str, set[str]]:
    engine = create_engine(url)
    inspector = inspect(engine)
    return {
        name: {c["name"] for c in inspector.get_columns(name)}
        for name in inspector.get_table_names()
    }


@pytest.fixture
def migration_env(tmp_path, monkeypatch):
    """Run Alembic against a dedicated temp SQLite DB."""
    url = f"sqlite:///{tmp_path}/migration.db"
    monkeypatch.setenv("DATABASE_URL", url)
    return url


def test_upgrade_head_on_fresh_db_matches_metadata(migration_env):
    command.upgrade(_alembic_config(migration_env), "head")

    migrated = _tables(migration_env)
    expected = {
        name: {c.name for c in table.columns}
        for name, table in Base.metadata.tables.items()
    }
    assert set(expected) <= set(migrated)
    assert migrated["audit_logs"] == expected["audit_logs"]
    assert migrated["ai_settings"] == expected["ai_settings"]
    assert migrated["consent_records"] == expected["consent_records"]
    assert migrated["conversion_jobs"] == expected["conversion_jobs"]
    assert migrated["organizations"] == expected["organizations"]


def test_legacy_create_all_db_upgrades_idempotently(tmp_path, monkeypatch):
    """A create_all-era DB must reach head cleanly (stamped at base)."""
    legacy_url = f"sqlite:///{tmp_path}/legacy.db"
    monkeypatch.setenv("DATABASE_URL", legacy_url)
    engine = create_engine(legacy_url)
    Base.metadata.create_all(engine)
    engine.dispose()

    cfg = _alembic_config(legacy_url)
    command.upgrade(cfg, "head")

    migrated = _tables(legacy_url)
    expected = {
        name: {c.name for c in table.columns}
        for name, table in Base.metadata.tables.items()
    }
    for name, columns in expected.items():
        assert migrated.get(name, set()) >= columns, f"{name} missing columns"


def test_legacy_create_all_db_stamped_mid_chain_upgrades_idempotently(
    tmp_path, monkeypatch
):
    """A create_all-era DB stamped at c3f8a1b2d4e5 (Issue #109 repro) must
    also reach head cleanly without duplicate table/column errors."""
    legacy_url = f"sqlite:///{tmp_path}/legacy_mid.db"
    monkeypatch.setenv("DATABASE_URL", legacy_url)
    engine = create_engine(legacy_url)
    Base.metadata.create_all(engine)
    engine.dispose()

    cfg = _alembic_config(legacy_url)
    command.stamp(cfg, "c3f8a1b2d4e5")
    command.upgrade(cfg, "head")

    migrated = _tables(legacy_url)
    expected = {
        name: {c.name for c in table.columns}
        for name, table in Base.metadata.tables.items()
    }
    for name, columns in expected.items():
        assert migrated.get(name, set()) >= columns, f"{name} missing columns"


def test_downgrade_base_then_upgrade_head_roundtrip(migration_env):
    command.upgrade(_alembic_config(migration_env), "head")
    cfg = _alembic_config(migration_env)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")

    migrated = _tables(migration_env)
    expected = {
        name: {c.name for c in table.columns}
        for name, table in Base.metadata.tables.items()
    }
    assert set(expected) <= set(migrated)
    assert migrated["ai_settings"] == expected["ai_settings"]
