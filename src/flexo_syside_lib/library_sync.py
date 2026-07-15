from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Iterable, List, Optional


_MODEL_SUFFIXES = {".sysml", ".syml", ".kerml"}


def safe_path_segment(name: str, default: str = "project") -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]+', "-", str(name or "").strip())
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return cleaned or default


def safe_model_filename(name: str, default_stem: str = "model") -> str:
    raw_name = Path(str(name or "").strip()).name
    suffix = Path(raw_name).suffix
    if suffix.lower() not in _MODEL_SUFFIXES:
        suffix = ".sysml"
    stem = safe_path_segment(Path(raw_name).stem or default_stem, default_stem)
    return f"{stem}{suffix}"


def _safe_relative_model_path(name: str, default_stem: str) -> Path:
    candidate = Path(str(name or "").replace("\\", "/"))
    parts = [part for part in candidate.parts if part not in {"", ".", ".."}]
    if not parts:
        return Path(safe_model_filename("", default_stem))
    if len(parts) == 1:
        return Path(safe_model_filename(parts[0], default_stem))
    safe_parts = [safe_path_segment(part, "library") for part in parts[:-1]]
    safe_parts.append(safe_model_filename(parts[-1], default_stem))
    return Path(*safe_parts)


def deduplicate_model_filenames(models: Iterable[Dict[str, str]]) -> List[Dict[str, str]]:
    used: Dict[str, int] = {}
    normalized: List[Dict[str, str]] = []
    for index, model in enumerate(models):
        relative_path = _safe_relative_model_path(model.get("name", ""), f"model-{index + 1}")
        key = relative_path.as_posix()
        count = used.get(key, 0)
        used[key] = count + 1
        if count == 0:
            final_path = relative_path
        else:
            final_path = relative_path.with_name(
                f"{relative_path.stem}-{count + 1}{relative_path.suffix}"
            )
        normalized.append({"name": final_path.as_posix(), "text": str(model.get("text", ""))})
    return normalized


def derive_sysand_library_name(iri: str, explicit_name: str = "") -> str:
    if explicit_name:
        return safe_path_segment(explicit_name, "library")
    tail = str(iri or "").rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1].strip()
    return safe_path_segment(tail, "library")


def normalize_sysand_clone_iri(iri: str) -> str:
    value = str(iri or "").strip()
    if not value:
        return value
    if value.startswith(("pkg:", "http://", "https://")):
        return value
    if "/" in value:
        return f"pkg:sysand/{value}"
    return value


def build_sysand_command(
    executable: str,
    subcommand: List[str],
    *,
    config_file: str = "",
    no_config: bool = False,
    index_urls: Optional[List[str]] = None,
    default_index_urls: Optional[List[str]] = None,
    no_index: bool = False,
    include_std: bool = False,
) -> List[str]:
    cmd = [executable]
    if no_config:
        cmd.append("--no-config")
    elif config_file:
        cmd.extend(["--config-file", config_file])
    cmd.extend(subcommand)
    if index_urls:
        cmd.extend(["--index", ",".join(index_urls)])
    if default_index_urls:
        cmd.extend(["--default-index", ",".join(default_index_urls)])
    if no_index:
        cmd.append("--no-index")
    if include_std:
        cmd.append("--include-std")
    return cmd


def run_sysand(
    cmd: List[str],
    *,
    cwd: Path,
    env: Optional[Dict[str, str]] = None,
) -> subprocess.CompletedProcess[str]:
    run_env = dict(**env) if env else {}
    base_env = {}
    try:
        import os

        base_env = os.environ.copy()
    except Exception:
        base_env = {}
    base_env.update({k: str(v) for k, v in run_env.items() if v is not None})
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        env=base_env,
        capture_output=True,
        text=True,
        check=False,
    )


def is_safe_within_dir(root: Path, target: Path) -> bool:
    try:
        target.resolve().relative_to(root.resolve())
        return True
    except Exception:
        return False


def find_primary_model_file(library_dir: Path) -> Optional[Path]:
    candidates: List[Path] = []
    for pattern in ("*.sysml", "*.syml", "*.kerml"):
        candidates.extend(
            path
            for path in library_dir.rglob(pattern)
            if ".sysand" not in path.parts
        )
    if not candidates:
        return None
    return sorted(candidates)[0]


def collect_textual_models_from_directory(library_dir: Path) -> List[Dict[str, str]]:
    models: List[Dict[str, str]] = []
    for pattern in ("*.sysml", "*.syml", "*.kerml"):
        for path in sorted(
            candidate
            for candidate in library_dir.rglob(pattern)
            if ".sysand" not in candidate.parts
        ):
            models.append(
                {
                    "name": path.relative_to(library_dir).as_posix(),
                    "text": path.read_text(encoding="utf-8"),
                }
            )
    return models


def collect_installed_environment_models(install_root: Path) -> List[tuple[str, str]]:
    models: List[tuple[str, str]] = []
    if not install_root.exists():
        return models
    for library_dir in sorted(path for path in install_root.iterdir() if path.is_dir()):
        if library_dir.name.startswith("."):
            continue
        for model in collect_textual_models_from_directory(library_dir):
            rel_name = Path(library_dir.name) / Path(model["name"])
            models.append((rel_name.as_posix(), model["text"]))
    return models


def materialize_textual_models(
    install_root: Path,
    library_name: str,
    models: Iterable[Dict[str, str]],
    *,
    clear_existing: bool = True,
) -> Dict[str, object]:
    normalized_name = safe_path_segment(library_name, "library")
    library_dir = install_root / normalized_name

    if clear_existing and library_dir.exists():
        if not is_safe_within_dir(install_root, library_dir):
            raise ValueError(f"Refusing to replace path outside root: {library_dir}")
        shutil.rmtree(library_dir)

    library_dir.mkdir(parents=True, exist_ok=True)

    file_paths: List[Path] = []
    normalized_models = deduplicate_model_filenames(models)
    for model in normalized_models:
        relative_path = Path(model["name"])
        target_path = library_dir / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(model["text"], encoding="utf-8")
        file_paths.append(target_path)

    primary_path = file_paths[0] if file_paths else None
    return {
        "library_name": normalized_name,
        "library_dir": library_dir,
        "file_paths": file_paths,
        "primary_path": primary_path,
    }
