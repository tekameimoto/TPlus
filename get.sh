#!/bin/sh
# Download and install the T+ release for macOS or Linux.
set -eu

TEKA_PYTHON=""
for candidate in python3 python3.15 python3.14 python3.13 python3.12 python3.11; do
  if command -v "$candidate" >/dev/null 2>&1 &&
     "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
    TEKA_PYTHON=$candidate
    break
  fi
done
[ -n "$TEKA_PYTHON" ] || {
  echo "T+ needs Python 3.11 or newer: https://www.python.org/downloads/" >&2
  exit 1
}
command -v curl >/dev/null 2>&1 || { echo "Install curl and try again." >&2; exit 1; }
TEKA_TMP=$(mktemp -d)
trap 'rm -rf "$TEKA_TMP"' 0
trap 'exit 1' 1 2 3 15
TEKA_RELEASE="https://github.com/tekameimoto/TPlus/releases/download/v0.9.0"
printf 'Downloading T+ 0.9.0...\n'
if ! curl --proto '=https' --tlsv1.2 -fsSL --retry 2 "$TEKA_RELEASE/TPlus-v0.9.0.zip" -o "$TEKA_TMP/TPlus-v0.9.0.zip" ||
   ! curl --proto '=https' --tlsv1.2 -fsSL --retry 2 "$TEKA_RELEASE/SHA256SUMS.txt" -o "$TEKA_TMP/SHA256SUMS.txt"; then
  echo "Couldn't download v0.9.0. Check your connection and that the release is public." >&2
  exit 1
fi

"$TEKA_PYTHON" - "$TEKA_TMP" <<'PY'
from pathlib import Path
from zipfile import ZipFile
import hashlib
import sys

root = Path(sys.argv[1]).resolve()
filename = "TPlus-v0.9.0.zip"
checksums = {}
for line in (root / "SHA256SUMS.txt").read_text().splitlines():
    parts = line.split()
    if len(parts) == 2:
        checksums[parts[1].lstrip("*")] = parts[0].lower()
expected = checksums.get(filename)
actual = hashlib.sha256((root / filename).read_bytes()).hexdigest()
if expected is None or actual != expected:
    sys.exit("Release checksum did not match. Nothing was installed.")
with ZipFile(root / filename) as archive:
    for member in archive.infolist():
        target = (root / member.filename).resolve()
        if not target.is_relative_to(root) or (member.external_attr >> 16) & 0o170000 == 0o120000:
            sys.exit("Invalid path in release archive. Nothing was installed.")
    archive.extractall(root)
if not (root / "compiler" / "install.sh").is_file():
    sys.exit("The release is missing its installer. Nothing was installed.")
print("Checksum verified.")
PY

sh "$TEKA_TMP/compiler/install.sh" "$@"
