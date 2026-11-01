"""Offline updater regression tests. No changes to the real user installation."""
from unittest.mock import patch
from contextlib import redirect_stdout
import updater
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from updater import Updater, UpdateError, validate_bundle, OPTIONAL_COMPILER


class UpdaterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="teka-update-test-")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / "TekaLang"
        self.plugin = self.base / "ide" / "TekaLang-IntelliJ"
        self.root.mkdir()
        self.plugin.mkdir(parents=True)
        (self.root / "teka.py").write_text("VERSION = '0.3.0'\n")
        (self.root / "teka").write_text("old-launcher\n")
        (self.plugin / "old.jar").write_bytes(b"old")
        self.feed = self.root / "releases" / "stable.json"
        self.feed.parent.mkdir()
        self.config = self.base / "updates.json"
        self.m = Updater(self.root, self.plugin, self.config, feed_override=self.feed)

    @staticmethod
    def plugin_bytes(version="0.4.0"):
        jar = io.BytesIO()
        with zipfile.ZipFile(jar, "w", zipfile.ZIP_DEFLATED) as zipout:
            zipout.writestr("META-INF/plugin.xml",
                f'<idea-plugin><id>dev.teka.lang</id><version>{version}</version></idea-plugin>')
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zipout:
            zipout.writestr(f"TekaLang-IntelliJ/lib/TekaLang-IntelliJ-{version}.jar", jar.getvalue())
        return output.getvalue()

    def write_release(self, version="0.4.0", alter=None):
        members = {
            "compiler/teka.py": f"VERSION = '{version}'\nprint('new compiler')\n".encode(),
            "compiler/python_style.py": b"# normalizer\n",
            "compiler/standard_modules.py": b"# native modules\n",
            "compiler/project_tools.py": b"# project scaffolding\n",
            "compiler/updater.py": b"# updater\n",
            "compiler/teka": b"#!/bin/sh\nexit 0\n",
            "plugin/TekaLang-IntelliJ.zip": self.plugin_bytes(version),
        }
        if alter:
            alter(members)
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zipout:
            for name, data in members.items():
                zipout.writestr(name, data)
        blob = output.getvalue()
        (self.feed.parent / "release.zip").write_bytes(blob)
        self.feed.write_text(json.dumps({
            "schema": 1, "channel": "stable", "version": version,
            "notes": "New features", "asset": "release.zip",
            "sha256": hashlib.sha256(blob).hexdigest(),
            "size_bytes": len(blob),
        }))
        return blob

    def test_check_upgrade(self):
        self.write_release()
        status = self.m.check()
        self.assertTrue(status["available"])
        self.assertEqual(status["current"], "0.3.0")
        self.assertEqual(status["latest"], "0.4.0")

    def test_install_updates_compiler_and_plugin(self):
        self.write_release()
        result = self.m.install()
        self.assertTrue(result["installed"])
        self.assertTrue(result["restart_required"])
        self.assertIn("VERSION = '0.4.0'", (self.root / "teka.py").read_text())
        self.assertTrue((self.plugin / "lib" / "TekaLang-IntelliJ-0.4.0.jar").is_file())
        self.assertFalse((self.plugin / "old.jar").exists())
        backup = Path(result["backup"])
        self.assertEqual((backup / "teka").read_text(), "old-launcher\n")
        self.assertEqual((backup / "TekaLang-IntelliJ" / "old.jar").read_bytes(), b"old")
        self.assertFalse(self.m.check()["available"])

    def test_optional_handbook_in_release(self):
        extras = {name: ("Optional release file: " + name + "\n").encode("utf-8")
                  for name in OPTIONAL_COMPILER}
        self.write_release(alter=lambda items: items.update({
            "compiler/" + name: data for name, data in extras.items()
        }))
        result = self.m.install()
        self.assertTrue(result["installed"])
        for name, data in extras.items():
            self.assertEqual((self.root / name).read_bytes(), data)

    def test_already_latest(self):
        (self.root / "teka.py").write_text("VERSION = '0.4.0'\n")
        self.write_release()
        self.assertFalse(self.m.check()["available"])
        self.assertFalse(self.m.install()["installed"])

    def test_downgrade_not_installed(self):
        (self.root / "teka.py").write_text("VERSION = '0.5.0'\n")
        self.write_release()
        self.assertFalse(self.m.check()["available"])
        self.assertFalse(self.m.install()["installed"])

    def test_checksum_mismatch_does_not_touch_files(self):
        self.write_release()
        manifest = json.loads(self.feed.read_text())
        manifest["sha256"] = "0" * 64
        self.feed.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(UpdateError, "checksum mismatch"):
            self.m.install()
        self.assertIn("0.3.0", (self.root / "teka.py").read_text())
        self.assertTrue((self.plugin / "old.jar").exists())

    def test_bad_manifest(self):
        self.feed.write_text("not json")
        with self.assertRaisesRegex(UpdateError, "Invalid update feed"):
            self.m.check()

    def test_unknown_member_rejected(self):
        self.write_release(alter=lambda d: d.update({"compiler/../../../hijack": b"bad"}))
        with self.assertRaisesRegex(UpdateError, "unexpected file"):
            self.m.install()

    def test_missing_member_rejected(self):
        self.write_release(alter=lambda d: d.pop("compiler/updater.py"))
        with self.assertRaisesRegex(UpdateError, "Missing release files"):
            self.m.install()

    def test_wrong_plugin_version_rejected(self):
        self.write_release(alter=lambda d: d.update({"plugin/TekaLang-IntelliJ.zip": self.plugin_bytes("1.0.0")}))
        with self.assertRaisesRegex(UpdateError, "Wrong plugin version"):
            self.m.install()

    def test_invalid_version(self):
        self.write_release()
        manifest = json.loads(self.feed.read_text())
        manifest["version"] = "xxx"
        self.feed.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(UpdateError, "Invalid semantic"):
            self.m.check()

    def test_external_http_feed_not_allowed(self):
        manager = Updater(self.root, self.plugin, self.config)
        with self.assertRaisesRegex(UpdateError, "HTTPS"):
            manager.set_source("http://updates.example.com/stable.json")

    def test_https_feed_saved(self):
        manager = Updater(self.root, self.plugin, self.config)
        manager.set_source("https://example.com/releases/stable.json")
        self.assertEqual(manager.source(), "https://example.com/releases/stable.json")
        manager.set_source(None)
        self.assertEqual(manager.source(), updater.OFFICIAL_RELEASE_API)

    def test_remote_asset_must_share_feed_host(self):
        self.write_release()
        manifest = json.loads(self.feed.read_text())
        manifest["asset"] = "https://another.example.com/release.zip"
        self.feed.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(UpdateError, "Local update filenames"):
            self.m.check()

    def test_zip_size_rejected(self):
        self.write_release()
        manifest = json.loads(self.feed.read_text())
        manifest["size_bytes"] = 0
        self.feed.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(UpdateError, "archive size"):
            self.m.check()

    def test_expected_member_set(self):
        self.write_release()
        blob = (self.feed.parent / "release.zip").read_bytes()
        members = validate_bundle(blob, "0.4.0")
        self.assertIn("compiler/teka.py", members)
        self.assertIn("plugin/TekaLang-IntelliJ.zip", members)


    def test_default_source_is_public_github(self):
        manager = Updater(self.root, self.plugin, self.config)
        self.assertEqual(manager.source(), updater.OFFICIAL_RELEASE_API)

    def github_payload(self, blob):
        root = updater.OFFICIAL_DOWNLOAD_ROOT + "v0.4.0/"
        return {"draft": False, "prerelease": False, "tag_name": "v0.4.0",
                "body": "A stable release",
                "assets": [
                    {"name": "TPlus-v0.4.0.zip", "size": len(blob),
                     "browser_download_url": root + "TPlus-v0.4.0.zip"},
                    {"name": "SHA256SUMS.txt", "size": 100,
                     "browser_download_url": root + "SHA256SUMS.txt"}]}

    def test_install_from_public_github_release(self):
        blob = self.write_release()
        payload = self.github_payload(blob)
        checksum = (hashlib.sha256(blob).hexdigest() + "  TPlus-v0.4.0.zip\n").encode()
        manager = Updater(self.root, self.plugin, self.config,
                          feed_override=updater.OFFICIAL_RELEASE_API)
        with patch("updater.read_limited", side_effect=[json.dumps(payload).encode(), checksum, blob]) as downloads:
            result = manager.install()
        self.assertTrue(result["installed"])
        self.assertEqual(downloads.call_count, 3)
        self.assertIn("0.4.0", (self.root / "teka.py").read_text())

    def test_github_rejects_external_download(self):
        payload = self.github_payload(self.write_release())
        payload["assets"][0]["browser_download_url"] = "https://example.org/TPlus-v0.4.0.zip"
        with self.assertRaisesRegex(UpdateError, "official T\\+ GitHub"):
            updater.github_release(payload)

    def test_github_rejects_draft_and_prerelease(self):
        for key in ["draft", "prerelease"]:
            payload = self.github_payload(b"archive")
            payload[key] = True
            with self.assertRaisesRegex(UpdateError, "published stable"):
                updater.github_release(payload)

    def test_github_rejects_ambiguous_checksums(self):
        payload = self.github_payload(b"archive")
        line = ("a" * 64 + "  TPlus-v0.4.0.zip\n").encode()
        with patch("updater.read_limited", return_value=line + line):
            with self.assertRaisesRegex(UpdateError, "ambiguous"):
                updater.github_release(payload)

    def test_update_without_intellij_only_changes_compiler(self):
        self.write_release()
        with patch("updater.default_plugin_dir", return_value=None):
            manager = Updater(self.root, config_path=self.config, feed_override=self.feed)
        result = manager.install()
        self.assertTrue(result["installed"])
        self.assertFalse(result["restart_required"])
        self.assertTrue((self.plugin / "old.jar").exists())

    def test_bare_update_command_installs_without_prompt(self):
        self.write_release()
        output = io.StringIO()
        with patch("updater.Updater", return_value=self.m), redirect_stdout(output):
            self.assertEqual(updater.cli([]), 0)
        self.assertIn("T+ updated to 0.4.0.", output.getvalue())
        self.assertIn("0.4.0", (self.root / "teka.py").read_text())


    def test_offline_feed_is_used_when_present(self):
        self.write_release()
        manager = Updater(self.root, self.plugin, self.config)
        self.assertEqual(manager.source().resolve(), self.feed.resolve())

    def test_compiler_update_rolls_back_on_replace_failure(self):
        self.write_release()
        old = (self.root / "teka.py").read_bytes()
        original_replace = updater.os.replace
        def fail_one(source, destination):
            if Path(destination).name == "standard_modules.py":
                raise OSError("simulated write failure")
            return original_replace(source, destination)
        with patch("updater.os.replace", side_effect=fail_one):
            with self.assertRaisesRegex(UpdateError, "rolled back"):
                self.m.install()
        self.assertEqual((self.root / "teka.py").read_bytes(), old)
        self.assertTrue((self.plugin / "old.jar").exists())

    def test_invalid_config_is_a_controlled_cli_error(self):
        manager = Updater(self.root, self.plugin, self.config)
        for value in ([], None, 1, {"feed_url": 123}, {"feed_url": []},
                      {"feed_url": "https:///missing-host"},
                      {"feed_url": "https://user:password@example.com/feed"}):
            with self.subTest(value=value):
                self.config.write_text(json.dumps(value))
                output = io.StringIO()
                with patch("updater.Updater", return_value=manager), redirect_stdout(output):
                    self.assertEqual(updater.cli(["status", "--json"]), 1)
                self.assertFalse(json.loads(output.getvalue())["ok"])

    def test_local_feed_rejects_windows_path_syntax(self):
        self.write_release()
        original = json.loads(self.feed.read_text())
        for name in ("..\\outside.zip", "C:outside.zip", "dir\\release.zip"):
            with self.subTest(name=name):
                self.feed.write_text(json.dumps({**original, "asset": name}))
                with self.assertRaisesRegex(UpdateError, "Local update filenames"):
                    self.m.check()

    def test_plugin_archive_rejects_unsafe_and_duplicate_members(self):
        for name in ("TekaLang-IntelliJ/..\\outside", "TekaLang-IntelliJ/C:payload",
                     "TekaLang-IntelliJ/../outside", "TekaLang-IntelliJ/lib/./extra.jar",
                     "TekaLang-IntelliJ/lib/TekaLang-IntelliJ-0.4.0.jar"):
            with self.subTest(name=name):
                plugin = io.BytesIO(self.plugin_bytes())
                import warnings
                with warnings.catch_warnings(), zipfile.ZipFile(plugin, "a") as archive:
                    warnings.simplefilter("ignore", UserWarning)
                    archive.writestr(name, b"extra")
                self.write_release(alter=lambda files: files.update({"plugin/TekaLang-IntelliJ.zip": plugin.getvalue()}))
                with self.assertRaises(UpdateError):
                    self.m.install()
                self.assertEqual((self.root / "teka.py").read_text(), "VERSION = '0.3.0'\n")
                self.assertFalse((self.root / "backups").exists())

    def test_missing_plugin_descriptor_is_controlled_error(self):
        jar = io.BytesIO()
        with zipfile.ZipFile(jar, "w") as archive:
            archive.writestr("other.txt", "no descriptor")
        plugin = io.BytesIO()
        with zipfile.ZipFile(plugin, "w") as archive:
            archive.writestr("TekaLang-IntelliJ/lib/TekaLang-IntelliJ-0.4.0.jar", jar.getvalue())
        blob = self.write_release(alter=lambda files: files.update({"plugin/TekaLang-IntelliJ.zip": plugin.getvalue()}))
        with self.assertRaises(UpdateError):
            validate_bundle(blob, "0.4.0")

    def test_nested_plugin_unpacked_size_limit(self):
        plugin = io.BytesIO(self.plugin_bytes())
        with zipfile.ZipFile(plugin, "a", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("TekaLang-IntelliJ/lib/one", b"x" * 1500)
            archive.writestr("TekaLang-IntelliJ/lib/two", b"x" * 1500)
        blob = self.write_release(alter=lambda files: files.update({"plugin/TekaLang-IntelliJ.zip": plugin.getvalue()}))
        with patch("updater.MAX_UNPACKED_BYTES", 2500):
            with self.assertRaisesRegex(UpdateError, "unpack"):
                validate_bundle(blob, "0.4.0")

    def managed_installation(self):
        from project_tools import record_install
        # Match the installer, which canonicalizes the prefix before recording
        # ownership (macOS temporary directories can be reached through /var).
        prefix = self.base.resolve() / "managed"
        root = prefix / "share/teka/0.3.0"
        root.parent.mkdir(parents=True)
        self.root.rename(root)
        self.root = root
        self.feed = root / "releases/stable.json"
        self.m = Updater(root, self.plugin, self.config, feed_override=self.feed)
        (prefix / "bin").mkdir()
        (prefix / "bin/teka").write_text("managed launcher")
        record_install(root, "posix", ["teka.py", "teka"])

    def test_managed_update_refreshes_ownership_for_uninstall(self):
        from project_tools import uninstall
        self.managed_installation()
        self.write_release()
        self.m.install()
        result = uninstall(self.root)
        self.assertIn(str(self.root / "teka.py"), result["remove"])
        self.assertIn(str(self.root / "standard_modules.py"), result["remove"])
        uninstall(self.root, apply=True)
        self.assertFalse((self.root / "teka.py").exists())
        self.assertTrue((self.root / "backups").exists())

    def test_managed_update_preserves_local_edits(self):
        self.managed_installation()
        self.write_release()
        compiler = self.root / "teka.py"
        compiler.write_text("VERSION = '0.3.0'\n# local edits\n")
        with self.assertRaisesRegex(UpdateError, "modified"):
            self.m.install()
        self.assertIn("local edits", compiler.read_text())
        self.assertFalse((self.root / "backups").exists())

    def test_ownership_write_failure_rolls_back_update(self):
        from project_tools import read_record
        self.managed_installation()
        self.write_release()
        before = (self.root / "teka.py").read_bytes()
        record = read_record(self.root)
        with patch("project_tools.atomic_record", side_effect=OSError("simulated ownership write failure")):
            with self.assertRaisesRegex(UpdateError, "rolled back"):
                self.m.install()
        self.assertEqual((self.root / "teka.py").read_bytes(), before)
        self.assertEqual(read_record(self.root), record)
        self.assertTrue((self.plugin / "old.jar").exists())


if __name__ == "__main__":
    unittest.main()
