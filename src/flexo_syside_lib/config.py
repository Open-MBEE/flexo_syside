from __future__ import annotations

import os
from pathlib import Path


DEFAULT_FLEXO_URL = "http://localhost:8080/"
ENV_FILE = ".env"


def load_env_from_repo_root(filename: str = ENV_FILE) -> str | None:
    cwd = Path(__file__).resolve().parent
    for parent in [cwd] + list(cwd.parents):
        env_path = parent / filename
        if env_path.exists():
            with env_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())

            print(f"[ENV] Loaded environment variables from: {env_path}")
            return str(env_path)

    print("[ENV] No .env file found in repo hierarchy.")
    return None


def default_base_and_token() -> tuple[str, str]:
    api_key = os.getenv("FLEXO_API_KEY")
    if not api_key:
        raise EnvironmentError("Missing FLEXO_API_KEY environment variable.")

    flexo_url = os.getenv("FLEXO_URL", DEFAULT_FLEXO_URL)
    base_url = flexo_url.rstrip("/") + "/"
    bearer_token = api_key if api_key.lower().startswith("bearer ") else f"Bearer {api_key}"
    return base_url, bearer_token
