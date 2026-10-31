# T+ Handbook — v0.9.0

The complete guide to the **currently implemented** T+ programming language. The public name is **T+**, the file extension remains **.teka**, the terminal executable is **teka**, and the T+ Standard Library imports begin with **teka.**.

T+ is an experimental English/Python hybrid that compiles to C++17 native executables. The language is free, offline-first, and doesn't need API tokens or a cloud AI. It is not fully Python compatible and does not implement the entire C++ language.

## 1. Get started

Install T+ using the instructions in [README.md](README.md). Building programs requires Python 3.11 or later and a C++17 compiler (Clang or GCC). Running already-built native executables doesn't require Python.

Create a file named hello.teka:

~~~teka
say "hello from T+"
name = ask("what is your name? ")
say "welcome " + name
~~~

Run it with:

~~~sh
teka check hello.teka
teka run hello.teka
teka build hello.teka -o hello
./hello
teka emit-cpp hello.teka
~~~

- **check**: type-check and parse, no execution
- **run**: compile with native C++17 backend and execute
- **build**: make native executable; add --release for -O3
- **emit-cpp**: inspect generated C++
- **new MyProject**: scaffold a project with teka.toml, src/main.teka and tests
- **doctor**: inspect installed compiler, C++ toolchain, raylib and IntelliJ plugin
- **stdlib**: list every currently supported native library function and signature
- **stdlib --json**: machine-readable standard library reference
- **docs**: print the location of this handbook
- **update**: install the latest stable GitHub release; **update check** checks without installing and **update status** shows local configuration
- **--version**: print T+ compiler version

Inside a project with teka.toml, use teka run or teka build with no filename.

## 2. English + Python commands

These exact commands work. T+ does not interpret arbitrary English sentences.

| T+ syntax | What it does | Python-like equivalent |
|---|---|---|
| say "hello" | Print text, then a newline | print("hello") |
| say x, y | Print several primitive values | print(x, y) |
| ask("Name? ") | Read user input as text | input("Name? ") |
| name = ask "Name? " | Read input into a variable | name = input("Name? ") |
| repeat 5 times: | Run an indented block five times | for i in range(5): |
| otherwise: | Else branch | else: |
| otherwise if condition: | Else-if branch | elif condition: |
| stop | Leave a loop | break |
| skip | Jump to next iteration | continue |
| is below | Less than | < |
| is above | Greater than | > |
| is at most | Less than or equal to | <= |
| is at least | Greater than or equal to | >= |
| is equal to | Equal to | == |
| is not equal to | Not equal to | != |

Example:

~~~teka
health = 9
repeat 3 times:
    if health is below 10:
        say "low health"
    otherwise:
        say "healthy"
    health += 1
~~~

Output: low health, healthy, healthy (one per line).

The repeat count must be an integer expression. A count of zero or less runs zero iterations. English comparison phrases are translated only in code, never inside string literals. Use either tabs or consistently indented spaces following a colon. Tabs are the default style for the editor.

## 3. Variables, types and operators

~~~teka
lives = 3
price = 4.5
message = "hello"
alive = True
lives += 1

var points: int = 0
let MAX_POINTS = 100
var speeds: list<float> = [2.0, 3.5]
~~~

The first name = value declares a mutable variable in that scope. Reassigning keeps its original static type. var is explicitly mutable; let is immutable.

Supported types are int (signed native 64-bit integer), float (native double), bool, string, typed list<T>, and declared class types. void is used only for functions returning no value. An int can be used where a float is expected.

Arithmetic: +, -, *, /, %, unary -. Comparisons: ==, !=, <, <=, >, >=. Logic: and, or, not (&&, || and ! also work). Parentheses group operations. % requires integers; + concatenates strings. Compound assignments: +=, -=, *=, /= and %=.

Booleans may be True / False or true / false. Strings may use single or double quotes and support escaped newline, tab, quotes and backslash.

**Missing Python features:** None, dictionaries, sets, tuples, slicing, generators, comprehensions, decorators, lambdas, arbitrary dynamic typing and Python's whole standard library.

## 4. Loops and decisions

~~~teka
x = 4
if x > 10:
    say "large"
elif x == 4:
    say "four"
else:
    say "other"

for i in range(3):
    say i

for number in [2, 4, 6]:
    say number

while x > 0:
    x -= 1
~~~

Supported: range(end), range(start, end) (exclusive end), list for-each loops, while, if / elif / else, break / stop, continue / skip, and pass (no-op).

Three-argument range(start,end,step) is not implemented. Legacy curly-brace blocks remain compatible: for i in 0..5 { print(i); }.

## 5. Functions

~~~teka
def square(x: int) -> int:
    return x * x

def greet(name: string):
    say "hello, " + name

say square(5)
greet("friend")
~~~

Output: 25 then hello, friend.

Parameters must have declared types. Return type annotation is optional: omitting it means void. Non-void functions must return a value on every valid path. Calls and recursion are supported. The old fn name(x: int) -> int { ... } form still works. Keyword arguments, default parameters and untyped functions are not implemented.

