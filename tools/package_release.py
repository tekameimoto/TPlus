"""Build validated release files without contacting GitHub or publishing."""
from __future__ import annotations
import argparse
import hashlib
import io
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from updater import ALL_COMPILER, MAX_BUNDLE_BYTES, UpdateError, current_version, validate_bundle


def release_version(root: Path, tag: str | None = None) -> str:
    source = (root / 'teka.py').read_text(encoding='utf-8')
    versions = re.findall(r"^VERSION = ['\"]([0-9]+\.[0-9]+\.[0-9]+)['\"]$", source, re.MULTILINE)
    if len(versions) != 1:
        raise ValueError('teka.py must contain exactly one literal VERSION assignment')
    version = versions[0]
    if tag is not None and tag != 'v' + version:
        raise ValueError('Release tag must match the compiler version: v' + version)
    return version


def archive_bytes(files: dict[str, bytes]) -> bytes:
    result = io.BytesIO()
    with zipfile.ZipFile(result, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, data in sorted(files.items()):
            entry = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            mode = 0o755 if name.endswith(('/teka', '/install.sh', '/install.command')) else 0o644
            entry.external_attr = (0o100000 | mode) << 16
            archive.writestr(entry, data)
    return result.getvalue()


def build(root: Path, plugin: Path, output: Path, tag: str | None = None) -> list[Path]:
    version = release_version(root, tag)
    # Refuse an existing output directory; do not replace an older release.
    if output.exists() or output.is_symlink():
        raise ValueError('Output directory already exists; choose a new directory')
    files = {}
    for name in ALL_COMPILER:
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('Missing or linked compiler file: ' + name)
        files['compiler/' + name] = path.read_bytes()
    if plugin.is_symlink() or not plugin.is_file() or plugin.stat().st_size > MAX_BUNDLE_BYTES:
        raise ValueError('Invalid plugin ZIP')
    files['plugin/TekaLang-IntelliJ.zip'] = plugin.read_bytes()
    bundle = archive_bytes(files)
    if len(bundle) > MAX_BUNDLE_BYTES:
        raise ValueError('Release exceeds the installed updater download limit')
    validate_bundle(bundle, version)
    artifacts = {f'TPlus-v{version}.zip': bundle,
                 f'TPlus-IntelliJ-v{version}.zip': files['plugin/TekaLang-IntelliJ.zip']}
    artifacts['SHA256SUMS.txt'] = ''.join(
        f'{hashlib.sha256(data).hexdigest()}  {name}\n'
        for name, data in sorted(artifacts.items())).encode()
    output.mkdir(parents=True)
    paths = []
    for name, data in artifacts.items():
        path = output / name
        with path.open('xb') as stream:
            stream.write(data)
        paths.append(path)
    verify(output, version)
    return paths


def verify(output: Path, version: str):
    expected = {f'TPlus-v{version}.zip', f'TPlus-IntelliJ-v{version}.zip'}
    lines = (output / 'SHA256SUMS.txt').read_text().splitlines()
    checked = set()
    for line in lines:
        parts = line.split()
        if len(parts) != 2 or parts[1] not in expected or parts[1] in checked:
            raise ValueError('Unexpected or duplicate checksum entry')
        checksum, name = parts
        if hashlib.sha256((output / name).read_bytes()).hexdigest() != checksum:
            raise ValueError('Checksum mismatch: ' + name)
        checked.add(name)
    if checked != expected:
        raise ValueError('Missing release checksum')
    files = validate_bundle((output / f'TPlus-v{version}.zip').read_bytes(), version)
    if files['plugin/TekaLang-IntelliJ.zip'] != (output / f'TPlus-IntelliJ-v{version}.zip').read_bytes():
        raise ValueError('Standalone plugin differs from bundled plugin')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plugin', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--tag')
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    try:
        version = release_version(ROOT, args.tag)
        if args.verify:
            verify(args.output, version)
        else:
            if args.plugin is None:
                parser.error('--plugin is required for packaging')
            build(ROOT, args.plugin, args.output, args.tag)
        print('Verified T+ ' + version)
    except (ValueError, OSError, UpdateError) as exc:
        parser.exit(1, f'Release packaging failed: {exc}\n')


if __name__ == '__main__':
    main()
