import tempfile
from pathlib import Path

from flexo_syside_lib.library_sync import (
    build_sysand_command,
    deduplicate_model_filenames,
    find_primary_model_file,
    materialize_textual_models,
    normalize_sysand_clone_iri,
)


def test_build_sysand_command_includes_resolution_flags():
    cmd = build_sysand_command(
        "sysand",
        ["clone", "--iri", "pkg:sysand/example/lib", "--target", "/tmp/lib", "--version", "1.2.3"],
        config_file="/home/jovyan/sysand.toml",
        index_urls=["https://idx1.example", "https://idx2.example"],
        default_index_urls=["https://default.example"],
        include_std=True,
    )

    assert cmd == [
        "sysand",
        "--config-file",
        "/home/jovyan/sysand.toml",
        "clone",
        "--iri",
        "pkg:sysand/example/lib",
        "--target",
        "/tmp/lib",
        "--version",
        "1.2.3",
        "--index",
        "https://idx1.example,https://idx2.example",
        "--default-index",
        "https://default.example",
        "--include-std",
    ]


def test_normalize_sysand_clone_iri_expands_shorthand():
    assert normalize_sysand_clone_iri("hugoormo/fibo2sysmlv2") == "pkg:sysand/hugoormo/fibo2sysmlv2"
    assert normalize_sysand_clone_iri("pkg:sysand/hugoormo/fibo2sysmlv2") == "pkg:sysand/hugoormo/fibo2sysmlv2"


def test_find_primary_model_file_skips_dot_sysand_tree():
    with tempfile.TemporaryDirectory() as tmp_dir:
        library_dir = Path(tmp_dir) / "demo"
        (library_dir / ".sysand" / "dep").mkdir(parents=True)
        (library_dir / ".sysand" / "dep" / "dep.sysml").write_text("package Dep; end;", encoding="utf-8")
        (library_dir / "root").mkdir()
        (library_dir / "root" / "main.sysml").write_text("package Main; end;", encoding="utf-8")

        found = find_primary_model_file(library_dir)

        assert found == library_dir / "root" / "main.sysml"


def test_deduplicate_model_filenames_normalizes_and_uniquifies_names():
    models = deduplicate_model_filenames(
        [
            {"name": "Package A", "text": "package A;"},
            {"name": "Package A", "text": "package A2;"},
            {"name": "domain.kerml", "text": "package Domain;"},
        ]
    )

    assert [model["name"] for model in models] == [
        "Package A.sysml",
        "Package A-2.sysml",
        "domain.kerml",
    ]


def test_materialize_textual_models_replaces_existing_library():
    with tempfile.TemporaryDirectory() as tmp_dir:
        install_root = Path(tmp_dir) / "sysmlenv"
        install_root.mkdir()
        stale_dir = install_root / "Demo Library"
        stale_dir.mkdir()
        (stale_dir / "stale.sysml").write_text("package Stale; end;", encoding="utf-8")

        result = materialize_textual_models(
            install_root,
            "Demo Library",
            [{"name": "root/main.sysml", "text": "package Main; end;"}],
        )

        assert result["library_name"] == "Demo Library"
        assert result["primary_path"] == Path(result["file_paths"][0])
        assert not (stale_dir / "stale.sysml").exists()
        assert (stale_dir / "root" / "main.sysml").read_text(encoding="utf-8") == "package Main; end;"
