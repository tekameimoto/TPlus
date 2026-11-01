"""Owned-file removal never deletes projects, edited files, or another install."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from project_tools import (InstallationError, RECORD, preflight, read_record,
                          record_install, record_update, uninstall)


class OwnershipTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="teka ownership ")
        self.addCleanup(self.tmp.cleanup)
        self.prefix = Path(self.tmp.name).resolve() / "prefix"
        self.root = self.prefix / "share/teka/0.9.0"
        self.launcher = self.prefix / "bin/teka"
        self.root.mkdir(parents=True)
        self.launcher.parent.mkdir(parents=True)
        (self.root / "teka.py").write_text("VERSION = '0.9.0'\n")
        (self.root / "README.md").write_text("readme")
        self.launcher.write_text("original launcher")
        record_install(self.root, "posix", ["teka.py", "README.md"])

    def test_preview_changes_nothing(self):
        before = {p: p.read_bytes() for p in self.prefix.rglob("*") if p.is_file()}
        result = uninstall(self.root)
        self.assertTrue(result["preview"])
        self.assertIn(str(self.launcher), result["remove"])
        self.assertEqual(before, {p: p.read_bytes() for p in self.prefix.rglob("*") if p.is_file()})

    def test_apply_preserves_edits_projects_and_backups(self):
        (self.root / "README.md").write_text("my notes")
        (self.root / "project.teka").write_text('say "keep me"')
        backups = self.root / "backups/updates"
        backups.mkdir(parents=True)
        (backups / "saved.py").write_text("old compiler")
        result = uninstall(self.root, apply=True)
        self.assertFalse(self.launcher.exists())
        self.assertFalse((self.root / "teka.py").exists())
        self.assertFalse((self.root / RECORD).exists())
        self.assertEqual((self.root / "README.md").read_text(), "my notes")
        self.assertEqual((self.root / "project.teka").read_text(), 'say "keep me"')
        self.assertEqual((backups / "saved.py").read_text(), "old compiler")
        self.assertIn(str(self.root / "README.md"), result["preserved"])

    def test_old_version_cannot_delete_active_new_launcher(self):
        newer = self.root.with_name("0.9.1")
        newer.mkdir()
        (newer / "teka.py").write_text("VERSION = '0.9.1'\n")
        self.launcher.write_text("newer launcher")
        record_install(newer, "posix", ["teka.py"])
        uninstall(self.root, apply=True)
        self.assertEqual(self.launcher.read_text(), "newer launcher")
        self.assertTrue((newer / "teka.py").is_file())
        self.assertFalse(self.root.exists())

    def test_legacy_installation_or_source_checkout_refuses_removal(self):
        (self.root / RECORD).unlink()
        with self.assertRaisesRegex(InstallationError, "No ownership record"):
            uninstall(self.root, apply=True)
        self.assertTrue((self.root / "teka.py").exists())

    def test_manifest_cannot_name_an_arbitrary_file(self):
        sentinel = self.prefix / "private.txt"
        sentinel.write_text("preserve")
        record = read_record(self.root)
        record["files"]["../../../private.txt"] = hashlib.sha256(sentinel.read_bytes()).hexdigest()
        (self.root / RECORD).write_text(json.dumps(record))
        with self.assertRaises(InstallationError):
            uninstall(self.root, apply=True)
        self.assertEqual(sentinel.read_text(), "preserve")

    def test_invalid_layout_is_controlled_error(self):
        record = read_record(self.root)
        record["layout"] = []
        (self.root / RECORD).write_text(json.dumps(record))
        with self.assertRaises(InstallationError):
            uninstall(self.root, apply=True)

    def test_owned_symlink_is_preserved_without_following_target(self):
        target = self.prefix / "private.txt"
        target.write_text("readme")
        path = self.root / "README.md"
        path.unlink()
        try:
            path.symlink_to(target)
        except OSError:
            self.skipTest("Symlinks unavailable")
        result = uninstall(self.root, apply=True)
        self.assertTrue(path.is_symlink())
        self.assertEqual(target.read_text(), "readme")
        self.assertIn(str(path), result["preserved"])

    def test_preflight_rejects_edited_installed_file(self):
        (self.root / "teka.py").write_text("custom compiler")
        with self.assertRaisesRegex(InstallationError, "modified"):
            preflight(self.root, "posix", ["teka.py"])
        self.assertEqual((self.root / "teka.py").read_text(), "custom compiler")

    def test_preflight_rejects_edited_launcher(self):
        self.launcher.write_text("custom launcher")
        with self.assertRaisesRegex(InstallationError, "Launcher was modified"):
            preflight(self.root, "posix", ["teka.py"])

    def test_update_refresh_allows_removing_new_owned_files(self):
        old = read_record(self.root)
        (self.root / "teka.py").write_text("VERSION = '0.9.1'\n")
        (self.root / "PRIVACY.md").write_text("# newly shipped helper")
        record_update(self.root, old, ["teka.py", "PRIVACY.md"])
        result = uninstall(self.root, apply=True)
        self.assertEqual(result["preserved"], [])
        self.assertFalse(self.root.exists())

    def test_windows_layout_preserves_unrelated_bin_files(self):
        root = self.prefix / "0.9.0"
        root.mkdir()
        (root / "teka.py").write_text("compiler")
        for name in ("teka.cmd", "launcher.json", "other.cmd"):
            (self.prefix / "bin" / name).write_text(name)
        record_install(root, "windows", ["teka.py"])
        uninstall(root, apply=True)
        self.assertTrue((self.prefix / "bin/other.cmd").is_file())
        self.assertFalse((self.prefix / "bin/teka.cmd").exists())

    def test_windows_preflight_protects_unrelated_launcher_manifest(self):
        manifest = self.prefix / "bin/launcher.json"
        manifest.write_text('{"application": "another tool"}')
        with self.assertRaisesRegex(InstallationError, "not owned"):
            preflight(self.prefix / "0.9.1", "windows", ["teka.py"])
        self.assertEqual(manifest.read_text(), '{"application": "another tool"}')

    def test_non_regular_ownership_record_is_rejected(self):
        path = self.root / RECORD
        path.unlink()
        path.mkdir()
        with self.assertRaisesRegex(InstallationError, "regular file"):
            uninstall(self.root, apply=True)
        self.assertTrue((self.root / "teka.py").is_file())


if __name__ == "__main__":
    unittest.main()
