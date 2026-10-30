import os
import subprocess
import sys
from pathlib import Path
from sqlalchemy import create_engine, inspect, text


def test_migration_upgrade_downgrade_and_seed(tmp_path):
    env = os.environ.copy()
    env["DATABASE_URL"] = "sqlite:///" + str(tmp_path / "migrations.db")

    def run(*args):
        return subprocess.run([sys.executable, *args], env=env, capture_output=True, text=True, check=True)

    run("-m", "alembic", "upgrade", "head")
    engine = create_engine(env["DATABASE_URL"])
    assert {"users", "locations", "businesses", "products", "price_history"} <= set(inspect(engine).get_table_names())
    first = run("-m", "scripts.seed")
    second = run("-m", "scripts.seed")
    assert "Created 6" in first.stdout and "already exists" in second.stdout
    with engine.connect() as c:
        assert c.scalar(text("SELECT COUNT(*) FROM products")) == 16
        assert c.scalar(text("SELECT COUNT(*) FROM price_history")) == 96
        assert c.scalar(text("SELECT COUNT(*) FROM users WHERE is_active=1")) == 0
    engine.dispose()
    run("-m", "alembic", "downgrade", "base")
    engine = create_engine(env["DATABASE_URL"])
    assert "products" not in inspect(engine).get_table_names()
    engine.dispose()
