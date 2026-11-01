"""T+ project scaffolding and installation diagnostics.

No third-party code is downloaded or executed by these helpers.
"""
from __future__ import annotations
from pathlib import Path
import re
import shutil
import sys
import tomllib
import argparse
import hashlib
import json
import os
import stat
import tempfile
from updater import ALL_COMPILER
from standard_modules import MODULES


class ProjectError(Exception):
    pass


def create_project(path: str) -> Path:
    root = Path(path).expanduser().absolute()
    name = root.name
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]{0,63}", name):
        raise ProjectError("Project name must use letters, digits, '_' or '-'")
    if root.exists():
        raise ProjectError(f"Project already exists: {root}. Existing files were not changed.")
    if not root.parent.is_dir():
        raise ProjectError(f"Parent folder not found: {root.parent}")
    if root.parent.is_symlink():
        raise ProjectError("Choose a real parent directory, not a symlink")
    root.mkdir()
    try:
        (root / "src").mkdir()
        (root / "tests").mkdir()
        (root / "teka.toml").write_text(
            '[project]\n'
            f'name = "{name}"\n'
            'version = "0.1.0"\n\n'
            '[build]\n'
            'entry = "src/main.teka"\n',
            encoding="utf-8",
        )
        (root / ".editorconfig").write_text(
            'root = true\n\n[*.teka]\nindent_style = tab\n'
            'indent_size = 4\ntab_width = 4\n',
            encoding="utf-8",
        )
        (root / "src" / "main.teka").write_text(
            "# First program in T+\n"
            f"say 'hello from {name}!'\n", encoding="utf-8",
        )
        (root / "tests" / "test_main.teka").write_text(
            "say 'T+ test program runs'\n", encoding="utf-8",
        )
        (root / "README.md").write_text(
            f"# {name}\n\n"
            "A T+ project.\n\n"
            "Run with: teka run\n"
            "Compile with: teka build --release\n"
            "Or open the folder in IntelliJ IDEA and run src/main.teka.\n",
            encoding="utf-8",
        )
    except Exception:
        shutil.rmtree(root)
        raise
    return root


def project_entry(directory: Path) -> Path | None:
    manifest = directory / "teka.toml"
    if not manifest.is_file():
        return None
    try:
        config = tomllib.loads(manifest.read_text(encoding="utf-8"))
        name = config["project"]["name"]
        path = config["build"]["entry"]
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise ProjectError(f"Invalid teka.toml: {exc}") from exc
    if not isinstance(name, str) or not isinstance(path, str):
        raise ProjectError("Project name and entry must be strings")
    entry = (directory / path).resolve()
    if not entry.is_relative_to(directory.resolve()):
        raise ProjectError("The project entry must stay inside the project folder")
    if entry.suffix != ".teka" or not entry.is_file():
        raise ProjectError(f"Entry does not exist or is not .teka: {entry}")
    return entry


def doctor(installed_root: Path) -> dict:
    compiler = shutil.which("clang++") or shutil.which("g++") or shutil.which("c++")
    include = next(
        (p for p in [Path("/opt/homebrew/include/raylib.h"),
                     Path("/usr/local/include/raylib.h")] if p.exists()), None
    )
    idea_plugins = Path.home() / "Library" / "Application Support" / "JetBrains"
    plugin_versions = []
    if idea_plugins.exists():
        for plugin in idea_plugins.glob("IntelliJIdea*/plugins/TekaLang-IntelliJ/lib/*.jar"):
            plugin_versions.append(str(plugin))
    return {
        "python": sys.version.split()[0],
        "python_supported": sys.version_info >= (3, 11),
        "cpp_compiler": compiler,
        "cpp_available": bool(compiler),
        "raylib_headers": str(include) if include else None,
        "graphics_available": sys.platform == "darwin" and bool(include) and bool(compiler),
        "intellij_plugin": sorted(plugin_versions),
        "root": str(installed_root),
        "stdlib": sorted(MODULES),
        "status": "ready" if sys.version_info >= (3, 11) and compiler else "incomplete",
    }


