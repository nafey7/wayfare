"""Test that migration files load in isolation without triggering app domain imports.

This guards against circular imports that only surface at ECS deploy time when the
migrate task runs without the full app context.

See: backend_python/docs/MIGRATIONS.md (Imports / circular-dependency rules)
Root cause: #639, fix: #665, enforced by: #670
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

_BACKEND_DIR = Path(__file__).resolve().parents[2]
_MIGRATIONS_DIR = _BACKEND_DIR / "app" / "database" / "migrations"

migration_files = sorted(_MIGRATIONS_DIR.glob("[0-9]*.py"))


def test_migrations_directory_is_non_empty() -> None:
    assert migration_files, f"No migration files found in {_MIGRATIONS_DIR}"


@pytest.mark.parametrize("path", migration_files, ids=lambda p: p.name)
def test_migration_loads_without_app_domains(path: Path) -> None:
    """Migration files must load without triggering app.domains imports.

    Runs each migration in a subprocess without the full app context to catch
    both direct and transitive circular import chains before they reach deploy.
    """
    env = os.environ.copy()
    env["PYTHONPATH"] = (
        f"{_BACKEND_DIR}:{env['PYTHONPATH']}"
        if "PYTHONPATH" in env
        else str(_BACKEND_DIR)
    )
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import importlib.util; "
                f"s = importlib.util.spec_from_file_location('m', r'{path}'); "
                "m = importlib.util.module_from_spec(s); "
                "s.loader.exec_module(m)"
            ),
        ],
        capture_output=True,
        timeout=10,
        env=env,
        check=False,
    )
    assert result.returncode == 0, (
        f"Migration {path.name} failed to load in isolation:\n{result.stderr.decode()}"
    )
