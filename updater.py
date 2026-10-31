#!/usr/bin/env python3
"""TekaLang update manager.

Release feed: local JSON file or explicitly configured HTTPS URL.
Checksums verify downloaded bundle integrity; no automatic code execution.
Plugin updates are staged for the next IntelliJ restart.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tempfile
import time
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import zipfile

MAX_FEED_BYTES = 128 * 1024
MAX_BUNDLE_BYTES = 20 * 1024 * 1024
MAX_UNPACKED_BYTES = 35 * 1024 * 1024
MAX_MEMBER_BYTES = 15 * 1024 * 1024
ALLOWED_COMPILER = ("teka.py", "python_style.py", "standard_modules.py", "project_tools.py", "updater.py", "teka")
OPTIONAL_COMPILER = ("TPLUS_HANDBOOK.md", "README.md", "LICENSE", "install.sh", "install.command", "install.ps1", "PRIVACY.md")
ALL_COMPILER = ALLOWED_COMPILER + OPTIONAL_COMPILER
OPTIONAL_BUNDLE_FILES = {f"compiler/{x}" for x in OPTIONAL_COMPILER}
REQUIRED_BUNDLE_FILES = {
    *(f"compiler/{x}" for x in ALLOWED_COMPILER),
    "plugin/TekaLang-IntelliJ.zip",
}
UPDATE_CONFIG = Path.home() / ".config" / "tekalang" / "updates.json"
OFFICIAL_RELEASE_API = "https://api.github.com/repos/tekameimoto/TPlus/releases/latest"
OFFICIAL_DOWNLOAD_ROOT = "https://github.com/tekameimoto/TPlus/releases/download/"


class UpdateError(Exception):
    pass


def parse_version(value: str) -> tuple[int, int, int]:
    if not isinstance(value, str) or not re.fullmatch(r"\d{1,4}\.\d{1,4}\.\d{1,4}", value):
        raise UpdateError(f"Invalid semantic version: {value!r}")
    return tuple(int(x) for x in value.split("."))


def current_version(root: Path) -> str:
    source = (root / "teka.py").read_text(encoding="utf-8")
    match = re.search(r"^VERSION\s*=\s*['\"]([0-9]+\.[0-9]+\.[0-9]+)['\"]", source, re.MULTILINE)
    if not match:
        raise UpdateError("Cannot determine installed TekaLang version")
    return match.group(1)


def default_plugin_dir() -> Path | None:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming")) / "JetBrains"
    elif sys.platform == "darwin":
        base = Path.home() / "Library/Application Support/JetBrains"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "JetBrains"
    if base.is_dir():
        for idea in sorted(base.glob("*Idea*"), reverse=True):
            plugin = idea / "plugins" / "TekaLang-IntelliJ"
            if plugin.is_dir():
                return plugin
    return None


def read_limited(source, maximum: int) -> bytes:
    if isinstance(source, Path):
        if not source.is_file():
            raise UpdateError(f"Update source not found: {source}")
        if source.stat().st_size > maximum:
            raise UpdateError("Update source exceeds the download limit")
        return source.read_bytes()
    request = urlparse(str(source))
    if request.scheme != "https" or not request.hostname:
        raise UpdateError("Remote update sources must use HTTPS")
    try:
        with urlopen(Request(str(source), headers={"User-Agent": "TPlus-Updater", "Accept": "application/json, application/octet-stream"}), timeout=15) as response:
            final = urlparse(response.geturl())
            if final.scheme != "https":
                raise UpdateError("Refusing an insecure HTTP redirect")
            data = response.read(maximum + 1)
    except UpdateError:
        raise
    except HTTPError as exc:
        if str(source) == OFFICIAL_RELEASE_API and exc.code == 404:
            raise UpdateError("No published T+ release is available yet.") from exc
        raise UpdateError(f"Update download failed (HTTP {exc.code}). Try again later.") from exc
    except Exception as exc:
        raise UpdateError(f"Could not access update feed: {exc}") from exc
    if len(data) > maximum:
        raise UpdateError("Download exceeds the allowed size")
    return data


def validate_bundle(data: bytes, version: str) -> dict[str, bytes]:
    """Reject corrupt or unsafe archives before touching an installation."""
    try:
        return _validate_bundle(data, version)
    except (zipfile.BadZipFile, KeyError, UnicodeError, RuntimeError, NotImplementedError) as exc:
        raise UpdateError('Invalid update archive or plugin descriptor') from exc


def _validate_bundle(data: bytes, version: str) -> dict[str, bytes]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(data), "r")
    except zipfile.BadZipFile as exc:
        raise UpdateError("Downloaded update bundle is not a valid ZIP") from exc
    with archive:
        files: dict[str, bytes] = {}
        total = 0
        for entry in archive.infolist():
            if entry.is_dir():
                continue
            path = PurePosixPath(entry.filename)
            if path.is_absolute() or ".." in path.parts or entry.filename not in REQUIRED_BUNDLE_FILES | OPTIONAL_BUNDLE_FILES:
                raise UpdateError(f"Update contains an unexpected file: {entry.filename}")
            mode = (entry.external_attr >> 16) & 0o170000
            if mode == stat.S_IFLNK:
                raise UpdateError("Symlinks in updates are not allowed")
            if entry.filename in files:
                raise UpdateError(f"Duplicate archive member: {entry.filename}")
            if entry.file_size > MAX_MEMBER_BYTES:
                raise UpdateError("A package file is too large")
            total += entry.file_size
            if total > MAX_UNPACKED_BYTES:
                raise UpdateError("Update bundle would unpack too much data")
            files[entry.filename] = archive.read(entry)
        if not REQUIRED_BUNDLE_FILES.issubset(files):
            raise UpdateError(f"Missing release files: {sorted(REQUIRED_BUNDLE_FILES - set(files))}")
        compiler = files["compiler/teka.py"].decode("utf-8")
        if f"VERSION = '{version}'" not in compiler and f'VERSION = "{version}"' not in compiler:
            raise UpdateError("Compiler version differs from manifest")
        plugin = files["plugin/TekaLang-IntelliJ.zip"]
        try:
            with zipfile.ZipFile(io.BytesIO(plugin)) as pzip:
                entries = pzip.infolist()
                names = [entry.filename for entry in entries]
                jar = f"TekaLang-IntelliJ/lib/TekaLang-IntelliJ-{version}.jar"
                if jar not in names:
                    raise UpdateError("Wrong plugin version in release bundle")
                seen = set()
                for info in entries:
                    name = info.filename
                    path = PurePosixPath(name)
                    if (path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name
                            or name.rstrip("/") != path.as_posix()
                            or not name.startswith("TekaLang-IntelliJ/")):
                        raise UpdateError("Unsafe IntelliJ plugin archive")
                    if name in seen:
                        raise UpdateError("Duplicate IntelliJ plugin archive member")
                    seen.add(name)
                    if info.file_size > MAX_MEMBER_BYTES:
                        raise UpdateError("Plugin file exceeds size limit")
                    total += info.file_size
                    if total > MAX_UNPACKED_BYTES:
                        raise UpdateError("Plugin bundle would unpack too much data")
                    if ((info.external_attr >> 16) & 0o170000) == stat.S_IFLNK:
                        raise UpdateError("Plugin symlinks are not allowed")
                with zipfile.ZipFile(io.BytesIO(pzip.read(jar))) as actual_jar:
                    if actual_jar.getinfo("META-INF/plugin.xml").file_size > MAX_FEED_BYTES:
                        raise UpdateError("Plugin descriptor exceeds size limit")
                    descriptor = actual_jar.read("META-INF/plugin.xml").decode("utf-8")
                    if "<id>dev.teka.lang</id>" not in descriptor or f"<version>{version}</version>" not in descriptor:
                        raise UpdateError("IntelliJ plugin identity or version does not match the release")
        except zipfile.BadZipFile as exc:
            raise UpdateError("Plugin bundle is not a valid ZIP") from exc
        return files


def github_release(payload: dict) -> dict:
    """Read a stable release from the project's public GitHub repository."""
    if not isinstance(payload, dict) or payload.get("draft") is not False or payload.get("prerelease") is not False:
        raise UpdateError("The update source did not return a published stable release")
    tag = payload.get("tag_name", "")
    if not isinstance(tag, str):
        raise UpdateError("Invalid release tag")
    version = tag.removeprefix("v")
    parse_version(version)
    filename = f"TPlus-v{version}.zip"
    assets = payload.get("assets", [])
    if not isinstance(assets, list):
        raise UpdateError("Invalid release assets")
    def asset(name):
        matches = [item for item in assets if isinstance(item, dict) and item.get("name") == name]
        if len(matches) != 1:
            raise UpdateError(f"Release is missing a unique {name} download")
        item = matches[0]
        expected = OFFICIAL_DOWNLOAD_ROOT + tag + "/" + name
        if item.get("browser_download_url") != expected:
            raise UpdateError("Release download must belong to the official T+ GitHub repository")
        return item
    bundle = asset(filename)
    checksums = asset("SHA256SUMS.txt")
    size = bundle.get("size")
    if type(size) is not int or not 0 < size <= MAX_BUNDLE_BYTES:
        raise UpdateError("Invalid release archive size")
    try:
        lines = read_limited(checksums["browser_download_url"], MAX_FEED_BYTES).decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise UpdateError("Invalid release checksum file") from exc
    matches = [parts[0].lower() for line in lines
               if len(parts := line.split()) == 2 and parts[1].lstrip("*") == filename]
    if len(matches) != 1 or not re.fullmatch(r"[0-9a-f]{64}", matches[0]):
        raise UpdateError("Release checksum is missing or ambiguous")
    return {"version": version, "notes": str(payload.get("body") or "")[:1000],
            "sha256": matches[0], "size_bytes": size,
            "archive": bundle["browser_download_url"], "feed": OFFICIAL_RELEASE_API}


