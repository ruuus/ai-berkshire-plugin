#!/usr/bin/env python3
"""Generate the distributable Codex plugin from the current upstream tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "ai-berkshire"
OVERLAY_ROOT = ROOT / "plugin-packaging" / "overlay"
CODEX_SKILLS = ROOT / "codex-skills"
SOURCE_TOOLS = ROOT / "tools"
UPSTREAM_URL = "https://github.com/xbtlin/ai-berkshire"
EXPECTED_SKILL_COUNT = 21
GENERATED_PATHS = (
    "skills",
    "tools",
    "LICENSE",
    "NOTICE",
    "requirements-optional.txt",
    "BUILD-INFO.json",
)
CANONICAL_PATHS = (
    "skills",
    "codex-skills",
    "tools",
    "scripts/sync-codex-skills.py",
)

ORIGINAL_TOOL_NOTE = (
    "- Use shared project tools from `tools/` in this repository. Prefer "
    "running commands from the repository root with paths like "
    "`python3 tools/financial_rigor.py ...`; if the current thread starts "
    "outside the repo, locate the actual checkout path first instead of "
    "assuming a fixed home-directory path."
)
PLUGIN_TOOL_NOTE = (
    "- This skill is distributed inside the AI Berkshire plugin. Resolve "
    "`{AI_BERKSHIRE_ROOT}` to the absolute directory two levels above this "
    "`SKILL.md` (the plugin root). Do not resolve tool paths against the "
    "thread working directory.\n"
    "- Shared tools live in `{AI_BERKSHIRE_ROOT}/tools/`. Before every tool "
    "call, replace the token with the resolved absolute plugin root and "
    "verify the target exists. On Windows, use an available launcher such "
    "as `python` or `py -3` when `python3` is unavailable.\n"
    "- References such as `../financial-data/SKILL.md` are sibling skills "
    "inside the same plugin; resolve them relative to this `SKILL.md`."
)
MANUAL_SKILL_NOTE = """## Shared plugin resources

This hand-written Codex skill is distributed inside the AI Berkshire plugin.
Resolve `{AI_BERKSHIRE_ROOT}` to the absolute directory two levels above this
`SKILL.md`. Shared validation and audit tools live in
`{AI_BERKSHIRE_ROOT}/tools/`; replace the token with the absolute path and
verify the target exists before invoking a tool. Never resolve tool paths
against the current thread working directory.

"""


class SyncError(RuntimeError):
    """Raised when upstream changed in a way that needs manual review."""


def command_output(args: list[str]) -> str:
    result = subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise SyncError(f"{' '.join(args)} failed: {detail}")
    return result.stdout.strip()


def resolve_ref(requested: str) -> str:
    candidates = [requested]
    if requested == "main":
        candidates.append("origin/main")
    for candidate in candidates:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", f"{candidate}^{{commit}}"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            return candidate
    raise SyncError(
        f"cannot resolve upstream ref {requested!r}; fetch it before syncing"
    )


def ensure_canonical_tree(ref: str) -> None:
    diff = subprocess.run(
        ["git", "diff", "--quiet", ref, "--", *CANONICAL_PATHS],
        cwd=ROOT,
        check=False,
    )
    if diff.returncode == 1:
        raise SyncError(
            f"canonical upstream files differ from {ref}; update that ref and "
            "merge it into codex-plugin before regenerating"
        )
    if diff.returncode:
        raise SyncError(f"git diff against {ref} failed")

    untracked = command_output(
        ["git", "ls-files", "--others", "--exclude-standard", "--", *CANONICAL_PATHS]
    )
    if untracked:
        raise SyncError(
            "untracked canonical source files are present:\n"
            + "\n".join(f"  {line}" for line in untracked.splitlines())
        )

    result = subprocess.run(
        [sys.executable, "scripts/sync-codex-skills.py", "--check"],
        cwd=ROOT,
        check=False,
    )
    if result.returncode:
        raise SyncError(
            "codex-skills are stale; regenerate them in the upstream tree first"
        )


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SyncError(f"{label}: expected one source match, found {count}")
    return text.replace(old, new, 1)


def adapt_generated_skill(text: str, label: str) -> str:
    text = replace_once(text, ORIGINAL_TOOL_NOTE, PLUGIN_TOOL_NOTE, label)
    output: list[str] = []
    for line in text.splitlines(keepends=True):
        if line.startswith("description:") or "This skill is generated from" in line:
            output.append(line)
            continue
        line = re.sub(
            r"(?<![A-Za-z0-9_./-])skills/([a-z0-9-]+)\.md",
            r"../\1/SKILL.md",
            line,
        )
        line = re.sub(
            r"(?<![A-Za-z0-9_}/.-])tools/",
            "{AI_BERKSHIRE_ROOT}/tools/",
            line,
        )
        output.append(line)
    return "".join(output)


def adapt_manual_skill(text: str, label: str) -> str:
    if "{AI_BERKSHIRE_ROOT}" in text:
        raise SyncError(f"{label}: manual plugin note already present upstream")
    return replace_once(
        text,
        "# Investment Memo Craft\n\n",
        "# Investment Memo Craft\n\n" + MANUAL_SKILL_NOTE,
        label,
    )


def patch_ashare_tool(text: str) -> str:
    text = replace_once(
        text,
        "设计原则：独立模块，不影响现有工具；使用 curl 直连绕过系统代理。",
        "设计原则：独立模块，不影响现有工具；优先 curl，回退 Python urllib，均不继承系统代理。",
        "ashare_data.py documentation",
    )
    text = replace_once(
        text,
        """import argparse
