# AI Berkshire Codex Plugin Guide

This branch is a slim, generated distribution for the AI Berkshire Codex plugin. The canonical research workflows and shared tools live in `xbtlin/ai-berkshire` and in this fork's `main` branch.

## Branch Contract

- Keep `main` aligned with upstream.
- Keep `codex-plugin` limited to plugin runtime files, packaging automation, CI, and maintainer documentation.
- Never merge `main` into `codex-plugin`; doing so restores the full upstream tree.
- Generate from a clean upstream checkout with `plugin-packaging/sync_from_upstream.py`.
- Treat `UPSTREAM.lock.json` as the source provenance lock.

## Maintained Files

- `.agents/plugins/marketplace.json`: repository marketplace entry.
- `plugins/ai-berkshire/.codex-plugin/plugin.json`: plugin manifest and version.
- `plugin-packaging/`: generator, validator, release builder, and portability overlay.
- `.github/workflows/`: validation and release automation.
- `README.md` and `PLUGIN.md`: user and maintainer documentation.

## Generated Files

Do not manually edit these paths:

- `plugins/ai-berkshire/skills/`
- `plugins/ai-berkshire/tools/`
- `plugins/ai-berkshire/LICENSE`
- `plugins/ai-berkshire/NOTICE`
- `plugins/ai-berkshire/requirements-optional.txt`
- `plugins/ai-berkshire/BUILD-INFO.json`
- `UPSTREAM.lock.json`

Regenerate them from the local `main` branch with:

```bash
python3 plugin-packaging/sync_from_upstream.py --upstream-ref main
```

Or generate from a separate clean checkout with:

```bash
python3 plugin-packaging/sync_from_upstream.py --source-dir /path/to/ai-berkshire
```

## Required Checks

Before handing off plugin changes, run:

```bash
python3 plugin-packaging/sync_from_upstream.py --check --upstream-ref main
python3 plugin-packaging/validate.py
python3 plugin-packaging/build_release.py --output-dir dist --expected-version 0.2.0
```

Use `--source-dir` instead of `--upstream-ref` when validating against an independent checkout. Adjust the expected release version whenever the manifest version changes.

## Editing Rules

- Preserve the required `.codex-plugin/plugin.json` entry point and marketplace source path.
- Keep plugin tool references rooted at `{AI_BERKSHIRE_ROOT}/tools/`.
- Put packaging-only adaptations in `plugin-packaging/overlay/` or the generator, not in copied upstream files.
- If an upstream patch context no longer matches, review the upstream change before updating the adapter.
- Keep root-level tracked paths within the whitelist enforced by `plugin-packaging/validate.py`.
- Do not modify or move existing version tags when slimming the branch.

This project is for learning and research, not investment advice.
