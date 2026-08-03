#!/usr/bin/env python3
"""Build reproducible offline marketplace archives for the Codex plugin."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
import stat
import tarfile
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "ai-berkshire"
MANIFEST_PATH = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
MARKETPLACE_PATH = ROOT / ".agents" / "plugins" / "marketplace.json"
GUIDE_PATH = ROOT / "plugin-packaging" / "OFFLINE_INSTALL.md"
BUILD_INFO_PATH = PLUGIN_ROOT / "BUILD-INFO.json"
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
ARCHIVE_MTIME = 0
REQUIRED_ARCHIVE_FILES = {
    ".agents/plugins/marketplace.json",
    "plugins/ai-berkshire/.codex-plugin/plugin.json",
    "plugins/ai-berkshire/LICENSE",
    "plugins/ai-berkshire/NOTICE",
    "README.md",
    "RELEASE-INFO.json",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build ZIP, tar.gz, and SHA256SUMS assets for offline installation."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "dist",
        help="Directory for release assets (default: %(default)s)",
    )
    parser.add_argument(
        "--expected-version",
        help="Fail unless this version matches plugin.json; an optional leading v is accepted.",
    )
    return parser.parse_args()


def read_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.relative_to(ROOT)} must contain a JSON object")
    return payload


def plugin_version(expected: str | None) -> tuple[str, dict]:
    manifest = read_json(MANIFEST_PATH)
    version = manifest.get("version")
    if not isinstance(version, str) or not version:
        raise ValueError("plugin manifest has no version")
    if expected and expected.removeprefix("v") != version:
        raise ValueError(
            f"release version {expected!r} does not match plugin version {version!r}"
        )
    return version, manifest


def ensure_regular_tree(path: Path) -> None:
    if not path.is_dir():
        raise FileNotFoundError(path)
    links = [item for item in path.rglob("*") if item.is_symlink()]
    if links:
        names = ", ".join(str(item.relative_to(ROOT)) for item in links)
        raise ValueError(f"release inputs must not contain symlinks: {names}")


def stage_release(parent: Path, version: str, manifest: dict) -> Path:
    archive_root = parent / f"ai-berkshire-plugin-v{version}"
    marketplace_target = archive_root / ".agents" / "plugins" / "marketplace.json"
    plugin_target = archive_root / "plugins" / "ai-berkshire"

    ensure_regular_tree(PLUGIN_ROOT)
    marketplace_target.parent.mkdir(parents=True)
    shutil.copy2(MARKETPLACE_PATH, marketplace_target)
    shutil.copytree(PLUGIN_ROOT, plugin_target)

    guide = GUIDE_PATH.read_text(encoding="utf-8")
    if guide.count("{{VERSION}}") < 1:
        raise ValueError("offline install guide has no {{VERSION}} placeholder")
    (archive_root / "README.md").write_text(
        guide.replace("{{VERSION}}", version),
        encoding="utf-8",
        newline="\n",
    )

    build_info = read_json(BUILD_INFO_PATH)
    release_info = {
        "name": manifest.get("name"),
        "version": version,
        "tag": f"v{version}",
        "repository": manifest.get("repository"),
        "upstreamCommit": build_info.get("upstreamCommit"),
    }
    (archive_root / "RELEASE-INFO.json").write_text(
        json.dumps(release_info, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return archive_root


def ordered_paths(root: Path) -> list[Path]:
    return [root, *sorted(root.rglob("*"), key=lambda path: path.relative_to(root).as_posix())]


def normalized_mode(path: Path) -> int:
    if path.is_dir():
        return 0o755
    return 0o755 if path.stat().st_mode & stat.S_IXUSR else 0o644


def build_zip(staged_root: Path, destination: Path) -> None:
    with zipfile.ZipFile(
        destination,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in ordered_paths(staged_root):
            name = path.relative_to(staged_root.parent).as_posix()
            is_directory = path.is_dir()
            if is_directory:
                name += "/"
            info = zipfile.ZipInfo(name, ZIP_TIMESTAMP)
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            mode = normalized_mode(path)
            file_type = stat.S_IFDIR if is_directory else stat.S_IFREG
            info.external_attr = (file_type | mode) << 16
            if is_directory:
                info.external_attr |= 0x10
                archive.writestr(info, b"")
            else:
                archive.writestr(info, path.read_bytes())


def build_tar_gz(staged_root: Path, destination: Path) -> None:
    with destination.open("wb") as raw:
        with gzip.GzipFile(
            filename="",
            mode="wb",
            compresslevel=9,
            fileobj=raw,
            mtime=ARCHIVE_MTIME,
        ) as compressed:
            with tarfile.open(
                fileobj=compressed,
                mode="w|",
                format=tarfile.PAX_FORMAT,
            ) as archive:
                for path in ordered_paths(staged_root):
                    name = path.relative_to(staged_root.parent).as_posix()
                    info = archive.gettarinfo(str(path), arcname=name)
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    info.mtime = ARCHIVE_MTIME
                    info.mode = normalized_mode(path)
                    if path.is_file():
                        with path.open("rb") as source:
                            archive.addfile(info, source)
                    else:
                        archive.addfile(info)


def expected_files(staged_root: Path) -> set[str]:
    return {
        path.relative_to(staged_root).as_posix()
        for path in staged_root.rglob("*")
        if path.is_file()
    }


def validate_archives(staged_root: Path, zip_path: Path, tar_path: Path) -> None:
    expected = expected_files(staged_root)
    missing = REQUIRED_ARCHIVE_FILES - expected
    if missing:
        raise ValueError(f"staged release is missing required files: {sorted(missing)}")

    prefix = f"{staged_root.name}/"
    with zipfile.ZipFile(zip_path) as archive:
        zip_files = {
            item.filename.removeprefix(prefix)
            for item in archive.infolist()
            if not item.is_dir()
        }
        bad_zip = archive.testzip()
    if bad_zip is not None:
        raise ValueError(f"corrupt ZIP member: {bad_zip}")
    if zip_files != expected:
        raise ValueError("ZIP contents differ from staged release")

    with tarfile.open(tar_path, mode="r:gz") as archive:
        tar_files = {
            item.name.removeprefix(prefix)
            for item in archive.getmembers()
            if item.isfile()
        }
    if tar_files != expected:
        raise ValueError("tar.gz contents differ from staged release")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_checksums(paths: list[Path], destination: Path) -> None:
    lines = [f"{sha256(path)}  {path.name}" for path in paths]
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    args = parse_args()
    version, manifest = plugin_version(args.expected_version)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    archive_basename = f"ai-berkshire-plugin-v{version}"
    zip_path = output_dir / f"{archive_basename}.zip"
    tar_path = output_dir / f"{archive_basename}.tar.gz"
    sums_path = output_dir / "SHA256SUMS"

    with tempfile.TemporaryDirectory(prefix="ai-berkshire-release-") as temp:
        staged_root = stage_release(Path(temp), version, manifest)
        build_zip(staged_root, zip_path)
        build_tar_gz(staged_root, tar_path)
        validate_archives(staged_root, zip_path, tar_path)

    write_checksums([zip_path, tar_path], sums_path)

    for path in (zip_path, tar_path, sums_path):
        print(f"{path} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
