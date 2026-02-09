"""
flexo_commit_helper.py

Utility for committing SysMLv2 textual models to a Flexo SysIDE server.

Typical usage:
    python flexo_commit_helper.py
"""

from __future__ import annotations
from typing import Optional, Dict, Tuple
import os
import pathlib
from pprint import pprint

import syside_license
from sysmlv2_client import SysMLV2Client
from flexo_syside_lib.core import convert_sysml_string_textual_to_json
from sysml_api.api_lib import (
    create_sysml_project,
    get_project_by_name,
    commit_to_project,
)


# === Constants ===
DEFAULT_FLEXO_URL = "http://localhost:8080/"
DEFAULT_PROJECT_NAME = "Flexo_SysIDE_TestProject"
ENV_FILE = ".env"


# === Environment Management ===
def load_env_from_repo_root(filename: str = ENV_FILE) -> Optional[str]:
    """
    Load key=value pairs from a `.env` file located in the current directory
    or any parent directory into `os.environ`.

    Args:
        filename: The name of the environment file to search for.

    Returns:
        The absolute path to the loaded `.env` file, or None if not found.
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


# === Core Commit Function ===
def commit_sysml_to_flexo(
    sysml_output: str,
    project_name: str,
    api_key: Optional[str] = None,
    project_id: Optional[str] = None,
    flexo_url: Optional[str] = None,
    verbose: bool = True,
) -> Dict[str, object]:
    """
    Commit SysMLv2 textual content to a Flexo SysIDE server project.

    Steps:
        1. Convert the SysML text to Flexo JSON format.
        2. Resolve or create the target project.
        3. Commit the change and return commit metadata.

    Args:
        sysml_output: SysMLv2 textual representation.
        project_name: Target project name.
        api_key: Optional override for FLEXO_API_KEY.
        project_id: Optional override for an existing project ID.
        flexo_url: Optional override for FLEXO_URL.
        verbose: Print diagnostic information if True.

    Returns:
        Dictionary containing base_url, project_id, commit_id, created_project,
        and the raw commit response.

    Raises:
        EnvironmentError: If credentials are missing.
        RuntimeError: If commit or connection fails.
    """
    api_key = api_key or os.getenv("FLEXO_API_KEY")
    if not api_key:
        raise EnvironmentError("Missing FLEXO_API_KEY environment variable or function argument.")

    flexo_url = flexo_url or os.getenv("FLEXO_URL", DEFAULT_FLEXO_URL)
    base_url = flexo_url.rstrip("/") + "/"
    bearer_token = api_key if api_key.lower().startswith("bearer ") else f"Bearer {api_key}"

    if verbose:
        print(f"[Flexo] Base URL: {base_url}")
        print(f"[Flexo] Target project: name='{project_name}', id={project_id}")
        print("[Flexo] Authentication token is configured.")

    # --- Build client ---
    try:
        client = SysMLV2Client(base_url=base_url, bearer_token=bearer_token)
        if verbose:
            print("[Flexo] SysMLV2Client initialized successfully.")
    except Exception as e:
        raise RuntimeError(f"Failed to initialize SysMLV2Client: {e}") from e

    # --- Convert SysML text to JSON ---
    try:
        change_payload_str, _ = convert_sysml_string_textual_to_json(sysml_output)
        if verbose:
            print("[Flexo] Converted SysML text to JSON payload.")
    except Exception as e:
        raise RuntimeError(f"SysML text conversion failed: {e}") from e

    # --- Resolve or create project ---
    created_project = False
    proj_id = project_id

    if not proj_id:
        project, found_id = get_project_by_name(client, project_name)
        if found_id:
            proj_id = found_id
            if verbose:
                print(f"[Flexo] Found existing project '{project_name}' -> id: {proj_id}")
        else:
            _, created_id, _ = create_sysml_project(client, project_name)
            proj_id = created_id
            created_project = True
            if verbose:
                print(f"[Flexo] Created new project '{project_name}' -> id: {proj_id}")
    else:
        if verbose:
            print(f"[Flexo] Using provided project ID: {proj_id}")

    # --- Commit the change ---
    try:
        commit_response, commit_id = commit_to_project(client, proj_id, change_payload_str)
        if verbose:
            print(f"[Flexo] Commit response: {commit_response}")
            print(f"[Flexo] Commit successful, ID: {commit_id}")
    except Exception as e:
        raise RuntimeError(f"Commit operation failed: {e}") from e

    if not commit_id:
        raise RuntimeError(f"Commit failed: {commit_response}")

    return {
        "base_url": base_url,
        "project_id": proj_id,
        "commit_id": commit_id,
        "created_project": created_project,
        "commit_response": commit_response,
    }


# === Simple Test Harness ===
def test_commit_to_flexo() -> None:
    """Verify that a SysMLv2 snippet can be committed to the Flexo server."""
    sysml_sample = """
    package TestPackage {
        part Satellite {
            attribute mass = 500.0;
        }
    }
    """
    print("[TEST] Starting Flexo commit test...")
    result = commit_sysml_to_flexo(
        sysml_output=sysml_sample,
        project_name=DEFAULT_PROJECT_NAME,
        verbose=True,
    )
    print("\n[TEST RESULT]")
    pprint(result)


# === Entrypoint ===
if __name__ == "__main__":
    load_env_from_repo_root()

    license_key = os.getenv("SYSIDE_LICENSE_KEY")
    if not license_key:
        raise EnvironmentError("Missing SYSIDE_LICENSE_KEY environment variable.")

    syside_license.check(license_key)

    test_commit_to_flexo()
