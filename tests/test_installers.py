"""Exercise local installers in isolated prefixes without changing user PATH."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from updater import ALLOWED_COMPILER, OPTIONAL_COMPILER, current_version

ROOT = Path(__file__).resolve().parents[1]


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="teka install tests ")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.source = self.base / "source with spaces"
        self.source.mkdir()
        for name in ALLOWED_COMPILER + OPTIONAL_COMPILER:
            if (ROOT / name).is_file():
                shutil.copy2(ROOT / name, self.source / name)
        self.prefix = self.base / "installed with spaces"
        self.windows = sys.platform == "win32"
        self.launcher = self.prefix / "bin" / ("teka.cmd" if self.windows else "teka")

    def install(self):
        if self.windows:
            shell = shutil.which("pwsh") or shutil.which("powershell")
            if not shell:
                self.skipTest("PowerShell unavailable")
            command = [shell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                       "-File", str(self.source / "install.ps1"), "-Prefix", str(self.prefix), "-NoPath"]
        else:
            command = ["sh", str(self.source / "install.sh"), "--prefix", str(self.prefix)]
        return subprocess.run(command, capture_output=True, text=True, timeout=60)

    def installed_root(self, version):
        return self.prefix / version if self.windows else self.prefix / "share/teka" / version

    def check_launcher(self, version):
        if self.windows:
            manifest = json.loads((self.prefix / "bin/launcher.json").read_text())
            self.assertEqual(Path(manifest["launcher"]).parent, self.installed_root(version))
            command = [manifest["python"], manifest["launcher"]]
        else:
            command = [str(self.launcher)]
        result = subprocess.run(command + ["--version"], capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "T+ " + version)
        result = subprocess.run(command + ["update", "status", "--json"], capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["current"], version)

    def test_reinstall_in_path_with_spaces(self):
        version = current_version(ROOT)
        for _ in range(2):
            result = self.install()
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.check_launcher(version)
        self.assertEqual((self.installed_root(version) / "PRIVACY.md").read_bytes(), (ROOT / "PRIVACY.md").read_bytes())

    def test_new_source_version_selects_new_directory(self):
        old = current_version(ROOT)
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        new = ".".join(old.split(".")[:2] + [str(int(old.split(".")[2]) + 1)])
        source = self.source / "teka.py"
        source.write_text(source.read_text(encoding="utf-8").replace(f"VERSION = '{old}'", f"VERSION = '{new}'"), encoding="utf-8")
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.check_launcher(new)
        self.assertEqual(current_version(self.installed_root(old)), old)
        self.assertEqual((self.installed_root(new) / ".tplus-install").read_text().strip(), "T+ " + new)

    def test_unrelated_launcher_is_preserved(self):
        self.launcher.parent.mkdir(parents=True)
        self.launcher.write_text("unrelated command")
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.launcher.read_text(), "unrelated command")
        self.assertFalse(self.installed_root(current_version(ROOT)).exists())

    def test_missing_version_fails_before_installing(self):
        (self.source / "teka.py").write_text("# No version assignment\n")
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.prefix.exists())


if __name__ == "__main__":
    unittest.main()
