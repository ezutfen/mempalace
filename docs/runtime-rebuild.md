# MemPalace runtime rebuild

This repo now ships a real runtime rebuild entrypoint:

- `scripts/rebuild_index.py`
- default manifest: `runtime/rebuild_manifest.json`

What it does:

1. Creates a machine-local runtime root.
2. Writes `runtime_root/.mempalace/config.json` with `palace_path=runtime_root/palace`.
3. Sets `HOME=runtime_root` and `MEMPALACE_PALACE_PATH=runtime_root/palace` for all child `mempalace` commands.
4. Rebuilds the derived Chroma/SQLite palace by re-mining each source listed in the manifest.

Why `HOME=runtime_root` matters:

MemPalace stores more than the palace DB itself under `~/.mempalace/` — for example:
- `config.json`
- `known_entities.json`
- locks
- WAL files
- cache directories

By rebasing `HOME` to the runtime root during rebuild, the full runtime state stays machine-local and disposable instead of leaking into the operator's real `~/.mempalace`.

## Manifest format

`runtime/rebuild_manifest.json` is a JSON object with a `sources` array.

Example:

```json
{
  "sources": [
    {
      "path": "~/code/cca-repo",
      "mode": "projects"
    },
    {
      "path": "~/.claude/projects/-home-you-code-atlas",
      "mode": "convos",
      "wing": "atlas",
      "extract": "general"
    }
  ]
}
```

Supported fields per source:

- `path` — required source directory
- `mode` — `projects` or `convos` (default: `projects`)
- `wing` — optional explicit wing name
- `extract` — convos-only extraction mode: `exchange` or `general`
- `include_ignored` — optional list of project-relative paths to force-include
- `no_gitignore` — optional bool
- `limit` — optional int
- `init_first` — optional bool; runs `mempalace init --yes --no-llm` before mining
- `redetect_origin` — optional bool; forwards `--redetect-origin` to `mempalace mine`

## Commands

Rebuild from the repo defaults:

```bash
python scripts/rebuild_index.py
```

Rebuild to an explicit runtime root + manifest:

```bash
python scripts/rebuild_index.py \
  --runtime-root /tmp/mempalace-runtime \
  --manifest /tmp/rebuild_manifest.json
```

Preserve an existing runtime root instead of deleting it first:

```bash
python scripts/rebuild_index.py --no-reset
```

## Notes

- The runtime root is treated as derived state. Deleting it is expected and safe if your manifest still points at the real canonical source directories.
- `init_first` is opt-in because `mempalace init` writes project-local files like `mempalace.yaml` and `entities.json` into the source tree.
- A plain `projects` source without `init_first` is non-mutating to the source tree and is the safer default for rebuild automation.
