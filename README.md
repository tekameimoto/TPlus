# T+ (TekaLang)

**English-style syntax. Native executables.**

[![Tests](https://github.com/tekameimoto/TPlus/actions/workflows/tests.yml/badge.svg)](https://github.com/tekameimoto/TPlus/actions/workflows/tests.yml)
[![Release](https://img.shields.io/github/v/release/tekameimoto/TPlus)](https://github.com/tekameimoto/TPlus/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

T+ is an experimental, statically typed, general-purpose programming language made by **Tekameimoto**. Today it supports console programs, file utilities, and optional raylib graphics. Networking, databases, user-created modules, and package management are planned; they are not available in v0.9.0.

Write a `.teka` file, then use `teka` to check, run, or build it. The compiler is written in Python; it translates T+ into C++17 and uses Clang or GCC to produce a native executable.

```teka
repeat 3 times:
    say "hello from T+"
```

[Install](#install) · [First program](#first-program) · [Language handbook](TPLUS_HANDBOOK.md) · [Examples](examples) · [Downloads](https://github.com/tekameimoto/TPlus/releases/latest)

## What works in v0.9.0

| Area | Available now |
| --- | --- |
| Language | Variables, static types, conditions, loops, typed functions, recursion, classes, and typed lists |
| Console | Text output, input, strings, and numeric conversions |
| Standard library | Math, random numbers, time, text operations, file access, and basic system information |
| Compiler | Syntax/type checks, generated C++ output, and native executable builds |
| Editor | IntelliJ IDEA plugin with highlighting, completion, diagnostics, and run actions |
| Graphics | Basic raylib drawing and input on macOS |

**Current limits:** no Python package imports, package registry, arbitrary user modules, dictionaries, sets, tuples, inheritance, async, or debugger. The JSON module currently provides string quoting, not a full JSON parser. T+ resembles Python in places but does not run general Python code.

See the [handbook](TPLUS_HANDBOOK.md) for exact syntax and every implemented standard-library signature.

## Install

You need **Python 3.11 or newer** and a **C++17 compiler** to run or build T+ source. An already-built console executable does not need the T+ compiler or Python; its normal operating-system and runtime-library requirements still apply.

The commands below install **v0.9.0**. They download the release ZIP from GitHub and verify its SHA-256 checksum.

### macOS

Install Python 3.11+ from [python.org](https://www.python.org/downloads/macos/) if needed. Install Apple's command-line compiler tools:

```sh
xcode-select --install
```

Then install T+:

```sh
curl -fsSL https://raw.githubusercontent.com/tekameimoto/TPlus/main/get.sh | sh
```

### Linux

On Ubuntu or Debian, install Python 3.11+ and GCC:

```sh
sudo apt update
sudo apt install python3 g++
```

Check `python3 --version`: if your distribution provides an older Python, install Python 3.11+ before continuing. On other distributions, use the equivalent Python and C++ compiler packages.

```sh
curl -fsSL https://raw.githubusercontent.com/tekameimoto/TPlus/main/get.sh | sh
```

### Windows

1. Install [Python 3.11+](https://www.python.org/downloads/windows/).
2. Install [MSYS2](https://www.msys2.org/). In **MSYS2 UCRT64**, run:

   ```sh
   pacman -S mingw-w64-ucrt-x86_64-gcc
   ```

3. Add `C:\msys64\ucrt64\bin` to your Windows **user PATH**, then open a new PowerShell window.
4. Install T+:

   ```powershell
   irm https://raw.githubusercontent.com/tekameimoto/TPlus/main/get.ps1 | iex
   ```

Windows builds use MinGW-w64 GCC or Clang. Microsoft's `cl` compiler is not supported.

### Verify the installation

Open a new terminal, then run:

```sh
teka --version
teka doctor
```

The version should be `T+ 0.9.0`. `teka doctor` reports the compiler and native toolchain it finds.

| System | Default compiler folder | Command |
| --- | --- | --- |
| macOS / Linux | `~/.local/share/teka/0.9.0` | `~/.local/bin/teka` |
| Windows | `%LOCALAPPDATA%\TPlus\0.9.0` | `%LOCALAPPDATA%\TPlus\bin\teka.cmd` |

If macOS or Linux cannot find `teka`, add this to your shell configuration (`~/.zshrc` for zsh or `~/.bashrc` for bash), then reopen Terminal:

```sh
export PATH="$HOME/.local/bin:$PATH"
```

## First program

Save the following as **`squares.teka`**. It defines a typed function, prints three squares, and writes a text file.

```teka
import teka.files

def square(value: int) -> int:
    return value * value

for number in range(1, 4):
    say square(number)

teka.files.write("result.txt", "Finished calculating squares.\n")
```

Run it:

```sh
teka run squares.teka
```

Output:

```text
1
4
9
```

The program also creates `result.txt` in the terminal's current directory. The file-writing function overwrites that file if it already exists.

To build a standalone program:

```sh
teka build squares.teka -o squares
```

Run `./squares` on macOS/Linux or `.\squares.exe` in Windows PowerShell. Build on the operating system you intend to run it on; this is not a cross-compilation command.

## Commands

| Command | Purpose |
| --- | --- |
| `teka check squares.teka` | Check syntax and types without running |
| `teka run squares.teka` | Compile and run |
| `teka build squares.teka -o squares` | Produce a native executable |
| `teka build squares.teka --release -o squares` | Build with optimization |
| `teka emit-cpp squares.teka` | Show generated C++ |
| `teka new MyProject` | Create a project with a source file, configuration, and tests |
| `teka stdlib` | List implemented library functions |
| `teka doctor` | Inspect the local installation and toolchain |

Inside a generated project, `teka run` and `teka build` use the entry point in `teka.toml`.

```sh
teka new MyProject
cd MyProject
teka run
```

Edit `src/main.teka` to change the program. The generated `tests/test_main.teka` is a sample program you can run with `teka run tests/test_main.teka`; there is no `teka test` runner yet.

## Update

```sh
teka update
```

This installs the latest published stable release, checks its checksum, and keeps a local backup for rollback if installation fails. It updates an installed IntelliJ plugin when one is found. Restart IntelliJ after a plugin update.

Updates currently replace files inside the existing installation directory. The directory name may therefore reflect the version originally installed; use `teka --version` to see the running compiler version. A checksum checks file integrity, not independent publisher authentication.

To check without installing:

```sh
teka update check
```

### Uninstall a source-installed version

The current source installers record the files they own. Preview removal first:

```sh
teka uninstall
```

Then apply it:

```sh
teka uninstall --yes
```

Only unchanged, recorded files are removed. Edited files, projects, update backups, other installed versions, editor plugins, and PATH entries are preserved. Removing an older version does not remove a newer version's launcher.

This command is **not included in the published v0.9.0 downloads**. Source checkouts and legacy installations without ownership records are never automatically deleted. See [installation lifecycle](docs/INSTALLATION_LIFECYCLE.md) for migration and recovery limits.

## IntelliJ IDEA

Requires **IntelliJ IDEA 2026.2 or newer** and an installed `teka` command.

1. Download [TPlus-IntelliJ-v0.9.0.zip](https://github.com/tekameimoto/TPlus/releases/download/v0.9.0/TPlus-IntelliJ-v0.9.0.zip).
2. Open **Settings → Plugins → ⚙ → Install Plugin from Disk**.
3. Select the ZIP and restart IntelliJ.
4. Open a `.teka` file to use highlighting, completion, diagnostics, and run actions.

The compiler works from a terminal without an editor plugin.

## Troubleshooting

| Problem | What to check |
| --- | --- |
| `teka: command not found` | Reopen the terminal; on macOS/Linux, add `~/.local/bin` to PATH as shown above |
| Python version error | Install Python 3.11+; the system's existing Python may be older |
| Native compilation fails | Run `teka doctor`; confirm that Clang or GCC is installed and on PATH |
| “Another command already exists” | The installer is protecting an existing launcher; use a different installation prefix below |
| A Python import or feature fails | Check the handbook: T+ supports its own built-in modules and a subset of Python-like syntax |
| A graphics program fails to build | Graphics currently require macOS and raylib: `brew install raylib` |

To install alongside an existing development launcher on macOS/Linux:

```sh
curl -fsSL https://raw.githubusercontent.com/tekameimoto/TPlus/main/get.sh | sh -s -- --prefix "$HOME/.local/teka-release"
```

Use that installation directly with `"$HOME/.local/teka-release/bin/teka" --version`, or add its `bin` folder to PATH.

<details>
<summary>Install from a ZIP or source checkout</summary>

Download [TPlus-v0.9.0.zip](https://github.com/tekameimoto/TPlus/releases/download/v0.9.0/TPlus-v0.9.0.zip), extract it, and open the `compiler` folder.

On macOS/Linux:

```sh
sh install.sh
```

On Windows:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

That execution-policy setting applies only to the current PowerShell process.

For a source checkout:

```sh
git clone https://github.com/tekameimoto/TPlus.git
cd TPlus
```

Run the appropriate installer above from the repository folder. Source checkouts follow `main`; release ZIPs are versioned snapshots.

The source installers derive their version from `teka.py`. On Windows, `install.ps1 -Prefix 'C:\Tools\TPlus' -NoPath` installs into a custom folder without changing PATH; invoke that folder's `bin\teka.cmd` directly. The download commands above remain pinned to the published v0.9.0 release.

</details>

## Development and support

Compiler tests require Python 3.11+ and a C++17 compiler:

```sh
python3 -m unittest discover -s tests -v
```

On Windows, use `python` if that is your Python command. IntelliJ plugin development requires Java 25; run `./gradlew test` from `intellij-plugin` (`gradlew.bat test` on Windows).

GitHub Actions tests the compiler and installers on macOS, Linux, and Windows, plus the IntelliJ plugin on Linux. Optional graphics checks depend on local raylib availability.

[Report a bug](https://github.com/tekameimoto/TPlus/issues) with the version, operating system, command, error output, and a small reproducing program. See [CONTRIBUTING.md](CONTRIBUTING.md) for contributions.

See the [development roadmap](docs/DEVELOPMENT_ROADMAP.md) for the implementation order and [stabilization audit](docs/STABILIZATION_AUDIT.md) for tested behavior, known gaps, and release boundaries.

## License and privacy

MIT licensed. See [LICENSE](LICENSE) and [third-party notices](THIRD_PARTY_NOTICES.md).

Compilation and editor diagnostics run locally. Installers and updates download from GitHub; they do not upload project source or use the developer's computer as a server. See [PRIVACY.md](PRIVACY.md) for network and local-file details.
