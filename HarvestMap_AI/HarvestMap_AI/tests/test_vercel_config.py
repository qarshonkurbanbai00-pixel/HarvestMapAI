import json
from pathlib import Path


def test_vercel_config_exists():
    config_path = Path("vercel.json")
    assert config_path.exists(), "vercel.json is required for Vercel deployment"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    builds = config.get("builds", [])
    assert builds, "Vercel should declare a Python serverless build"
    assert any(item.get("use") == "@vercel/python" for item in builds)


def test_vercel_python_entrypoint_exists():
    entrypoint = Path("api/index.py")
    assert entrypoint.exists(), "api/index.py is required as the serverless FastAPI entrypoint"
    content = entrypoint.read_text(encoding="utf-8")
    assert "from app.main import app" in content
