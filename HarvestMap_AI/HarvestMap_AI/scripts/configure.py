"""Generate local-only secrets. Never commits credentials to source."""

from pathlib import Path
import secrets

path = Path(".env")
if path.exists():
    print(".env already exists; leaving it unchanged.")
else:
    password = secrets.token_urlsafe(24)
    content = (
        Path(".env.example")
        .read_text()
        .replace("REPLACE_WITH_RANDOM_32_PLUS_CHARACTERS", secrets.token_urlsafe(48))
        .replace("REPLACE_WITH_RANDOM_DATABASE_PASSWORD", password)
    )
    path.write_text(content)
    path.chmod(0o600)
    print("Created .env with random local secrets. Review before using Docker.")
