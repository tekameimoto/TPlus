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
sys.path.insert(0, str(source))
from project_tools import install_local, InstallationError
from updater import current_version, UpdateError
try:
    destination = install_local(source, prefix, "posix")
    version = current_version(destination)
except (InstallationError, UpdateError, OSError, ValueError) as exc:
    sys.exit(f"T+ installation error: {exc}")
launcher = prefix / "bin" / "teka"
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
