"""Release packages must be repeatable and accepted by the installed updater."""
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile
from tools.package_release import build, verify, release_version
import test_updater
from updater import ALL_COMPILER, UpdateError

ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.source = self.base / 'source'
        self.source.mkdir()
        for name in ALL_COMPILER:
            shutil.copy2(ROOT / name, self.source / name)
        self.version = release_version(self.source)
        self.plugin = self.base / 'plugin.zip'
        self.plugin.write_bytes(test_updater.UpdaterTests.plugin_bytes(self.version))
        self.output = self.base / 'output'

    def test_repeatable_packages_ignore_paths_timestamps_and_private_files(self):
        (self.source / 'private.txt').write_text('must not ship')
        first = build(self.source, self.plugin, self.output, 'v' + self.version)
        other = self.base / 'other'
        second = build(self.source, self.plugin, other)
        self.assertEqual([p.read_bytes() for p in first], [p.read_bytes() for p in second])
        with zipfile.ZipFile(first[0]) as archive:
            self.assertNotIn('private.txt', archive.namelist())
            self.assertEqual(len(archive.namelist()), len(ALL_COMPILER) + 1)
            for entry in archive.infolist():
                self.assertEqual(entry.date_time, (1980, 1, 1, 0, 0, 0))
                self.assertEqual(entry.extra, b'')
                self.assertEqual(entry.comment, b'')
        verify(self.output, self.version)

    def test_wrong_tag_is_rejected_before_output(self):
        with self.assertRaisesRegex(ValueError, 'tag'):
            build(self.source, self.plugin, self.output, 'v99.0.0')
        self.assertFalse(self.output.exists())

    def test_plugin_version_mismatch_is_rejected(self):
        self.plugin.write_bytes(test_updater.UpdaterTests.plugin_bytes('99.0.0'))
        with self.assertRaises(UpdateError):
            build(self.source, self.plugin, self.output)
        self.assertFalse(self.output.exists())

    def test_missing_source_is_rejected(self):
        (self.source / 'install.ps1').unlink()
        with self.assertRaises(ValueError):
            build(self.source, self.plugin, self.output)
        self.assertFalse(self.output.exists())

    def test_existing_output_is_never_replaced(self):
        self.output.mkdir()
        keep = self.output / 'keep'
        keep.write_bytes(b'keep')
        with self.assertRaises(ValueError):
            build(self.source, self.plugin, self.output)
        self.assertEqual(keep.read_bytes(), b'keep')

    def test_tampered_artifact_fails_verification(self):
        paths = build(self.source, self.plugin, self.output)
        paths[0].write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'Checksum mismatch'):
            verify(self.output, self.version)

    def test_duplicate_checksums_are_rejected(self):
        build(self.source, self.plugin, self.output)
        sums = self.output / 'SHA256SUMS.txt'
        sums.write_text(sums.read_text() * 2)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            verify(self.output, self.version)

    def test_ambiguous_version_is_rejected(self):
        with (self.source / 'teka.py').open('a') as stream:
            stream.write("\nVERSION = '1.0.0'\n")
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            release_version(self.source)
