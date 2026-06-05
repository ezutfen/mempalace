#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from mempalace.runtime_rebuild import rebuild_runtime

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_ROOT = ROOT / "runtime"
DEFAULT_MANIFEST = DEFAULT_RUNTIME_ROOT / "rebuild_manifest.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rebuild a MemPalace runtime palace from a manifest of source directories.")
    parser.add_argument("--runtime-root", default=str(DEFAULT_RUNTIME_ROOT), help="Runtime root holding the derived palace and ~/.mempalace state")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="JSON manifest describing sources to mine into the runtime palace")
    parser.add_argument("--python-bin", default=None, help="Python interpreter used to invoke 'python -m mempalace' (default: current interpreter)")
    parser.add_argument("--no-reset", action="store_true", help="Do not delete the existing runtime root before rebuilding")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = rebuild_runtime(
        manifest_path=args.manifest,
        runtime_root=args.runtime_root,
        python_bin=args.python_bin,
        repo_root=ROOT,
        reset=not args.no_reset,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
