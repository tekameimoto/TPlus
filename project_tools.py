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
import errno
from contextlib import contextmanager
import shlex
import hashlib
import json
import os
import stat
import tempfile
from updater import ALL_COMPILER, UpdateError
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
    root = root.absolute()
    record = read_record(root)
    if record is not None:
        prefix = prefix_for(root, record['layout'])
        if apply:
            with lifecycle_lock(prefix):
                recover_install(prefix)
                return _uninstall(root, True)
        if (prefix / TRANSACTION).exists():
            raise InstallationError('An installation needs recovery. Re-run the installer before previewing removal.')
    return _uninstall(root, apply)


def _uninstall(root: Path, apply: bool = False) -> dict:
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


LOCK = '.tplus-lifecycle.lock'
TRANSACTION = '.tplus-install-transaction'
MAX_INSTALL_FILE = 20 * 1024 * 1024


@contextmanager
def lifecycle_lock(prefix: Path):
    """OS lock releases on process exit; keep its inode for other contenders."""
    plain_path(prefix / LOCK)
    prefix.mkdir(parents=True, exist_ok=True)
    fd = os.open(prefix / LOCK, os.O_CREAT | os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    acquired = False
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise InstallationError('Lifecycle lock must be a regular file')
        if os.fstat(fd).st_size == 0:
            os.write(fd, b'0')
        os.lseek(fd, 0, os.SEEK_SET)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise InstallationError('Another T+ installation operation is running. Try again when it finishes.') from exc
        acquired = True
        yield
    finally:
        if acquired:
            if os.name == 'nt':
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def sync_directory(path: Path):
    if os.name != 'nt':
        fd = os.open(path, os.O_RDONLY)
        try:
            try:
                os.fsync(fd)
            except OSError as exc:
                if exc.errno not in {errno.EINVAL, errno.ENOTSUP}:
                    raise
        finally:
            os.close(fd)


def atomic_file(path: Path, data: bytes, mode: int = 0o644):
    plain_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.teka-write-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
        sync_directory(path.parent)
    finally:
        Path(temporary).unlink(missing_ok=True)


def limited_bytes(path: Path) -> bytes:
    plain_path(path)
    if not path.is_file() or path.stat().st_size > MAX_INSTALL_FILE:
        raise InstallationError(f'Invalid or oversized installation file: {path}')
    with path.open('rb') as stream:
        data = stream.read(MAX_INSTALL_FILE + 1)
    if len(data) > MAX_INSTALL_FILE:
        raise InstallationError('Installation file exceeds size limit')
    return data


def install_paths(layout: str, version: str) -> tuple[str, set[str]]:
    if layout not in LAUNCHERS or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version):
        raise InstallationError('Invalid installation journal layout or version')
    root = f'share/teka/{version}' if layout == 'posix' else version
    return root, {f'{root}/{name}' for name in OWNED_FILES | {RECORD}} | {f'bin/{name}' for name in LAUNCHERS[layout]}


def clean_transaction(prefix: Path):
    """Delete only recognized work files; never recursively delete user files."""
    stage = prefix / TRANSACTION
    plain_path(stage)
    if not stage.exists():
        return
    files, directories = [], []
    for item in stage.iterdir():
        plain_path(item)
        if item.name in {'before', 'after'} and item.is_dir():
            directories.append(item)
            for blob in item.iterdir():
                plain_path(blob)
                if not blob.is_file() or not re.fullmatch(r'[0-9]{1,3}|\.teka-write-[A-Za-z0-9_-]+', blob.name):
                    raise InstallationError('Unexpected recovery file; transaction retained for inspection')
                files.append(blob)
        elif item.is_file() and (item.name in {'owner', 'journal.json'} or re.fullmatch(r'\.teka-write-[A-Za-z0-9_-]+', item.name)):
            files.append(item)
        else:
            raise InstallationError('Unexpected recovery file; transaction retained for inspection')
    # Keep journal and ownership marker until work files/directories are gone.
    for item in files:
        if item.parent == stage and item.name in {'owner', 'journal.json'}:
            continue
        item.unlink()
    for directory in directories:
        directory.rmdir()
    (stage / 'journal.json').unlink(missing_ok=True)
    (stage / 'owner').unlink(missing_ok=True)
    stage.rmdir()
    sync_directory(prefix)


