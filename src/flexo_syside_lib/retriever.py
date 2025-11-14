"""
flexo_model_retriever.py

Utility script to authenticate with a Flexo SysMLv2 server, locate a project,
fetch its latest commit, and convert the model snapshot to textual SysML form.

How to test:
    python flexo_model_retriever.py
"""

from __future__ import annotations
from typing import Tuple, Optional
import os
import pathlib
print('Retriever is loading...')
import syside_license
from sysmlv2_client import SysMLV2Client
from flexo_syside_lib.core import convert_json_to_sysml_textual
from sysml_api.api_lib import get_project_by_name, get_last_commit_from_project


# === Constants ===
DEFAULT_PROJECT_NAME = "Flexo_SysIDE_TestProject"
DEFAULT_FLEXO_URL = "http://localhost:8080/"
ENV_FILE = ".env"


# === Environment Helpers ===
def load_env_from_repo_root(filename: str = ENV_FILE) -> Optional[str]:
    """
    Search for a `.env` file in the current directory or its parents,
    load key=value pairs into `os.environ`, and return the path to the file.

    Args:
        filename: Name of the environment file to search for (default: ".env").

    Returns:
        The path to the loaded .env file as a string, or None if not found.
    """
    cwd = pathlib.Path(__file__).resolve().parent

    for parent in [cwd] + list(cwd.parents):
        env_path = parent / filename
        if env_path.exists():
            with env_path.open("r") as f:
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


def _default_base_and_token() -> Tuple[str, str]:
    """
    Construct the Flexo base URL and Bearer token from environment variables.

    Returns:
        (base_url, bearer_token) tuple.

    Raises:
        EnvironmentError: if FLEXO_API_KEY is not set.
    """
    api_key = os.getenv("FLEXO_API_KEY")
    if not api_key:
        raise EnvironmentError("Missing FLEXO_API_KEY environment variable.")

    flexo_url = os.getenv("FLEXO_URL", DEFAULT_FLEXO_URL)
    base_url = flexo_url.rstrip("/") + "/"
    bearer_token = api_key if api_key.lower().startswith("bearer ") else f"Bearer {api_key}"

    return base_url, bearer_token


# === Main Model Retrieval ===
def retrieve_latest_sysml_full_model(
    project_name: str = DEFAULT_PROJECT_NAME,
    verbose: bool = True,
) -> str:
    """
    Retrieve the latest full SysMLv2 model snapshot for a given project.

    Steps:
        1. Resolve the project by name on the Flexo server.
        2. Identify its latest commit.
        3. Fetch and convert all model elements to textual SysML.

    Args:
        project_name: Name of the project to query.
        verbose: If True, print diagnostic information.

    Returns:
        SysML textual representation of the model.

    Raises:
        EnvironmentError: if required environment variables are missing.
        RuntimeError: if the project cannot be found.
    """
    base_url, bearer_token = _default_base_and_token()

    if verbose:
        print(f"[Flexo] Base URL: {base_url}")
        print(f"[Flexo] Resolving project: '{project_name}'")

    client = SysMLV2Client(base_url=base_url, bearer_token=bearer_token)

    # --- Project lookup ---
    project_obj, project_id = get_project_by_name(client, project_name)
    if not project_id:
        raise RuntimeError(f"Project '{project_name}' not found on server {base_url}")

    if verbose:
        print(f"[Flexo] Found project '{project_name}' with ID: {project_id}")

    # --- Latest commit lookup ---
    latest_commit_id = get_last_commit_from_project(client, project_obj)
    if verbose and latest_commit_id:
        print(f"[Flexo] Latest commit ID: {latest_commit_id}")

    # --- Model retrieval ---
    elements = client.list_elements(project_id, latest_commit_id)
    sysml_text, _ = convert_json_to_sysml_textual(elements)

    return sysml_text


# === Entrypoint ===
if __name__ == "__main__":
    load_env_from_repo_root()

    license_key = os.getenv("SYSIDE_LICENSE_KEY")
    if not license_key:
        raise EnvironmentError("Missing SYSIDE_LICENSE_KEY environment variable.")

    syside_license.check(license_key)

    sysml_textual = retrieve_latest_sysml_full_model()

    print("\n=== Latest Commit (Full Model) ===\n")
    print(sysml_textual)