import json
import os
import subprocess
import sys
from decimal import Decimal, ROUND_HALF_EVEN
""",
        """import argparse
import json
import os
import shutil
import subprocess
import sys
from decimal import Decimal, ROUND_HALF_EVEN
from urllib.error import URLError
from urllib.request import ProxyHandler, Request, build_opener
""",
        "ashare_data.py imports",
    )
    text = replace_once(
        text,
        "_TIMEOUT = 15\n",
        """_TIMEOUT = 15
_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
""",
        "ashare_data.py constants",
    )
    old = """def _curl(url):
    \"\"\"用 curl --noproxy 直连，绕过系统代理。\"\"\"
    result = subprocess.run(
        [\"/usr/bin/curl\", \"-s\", \"--noproxy\", \"*\",
         \"-H\", \"User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)\",
         url],
        capture_output=True, timeout=_TIMEOUT,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise ConnectionError(f\"请求失败: {url}\")
    # 腾讯行情 API 返回 GBK 编码，其他返回 UTF-8
    try:
        return result.stdout.decode(\"utf-8\")
    except UnicodeDecodeError:
        return result.stdout.decode(\"gbk\")
"""
    new = """def _decode_response(payload):
    \"\"\"Decode Tencent's GBK response and UTF-8 JSON responses.\"\"\"
    try:
        return payload.decode(\"utf-8\")
    except UnicodeDecodeError:
        return payload.decode(\"gbk\")


def _urllib_get(url):
    \"\"\"Fetch directly with stdlib without inheriting system proxy settings.\"\"\"
    opener = build_opener(ProxyHandler({}))
    request = Request(url, headers={\"User-Agent\": _USER_AGENT})
    with opener.open(request, timeout=_TIMEOUT) as response:
        return response.read()


def _curl(url):
    \"\"\"Cross-platform direct HTTP fetch with curl and stdlib fallbacks.\"\"\"
    errors = []
    curl = shutil.which(\"curl\") or shutil.which(\"curl.exe\")
    if curl:
        try:
            result = subprocess.run(
                [
                    curl,
                    \"-s\",
                    \"--noproxy\",
                    \"*\",
                    \"-H\",
                    f\"User-Agent: {_USER_AGENT}\",
                    url,
                ],
                capture_output=True,
                timeout=_TIMEOUT,
            )
            if result.returncode == 0 and result.stdout.strip():
                return _decode_response(result.stdout)
            errors.append(f\"curl exit={result.returncode}\")
        except (OSError, subprocess.SubprocessError) as error:
            errors.append(f\"curl: {error}\")

    try:
        payload = _urllib_get(url)
        if payload.strip():
            return _decode_response(payload)
        errors.append(\"urllib: empty response\")
    except (OSError, URLError) as error:
        errors.append(f\"urllib: {error}\")

    detail = \"; \".join(errors) if errors else \"no HTTP backend available\"
    raise ConnectionError(f\"请求失败: {url} ({detail})\")
"""
    return replace_once(text, old, new, "ashare_data.py HTTP backend")


def patch_xueqiu_tool(text: str) -> str:
    text = replace_once(
        text,
        "--output ../reports/拼多多/段永平雪球发言-PDD相关.md",
        "--output reports/拼多多/段永平雪球发言-PDD相关.md",
        "xueqiu_scraper.py report path",
    )
    text = replace_once(
        text,
        "登录态缓存默认 /tmp/xueqiu_state.json，可用 --state-path 覆盖。",
        "登录态缓存默认写入操作系统临时目录，可用 --state-path 覆盖。",
        "xueqiu_scraper.py temporary path documentation",
    )
    text = replace_once(
        text,
        """import argparse
import asyncio
import json
import os
import random
import re
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright
""",
        """import argparse
import asyncio
import json
import os
import random
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ModuleNotFoundError:
    async_playwright = None


TEMP_DIR = Path(tempfile.gettempdir())
DEFAULT_STATE_PATH = TEMP_DIR / \"xueqiu_state.json\"
OPTIONAL_REQUIREMENTS = Path(__file__).resolve().parents[1] / \"requirements-optional.txt\"
""",
        "xueqiu_scraper.py imports",
    )
    text = replace_once(
        text,
        """    ap.add_argument('--state-path', type=str, default='/tmp/xueqiu_state.json',
                    help='登录态缓存文件（默认 /tmp/xueqiu_state.json）')
""",
        """    ap.add_argument('--state-path', type=str, default=str(DEFAULT_STATE_PATH),
                    help=f'登录态缓存文件（默认 {DEFAULT_STATE_PATH}）')
""",
        "xueqiu_scraper.py state argument",
    )
    text = replace_once(
        text,
        """    if not args.user_id:
        print(\"需要 --user-id\")
        return

    progress_path = args.state_path + f'.progress.{args.user_id}'
    raw_json = args.raw_json or f'/tmp/xueqiu_{args.user_id}_raw.json'
""",
        """    if not args.user_id:
        print(\"需要 --user-id\")
        return

    if async_playwright is None:
        raise SystemExit(
            \"缺少可选依赖 Playwright。请先运行：\\n\"
            f'  \"{sys.executable}\" -m pip install -r \"{OPTIONAL_REQUIREMENTS}\"\\n'
            f'  \"{sys.executable}\" -m playwright install chromium'
        )

    progress_path = args.state_path + f'.progress.{args.user_id}'
    raw_json = args.raw_json or str(TEMP_DIR / f'xueqiu_{args.user_id}_raw.json')
""",
        "xueqiu_scraper.py optional dependency guard",
    )
    return text


def write_text_lf(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def write_json(path: Path, payload: dict) -> None:
    write_text_lf(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )


def provenance(ref: str) -> dict[str, str]:
    return {
        "commit": command_output(["git", "rev-parse", f"{ref}^{{commit}}"]),
        "commitDate": command_output(["git", "show", "-s", "--format=%cI", ref]),
    }


def build_expected(destination: Path, ref: str) -> dict:
    skills_out = destination / "skills"
    tools_out = destination / "tools"
    shutil.copytree(CODEX_SKILLS, skills_out, copy_function=shutil.copy2)
    shutil.copytree(SOURCE_TOOLS, tools_out, copy_function=shutil.copy2)

    skill_dirs = sorted(
        path for path in skills_out.iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    )
    if len(skill_dirs) != EXPECTED_SKILL_COUNT:
        raise SyncError(
            f"found {len(skill_dirs)} Codex skills; expected {EXPECTED_SKILL_COUNT}"
        )

    for skill_dir in skill_dirs:
        skill_path = skill_dir / "SKILL.md"
        text = skill_path.read_text(encoding="utf-8")
        if skill_dir.name == "investment-memo-craft":
            adapted = adapt_manual_skill(text, str(skill_path))
        else:
            adapted = adapt_generated_skill(text, str(skill_path))
        write_text_lf(skill_path, adapted)

    ashare_path = tools_out / "ashare_data.py"
    write_text_lf(
        ashare_path,
        patch_ashare_tool(ashare_path.read_text(encoding="utf-8")),
    )
    xueqiu_path = tools_out / "xueqiu_scraper.py"
    write_text_lf(
        xueqiu_path,
        patch_xueqiu_tool(xueqiu_path.read_text(encoding="utf-8")),
    )
    shutil.copy2(OVERLAY_ROOT / "tools" / "plugin_doctor.py", tools_out)
    shutil.copy2(ROOT / "LICENSE", destination / "LICENSE")
    shutil.copy2(OVERLAY_ROOT / "NOTICE", destination / "NOTICE")
    shutil.copy2(
        OVERLAY_ROOT / "requirements-optional.txt",
        destination / "requirements-optional.txt",
    )

    manifest = json.loads(
        (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    source = provenance(ref)
    tool_count = sum(1 for path in tools_out.iterdir() if path.is_file())
    build_info = {
        "plugin": manifest["name"],
        "version": manifest["version"],
        "upstream": UPSTREAM_URL,
        "upstreamCommit": source["commit"],
        "upstreamCommitDate": source["commitDate"],
        "skillCount": len(skill_dirs),
        "toolFileCount": tool_count,
    }
    write_json(destination / "BUILD-INFO.json", build_info)
    return {
        "upstream": UPSTREAM_URL,
        "sourceBranch": "main",
        "sourceCommit": source["commit"],
        "sourceCommitDate": source["commitDate"],
        "pluginVersion": manifest["version"],
        "skillCount": len(skill_dirs),
        "toolFileCount": tool_count,
    }


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def tree_state(path: Path) -> dict[str, tuple[str, int]]:
    if not path.exists():
        raise SyncError(f"missing generated path: {path}")
    if path.is_file():
        return {
            path.name: (
                file_digest(path),
                stat.S_IMODE(path.stat().st_mode),
            )
        }
    state: dict[str, tuple[str, int]] = {}
    for item in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
        state[str(item.relative_to(path))] = (
            file_digest(item),
            stat.S_IMODE(item.stat().st_mode),
        )
    return state


def compare_generated(expected_plugin: Path, expected_lock: Path) -> None:
    stale: list[str] = []
    for relative in GENERATED_PATHS:
        expected = expected_plugin / relative
        actual = PLUGIN_ROOT / relative
        try:
            if tree_state(expected) != tree_state(actual):
                stale.append(str(actual.relative_to(ROOT)))
        except SyncError:
            stale.append(str(actual.relative_to(ROOT)))
    if not (ROOT / "UPSTREAM.lock.json").is_file():
        stale.append("UPSTREAM.lock.json")
    elif tree_state(expected_lock) != tree_state(ROOT / "UPSTREAM.lock.json"):
        stale.append("UPSTREAM.lock.json")

    if stale:
        raise SyncError(
            "generated plugin files are stale:\n"
            + "\n".join(f"  {path}" for path in stale)
            + "\nrun: python3 plugin-packaging/sync_from_upstream.py"
        )


def install_generated(expected_plugin: Path, expected_lock: Path) -> None:
    PLUGIN_ROOT.mkdir(parents=True, exist_ok=True)
    for relative in GENERATED_PATHS:
        source = expected_plugin / relative
        target = PLUGIN_ROOT / relative
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
        if source.is_dir():
            shutil.copytree(source, target, copy_function=shutil.copy2)
        else:
            shutil.copy2(source, target)
    shutil.copy2(expected_lock, ROOT / "UPSTREAM.lock.json")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate the AI Berkshire Codex plugin from the canonical tree."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify committed generated files without changing them.",
    )
    parser.add_argument(
        "--upstream-ref",
        default="main",
        help="Git ref that represents the mirrored upstream main branch.",
    )
    args = parser.parse_args()

    try:
        ref = resolve_ref(args.upstream_ref)
        ensure_canonical_tree(ref)
        with tempfile.TemporaryDirectory(prefix="ai-berkshire-plugin-") as temp:
            temp_root = Path(temp)
            expected_plugin = temp_root / "plugin"
            expected_plugin.mkdir()
            lock = build_expected(expected_plugin, ref)
            expected_lock = temp_root / "UPSTREAM.lock.json"
            write_json(expected_lock, lock)
            if args.check:
                compare_generated(expected_plugin, expected_lock)
                action = "verified"
            else:
                install_generated(expected_plugin, expected_lock)
                action = "generated"
        print(
            f"{action} ai-berkshire {lock['pluginVersion']} from "
            f"{lock['sourceCommit']} ({lock['skillCount']} skills, "
            f"{lock['toolFileCount']} tool files)"
        )
        return 0
    except (OSError, KeyError, json.JSONDecodeError, SyncError) as error:
        print(f"sync failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