# Installation ownership: local metadata only; no downloads or recursive deletion.
RECORD = ".tplus-install.json"
OWNED_FILES = frozenset(ALL_COMPILER) | {"launcher.py", "launcher.json", ".tplus-install"}
LAUNCHERS = {"posix": ("teka",), "windows": ("teka.cmd", "launcher.json")}


class InstallationError(Exception):
    pass


def linked(path: Path) -> bool:
    """Include Windows junctions/reparse points, even on Python 3.11."""
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def plain_path(path: Path):
    for part in (path, *path.parents):
        if linked(part):
            raise InstallationError(f"Refusing a symlink or junction in installation path: {part}")


def digest(path: Path) -> str:
    plain_path(path)
    if not path.is_file():
        raise InstallationError(f"Expected a regular installed file: {path}")
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def prefix_for(root: Path, layout: str) -> Path:
    if not isinstance(layout, str) or layout not in LAUNCHERS or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", root.name):
        raise InstallationError("Unrecognized installation layout; no files were removed")
    if layout == "posix":
        if root.parent.name != "teka" or root.parent.parent.name != "share":
            raise InstallationError("Unrecognized installation directory")
        return root.parent.parent.parent
    return root.parent


def atomic_record(root: Path, record: dict):
    path = root / RECORD
    plain_path(path)
    fd, temporary = tempfile.mkstemp(prefix=".teka-ownership-", dir=root)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(record, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def read_record(root: Path) -> dict | None:
    path = root / RECORD
    plain_path(path)
    if not path.exists():
        return None
    if not path.is_file():
        raise InstallationError("Installation record must be a regular file")
    if path.stat().st_size > 64 * 1024:
        raise InstallationError("Installation record is too large")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise InstallationError("Invalid installation record") from exc
    if not isinstance(record, dict) or type(record.get("schema")) is not int or record["schema"] != 1:
        raise InstallationError("Unsupported installation record")
    prefix_for(root, record.get("layout"))
    for key, allowed in (("files", OWNED_FILES), ("launchers", LAUNCHERS[record["layout"]])):
        entries = record.get(key)
        if not isinstance(entries, dict):
            raise InstallationError("Invalid installation ownership entries")
        for name, checksum in entries.items():
            if name not in allowed or not isinstance(checksum, str) or not re.fullmatch(r"[0-9a-f]{64}", checksum):
                raise InstallationError("Invalid installation ownership entry")
    return record


def matches(path: Path, checksum: str) -> bool:
    try:
        return digest(path) == checksum
    except (OSError, InstallationError):
        return False


def preflight(root: Path, layout: str, names: list[str]):
    """Check every destination before either installer starts copying files."""
    prefix = prefix_for(root, layout)
    plain_path(root)
    record = read_record(root)
    if record and record["layout"] != layout:
        raise InstallationError("Installation layout does not match its ownership record")
    for name in names:
        if name not in OWNED_FILES:
            raise InstallationError(f"Unsupported installed filename: {name}")
        path = root / name
        plain_path(path)
        if path.exists() and not path.is_file():
            raise InstallationError(f"Installation destination is not a file: {path}")
        if record and path.exists() and not matches(path, record["files"].get(name, "")):
            raise InstallationError(f"Installed file was modified or is not owned: {path}. Save it elsewhere before reinstalling.")
    previous = []
    if root.parent.is_dir():
        for version in root.parent.iterdir():
            if version.is_dir() and not linked(version) and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version.name):
                old = read_record(version)
                if old and old["layout"] == layout:
                    previous.append(old)
    for name in LAUNCHERS[layout]:
        path = prefix / "bin" / name
        plain_path(path)
        if path.exists() and not path.is_file():
            raise InstallationError(f"Launcher destination is not a file: {path}")
        expected = [old["launchers"][name] for old in previous if name in old["launchers"]]
        if path.exists() and expected and not any(matches(path, checksum) for checksum in expected):
            raise InstallationError(f"Launcher was modified or is not owned: {path}")
        if path.exists() and not expected and name == "launcher.json":
            # The shared bin directory may contain an unrelated JSON file.
            # Accept only a recognizable legacy T+ installation manifest.
            try:
                info = json.loads(path.read_text(encoding="utf-8"))
                target = Path(info["launcher"])
                valid = (target.name == "launcher.py" and target.parent.parent == prefix
                         and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", target.parent.name)
                         and (target.parent / ".tplus-install").is_file())
            except (OSError, ValueError, KeyError, TypeError):
                valid = False
            if not valid:
                raise InstallationError(f"Launcher manifest is not owned by T+: {path}")