def read_journal(prefix: Path) -> dict:
    path = prefix / TRANSACTION / 'journal.json'
    if path.stat().st_size > 64 * 1024:
        raise InstallationError('Installation journal is too large')
    try:
        journal = json.loads(limited_bytes(path))
        if type(journal['schema']) is not int or journal['schema'] != 1 or journal['state'] not in {'prepared', 'committed', 'rolled_back'}:
            raise ValueError()
        _, allowed = install_paths(journal['layout'], journal['version'])
        entries = journal['entries']
        if not isinstance(entries, list) or not 0 < len(entries) <= len(allowed):
            raise ValueError()
        seen = set()
        for entry in entries:
            if entry['path'] not in allowed or entry['path'] in seen:
                raise ValueError()
            seen.add(entry['path'])
            for key in ('before', 'after'):
                value = entry[key]
                if key == 'before' and value is None:
                    continue
                if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
                    raise ValueError()
            for key in ('old_mode', 'new_mode'):
                if type(entry[key]) is not int or not 0 <= entry[key] <= 0o777:
                    raise ValueError()
    except (ValueError, KeyError, TypeError, UnicodeError) as exc:
        raise InstallationError('Invalid installation journal; no recovery files were applied') from exc
    return journal


def recover_install(prefix: Path):
    """Caller holds lifecycle_lock. Roll back only recognized, unchanged files."""
    stage = prefix / TRANSACTION
    plain_path(stage)
    if not stage.exists():
        return
    owner = stage / 'owner'
    if not owner.exists():
        if not any(stage.iterdir()):
            stage.rmdir()
            return
        raise InstallationError('Unrecognized recovery directory; nothing was overwritten')
    if limited_bytes(owner) != b'T+ install transaction 1\n':
        raise InstallationError('Unrecognized recovery directory; nothing was overwritten')
    if not (stage / 'journal.json').exists():
        # Preparation did not finish: installed files have not been touched.
        clean_transaction(prefix)
        return
    journal = read_journal(prefix)
    if journal['state'] in {'committed', 'rolled_back'}:
        clean_transaction(prefix)
        return
    restores = []
    for index, entry in enumerate(journal['entries']):
        target = prefix / entry['path']
        plain_path(target)
        current = digest(target) if target.exists() else None
        if current not in (entry['before'], entry['after']):
            raise InstallationError(f'File changed after interrupted install: {target}. Recovery stopped; files were preserved.')
        old = None
        if entry['before'] is not None:
            old = limited_bytes(stage / 'before' / str(index))
            if hashlib.sha256(old).hexdigest() != entry['before']:
                raise InstallationError('Recovery backup checksum mismatch; files were preserved')
        restores.append((target, old, entry['old_mode']))
    # Validate every file and backup before changing any destination.
    for target, old, mode in restores:
        if old is None:
            target.unlink(missing_ok=True)
            if target.parent.exists():
                sync_directory(target.parent)
        else:
            atomic_file(target, old, mode)
    root, _ = install_paths(journal['layout'], journal['version'])
    try:
        (prefix / root).rmdir()
    except OSError:
        pass
    journal['state'] = 'rolled_back'
    atomic_file(stage / 'journal.json', json.dumps(journal).encode(), 0o600)
    clean_transaction(prefix)


def apply_install(prefix: Path, layout: str, version: str, payload: dict[str, tuple[bytes, int]]):
    """Caller holds lifecycle_lock and has validated ownership of destinations."""
    _, allowed = install_paths(layout, version)
    if not payload or not set(payload).issubset(allowed):
        raise InstallationError('Unsupported installation destination')
    stage = prefix / TRANSACTION
    plain_path(stage)
    stage.mkdir(mode=0o700)
    try:
        # Write the marker before creating any backup or changing installed files.
        with (stage / 'owner').open('xb') as stream:
            stream.write(b'T+ install transaction 1\n')
            stream.flush()
            os.fsync(stream.fileno())
        entries = []
        for index, (name, (data, mode)) in enumerate(payload.items()):
            target = prefix / name
            plain_path(target)
            if len(data) > MAX_INSTALL_FILE:
                raise InstallationError('Installation file exceeds size limit')
            old = limited_bytes(target) if target.exists() else None
            old_mode = stat.S_IMODE(target.stat().st_mode) & 0o777 if old is not None else 0o644
            if old is not None:
                atomic_file(stage / 'before' / str(index), old, 0o600)
            atomic_file(stage / 'after' / str(index), data, 0o600)
            entries.append({'path': name, 'before': hashlib.sha256(old).hexdigest() if old is not None else None,
                            'after': hashlib.sha256(data).hexdigest(), 'old_mode': old_mode, 'new_mode': mode})
        journal = {'schema': 1, 'state': 'prepared', 'layout': layout, 'version': version, 'entries': entries}
        atomic_file(stage / 'journal.json', json.dumps(journal).encode(), 0o600)
        sync_directory(stage)
        sync_directory(prefix)
        for index, entry in enumerate(entries):
            data = limited_bytes(stage / 'after' / str(index))
            if hashlib.sha256(data).hexdigest() != entry['after']:
                raise InstallationError('Staged file checksum mismatch')
            atomic_file(prefix / entry['path'], data, entry['new_mode'])
        journal['state'] = 'committed'
        atomic_file(stage / 'journal.json', json.dumps(journal).encode(), 0o600)
    except BaseException:
        # A hard process termination bypasses this; the next installer recovers.
        recover_install(prefix)
        raise
    clean_transaction(prefix)


