# T+ (TekaLang) language reference

T+ is a statically typed programming language with English-style commands and Python-like indentation. Its compiler is written in Python and generates C++17, which a native C++ compiler builds into an executable.

Official repository: https://github.com/tekameimoto/TPlus

This reference describes v0.9.0. Source files use `.teka`; the command is `teka`. T+ is not Python and cannot import Python packages.

## A complete program

```teka
import teka.random as rng

def twice(value: int) -> int:
    return value * 2

score = rng.randint(1, 6)
repeat 3 times:
    say twice(score)
```

Save as `example.teka`, then run:

```sh
teka check example.teka
teka run example.teka
teka build example.teka -o example
```

## Writing T+ code

- Use `say "hello"` for output and `name = ask("Name? ")` for text input.
- Use indented blocks after a colon.
- Declare variables with `name = value`, or explicit types such as `var count: int = 0`.
- Function parameters need types. A function returning a value needs a return type.
- Use `if`, `elif`, `else`, `while`, `for i in range(5):`, or `repeat 5 times:`.
- Import built-in modules such as `teka.math`, `teka.random`, and `teka.files`.
- Use `teka stdlib` or `teka stdlib --json` to inspect implemented library signatures.

## Current limits

T+ does not support arbitrary Python packages, dictionaries, sets, tuples, inheritance, async functions, or a package registry. Do not assume a Python feature works because its syntax looks similar. Graphics currently require macOS and raylib.

For code generation, use the implemented syntax and signatures in the [handbook](TPLUS_HANDBOOK.md), compare with [examples](examples), and check generated code with `teka check`. The handbook labels planned features separately.

## Documentation

- [Installation, updates, and first program](README.md)
- [Complete language handbook and standard library](TPLUS_HANDBOOK.md)
- [Example programs](examples)
- [Compiler tests](tests)
- [Release downloads](https://github.com/tekameimoto/TPlus/releases)
