from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RuntimeSource:
    path: Path
    mode: str = "projects"
    wing: str | None = None
    extract: str = "exchange"
    include_ignored: list[str] | None = None
    no_gitignore: bool = False
    limit: int = 0
    init_first: bool = False
    redetect_origin: bool = False


def _expand_path(value: str | os.PathLike[str]) -> Path:
    return Path(value).expanduser().resolve()


def load_manifest(manifest_path: str | os.PathLike[str]) -> list[RuntimeSource]:
    path = _expand_path(manifest_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_sources = payload.get("sources", [])
    if not isinstance(raw_sources, list):
        raise ValueError(f"manifest {path} must contain a 'sources' list")
    sources: list[RuntimeSource] = []
    for raw in raw_sources:
        if not isinstance(raw, dict):
            raise ValueError(f"manifest {path} contains a non-object source entry")
        source_path = raw.get("path")
        if not source_path:
            raise ValueError(f"manifest {path} contains a source without 'path'")
        mode = str(raw.get("mode", "projects"))
        if mode not in {"projects", "convos"}:
            raise ValueError(f"unsupported source mode {mode!r} in {path}")
        extract = str(raw.get("extract", "exchange"))
        if extract not in {"exchange", "general"}:
            raise ValueError(f"unsupported extract mode {extract!r} in {path}")
        include_ignored = raw.get("include_ignored") or []
        if not isinstance(include_ignored, list):
            raise ValueError(f"include_ignored for {source_path} must be a list")
        sources.append(
            RuntimeSource(
                path=_expand_path(str(source_path)),
                mode=mode,
                wing=raw.get("wing"),
                extract=extract,
                include_ignored=[str(item) for item in include_ignored],
                no_gitignore=bool(raw.get("no_gitignore", False)),
                limit=int(raw.get("limit", 0) or 0),
                init_first=bool(raw.get("init_first", False)),
                redetect_origin=bool(raw.get("redetect_origin", False)),
            )
        )
    return sources


def runtime_env(runtime_root: str | os.PathLike[str], palace_path: str | os.PathLike[str]) -> dict[str, str]:
    env = dict(os.environ)
    env["HOME"] = str(_expand_path(runtime_root))
    env["MEMPALACE_PALACE_PATH"] = str(_expand_path(palace_path))
    return env


def write_runtime_config(runtime_root: str | os.PathLike[str], palace_path: str | os.PathLike[str], collection_name: str = "mempalace_drawers") -> Path:
    runtime_root_path = _expand_path(runtime_root)
    config_dir = runtime_root_path / ".mempalace"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "palace_path": str(_expand_path(palace_path)),
                "collection_name": collection_name,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return config_path


def run_command(cmd: list[str], *, env: dict[str, str], cwd: str | os.PathLike[str]) -> None:
    subprocess.run(cmd, check=True, env=env, cwd=str(cwd))


def _init_command(python_bin: str, palace_path: Path, source: RuntimeSource) -> list[str]:
    return [
        python_bin,
        "-m",
        "mempalace",
        "--palace",
        str(palace_path),
        "init",
        str(source.path),
        "--yes",
        "--no-llm",
    ]


def _mine_command(python_bin: str, palace_path: Path, source: RuntimeSource) -> list[str]:
    cmd = [
        python_bin,
        "-m",
        "mempalace",
        "--palace",
        str(palace_path),
        "mine",
        str(source.path),
        "--mode",
        source.mode,
    ]
    if source.wing:
        cmd.extend(["--wing", source.wing])
    if source.mode == "convos":
        cmd.extend(["--extract", source.extract])
    if source.no_gitignore:
        cmd.append("--no-gitignore")
    for item in source.include_ignored or []:
        cmd.extend(["--include-ignored", item])
    if source.limit > 0:
        cmd.extend(["--limit", str(source.limit)])
    if source.redetect_origin:
        cmd.append("--redetect-origin")
    return cmd


def rebuild_runtime(
    *,
    manifest_path: str | os.PathLike[str],
    runtime_root: str | os.PathLike[str],
    python_bin: str | None = None,
    repo_root: str | os.PathLike[str] | None = None,
    reset: bool = True,
) -> dict[str, Any]:
    runtime_root_path = _expand_path(runtime_root)
    palace_path = runtime_root_path / "palace"
    if reset and runtime_root_path.exists():
        shutil.rmtree(runtime_root_path)
    runtime_root_path.mkdir(parents=True, exist_ok=True)
    config_path = write_runtime_config(runtime_root_path, palace_path)
    sources = load_manifest(manifest_path)
    for source in sources:
        if not source.path.exists():
            raise FileNotFoundError(f"manifest source does not exist: {source.path}")
    env = runtime_env(runtime_root_path, palace_path)
    repo_cwd = _expand_path(repo_root or Path.cwd())
    interpreter = python_bin or sys.executable
    commands_run: list[list[str]] = []
    for source in sources:
        if source.init_first:
            init_cmd = _init_command(interpreter, palace_path, source)
            run_command(init_cmd, env=env, cwd=repo_cwd)
            commands_run.append(init_cmd)
        mine_cmd = _mine_command(interpreter, palace_path, source)
        run_command(mine_cmd, env=env, cwd=repo_cwd)
        commands_run.append(mine_cmd)
    return {
        "manifest_path": str(_expand_path(manifest_path)),
        "runtime_root": str(runtime_root_path),
        "palace_path": str(palace_path),
        "config_path": str(config_path),
        "sources": [str(source.path) for source in sources],
        "commands_run": commands_run,
    }
