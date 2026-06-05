import json
from pathlib import Path

import pytest

import mempalace.runtime_rebuild as runtime_rebuild


def test_load_manifest_parses_sources(tmp_path: Path):
    manifest = tmp_path / "rebuild_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "sources": [
                    {"path": "~/code/project-a", "mode": "projects", "init_first": True},
                    {
                        "path": "/tmp/convos",
                        "mode": "convos",
                        "wing": "atlas",
                        "extract": "general",
                        "include_ignored": ["docs/generated"],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    sources = runtime_rebuild.load_manifest(manifest)

    assert len(sources) == 2
    assert sources[0].path == Path.home() / "code" / "project-a"
    assert sources[0].init_first is True
    assert sources[1].wing == "atlas"
    assert sources[1].extract == "general"
    assert sources[1].include_ignored == ["docs/generated"]


def test_rebuild_runtime_resets_runtime_writes_config_and_runs_sources(monkeypatch, tmp_path: Path):
    project_dir = tmp_path / "project"
    convo_dir = tmp_path / "convos"
    project_dir.mkdir()
    convo_dir.mkdir()
    runtime_root = tmp_path / "runtime"
    stale_file = runtime_root / "palace" / "stale.txt"
    stale_file.parent.mkdir(parents=True)
    stale_file.write_text("old", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "sources": [
                    {"path": str(project_dir), "mode": "projects", "init_first": True},
                    {"path": str(convo_dir), "mode": "convos", "wing": "atlas", "extract": "general"},
                ]
            }
        ),
        encoding="utf-8",
    )

    calls = []

    def fake_run(cmd, *, env, cwd):
        calls.append((cmd, env, cwd))

    monkeypatch.setattr(runtime_rebuild, "run_command", fake_run)

    result = runtime_rebuild.rebuild_runtime(
        manifest_path=manifest,
        runtime_root=runtime_root,
        python_bin="/fake/python",
        repo_root=tmp_path,
        reset=True,
    )

    config_path = runtime_root / ".mempalace" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert result["palace_path"] == str(runtime_root / "palace")
    assert config["palace_path"] == str(runtime_root / "palace")
    assert stale_file.exists() is False
    assert calls[0][0] == [
        "/fake/python",
        "-m",
        "mempalace",
        "--palace",
        str(runtime_root / "palace"),
        "init",
        str(project_dir),
        "--yes",
        "--no-llm",
    ]
    assert calls[1][0] == [
        "/fake/python",
        "-m",
        "mempalace",
        "--palace",
        str(runtime_root / "palace"),
        "mine",
        str(project_dir),
        "--mode",
        "projects",
    ]
    assert calls[2][0] == [
        "/fake/python",
        "-m",
        "mempalace",
        "--palace",
        str(runtime_root / "palace"),
        "mine",
        str(convo_dir),
        "--mode",
        "convos",
        "--wing",
        "atlas",
        "--extract",
        "general",
    ]
    assert calls[0][1]["HOME"] == str(runtime_root)
    assert calls[0][1]["MEMPALACE_PALACE_PATH"] == str(runtime_root / "palace")


def test_rebuild_runtime_rejects_missing_source(tmp_path: Path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"sources": [{"path": str(tmp_path / 'missing')}] }), encoding="utf-8")

    with pytest.raises(FileNotFoundError):
        runtime_rebuild.rebuild_runtime(
            manifest_path=manifest,
            runtime_root=tmp_path / "runtime",
            python_bin="/fake/python",
            repo_root=tmp_path,
        )
