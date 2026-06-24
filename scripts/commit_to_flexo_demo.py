from __future__ import annotations

from pprint import pprint

from flexo_syside_lib.committer import (
    DEFAULT_PROJECT_NAME,
    commit_sysml_to_flexo,
    load_env_from_repo_root,
)


def main() -> None:
    load_env_from_repo_root()
    sysml_sample = """
    package TestPackage {
        part Satellite {
            attribute mass = 500.0;
        }
    }
    """
    result = commit_sysml_to_flexo(
        sysml_output=sysml_sample,
        project_name=DEFAULT_PROJECT_NAME,
        verbose=True,
    )
    pprint(result)


if __name__ == "__main__":
    main()
