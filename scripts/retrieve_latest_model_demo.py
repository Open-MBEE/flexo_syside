from __future__ import annotations

from flexo_syside_lib.retriever import (
    load_env_from_repo_root,
    retrieve_latest_sysml_full_model,
)


def main() -> None:
    load_env_from_repo_root()
    sysml_textual = retrieve_latest_sysml_full_model()
    print("\n=== Latest Commit (Full Model) ===\n")
    print(sysml_textual)


if __name__ == "__main__":
    main()