## 6. Classes and objects

~~~teka
class Player:
    def __init__(self):
        self.health = 100

    def heal(self, amount: int):
        self.health += amount

    def get_health(self) -> int:
        return self.health

hero = Player()
hero.heal(5)
say hero.get_health()
~~~

Output: 105.

Use self for instance methods. Define fields in __init__, use ClassName(...) to construct objects, and use dot notation to access fields and methods. Typed method parameters and return annotations work. Inheritance, decorators, static methods, arbitrary class-level values and general Python class mechanics do not.

## 7. Lists, strings and built-in functions

~~~teka
var items: list<int> = [10, 20]
push(items, 30)
say len(items)
say items[0]
say pop(items)
say int("42")
say float("3.5")
say bool("hi")
say str(15)
~~~

Output: 3, 10, 30, 42, 3.5, true, 15 (one per line).

| Built-in | Behavior |
|---|---|
| print(value, ...) | Print primitive values separated by spaces; zero arguments okay |
| input(prompt) | Read line of text; prompt optional |
| len(value) | String byte length or list element count |
| push(mutable_list, value) | Append type-compatible value |
| pop(mutable_list) | Remove and return last element |
| str(value) | Convert primitive to string |
| int(value) | Convert a primitive or numeric string to integer |
| float(value) | Convert primitive or numeric string to float |
| bool(value) | Convert primitive or string to bool |

List indexing starts at zero and is bounds-checked. Empty lists need an explicit type such as var xs: list<int> = []. Lists must have compatible element types. Directly printing whole lists or arbitrary class instances is not supported.

## 8. The T+ Standard Library

Namespaced imports:

~~~teka
import teka.math
say teka.math.sqrt(81)

import teka.random as rng
say rng.randint(1, 6)

import math
say math.pi
~~~

The namespace import stays under teka.module unless aliased with as. Older direct random and math imports still work. T+ has its own native C++ helper implementations, not Python package imports.

Important module notes:

- **teka.math:** numeric math and pi/e constants.
- **teka.random:** randint includes both endpoints; randrange excludes end; random returns [0,1); uniform returns a floating random number between bounds. Bad bounds cause runtime errors.
- **teka.time:** sleep/wait block this native thread (0–86400 seconds); now gives seconds since Unix epoch; monotonic measures elapsed time only.
- **teka.text:** upper/lower are ASCII oriented; contains, starts_with, ends_with and replace compare bytes and do not perform Unicode normalization.
- **teka.files:** read returns text; write overwrites a file; append adds text; exists checks existence. Relative paths resolve against the process working directory. Be careful: write can overwrite existing files.
- **teka.json:** only quote(string) is currently implemented; complete object encoding, JSON parsing and typed dictionaries are **not yet supported**.
- **teka.system:** platform and getenv support.
- **teka.graphics:** facade for the existing basic raylib graphics functions; raylib is needed only when compiling graphics programs.

### Complete list of every implemented module signature

This section is generated from the actual native module registry, not from planned features. The command teka stdlib also prints it.

<!-- BEGIN AUTO LIBRARY -->

#### import teka.files

| Function or constant | Parameters | Returns |
|---|---|---|
| append(...) | string, string | void |
| exists(...) | string | bool |
| read(...) | string | string |
| write(...) | string, string | void |

#### import teka.graphics

| Function or constant | Parameters | Returns |
|---|---|---|
| begin(...) | none | void |
| circle(...) | float, float, float, int, int, int | void |
| clear(...) | int, int, int | void |
| close(...) | none | void |
| dt(...) | none | float |
| end(...) | none | void |
| fps(...) | none | int |
| key(...) | string | bool |
| line(...) | float, float, float, float, float, int, int, int | void |
| mouse_x(...) | none | int |
| mouse_y(...) | none | int |
| open(...) | string, int, int | void |
| pressed(...) | string | bool |
| rand(...) | int, int | int |
| rect(...) | float, float, float, float, int, int, int | void |
| running(...) | none | bool |
| text(...) | string, float, float, int, int, int, int | void |
| time(...) | none | float |
| triangle(...) | float, float, float, float, float, float, int, int, int | void |

#### import teka.json

| Function or constant | Parameters | Returns |
|---|---|---|
| quote(...) | string | string |

#### import teka.math

| Function or constant | Parameters | Returns |
|---|---|---|
| ceil(...) | float | int |
| cos(...) | float | float |
| floor(...) | float | int |
| pow(...) | float, float | float |
| sin(...) | float | float |
| sqrt(...) | float | float |
| tan(...) | float | float |
| e | constant | float |
| pi | constant | float |

#### import teka.random

| Function or constant | Parameters | Returns |
|---|---|---|
| randint(...) | int, int | int |
| random(...) | none | float |
| randrange(...) | int | int |
| uniform(...) | float, float | float |

