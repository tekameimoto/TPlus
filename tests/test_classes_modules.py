"""Regression coverage for TekaLang's native modules and typed class model."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
LANG = ROOT / "teka.py"


def execute(source, action="check", stdin=""):
    with tempfile.TemporaryDirectory(prefix="teka-classes-") as temp:
        path = Path(temp) / "demo.teka"
        path.write_text(source, encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(LANG), action, str(path)],
            input=stdin, capture_output=True, text=True, timeout=25
        )


class NativeModulesAndClasses(unittest.TestCase):
    def good(self, source, result=None, stdin=""):
        run = execute(source, "run" if result is not None else "check", stdin)
        self.assertEqual(run.returncode, 0, run.stderr)
        if result is not None:
            self.assertEqual(run.stdout, result)

    def bad(self, source, expected):
        run = execute(source)
        self.assertNotEqual(run.returncode, 0, "Expected compiler failure")
        self.assertIn(expected, run.stderr)

    def test_random_inclusive_bounds(self):
        self.good("import random\nprint(random.randint(9, 9))", "9\n")

    def test_random_module_alias(self):
        self.good("import random as rng\nprint(rng.randint(18, 18))", "18\n")

    def test_random_randrange(self):
        self.good("import random\nprint(random.randrange(1))", "0\n")

    def test_random_random_in_range(self):
        self.good("import random\nvar x: float = random.random()\nif x >= 0.0 and x < 1.0:\n    print('good')", "good\n")

    def test_random_invalid_range_runtime_error(self):
        run = execute("import random\nprint(random.randint(5, 3))", "run")
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("requires start <= stop", run.stderr)

    def test_math_sqrt_and_pi(self):
        self.good("import math\nprint(math.sqrt(144))\nprint(math.pi > 3.14)", "12\ntrue\n")

    def test_math_functions(self):
        self.good("import math\nprint(math.floor(4.9), math.ceil(4.1), math.pow(2, 3))", "4 5 8\n")

    def test_math_alias(self):
        self.good("import math as m\nprint(m.sqrt(81))", "9\n")

    def test_math_negative_sqrt_error(self):
        run = execute("import math\nprint(math.sqrt(-1))", "run")
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("nonnegative", run.stderr)

    def test_module_dot_typo(self):
        self.bad("import random\nprint(random.randit(1, 5))", "Did you mean 'randint'")

    def test_module_access_without_call(self):
        self.bad("import random\nlet x = random.randint", "must be called")

    def test_module_requires_import(self):
        self.bad("print(random.randint(1, 3))", "Unknown variable 'random'")

    def test_unknown_module(self):
        self.bad("import requests\nprint(1)", "Unknown module 'requests'")

    def test_unknown_property_type(self):
        self.bad("let number = 3\nprint(number.value)", "Type 'int' has no member")

    def test_renamed_module_typo(self):
        self.bad("import math as m\nprint(math.pi)", "Unknown variable 'math'")

    def test_simple_class_construction(self):
        self.good("""class Player:
    def __init__(self):
        self.health = 10

player = Player()
print(player.health)
""", "10\n")

    def test_class_methods(self):
        self.good("""class Player:
    def __init__(self):
        self.health = 10

    def heal(self, points: int):
        self.health += points

player = Player()
player.heal(7)
print(player.health)
""", "17\n")

    def test_class_method_returns_value(self):
        self.good("""class Count:
    def __init__(self):
        self.count = 4

    def get(self) -> int:
        return self.count

obj = Count()
print(obj.get())
""", "4\n")

    def test_recursive_class_member_chain(self):
        self.good("""class Position:
    def __init__(self):
        self.x = 8

class Player:
    def __init__(self):
        self.position = Position()

p = Player()
print(p.position.x)
""", "8\n")

    def test_ctor_args(self):
        self.good("""class Person:
    def __init__(self, x: int):
        self.age = x

