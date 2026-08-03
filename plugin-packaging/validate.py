#!/usr/bin/env python3
"""Validate the generated AI Berkshire Codex plugin without network access."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "ai-berkshire"
SKILLS_ROOT = PLUGIN_ROOT / "skills"
MANIFEST_PATH = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
MARKETPLACE_PATH = ROOT / ".agents" / "plugins" / "marketplace.json"
LOCK_PATH = ROOT / "UPSTREAM.lock.json"
BUILD_INFO_PATH = PLUGIN_ROOT / "BUILD-INFO.json"
EXPECTED_SKILL_COUNT = 21
CANONICAL_PATHS = (
    "skills",
    "codex-skills",
    "tools",
    "scripts/sync-codex-skills.py",
)
SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
BARE_TOOL_PATH = re.compile(r"(?<![A-Za-z0-9_}/.-])tools/")
CANONICAL_SKILL_REF = re.compile(r"skills/([a-z0-9-]+)\.md")
SIBLING_SKILL_REF = re.compile(r"\.\./([a-z0-9-]+)/SKILL\.md")


class Validator:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def require(self, condition: bool, message: str) -> None:
        if not condition:
            self.errors.append(message)

    def json_file(self, path: Path) -> dict:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            self.errors.append(f"missing {path.relative_to(ROOT)}")
            return {}
        except json.JSONDecodeError as error:
            self.errors.append(f"invalid JSON in {path.relative_to(ROOT)}: {error}")
            return {}
        if not isinstance(payload, dict):
            self.errors.append(f"{path.relative_to(ROOT)} must contain a JSON object")
            return {}
        return payload


def frontmatter(text: str, path: Path, validator: Validator) -> dict[str, str]:
    if not text.startswith("---\n"):
        validator.errors.append(f"{path.relative_to(ROOT)} has no YAML frontmatter")
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        validator.errors.append(f"{path.relative_to(ROOT)} has unclosed frontmatter")
        return {}
    result: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip().strip("\"'")
    return result


def validate_manifest(validator: Validator) -> tuple[dict, dict, dict]:
    manifest = validator.json_file(MANIFEST_PATH)
    marketplace = validator.json_file(MARKETPLACE_PATH)
    lock = validator.json_file(LOCK_PATH)

    validator.require(manifest.get("name") == "ai-berkshire", "manifest name must be ai-berkshire")
    version = manifest.get("version")
    validator.require(
        isinstance(version, str) and SEMVER.fullmatch(version) is not None,
        "manifest version must be SemVer",
    )
    validator.require(manifest.get("skills") == "./skills/", "manifest skills path must be ./skills/")
    validator.require(manifest.get("license") == "MIT", "manifest license must be MIT")
    validator.require(
        manifest.get("repository") == "https://github.com/ruuus/ai-berkshire-plugin",
        "manifest repository must point to the maintained fork",
    )
    interface = manifest.get("interface", {})
    validator.require(isinstance(interface, dict), "manifest interface must be an object")
    if isinstance(interface, dict):
        validator.require(
            interface.get("displayName") == "AI Berkshire",
            "interface displayName must be AI Berkshire",
        )
        validator.require(
            interface.get("category") == "Productivity",
            "interface category must be Productivity",
        )

    validator.require(
        marketplace.get("name") == "ai-berkshire-plugin",
        "marketplace name must be ai-berkshire-plugin",
    )
    plugins = marketplace.get("plugins")
    validator.require(
        isinstance(plugins, list) and len(plugins) == 1,
        "marketplace must contain exactly one plugin",
    )
    if isinstance(plugins, list) and len(plugins) == 1 and isinstance(plugins[0], dict):
        entry = plugins[0]
        validator.require(entry.get("name") == "ai-berkshire", "marketplace plugin name mismatch")
        validator.require(
            entry.get("source") == {
                "source": "local",
                "path": "./plugins/ai-berkshire",
            },
            "marketplace source must be the repository-local plugin path",
        )
        validator.require(
            entry.get("policy") == {
                "installation": "AVAILABLE",
                "authentication": "ON_INSTALL",
            },
            "marketplace policy mismatch",
        )
        validator.require(entry.get("category") == "Productivity", "marketplace category mismatch")

    validator.require(lock.get("pluginVersion") == version, "lock version differs from manifest")
    validator.require(
        lock.get("skillCount") == EXPECTED_SKILL_COUNT,
        "lock skill count mismatch",
    )
    return manifest, marketplace, lock


def skill_files() -> list[Path]:
    return sorted(SKILLS_ROOT.glob("*" + "/SKILL.md"))


def validate_skills(validator: Validator) -> list[Path]:
    skill_paths = skill_files()
    validator.require(
        len(skill_paths) == EXPECTED_SKILL_COUNT,
        f"expected {EXPECTED_SKILL_COUNT} skills, found {len(skill_paths)}",
    )
    seen: set[str] = set()
    skill_names = {path.parent.name for path in skill_paths}

    for path in skill_paths:
        text = path.read_text(encoding="utf-8")
        metadata = frontmatter(text, path, validator)
        name = metadata.get("name", "")
        validator.require(NAME.fullmatch(name) is not None, f"{path}: invalid skill name {name!r}")
        validator.require(name == path.parent.name, f"{path}: frontmatter name differs from directory")
        validator.require(name not in seen, f"duplicate skill name: {name}")
        seen.add(name)
        validator.require(
            "{AI_BERKSHIRE_ROOT}" in text,
            f"{path.relative_to(ROOT)} has no plugin-root resolution instruction",
        )
        validator.require(
            "/usr/bin/curl" not in text
            and "/tmp/xueqiu" not in text
            and "~/ai-berkshire" not in text,
            f"{path.relative_to(ROOT)} contains a machine-specific path",
        )

        for line_number, line in enumerate(text.splitlines(), 1):
            if BARE_TOOL_PATH.search(line):
                validator.errors.append(
                    f"{path.relative_to(ROOT)}:{line_number} contains unresolved bare tools/"
                )
            if (
                CANONICAL_SKILL_REF.search(line)
                and not line.startswith("description:")
                and "This skill is generated from" not in line
                and "Do not add a same-named" not in line
            ):
                validator.errors.append(
                    f"{path.relative_to(ROOT)}:{line_number} contains unresolved canonical skill path"
                )
        for target in SIBLING_SKILL_REF.findall(text):
            validator.require(
                target in skill_names,
                f"{path.relative_to(ROOT)} references missing sibling skill {target}",
            )

    return skill_paths


def compile_python(validator: Validator) -> list[Path]:
    paths = sorted(PLUGIN_ROOT.glob("tools/*.py"))
    paths.extend(sorted((ROOT / "plugin-packaging").glob("*.py")))
    for path in paths:
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except (OSError, SyntaxError, UnicodeError) as error:
            validator.errors.append(f"cannot compile {path.relative_to(ROOT)}: {error}")
    return paths


def validate_portability(validator: Validator) -> None:
    ashare = (PLUGIN_ROOT / "tools" / "ashare_data.py").read_text(encoding="utf-8")
    validator.require('shutil.which("curl")' in ashare, "ashare_data.py has no PATH-based curl lookup")
    validator.require("ProxyHandler({})" in ashare, "ashare_data.py has no proxy-free urllib fallback")
    validator.require('"/usr/bin/curl"' not in ashare, "ashare_data.py still hard-codes /usr/bin/curl")

    xueqiu = (PLUGIN_ROOT / "tools" / "xueqiu_scraper.py").read_text(encoding="utf-8")
    validator.require("except ModuleNotFoundError:" in xueqiu, "xueqiu scraper eagerly requires Playwright")
    validator.require("tempfile.gettempdir()" in xueqiu, "xueqiu scraper hard-codes its temp directory")
    validator.require("/tmp/xueqiu_state.json" not in xueqiu, "xueqiu scraper retains a Unix temp path")


def validate_build_info(validator: Validator, manifest: dict, lock: dict) -> None:
    build = validator.json_file(BUILD_INFO_PATH)
    skill_count = len(skill_files())
    tool_count = len([path for path in (PLUGIN_ROOT / "tools").iterdir() if path.is_file()])
    validator.require(build.get("version") == manifest.get("version"), "build version mismatch")
    validator.require(build.get("upstreamCommit") == lock.get("sourceCommit"), "build commit mismatch")
    validator.require(build.get("skillCount") == skill_count, "build skill count mismatch")
    validator.require(build.get("toolFileCount") == tool_count, "build tool count mismatch")
    validator.require(lock.get("toolFileCount") == tool_count, "lock tool count mismatch")
    validator.require(
        (PLUGIN_ROOT / "LICENSE").read_bytes() == (ROOT / "LICENSE").read_bytes(),
        "plugin LICENSE differs from upstream LICENSE",
    )

    source_commit = lock.get("sourceCommit")
    if not isinstance(source_commit, str) or not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        validator.errors.append("lock sourceCommit must be a full Git SHA")
        return
    exists = subprocess.run(
        ["git", "cat-file", "-e", f"{source_commit}^{{commit}}"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    validator.require(exists.returncode == 0, "lock source commit is unavailable in Git history")
    if exists.returncode == 0:
        diff = subprocess.run(
            ["git", "diff", "--quiet", source_commit, "--", *CANONICAL_PATHS],
            cwd=ROOT,
            check=False,
        )
        validator.require(
            diff.returncode == 0,
            "canonical source tree differs from the commit recorded in UPSTREAM.lock.json",
        )


def smoke_help(validator: Validator) -> None:
    names = (
        "financial_rigor.py",
        "report_audit.py",
        "ashare_data.py",
        "twstock_data.py",
        "xueqiu_scraper.py",
    )
    for name in names:
        result = subprocess.run(
            [sys.executable, str(PLUGIN_ROOT / "tools" / name), "--help"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        validator.require(
            result.returncode == 0,
            f"{name} --help failed: {(result.stderr or result.stdout).strip()}",
        )

    doctor = subprocess.run(
        [sys.executable, str(PLUGIN_ROOT / "tools" / "plugin_doctor.py"), "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    validator.require(
        doctor.returncode == 0,
        f"plugin_doctor.py failed: {(doctor.stderr or doctor.stdout).strip()}",
    )
    if doctor.returncode == 0:
        try:
            payload = json.loads(doctor.stdout)
            statuses = {item.get("status") for item in payload.get("checks", [])}
            validator.require("fail" not in statuses, "plugin doctor reported a failed check")
        except json.JSONDecodeError as error:
            validator.errors.append(f"plugin doctor returned invalid JSON: {error}")


def main() -> int:
    validator = Validator()
    manifest, _, lock = validate_manifest(validator)
    validate_skills(validator)
    compile_python(validator)

    required = (
        PLUGIN_ROOT / "tools" / "ashare_data.py",
        PLUGIN_ROOT / "tools" / "xueqiu_scraper.py",
        PLUGIN_ROOT / "LICENSE",
        ROOT / "LICENSE",
    )
    if all(path.is_file() for path in required):
        validate_portability(validator)
        validate_build_info(validator, manifest, lock)
        smoke_help(validator)

    if validator.errors:
        print("Plugin validation failed:", file=sys.stderr)
        for error in validator.errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(
        f"Validated ai-berkshire {manifest.get('version')} "
        f"({EXPECTED_SKILL_COUNT} skills, offline checks passed)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
