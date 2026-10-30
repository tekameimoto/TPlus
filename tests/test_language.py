"""Regression tests for TekaLang 0.2."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEKA = ROOT / "teka.py"

def invoke(source, mode="check"):
    with tempfile.TemporaryDirectory() as tmp:
        file = Path(tmp) / "main.teka"
        file.write_text(source, encoding="utf-8")
        return subprocess.run([sys.executable, str(TEKA), mode, str(file)],
                              text=True, capture_output=True, timeout=25)

class TekaLanguageTests(unittest.TestCase):
    def good(self, source):
        r = invoke(source)
        self.assertEqual(r.returncode, 0, r.stderr)

    def bad(self, source, fragment):
        r = invoke(source)
        self.assertNotEqual(r.returncode, 0, "Expected compile error")
        self.assertIn(fragment, r.stderr)

    def run_out(self, source, expected):
        r = invoke(source, "run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, expected)

    def test_hello(self):
        self.run_out('print("hello", 42);', "hello 42\n")

    def test_fibonacci(self):
        self.run_out('fn fib(n: int) -> int { if n <= 1 {return n;} else {return fib(n - 1) + fib(n - 2);} } print(fib(8));', "21\n")

    def test_list_literal_and_index(self):
        self.run_out('let xs = [2, 3, 5]; print(xs[2]);', "5\n")

    def test_nested_list(self):
        self.run_out('let grid = [[1,2], [3,4]]; print(grid[1][0]);', "3\n")

    def test_list_mutation(self):
        self.run_out('var xs: list<int> = [3, 5]; push(xs, 8); xs[0] = 1; print(len(xs), pop(xs), len(xs), xs[0]);',
                     "3 8 2 1\n")

    def test_empty_typed_list(self):
        self.run_out('var a: list<string> = []; push(a, "hi"); print(a[0]);', "hi\n")

    def test_foreach(self):
        self.run_out('var t = 0; for item in [1, 2, 3] { t = t + item; } print(t);', "6\n")

    def test_continue_and_break(self):
        self.run_out('var t = 0; for i in 0..8 { if i == 2 {continue;} if i == 5 {break;} t = t + i; } print(t);', "8\n")

    def test_len_string(self):
        self.run_out('print(len("teka"));', "4\n")

    def test_bool_print(self):
        self.run_out('print(true, false);', "true false\n")

    def test_list_function_parameter(self):
        self.run_out('fn total(xs: list<int>) -> int { var v = 0; for x in xs { v = v + x; } return v; } print(total([1,2,3]));', "6\n")

    def test_immutable_assignment_rejected(self):
        self.bad('let a = 1; a = 2;', "immutable")

    def test_immutable_index_rejected(self):
        self.bad('let a = [1]; a[0] = 3;', "immutable")

    def test_push_immutable_rejected(self):
        self.bad('let a = [1]; push(a, 2);', "mutable")

    def test_wrong_push_type_rejected(self):
        self.bad('var a = [1]; push(a, "no");', "Expected int")

    def test_invalid_list_mixed_types(self):
        self.bad('let a = ["x", 4];', "compatible")

    def test_empty_inference_rejected(self):
        self.bad('let a = [];', "explicit type")

    def test_index_not_int(self):
        self.bad('let a = [1]; print(a["hi"]);', "index must be int")

    def test_len_wrong_type(self):
        self.bad('print(len(42));', "len requires")

    def test_break_outside_loop(self):
        self.bad('break;', "inside a loop")

    def test_continue_outside_loop(self):
        self.bad('continue;', "inside a loop")

    def test_reserved_builtin_name(self):
        self.bad('let push = 5;', "Reserved")

    def test_missing_return(self):
        self.bad('fn f(x: int) -> int { print(x); }', "might exit")

    def test_type_error(self):
        self.bad('let x: int = true;', "Expected int")

    def test_bad_syntax(self):
        self.bad('var x = ', "Expected expression")

    def test_python_def_with_tabs(self):
        self.run_out("def square(n: int) -> int:\n\treturn n * n\n\nprint(square(9))\n", "81\n")

    def test_python_range(self):
        self.run_out("x = 0\nfor i in range(1, 5):\n\tx = x + i\nprint(x)\n", "10\n")

    def test_python_foreach(self):
        self.run_out("xs = [2, 4, 6]\nfor x in xs:\n\tprint(x)\n", "2\n4\n6\n")

    def test_python_elif_else(self):
        self.run_out("x = 2\nif x == 1:\n\tprint('one')\nelif x == 2:\n\tprint('two')\nelse:\n\tprint('three')\n", "two\n")

    def test_python_nested_blocks(self):
        self.run_out("for x in range(3):\n\tif x == 1:\n\t\tprint('middle')\n\telse:\n\t\tprint(x)\n", "0\nmiddle\n2\n")

    def test_python_bool_constants(self):
        self.run_out("if True and not False:\n\tprint('yes')\n", "yes\n")

    def test_python_single_quotes_and_comments(self):
        self.run_out("print('hello # world') # hello\nprint('safe // url')\n", "hello # world\nsafe // url\n")

    def test_python_pass(self):
        self.run_out("if true:\n\tpass\nprint('done')\n", "done\n")

    def test_python_auto_decl_and_reassign(self):
        self.run_out("score = 1\nscore = score + 2\nprint(score)\n", "3\n")

    def test_python_typed_empty(self):
        self.run_out("var xs: list<int> = []\npush(xs, 3)\nprint(xs[0])\n", "3\n")

    def test_python_missing_block(self):
        self.bad("if true:\nprint(1)\n", "Expected an indented block")

    def test_python_unexpected_indent(self):
        self.bad("print(1)\nif true:\n\tprint(2)\n\t\tprint(3)\n", "Unexpected indentation")

    def test_python_bad_dedent(self):
        self.bad("if true:\n\tif true:\n\t\tprint(1)\n  print(2)\n", "Inconsistent dedent")

    def test_python_mixed_tabs_spaces(self):
        self.bad("if true:\n\t print(3)\n", "mix tabs and spaces")

    def test_python_not_full_python(self):
        self.bad("def add(a, b):\n\treturn a + b\n", "Expected")

    def test_python_typo_suggestion(self):
        self.bad("score = 2\nprint(scroe)\n", "Did you mean 'score'")

    def test_json_diagnostics(self):
        p = subprocess.run([sys.executable, str(TEKA), "check", "--stdin", "--json"],
                           input="print(unknown)\n", text=True, capture_output=True)
        import json
        payload = json.loads(p.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["errors"][0]["line"], 1)
        self.assertGreaterEqual(payload["errors"][0]["column"], 1)

    def test_json_valid(self):
        p = subprocess.run([sys.executable, str(TEKA), "check", "--stdin", "--json"],
                           input="print('hello')\n", text=True, capture_output=True)
        import json
        payload = json.loads(p.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["errors"], [])


    def test_python_augmented_assignment(self):
        self.run_out("x = 5\nx += 2\nx *= 3\nprint(x)\n", "21\n")

    def test_unknown_function_suggestion(self):
        self.bad("prin('hi')\n", "Did you mean 'print'")

    def test_python_range_step_rejected(self):
        self.bad("for i in range(0, 10, 2):\n\tprint(i)\n", "range() currently supports")

    def test_error_caret_diagnostic(self):
        r = invoke("print(missing)\n")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("^", r.stderr)
        self.assertIn("1 | print(missing)", r.stderr)


if __name__ == "__main__":
    unittest.main()