p = Person(14)
print(p.age)
""", "14\n")

    def test_method_call_inside_method(self):
        self.good("""class Counter:
    def __init__(self):
        self.count = 2

    def get(self) -> int:
        return self.count

    def print_total(self):
        print(self.get())

a = Counter()
a.print_total()
""", "2\n")

    def test_class_member_typo(self):
        self.bad("""class Player:
    def __init__(self):
        self.health = 10

p = Player()
print(p.healt)
""", "Did you mean 'health'")

    def test_unknown_object_method(self):
        self.bad("""class Player:
    def __init__(self):
        self.health = 10

p = Player()
p.hael()
""", "Unknown method")

    def test_field_types_remain_strict(self):
        self.bad("""class Player:
    def __init__(self):
        self.health = 10
        self.health = 'oops'
""", "Expected int, got string")

    def test_new_field_must_be_ctor(self):
        self.bad("""class A:
    def __init__(self):
        self.x = 1
    def update(self):
        self.y = 2
""", "declare fields in __init__")

    def test_wrong_member_signature(self):
        self.bad("""class C:
    def __init__(self):
        self.number = 5
    def update(self, value: int):
        self.number = value
c = C()
c.update('hello')
""", "Expected int, got string")

    def test_bad_self_method(self):
        self.bad("""class C:
    def go(x: int):
        print(x)
""", "must declare 'self'")

    def test_class_and_module_name_collision(self):
        self.bad("import random\nclass random:\n    def __init__(self):\n        pass\n", "already defined or reserved")

    def test_input_int_works(self):
        self.good("guess = int(input('Guess: '))\nprint(guess * 2)", "Guess: 42\n", "21\n")

    def test_input_bad_integer(self):
        run = execute("x = int(input('Number: '))\nprint(x)", "run", "frog\n")
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("invalid integer", run.stderr)

    def test_input_eof(self):
        run = execute("print(input('Number: '))", "run")
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("end of input", run.stderr)

    def test_exact_guessing_game(self):
        source = (ROOT / "examples" / "guessing_game.teka").read_text()
        run = execute(source, "run", "50\n50\n50\n50\n50\n50\n50\n")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("Welcome to TekaLang!", run.stdout)
        self.assertTrue("You win!" in run.stdout or "Game over!" in run.stdout)

    def test_deterministic_guess_win(self):
        source = (ROOT / "examples" / "guessing_game.teka").read_text()
        source = source.replace("random.randint(1, 100)", "random.randint(50, 50)")
        self.good(source, "Welcome to TekaLang!\nGuess a number from 1 to 100\nGuess: You win!\n", "50\n")

    def test_all_seven_wrong_guesses(self):
        source = (ROOT / "examples" / "guessing_game.teka").read_text()
        source = source.replace("random.randint(1, 100)", "random.randint(50, 50)")
        self.good(source, "Welcome to TekaLang!\nGuess a number from 1 to 100\n"
                          + "Guess: Too low!\n" * 7
                          + "Game over!\nAnswer: 50\n", "1\n" * 7)

    def test_legacy_graphics_still_checks(self):
        source = (ROOT / "examples" / "native_graphics_smoke.teka").read_text()
        self.assertEqual(execute(source).returncode, 0)

    def test_class_return_annotation(self):
        self.good("""class Position:
    def __init__(self):
        self.x = 5

def make_position() -> Position:
    return Position()

pos = make_position()
print(pos.x)
""", "5\n")

    def test_unknown_class_annotation_rejected(self):
        self.bad("""def make() -> Nonexistent:
    return 5
""", "Unknown type 'Nonexistent'")

    def test_class_typed_variable(self):
        self.good("""class P:
    def __init__(self):
        self.x = 7

var player: P = P()
print(player.x)
""", "7\n")

    def test_chained_class_method_return(self):
        self.good("""class Position:
    def __init__(self):
        self.x = 13

class Player:
    def __init__(self):
        self.position = Position()
    def current(self) -> Position:
        return self.position

p = Player()
print(p.current().x)
""", "13\n")


if __name__ == "__main__":
    unittest.main()