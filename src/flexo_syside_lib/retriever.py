"""
flexo_model_retriever.py

Utility script to authenticate with a Flexo SysMLv2 server, locate a project,
fetch its latest commit, and convert the model snapshot to textual SysML form.

How to test:
    python flexo_model_retriever.py
"""

from __future__ import annotations
from typing import Optional

from sysmlv2_client import SysMLV2Client
from flexo_syside_lib.core import convert_json_to_sysml_textual
from .config import DEFAULT_FLEXO_URL, default_base_and_token, load_env_from_repo_root
from sysml_api.api_lib import get_project_by_name, get_last_commit_from_project


DEFAULT_PROJECT_NAME = "Flexo_SysIDE_TestProject"


# === Main Model Retrieval ===
def retrieve_latest_sysml_full_model(
    project_name: str = DEFAULT_PROJECT_NAME,
    base_url: Optional[str] = None,
    bearer_token: Optional[str] = None,
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
    if base_url is None or bearer_token is None:
        base_url, bearer_token = default_base_and_token()

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
    (sysml_text, model), warnings = convert_json_to_sysml_textual(elements)

    return (sysml_text, model), warnings
