"""Build and verify a complete source archive without secrets or generated state."""

from pathlib import Path
import hashlib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
    "htmlcov",
    "test-results",
    ".playwright",
}
EXCLUDED_NAMES = {".env", ".coverage", ".DS_Store", "MANIFEST.sha256"}
EXCLUDED_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".pyc", ".pyo", ".zip", ".log"}
REQUIRED = [
    "README.md",
    "requirements.txt",
    "requirements-dev.txt",
    "requirements-lock.txt",
    ".env.example",
    ".gitignore",
    "Dockerfile",
    "compose.yaml",
    "alembic.ini",
    "pyproject.toml",
    "app/main.py",
    "app/models.py",
    "app/database.py",
    "app/config.py",
    "app/schemas.py",
    "app/security.py",
    "app/services.py",
    "app/routes/auth.py",
    "app/routes/admin.py",
    "app/routes/catalog.py",
    "app/routes/assistant.py",
    "app/templates/index.html",
    "app/templates/docs.html",
    "app/static/js/app.js",
    "app/static/js/docs.js",
    "app/static/css/app.css",
    "app/static/vendor/leaflet.js",
    "app/static/vendor/leaflet.css",
    "app/static/vendor/images/layers.png",
    "app/static/vendor/images/layers-2x.png",
    "app/static/vendor/chart.umd.js",
    "app/static/vendor/swagger-ui-bundle.js",
    "app/static/vendor/swagger-ui.css",
    "scripts/configure.py",
    "scripts/seed.py",
    "scripts/create_admin.py",
    "scripts/browser_check.py",
    "scripts/postgres_check.py",
    "tests/conftest.py",
    "tests/test_auth.py",
    "tests/test_catalog.py",
    "tests/test_map_analytics.py",
    "tests/test_trends.py",
    "tests/test_migrations.py",
    "migrations/env.py",
    "migrations/versions/0001_initial_initial_portable_schema.py",
    "migrations/versions/0002_postgis.py",
    "docs/VERIFICATION.md",
    "docs/LIMITATIONS.md",
    "docs/SECURITY.md",
    "THIRD_PARTY_NOTICES.md",
    "LICENSE",
]


def main():
    files = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue
        if path.name in EXCLUDED_NAMES or path.name.startswith(".env.") and path.name != ".env.example":
            continue
        if path.suffix in EXCLUDED_SUFFIXES:
            continue
        files.append((rel.as_posix(), path))
    names = {name for name, _ in files}
    missing = set(REQUIRED) - names
    if missing:
        raise SystemExit("Required files are missing: " + ", ".join(sorted(missing)))
    if any(path.stat().st_size == 0 for name, path in files if not name.endswith("__init__.py")):
        raise SystemExit("An unexpected empty source file was found.")
    manifest = "\n".join(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {name}" for name, path in sorted(files)) + "\n"
    destination = ROOT.parent / "HarvestMap_AI.zip"
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, path in sorted(files):
            archive.write(path, "HarvestMap_AI/" + name)
        archive.writestr("HarvestMap_AI/MANIFEST.sha256", manifest)
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None, "Archive CRC check failed"
        assert set(REQUIRED) <= {n.removeprefix("HarvestMap_AI/") for n in archive.namelist()}
        assert len(archive.namelist()) == len(files) + 1
        for line in archive.read("HarvestMap_AI/MANIFEST.sha256").decode().splitlines():
            expected, name = line.split("  ", 1)
            assert hashlib.sha256(archive.read("HarvestMap_AI/" + name)).hexdigest() == expected
    print(f"Created {destination.name}: {len(files) + 1} entries, {destination.stat().st_size:,} bytes")
    print("PASS required-file completeness, secret/cache exclusions, CRC integrity and every SHA-256 manifest entry")
    print("Archive SHA-256: " + hashlib.sha256(destination.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
