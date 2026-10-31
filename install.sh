#!/bin/sh
# Install a local copy of T+ without administrator access.
set -eu

SOURCE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PREFIX="${HOME}/.local"
case "${1:-}" in
  --help|-h)
    echo "Usage: sh install.sh [--prefix DIRECTORY]"
    echo "Default: $PREFIX"
    exit 0 ;;
  --prefix)
    [ "$#" -eq 2 ] || { echo "Usage: sh install.sh --prefix DIRECTORY" >&2; exit 1; }
    PREFIX=$2 ;;
  "")
    [ "$#" -eq 0 ] || { echo "Unexpected argument" >&2; exit 1; } ;;
  *) echo "Usage: sh install.sh [--prefix DIRECTORY]" >&2; exit 1 ;;
esac

TEKA_PYTHON=""
for candidate in python3 python3.15 python3.14 python3.13 python3.12 python3.11; do
  if command -v "$candidate" >/dev/null 2>&1 &&
     "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
    TEKA_PYTHON=$candidate
    break
  fi
done
[ -n "$TEKA_PYTHON" ] || {
  echo "T+ needs Python 3.11 or newer. Install it from https://www.python.org/downloads/ and try again." >&2
  exit 1
}

exec "$TEKA_PYTHON" - "$SOURCE_DIR" "$PREFIX" <<'PY'
from pathlib import Path
import os
import shlex
import shutil
import sys

source = Path(sys.argv[1]).resolve()
prefix = Path(sys.argv[2]).expanduser().resolve()
launcher = prefix / "bin" / "teka"
required = ["teka.py", "python_style.py", "standard_modules.py", "project_tools.py", "updater.py", "TPLUS_HANDBOOK.md"]
missing = [name for name in required if not (source / name).is_file()]
if missing:
    sys.exit("Incomplete T+ folder: missing " + ", ".join(missing))
sys.path.insert(0, str(source))
from updater import current_version, UpdateError
try:
    version = current_version(source)
except UpdateError as exc:
    sys.exit(str(exc))
destination = prefix / "share" / "teka" / version
if launcher.exists() or launcher.is_symlink():
    if launcher.is_symlink() or not launcher.is_file() or "# TPlus launcher" not in launcher.read_text(errors="replace"):
        sys.exit(f"Another command already exists at {launcher}. Use --prefix to choose another folder.")
if destination.exists() and not (destination / ".tplus-install").is_file():
    sys.exit(f"{destination} already exists and is not marked as a T+ installation. Choose another --prefix.")
destination.mkdir(parents=True, exist_ok=True)
for name in required + ["README.md", "LICENSE", "PRIVACY.md", "install.sh", "install.command"]:
    if (source / name).is_file() and (source / name).resolve() != (destination / name).resolve():
        shutil.copy2(source / name, destination / name)
(destination / ".tplus-install").write_text(f"T+ {version}\n", encoding="utf-8")
launcher.parent.mkdir(parents=True, exist_ok=True)
python = shlex.quote(sys.executable)
compiler = shlex.quote(str(destination / "teka.py"))
updater = shlex.quote(str(destination / "updater.py"))
launcher.write_text(f'#!/bin/sh\n# TPlus launcher\nif [ "${{1:-}}" = update ]; then\n  shift\n  exec {python} {updater} "$@"\nfi\nexec {python} {compiler} "$@"\n')
launcher.chmod(0o755)
print(f"T+ {version} installed in {destination}")
print(f"Command: {launcher}")
path_entries = [Path(p).expanduser().resolve() for p in os.environ.get("PATH", "").split(os.pathsep) if p]
if launcher.parent not in path_entries:
    shell_name = Path(os.environ.get("SHELL", "/bin/sh")).name
    config = "~/.zshrc" if shell_name == "zsh" else "~/.bashrc" if shell_name == "bash" else "your shell's startup file"
    print(f"\nAdd this line to {config}, then open a new Terminal:")
    print("export PATH=" + shlex.quote(str(launcher.parent)) + ':"$PATH"')
print("\nTry: teka --version")
if not any(shutil.which(name) for name in ["c++", "clang++", "g++"]):
    print("\nA C++17 compiler is also needed to run or build programs.")
    print("macOS: xcode-select --install")
    print("Ubuntu/Debian: sudo apt install g++")
PY
