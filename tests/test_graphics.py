"""Tests for the native raylib-backed TekaLang game API.

Native graphical windows are smoke-tested separately so the general test
suite does not flash windows or require a GUI session.
"""
from pathlib import Path
import json
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TEKA = ROOT / "teka.py"

def invoke(src, action="check"):
    with tempfile.TemporaryDirectory(prefix="teka-game-test-") as tmp:
        file = Path(tmp) / "test.teka"
        file.write_text(src)
        return subprocess.run([sys.executable, str(TEKA), action, str(file)],
                              capture_output=True, text=True, timeout=30)

class NativeGraphicsTests(unittest.TestCase):
    def test_str_integer(self):
        r = invoke("print(str(124));", "run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "124\n")

    def test_str_boolean(self):
        r = invoke("print(str(true), str(false));", "run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "true false\n")

    def test_str_string_identity(self):
        r = invoke("print(str('nova'));", "run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "nova\n")

    def test_str_float(self):
        r = invoke("print(str(2.5));", "run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(r.stdout.startswith("2.5"))

    def test_game_random_native_link(self):
        if sys.platform != "darwin":
            self.skipTest("Native raylib linking is currently supported on macOS only")
        if not any((Path(prefix) / "include/raylib.h").is_file() for prefix in ["/opt/homebrew", "/usr/local"]):
            self.skipTest("raylib development files are not installed")
        r = invoke("print(game_rand(6, 6));", "run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "6\n")

    def test_graphics_native_cpp_includes_raylib(self):
        r = invoke("game_open('Hello', 320, 180); game_close();", "emit-cpp")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('#include "raylib.h"', r.stdout)
        self.assertIn("tk_game_open(", r.stdout)

    def test_pure_cpp_omits_graphics_dependency(self):
        r = invoke("print(42);", "emit-cpp")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn('#include "raylib.h"', r.stdout)

    def test_game_key_returns_bool(self):
        r = invoke("let down: bool = game_key('W');")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_game_function_in_user_function(self):
        r = invoke("fn frame() -> void { game_begin(); game_end(); }")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_wrong_graphics_argument_type(self):
        r = invoke("game_open(12, 200, 200);")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Expected string, got int", r.stderr)

    def test_wrong_graphics_arity(self):
        r = invoke("game_rect(1, 2, 3);")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("takes 7 arguments", r.stderr)

    def test_graphics_coordinates_allow_ints(self):
        r = invoke("game_circle(5, 6, 7, 200, 150, 90);")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_graphics_colors_reject_floats(self):
        r = invoke("game_clear(0.5, 10, 20);")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Expected int, got float", r.stderr)

    def test_graphics_funcs_are_reserved(self):
        r = invoke("var game_open = 2;")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Reserved name", r.stderr)

    def test_str_function_is_reserved(self):
        r = invoke("var str = 3;")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Reserved name", r.stderr)

    def test_str_list_rejected(self):
        r = invoke("print(str([1, 2]));")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("cannot convert list", r.stderr)

    def test_main_game_passes_typecheck(self):
        game = Path.home() / "IdeaProjects" / "TekaNova" / "main.teka"
        if not game.exists():
            self.skipTest("Demo game not present")
        r = subprocess.run([sys.executable, str(TEKA), "check", str(game)],
                           capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_game_io_color_primitives(self):
        r = invoke("""game_clear(2, 5, 10);
game_line(1, 2, 3, 4, 2, 100, 200, 250);
game_triangle(1, 2, 3, 4, 5, 6, 12, 25, 40);
game_text('hi', 0, 0, 15, 255, 255, 255);
""")
        self.assertEqual(r.returncode, 0, r.stderr)

if __name__ == "__main__":
    unittest.main()