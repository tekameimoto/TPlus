"""Regressions for non-destructive builds and offline CLI diagnostics."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import teka
from project_tools import doctor
from standard_modules import MODULES


class StabilizationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="teka stabilization ")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "hello.teka"
        self.source.write_text('say "hello"\n', encoding="utf-8")
        self.output = self.root / ("hello.exe" if sys.platform == "win32" else "hello")

    def invoke(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = teka.main(list(args))
        return code, stdout.getvalue(), stderr.getvalue()

    def test_build_never_overwrites_source(self):
        old = self.source.read_bytes()
        with patch("teka.subprocess.run") as backend:
            code, out, err = self.invoke("build", str(self.source), "-o", str(self.source), "--json")
        self.assertEqual(code, 1)
        self.assertFalse(json.loads(out)["ok"])
        self.assertIn("source", out)
        backend.assert_not_called()
        self.assertEqual(self.source.read_bytes(), old)

    def test_build_rejects_hardlink_to_source(self):
        try:
            os.link(self.source, self.output)
        except OSError:
            self.skipTest("Hard links unavailable")
        with patch("teka.subprocess.run") as backend:
            code, out, err = self.invoke("build", str(self.source), "-o", str(self.output))
        self.assertEqual(code, 1)
        backend.assert_not_called()
        self.assertEqual(self.source.read_text(), 'say "hello"\n')

    def test_failed_backend_preserves_previous_build(self):
        self.output.write_bytes(b"previous executable")
        def fail(command, **kwargs):
            Path(command[command.index("-o") + 1]).write_bytes(b"partial output")
            return subprocess.CompletedProcess(command, 1, "", "simulated linker failure")
        with patch("teka.subprocess.run", side_effect=fail):
            code, out, err = self.invoke("build", str(self.source), "-o", str(self.output))
        self.assertEqual(code, 1)
        self.assertIn("simulated linker failure", err)
        self.assertEqual(self.output.read_bytes(), b"previous executable")
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), sorted([self.source.name, self.output.name]))

    def test_build_rejects_output_symlink(self):
        target = self.root / "unrelated"
        target.write_bytes(b"keep me")
        try:
            self.output.symlink_to(target)
        except OSError:
            self.skipTest("Symlinks unavailable")
        with patch("teka.subprocess.run") as backend:
            code, out, err = self.invoke("build", str(self.source), "-o", str(self.output))
        self.assertEqual(code, 1)
        backend.assert_not_called()
        self.assertEqual(target.read_bytes(), b"keep me")

    def test_deep_source_produces_json_diagnostic(self):
        for source in ('say ' + '(' * 2000 + '1' + ')' * 2000,
                       'say ' + ' + '.join(['1'] * 2000)):
            with self.subTest(source=source[:30]), patch("sys.stdin", io.StringIO(source)):
                code, out, err = self.invoke("check", "--stdin", "--json")
                self.assertEqual(code, 1)
                self.assertEqual(json.loads(out)["errors"][0]["code"], "E401")
                self.assertNotIn("Traceback", err)

    def test_doctor_uses_module_registry(self):
        self.assertEqual(doctor(self.root)["stdlib"], sorted(MODULES))

    def test_doctor_agrees_with_stdlib_command(self):
        code, out, err = self.invoke("stdlib", "--json")
        self.assertEqual(code, 0)
        self.assertEqual(doctor(self.root)["stdlib"], sorted(json.loads(out)))

    def test_doctor_does_not_claim_linux_graphics_from_header_alone(self):
        with patch("project_tools.sys.platform", "linux"), patch("pathlib.Path.exists", return_value=True):
            self.assertFalse(doctor(self.root)["graphics_available"])


if __name__ == "__main__":
    unittest.main()
