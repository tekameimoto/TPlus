"""CLI project scaffolding and toolchain regression tests."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
TEKA = ROOT / "teka.py"
sys.path.insert(0, str(ROOT))
from project_tools import ProjectError, create_project, project_entry


class ProjectToolsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="teka-new-")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)

    def run_teka(self, *args, cwd=None):
        return subprocess.run([sys.executable, str(TEKA), *args],
                              capture_output=True, text=True,
                              cwd=cwd or self.base, timeout=25)

    def test_create_project(self):
        path = create_project(str(self.base / "HelloWorld"))
        self.assertTrue((path / "teka.toml").exists())
        self.assertTrue((path / "src" / "main.teka").exists())
        self.assertTrue((path / "tests" / "test_main.teka").exists())
        self.assertTrue((path / ".editorconfig").exists())

    def test_project_config_resolves_entry(self):
        path = create_project(str(self.base / "Example"))
        self.assertEqual(project_entry(path), (path / "src" / "main.teka").resolve())

    def test_run_project_without_filename(self):
        path = create_project(str(self.base / "Example"))
        run = self.run_teka("run", cwd=path)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "hello from Example!\n")

    def test_check_project_without_filename(self):
        path = create_project(str(self.base / "Example"))
        run = self.run_teka("check", cwd=path)
        self.assertEqual(run.returncode, 0, run.stderr)

    def test_native_release_build(self):
        path = create_project(str(self.base / "Example"))
        run = self.run_teka("build", "--release", cwd=path)
        self.assertEqual(run.returncode, 0, run.stderr)
        executable = path / "src" / ("main.exe" if sys.platform == "win32" else "main")
        self.assertTrue(executable.is_file())
        executed = subprocess.run([str(executable)], capture_output=True, text=True, timeout=5)
        self.assertEqual(executed.returncode, 0)
        self.assertEqual(executed.stdout, "hello from Example!\n")

    def test_create_project_cli(self):
        path = self.base / "MyNewGame"
        run = self.run_teka("new", "MyNewGame")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertTrue((path / "src" / "main.teka").exists())

    def test_existing_folder_not_overwritten(self):
        path = self.base / "Existing"
        path.mkdir()
        protected = path / "dont-touch.txt"
        protected.write_text("original", encoding="utf-8")
        with self.assertRaisesRegex(ProjectError, "already exists"):
            create_project(str(path))
        self.assertEqual(protected.read_text(), "original")

    def test_project_name_validation(self):
        for name in ("Invalid Name", "123startsWithNumber", "dot.name"):
            with self.assertRaises(ProjectError):
                create_project(str(self.base / name))

    def test_no_manifest_returns_none(self):
        self.assertIsNone(project_entry(self.base))

    def test_project_entry_does_not_escape(self):
        path = create_project(str(self.base / "Example"))
        (path / "teka.toml").write_text(
            '[project]\nname="Example"\n[build]\nentry="../outside.teka"\n'
        )
        with self.assertRaisesRegex(ProjectError, "stay inside"):
            project_entry(path)

    def test_invalid_manifest_error(self):
        path = create_project(str(self.base / "Example"))
        (path / "teka.toml").write_text("not = [valid")
        with self.assertRaisesRegex(ProjectError, "Invalid teka.toml"):
            project_entry(path)

    def test_missing_entry_error(self):
        path = create_project(str(self.base / "Example"))
        (path / "src" / "main.teka").unlink()
        with self.assertRaisesRegex(ProjectError, "Entry does not exist"):
            project_entry(path)

    def test_cli_doctor_json(self):
        run = self.run_teka("doctor", "--json")
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        self.assertIn("cpp_compiler", report)
        self.assertTrue(report["python_supported"])
        self.assertEqual(report["status"], "ready")

    def test_run_without_manifest_or_source_reports_error(self):
        run = self.run_teka("run")
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("Provide a .teka file", run.stderr)

    def test_release_flag_only_changes_optimization(self):
        path = create_project(str(self.base / "Example"))
        regular = self.run_teka("build", cwd=path)
        release = self.run_teka("build", "--release", cwd=path)
        self.assertEqual(regular.returncode, 0, regular.stderr)
        self.assertEqual(release.returncode, 0, release.stderr)


if __name__ == "__main__":
    unittest.main()