def install_local(source: Path, prefix: Path, layout: str) -> Path:
    from updater import current_version
    source, prefix = source.resolve(), prefix.expanduser().resolve()
    required = ['teka.py', 'python_style.py', 'standard_modules.py', 'project_tools.py', 'updater.py', 'TPLUS_HANDBOOK.md']
    for name in required:
        if not (source / name).is_file():
            raise InstallationError(f'Incomplete T+ folder: missing {name}')
    version = current_version(source)
    relative, _ = install_paths(layout, version)
    root = prefix / relative
    extras = ['README.md', 'LICENSE', 'PRIVACY.md'] + (['install.sh', 'install.command'] if layout == 'posix' else ['install.ps1'])
    files = {name: (limited_bytes(source / name), stat.S_IMODE((source / name).stat().st_mode) & 0o777)
             for name in required + extras if (source / name).is_file()}
    files['.tplus-install'] = (f'T+ {version}\n'.encode(), 0o644)
    if layout == 'posix':
        python, compiler, updater = map(shlex.quote, [sys.executable, str(root / 'teka.py'), str(root / 'updater.py')])
        launcher = f'#!/bin/sh\n# TPlus launcher\nif [ "${{1:-}}" = update ]; then\n  shift\n  exec {python} {updater} "$@"\nfi\nexec {python} {compiler} "$@"\n'
        launchers = {'teka': (launcher.encode(), 0o755)}
    else:
        code = 'from pathlib import Path\nimport runpy, sys\nroot = Path(__file__).resolve().parent\nargs = sys.argv[1:]\ntarget = "teka.py"\nif args and args[0] == "update":\n    target = "updater.py"\n    args = args[1:]\nsys.path.insert(0, str(root))\nsys.argv = [str(root / target)] + args\nrunpy.run_path(str(root / target), run_name="__main__")\n'
        files['launcher.py'] = (code.encode(), 0o644)
        manifest = json.dumps({'python': sys.executable, 'launcher': str(root / 'launcher.py')}).encode()
        files['launcher.json'] = (manifest, 0o644)
        python, entry = [s.replace('%', '%%') for s in (sys.executable, str(root / 'launcher.py'))]
        command = f'@echo off\r\nrem TPlus launcher\r\n"{python}" "{entry}" %*\r\n'
        launchers = {'teka.cmd': (command.encode(), 0o644), 'launcher.json': (manifest, 0o644)}
    record = {'schema': 1, 'layout': layout,
              'files': {name: hashlib.sha256(data).hexdigest() for name, (data, _) in files.items()},
              'launchers': {name: hashlib.sha256(data).hexdigest() for name, (data, _) in launchers.items()}}
    payload = {f'{relative}/{name}': value for name, value in files.items()}
    payload[f'{relative}/{RECORD}'] = ((json.dumps(record, indent=2, sort_keys=True) + '\n').encode(), 0o600)
    payload.update({f'bin/{name}': value for name, value in launchers.items()})
    with lifecycle_lock(prefix):
        if (prefix / TRANSACTION).exists() and source.is_relative_to(prefix):
            raise InstallationError('Use a fresh source folder outside the installation prefix to recover this interrupted install.')
        recover_install(prefix)
        preflight(root, layout, list(files))
        if root.exists() and not (root / '.tplus-install').is_file():
            raise InstallationError(f'{root} is not marked as a T+ installation. Choose another prefix.')
        launcher = prefix / 'bin' / ('teka' if layout == 'posix' else 'teka.cmd')
        marker = '# TPlus launcher' if layout == 'posix' else 'rem TPlus launcher'
        if launcher.exists() and marker not in launcher.read_text(encoding='utf-8', errors='replace'):
            raise InstallationError(f'Another command already exists at {launcher}. Choose another prefix.')
        apply_install(prefix, layout, version, payload)
    return root


def cli(argv=None):
    parser = argparse.ArgumentParser(description='T+ local installation management')
    parser.add_argument('action', choices=['preflight', 'record', 'uninstall', 'install'])
    parser.add_argument('--root', type=Path)
    parser.add_argument('--prefix', type=Path)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--layout', choices=LAUNCHERS, default='posix')
    parser.add_argument('--files', nargs='*', default=[])
    parser.add_argument('--yes', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.action == 'install':
            if args.source is None or args.prefix is None:
                parser.error('install requires --source and --prefix')
            print(install_local(args.source, args.prefix, args.layout))
        else:
            if args.root is None:
                parser.error('--root is required')
            if args.action == 'preflight':
                preflight(args.root, args.layout, args.files)
            elif args.action == 'record':
                record_install(args.root, args.layout, args.files)
            else:
                print(json.dumps(uninstall(args.root, args.yes)))
        return 0
    except (InstallationError, UpdateError, OSError, ValueError) as exc:
        print(f'T+ installation error: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(cli())
