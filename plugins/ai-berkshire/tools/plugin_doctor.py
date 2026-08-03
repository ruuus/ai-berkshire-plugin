#!/usr/bin/env python3
"""Offline portability checks for the AI Berkshire Codex plugin."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import shutil
import sys
import tempfile
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = PLUGIN_ROOT / "skills"
TOOLS_ROOT = PLUGIN_ROOT / "tools"
MANIFEST_PATH = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
CORE_TOOLS = ("financial_rigor.py", "report_audit.py")


def result(name: str, status: str, detail: str) -> dict[str, str]:
    return {"name": name, "status": status, "detail": detail}


def run_checks() -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []

    version = platform.python_version()
    checks.append(
        result(
            "python",
            "pass" if sys.version_info >= (3, 8) else "fail",
            f"Python {version}; requires Python 3.8+",
        )
    )

    if MANIFEST_PATH.is_file():
        try:
            manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
            valid = manifest.get("name") == "ai-berkshire"
            checks.append(
                result(
                    "manifest",
                    "pass" if valid else "fail",
                    f"name={manifest.get('name')!r}, version={manifest.get('version')!r}",
                )
            )
        except (OSError, json.JSONDecodeError) as error:
            checks.append(result("manifest", "fail", str(error)))
    else:
        checks.append(result("manifest", "fail", f"missing {MANIFEST_PATH}"))

    skill_count = 0
    if SKILLS_ROOT.is_dir():
        skill_count = sum(
            1
            for child in SKILLS_ROOT.iterdir()
            if child.is_dir() and (child / "SKILL.md").is_file()
        )
    checks.append(
        result(
            "skills",
            "pass" if skill_count == 21 else "fail",
            f"found {skill_count}; expected 21",
        )
    )

    missing_core = [name for name in CORE_TOOLS if not (TOOLS_ROOT / name).is_file()]
    checks.append(
        result(
            "core-tools",
            "fail" if missing_core else "pass",
            f"missing: {', '.join(missing_core)}"
            if missing_core
            else "financial rigor and report audit available",
        )
    )

    playwright_available = importlib.util.find_spec("playwright") is not None
    checks.append(
        result(
            "playwright",
            "pass" if playwright_available else "warn",
            "available for xueqiu_scraper.py"
            if playwright_available
            else "optional; install requirements-optional.txt and Chromium for xueqiu_scraper.py",
        )
    )

    curl = shutil.which("curl") or shutil.which("curl.exe")
    checks.append(
        result(
            "http-backend",
            "pass",
            f"curl={curl}"
            if curl
            else "curl not found; ashare_data.py will use Python urllib",
        )
    )

    temp_dir = Path(tempfile.gettempdir())
    checks.append(
        result(
            "temporary-directory",
            "pass" if temp_dir.is_dir() and os.access(temp_dir, os.W_OK) else "fail",
            str(temp_dir),
        )
    )

    return checks


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check AI Berkshire plugin portability and optional dependencies."
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat optional dependency warnings as failures.",
    )
    args = parser.parse_args()

    checks = run_checks()
    if args.json:
        print(
            json.dumps(
                {"plugin_root": str(PLUGIN_ROOT), "checks": checks},
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        labels = {"pass": "PASS", "warn": "WARN", "fail": "FAIL"}
        print(f"AI Berkshire plugin doctor: {PLUGIN_ROOT}")
        for check in checks:
            print(f"[{labels[check['status']]}] {check['name']}: {check['detail']}")

    failed = any(check["status"] == "fail" for check in checks)
    warned = any(check["status"] == "warn" for check in checks)
    return 1 if failed or (args.strict and warned) else 0


if __name__ == "__main__":
    raise SystemExit(main())
