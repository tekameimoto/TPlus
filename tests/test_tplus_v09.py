"""T+ v0.9: English syntax, namespace imports and native standard library."""
from pathlib import Path
import subprocess
import tempfile
import sys
import unittest

LANG = Path(__file__).resolve().parents[1] / "teka.py"

def invoke(source, mode="run", stdin=""):
    with tempfile.TemporaryDirectory(prefix="tplus-v09-") as tmp:
        src = Path(tmp) / "main.teka"
        src.write_text(source, encoding="utf-8")
        return subprocess.run([sys.executable, str(LANG), mode, str(src)],
                              input=stdin, text=True, capture_output=True, timeout=30, cwd=tmp)

class TPlusHybridTests(unittest.TestCase):
    def runs(self, code, expected):
        p=invoke(code)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout, expected)
    def rejects(self, code, expected):
        p=invoke(code,"check")
        self.assertNotEqual(p.returncode, 0, p.stdout)
        self.assertIn(expected, p.stderr)

    def test_say_and_old_print(self):
        self.runs("say 'hi'\nprint('old')\nsay('new')", "hi\nold\nnew\n")
    def test_ask_with_parens(self):
        p=invoke("name = ask('name: ')\nsay name", stdin="Ada\n")
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(p.stdout,"name: Ada\n")
    def test_ask_without_parens(self):
        p=invoke("name = ask 'name: '\nsay name", stdin="Ada\n")
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(p.stdout,"name: Ada\n")
    def test_ask_word_preserved_in_strings(self):
        self.runs('print("ask(hello)")\ntext = "ask(again)"\nsay text', "ask(hello)\nask(again)\n")

    def test_repeat_only_mode(self):
        self.runs("repeat 3 times:\n\tsay 'yes'", "yes\nyes\nyes\n")
    def test_repeat_count_expression(self):
        self.runs("count = 2\nrepeat count + 1 times:\n\tsay 'x'", "x\nx\nx\n")
    def test_repeat_and_english_conditions(self):
        self.runs("health = 10\nrepeat 2 times:\n\tif health is at least 10:\n\t\tsay 'ok'\n\totherwise:\n\t\tsay 'no'", "ok\nok\n")
    def test_english_all_comparators(self):
        self.runs("""x = 7
if x is above 6 and x is below 8 and x is equal to 7 and x is not equal to 5:
    say "first"
if x is at most 7 and x is at least 7:
    say "second"
""", "first\nsecond\n")
    def test_english_does_not_replace_strings(self):
        self.runs('say "is below and is above"', "is below and is above\n")
    def test_otherwise_if(self):
        self.runs("x = 2\nif x == 1:\n\tsay 'one'\notherwise if x == 2:\n\tsay 'two'\notherwise:\n\tsay 'three'", "two\n")
    def test_stop_and_skip(self):
        self.runs("repeat 4 times:\n\tsay 'first'\n\tskip\n\tsay 'never'\nrepeat 4 times:\n\tsay 'once'\n\tstop", "first\nfirst\nfirst\nfirst\nonce\n")
    def test_namespace_random(self):
        self.runs("import teka.random\nsay teka.random.randint(9,9)", "9\n")
    def test_namespace_multiple(self):
        self.runs("import teka.random\nimport teka.math\nsay teka.math.sqrt(teka.random.randint(16,16))", "4\n")
    def test_namespace_alias(self):
        self.runs("import teka.random as rng\nsay rng.randint(6,6)", "6\n")
    def test_missing_namespace_import(self):
        self.rejects("import teka.math\nsay teka.random.randint(1,2)", "Import it first")
    def test_time(self):
        self.runs("import teka.time\nteka.time.sleep(0)\nsay teka.time.now() > 0.0", "true\n")
    def test_text(self):
        self.runs("""import teka.text
say teka.text.upper("abc"), teka.text.lower("ABC")
say teka.text.contains("abcdef","cd"), teka.text.starts_with("abc","a"), teka.text.ends_with("abc","bc")
say teka.text.replace("a-b-c", "-", " ")
""", "ABC abc\ntrue true true\na b c\n")
    def test_file_io(self):
        self.runs("""import teka.files
teka.files.write("notes.txt", "one")
teka.files.append("notes.txt", " two")
say teka.files.exists("notes.txt")
say teka.files.read("notes.txt")
""", "true\none two\n")
    def test_missing_file_runtime_error(self):
        p=invoke("import teka.files\nsay teka.files.read('missing.txt')")
        self.assertNotEqual(p.returncode,0)
        self.assertIn("cannot open",p.stderr)
    def test_json_quote(self):
        self.runs('import teka.json\nsay teka.json.quote("hello")', '"hello"\n')
    def test_system(self):
        p=invoke("import teka.system\nsay teka.system.platform()")
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn(p.stdout.strip(),{"macos","linux","windows","unknown"})
    def test_graphics_facade_checks(self):
        p=invoke("import teka.graphics\nteka.graphics.open('test', 640, 480)\nteka.graphics.close()","check")
        self.assertEqual(p.returncode,0,p.stderr)
    def test_stdlib_reference_machine_readable(self):
        import json
        response = subprocess.run([sys.executable, str(LANG), "stdlib", "--json"],
                                  text=True, capture_output=True, timeout=15)
        self.assertEqual(response.returncode, 0, response.stderr)
        modules = json.loads(response.stdout)
        self.assertIn("files", modules)
        self.assertIn("graphics", modules)
        self.assertIn("uniform", modules["random"]["functions"])

    def test_handbook_path_command(self):
        response = subprocess.run([sys.executable, str(LANG), "docs"],
                                  text=True, capture_output=True, timeout=15)
        self.assertEqual(response.returncode, 0, response.stderr)
        doc = Path(response.stdout.strip())
        self.assertTrue(doc.is_file())
        self.assertIn("T+ Handbook", doc.read_text())

    def test_graphics_facade_covers_old_api(self):
        from teka import GAME_FUNCTIONS
        from standard_modules import MODULES
        mapped = MODULES["graphics"].functions
        self.assertEqual(set(mapped), {name[5:] for name in GAME_FUNCTIONS})
        for method, info in mapped.items():
            args, returns = GAME_FUNCTIONS["game_"+method]
            self.assertEqual(list(info.args), args)
            self.assertEqual(info.returns, returns)

    def test_python_random_still_works(self):
        self.runs("import random as r\nprint(r.randint(1,1))","1\n")
    def test_bad_module(self):
        self.rejects("import teka.requests\nsay 1","Unknown module")
    def test_repeated_namespace_same_import_allowed(self):
        self.runs("import teka.math\nimport teka.math\nsay teka.math.pi > 3.0","true\n")

if __name__ == "__main__":
    unittest.main()