class Updater:
    def __init__(self, root: Path, plugin_dir: Path | None = None,
                 config_path: Path | None = None, feed_override=None):
        self.root = root.resolve()
        self.plugin_dir = plugin_dir if plugin_dir is not None else default_plugin_dir()
        self.config_path = config_path or UPDATE_CONFIG
        self.feed_override = feed_override

    def source(self):
        if self.feed_override is not None:
            return self.feed_override
        try:
            data = json.loads(self.config_path.read_text("utf-8"))
            if not isinstance(data, dict):
                raise UpdateError("Update source configuration must be a JSON object")
            remote = data.get("feed_url")
            if remote is not None and not isinstance(remote, str):
                raise UpdateError("Configured update feed must be an HTTPS URL or null")
            if remote:
                parsed = urlparse(remote)
                if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                    raise UpdateError("Configured remote update feed must be a valid HTTPS URL without credentials")
                return remote
        except FileNotFoundError:
            pass
        except (ValueError, TypeError) as exc:
            raise UpdateError("Your update source configuration is not valid JSON") from exc
        local = self.root / "releases" / "stable.json"
        return local if local.is_file() else OFFICIAL_RELEASE_API

    def set_source(self, url: str | None):
        if url:
            parsed = urlparse(url)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                raise UpdateError("Use a valid HTTPS URL for a remote update feed")
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        dest = self.config_path
        fd, temporary = tempfile.mkstemp(prefix=".teka-feed-", dir=str(dest.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump({"feed_url": url}, stream, indent=2)
            os.chmod(temporary, 0o600)
            os.replace(temporary, dest)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def release(self):
        feed = self.source()
        contents = read_limited(feed, MAX_FEED_BYTES)
        try:
            payload = json.loads(contents)
        except (ValueError, UnicodeDecodeError) as exc:
            raise UpdateError("Invalid update feed JSON") from exc
        if feed == OFFICIAL_RELEASE_API:
            return github_release(payload)
        if not isinstance(payload, dict) or payload.get("schema") != 1:
            raise UpdateError("Unsupported release feed format")
        if payload.get("channel") != "stable":
            raise UpdateError("Only stable releases are supported")
        version = payload.get("version")
        parse_version(version)
        asset = payload.get("asset")
        checksum = payload.get("sha256")
        size = payload.get("size_bytes")
        if not isinstance(asset, str) or not asset or len(asset) > 2048:
            raise UpdateError("Release feed is missing the ZIP asset")
        if not isinstance(checksum, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", checksum):
            raise UpdateError("Release checksum must be SHA-256")
        if type(size) is not int or not 0 < size <= MAX_BUNDLE_BYTES:
            raise UpdateError("Invalid release archive size")
        if isinstance(feed, Path):
            # For local feeds, ZIP must remain alongside the manifest.
            if asset in {".", ".."} or any(char in asset for char in ("/", "\\", ":", "\0")):
                raise UpdateError("Local update filenames must be alongside the feed")
            archive_source = feed.parent / asset
        else:
            url = urljoin(feed, asset)
            parsed = urlparse(url)
            origin = urlparse(feed)
            if parsed.scheme != "https" or parsed.netloc != origin.netloc:
                raise UpdateError("Release asset must use the feed's HTTPS host")
            archive_source = url
        return {
            "version": version,
            "notes": str(payload.get("notes", ""))[:1000],
            "sha256": checksum.lower(),
            "size_bytes": size,
            "archive": archive_source,
            "feed": str(feed),
        }

    def check(self):
        return self._status(self.release())

    def _status(self, release):
        now = current_version(self.root)
        available = parse_version(release["version"]) > parse_version(now)
        return {
            "ok": True, "current": now, "latest": release["version"],
            "available": available, "notes": release["notes"],
            "source": str(self.source()),
            "hosted": isinstance(self.source(), str),
        }

    def install(self):
        release = self.release()
        status = self._status(release)
        if not status["available"]:
            return {**status, "installed": False, "message": "Already up to date"}
        blob = read_limited(release["archive"], MAX_BUNDLE_BYTES)
        if len(blob) != release["size_bytes"]:
            raise UpdateError("Update archive size does not match the manifest")
        if hashlib.sha256(blob).hexdigest() != release["sha256"]:
            raise UpdateError("Update archive checksum mismatch; nothing was installed")
        files = validate_bundle(blob, release["version"])

        # Keep old sources and IntelliJ plugin so a failed transaction can roll back.
        backups = self.root / "backups" / "updates"
        backups.mkdir(parents=True, exist_ok=True)
        unique = f"{int(time.time())}-{os.getpid()}"
        backup = backups / f"{status['current']}-to-{release['version']}-{unique}"
        backup.mkdir(parents=True)
        old_files: dict[str, bytes | None] = {}
        for filename in ALL_COMPILER:
            dest = self.root / filename
            old_files[filename] = dest.read_bytes() if dest.exists() else None
            if dest.exists():
                shutil.copy2(dest, backup / filename)

        stage_parent = self.plugin_dir.parent if self.plugin_dir is not None else self.root
        stage_parent.mkdir(parents=True, exist_ok=True)
        saved_plugin = backup / "TekaLang-IntelliJ"
        moved_plugin = False
        stage = Path(tempfile.mkdtemp(prefix=".teka-stage-", dir=str(stage_parent)))
        modified: list[str] = []
        try:
            # Validate and stage all components before changing any installed file.
            with zipfile.ZipFile(io.BytesIO(files["plugin/TekaLang-IntelliJ.zip"])) as pluginzip:
                pluginzip.extractall(stage)
            new_plugin = stage / "TekaLang-IntelliJ"
            if not new_plugin.is_dir():
                raise UpdateError("Staged plugin directory was not created")
            staged_files: dict[str, Path] = {}
            for name in ALL_COMPILER:
                if f"compiler/{name}" not in files:
                    continue
                staging = self.root / (f".{name}.update-{unique}")
                staging.write_bytes(files[f"compiler/{name}"])
                if name == "teka":
                    os.chmod(staging, 0o755)
                staged_files[name] = staging
            try:
                for name, staging in staged_files.items():
                    os.replace(staging, self.root / name)
                    modified.append(name)
                if self.plugin_dir is not None and self.plugin_dir.exists():
                    shutil.move(str(self.plugin_dir), str(saved_plugin))
                    moved_plugin = True
                if self.plugin_dir is not None:
                    shutil.move(str(new_plugin), str(self.plugin_dir))
            finally:
                for staging in staged_files.values():
                    staging.unlink(missing_ok=True)
        except Exception as exc:
            for name in modified:
                dest = self.root / name
                old = old_files[name]
                if old is None:
                    dest.unlink(missing_ok=True)
                else:
                    dest.write_bytes(old)
                    if name == "teka":
                        os.chmod(dest, 0o755)
            if self.plugin_dir is not None and self.plugin_dir.exists() and moved_plugin:
                shutil.rmtree(self.plugin_dir)
            if moved_plugin and saved_plugin.is_dir():
                shutil.move(str(saved_plugin), str(self.plugin_dir))
            raise UpdateError(f"Update rolled back: {exc}") from exc
        finally:
            shutil.rmtree(stage, ignore_errors=True)
        return {
            "ok": True, "current": status["current"], "latest": release["version"],
            "installed": True, "restart_required": self.plugin_dir is not None,
            "backup": str(backup),
            "message": "T+ updated." + (" Restart IntelliJ IDEA to load the plugin." if self.plugin_dir is not None else ""),
        }


def cli(argv=None):
    parser = argparse.ArgumentParser(prog="teka update", description="TekaLang release updater")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("check")
    ins = sub.add_parser("install")
    ins.add_argument("--yes", action="store_true", help=argparse.SUPPRESS)
    src = sub.add_parser("source")
    src.add_argument("url", nargs="?", help="HTTPS feed URL, or 'default' to reset")
    for name in ("status", "check", "install", "source"):
        subparser = next(p for p in sub.choices.values() if p.prog.endswith(name))
        subparser.add_argument("--json", action="store_true")
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0].startswith("--"):
        argv.insert(0, "install")
    args = parser.parse_args(argv)
    updater = Updater(Path(__file__).resolve().parent)
    try:
        if args.command == "source":
            if args.url:
                updater.set_source(None if args.url in {"local", "default", "github"} else args.url)
            result = {"ok": True, "source": str(updater.source()),
                      "hosted": isinstance(updater.source(), str)}
        elif args.command == "status":
            result = {"ok": True, "current": current_version(updater.root),
                      "source": str(updater.source()),
                      "hosted": isinstance(updater.source(), str)}
        elif args.command == "check":
            result = updater.check()
        else:
            result = updater.install()
        if args.json:
            print(json.dumps(result))
        elif args.command in {"install", "check"}:
            if result.get("installed"):
                print(f"T+ updated to {result['latest']}.")
                if result.get("restart_required"):
                    print("Restart IntelliJ IDEA to load the updated plugin.")
            elif result.get("available"):
                print(f"T+ {result['latest']} is available. Run: teka update")
            else:
                print(f"T+ {result['current']} is up to date.")
        else:
            for key, value in result.items():
                if key not in {"ok", "hosted"}:
                    print(f"{key}: {value}")
        return 0
    except (UpdateError, OSError, ValueError) as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}))
        else:
            print(f"TekaLang updater error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(cli())