def record_install(root: Path, layout: str, names: list[str]):
    prefix = prefix_for(root, layout)
    if any(name not in OWNED_FILES for name in names):
        raise InstallationError("Unsupported installation files")
    record = {"schema": 1, "layout": layout,
              "files": {name: digest(root / name) for name in names},
              "launchers": {name: digest(prefix / "bin" / name) for name in LAUNCHERS[layout]}}
    atomic_record(root, record)


def prepare_update(root: Path, names: list[str]) -> dict | None:
    record = read_record(root)
    if record is not None:
        preflight(root, record["layout"], names)
    return record


def record_update(root: Path, old: dict, names: list[str]):
    record = {**old, "files": dict(old["files"])}
    for name in names:
        if name not in OWNED_FILES:
            raise InstallationError("Unsupported update file")
        record["files"][name] = digest(root / name)
    atomic_record(root, record)


def uninstall(root: Path, apply: bool = False) -> dict:
    """Preview by default. Only remove exact, unchanged files from this install."""
    root = root.absolute()
    record = read_record(root)
    if record is None:
        raise InstallationError("No ownership record. This may be a source checkout or legacy installation; nothing was removed. Reinstall with the current installer to register owned files.")
    prefix = prefix_for(root, record["layout"])
    candidates = [(root / name, checksum) for name, checksum in record["files"].items()]
    candidates += [(prefix / "bin" / name, checksum) for name, checksum in record["launchers"].items()]
    remove, preserve = [], []
    for path, checksum in candidates:
        if not path.exists() and not linked(path):
            continue
        if matches(path, checksum):
            remove.append((path, checksum))
        else:
            preserve.append(str(path))
    # Anything not recorded, including projects, update backups and caches,
    # is left alone. Never recursively delete the installation directory.
    known = set(record["files"]) | {RECORD}
    preserve += [str(path) for path in root.iterdir() if path.name not in known]
    removed = []
    if apply:
        for path, checksum in remove:
            if not matches(path, checksum):
                raise InstallationError(f"File changed during uninstall; stopped at {path}")
            path.unlink()
            removed.append(str(path))
        (root / RECORD).unlink()
        # Never remove prefix/bin or its PATH entry: they can be shared.
        try:
            root.rmdir()
        except OSError:
            pass
    return {"ok": True, "preview": not apply, "remove": [str(p) for p, _ in remove],
            "removed": removed, "preserved": sorted(set(preserve)),
            "path_unchanged": True}


def cli(argv=None):
    parser = argparse.ArgumentParser(description="T+ local installation ownership")
    parser.add_argument("action", choices=["preflight", "record", "uninstall"])
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--layout", choices=LAUNCHERS, default="posix")
    parser.add_argument("--files", nargs="*", default=[])
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.action == "preflight":
            preflight(args.root, args.layout, args.files)
        elif args.action == "record":
            record_install(args.root, args.layout, args.files)
        else:
            print(json.dumps(uninstall(args.root, args.yes)))
        return 0
    except (InstallationError, OSError) as exc:
        print(f"T+ installation error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(cli())