#### import teka.system

| Function or constant | Parameters | Returns |
|---|---|---|
| getenv(...) | string | string |
| platform(...) | none | string |

#### import teka.text

| Function or constant | Parameters | Returns |
|---|---|---|
| contains(...) | string, string | bool |
| ends_with(...) | string, string | bool |
| lower(...) | string | string |
| replace(...) | string, string, string | string |
| starts_with(...) | string, string | bool |
| upper(...) | string | string |

#### import teka.time

| Function or constant | Parameters | Returns |
|---|---|---|
| monotonic(...) | none | float |
| now(...) | none | float |
| sleep(...) | float | void |
| wait(...) | float | void |


<!-- END AUTO LIBRARY -->

## 9. Game programming

~~~teka
game_open("First T+ Game", 640, 360)
while game_running():
    game_begin()
    game_clear(8, 12, 22)
    game_circle(320, 180, 40, 80, 180, 255)
    game_text("T+", 30, 30, 28, 255, 255, 255)
    game_end()
game_close()
~~~

The game_* APIs compile directly to native raylib calls. Install raylib on Mac with brew install raylib. Game programs need a graphical display to run. Keys include W, A, S, D, UP, DOWN, LEFT, RIGHT, SPACE, ENTER, ESC, R, P, SHIFT. Colors use RGB 0–255. Coordinates use pixels; frame helpers provide elapsed time and FPS.

### Complete list of native game functions

<!-- BEGIN AUTO GAME -->

| Built-in game_* function | Parameters | Returns |
|---|---|---|
| game_begin(...) | none | void |
| game_circle(...) | float, float, float, int, int, int | void |
| game_clear(...) | int, int, int | void |
| game_close(...) | none | void |
| game_dt(...) | none | float |
| game_end(...) | none | void |
| game_fps(...) | none | int |
| game_key(...) | string | bool |
| game_line(...) | float, float, float, float, float, int, int, int | void |
| game_mouse_x(...) | none | int |
| game_mouse_y(...) | none | int |
| game_open(...) | string, int, int | void |
| game_pressed(...) | string | bool |
| game_rand(...) | int, int | int |
| game_rect(...) | float, float, float, float, int, int, int | void |
| game_running(...) | none | bool |
| game_text(...) | string, float, float, int, int, int, int | void |
| game_time(...) | none | float |
| game_triangle(...) | float, float, float, float, float, float, int, int, int | void |

<!-- END AUTO GAME -->

## 10. Autocomplete and errors

The IntelliJ plugin provides syntax highlighting, offline suggestions, gray inline completions accepted with Tab, completion popup (Ctrl+Space), snippets and live compiler error annotations. It learns symbol names from the open file and suggests namespaced members for imported T+ modules. Suggestions are deterministic and local: no tokens, AI service, or uploaded code. It is not yet a complete semantic language server.

Compiler errors show file, line, column, code and caret. An unknown name may suggest a nearby spelling. For machine-readable output:

~~~sh
teka check main.teka --json
printf 'say missing_name\n' | teka check --stdin --json
~~~

After updating the plugin, restart IntelliJ before testing new completion. If the editor is not suggesting names, enable Show suggestions as you type under code-completion settings, or use Ctrl+Space.

## 11. Projects and updater

~~~sh
teka new MyProject
cd MyProject
teka run
teka build --release
teka doctor
teka update status
teka update check
~~~

The generated teka.toml identifies the project, version and source entry. Run `teka update` to install the latest published stable release from GitHub. The updater verifies SHA-256 checksums, backs up older versions, and attempts rollback after installation failures. Explicitly configured offline and trusted HTTPS feeds are also supported. Draft releases are not available to the public updater.

**TekaPack is planned, not functional yet.** Arbitrary local imports, dependency installation, package registry, lockfiles, and teka add remain future work. Only the built-in modules listed by teka stdlib work today.

## 12. Troubleshooting

- Unknown module: use teka stdlib to see what T+ actually supports.
- Compiler errors: read the highlighted source position and error description, then fix types/typos.
- Failed native build: check the C++ compiler with teka doctor.
- Failed raylib build: install raylib; regular T+ programs don't need it.
- No IntelliJ Tab completion: restart the IDE after installing the T+ plugin.
- Unsupported Python code: T+ is not Python and cannot import arbitrary Python packages.
- Want a complete language command list: this handbook includes every built-in, native module and game API, with executable examples.
- For code requiring additional features: check the roadmap below, not guesses.

## 13. Roadmap (not implemented in v0.9)

See [DEVELOPMENT_ROADMAP.md](docs/DEVELOPMENT_ROADMAP.md) for the phased implementation sequence and acceptance criteria.

Full Python collections/syntax, arbitrary user modules, package installer and registry, complete JSON parser/serializer, memory and threading APIs, graphics sprites/audio/3D, robust project-wide semantic indexing, formatting/refactoring, debugger, multi-error recovery.

**Never confuse planned features with working commands.**