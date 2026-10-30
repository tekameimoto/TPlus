# T+ (TekaLang)

[![Tests](https://github.com/tekameimoto/TPlus/actions/workflows/tests.yml/badge.svg)](https://github.com/tekameimoto/TPlus/actions/workflows/tests.yml)

T+ (TekaLang) is an open-source programming language with English-style commands that compiles to native executables through C++17.

This is the official T+ compiler, standard library, documentation, and IntelliJ IDEA plugin.

Write `.teka` files. Use `teka` to check, run, and compile them.

```teka
repeat 3 times:
    say "hello from T+"
```

[Language handbook](TPLUS_HANDBOOK.md) · [Quick language reference](LANGUAGE.md) · [Examples](examples) · [Releases](https://github.com/tekameimoto/TPlus/releases)

## Install

**macOS · Linux · Windows**

Requires Python 3.11+ and a C++17 compiler.

> The one-command installers require the published v0.9.0 release. If no release is listed yet, use the source installation instructions below.

### macOS and Linux

Copy this command into Terminal:

```sh
curl -fsSL https://raw.githubusercontent.com/tekameimoto/TPlus/main/get.sh | sh
```

### Windows

Copy this command into PowerShell:

```powershell
irm https://raw.githubusercontent.com/tekameimoto/TPlus/main/get.ps1 | iex
```

Windows installs under `%LOCALAPPDATA%\TPlus` and adds `teka` to your user PATH. Open a new Terminal after installation.

### Compiler setup

On Windows, install [MSYS2](https://www.msys2.org/), open **MSYS2 UCRT64**, and run:

```sh
pacman -S mingw-w64-ucrt-x86_64-gcc
```

Add `C:\msys64\ucrt64\bin` to your Windows user PATH, then reopen Terminal. T+ uses MinGW-w64 GCC or Clang; the MSVC `cl` command is not supported.

The installer downloads v0.9.0, checks its SHA-256 checksum, and installs T+ in your home folder. It prints the PATH setup if needed. Administrator access is not required.

On macOS, install the compiler tools with `xcode-select --install` if you haven't already. On Ubuntu or Debian, use `sudo apt install g++`.

<details>
<summary>Install from a ZIP or source</summary>

Download **TPlus-v0.9.0.zip** from [Releases](https://github.com/tekameimoto/TPlus/releases), unzip it, and run this from the `compiler` folder:

```sh
sh install.sh
```

On macOS, you can also double-click `install.command`.

On Windows, run this from the extracted `compiler` folder:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

The execution policy flag applies only to that PowerShell process.

To install from source:

```sh
git clone https://github.com/tekameimoto/TPlus.git
cd TPlus
sh install.sh
```

For a source checkout on Windows, run the same PowerShell installation command from the repository folder.

On macOS and Linux, the default locations are `~/.local/share/teka/0.9.0` for the compiler and `~/.local/bin/teka` for the command. Choose a different location with `sh install.sh --prefix /your/path`.

</details>

## First program

Save this as `hello.teka`:

```teka
say "hello from T+"
```

Run it:

```sh
teka run hello.teka
```

| Command | What it does |
| --- | --- |
| `teka run hello.teka` | Compile and run |
| `teka check hello.teka` | Check for errors |
| `teka build hello.teka -o hello` | Build an executable |
| `teka --version` | Show the installed version |

The [handbook](TPLUS_HANDBOOK.md) covers functions, lists, typed classes, and the standard library.

## Update

On macOS, Linux, and Windows:

```sh
teka update
```

This installs the latest published stable release from GitHub after checking the download's size and SHA-256 checksum. It updates an existing IntelliJ plugin when one is found; otherwise, it updates only the compiler. Restart IntelliJ after a plugin update.

To check without installing:

```sh
teka update check
```

The updater keeps a local backup and rolls back files if installation fails. It does not change your `.teka` projects. While releases are private drafts, the public updater will report that no published release is available.

## IntelliJ IDEA

Download **TPlus-IntelliJ-v0.9.0.zip** from [Releases](https://github.com/tekameimoto/TPlus/releases). Open **Settings → Plugins → ⚙ → Install Plugin from Disk**, choose the ZIP, and restart.

The plugin provides syntax highlighting, completion, diagnostics, and run actions for `.teka` files. Install the `teka` command first. Requires IntelliJ IDEA 2026.2 or newer.

## Language status

Version 0.9 supports console programs, functions, lists, typed classes, file access, and native `teka.*` modules. Console programs are intended for all three operating systems. Windows builds produce `.exe` files. Basic graphics are available on macOS with raylib installed (`brew install raylib`).

Python packages, inheritance, async, and a debugger are not supported yet. The handbook lists the current syntax and limits.

## Development

Compiler tests:

```sh
python3 -m unittest discover -s tests -v
```

IntelliJ plugin tests (Java 25):

```sh
cd intellij-plugin
./gradlew test
```

GitHub Actions runs both suites on pushes and pull requests. See [CONTRIBUTING.md](CONTRIBUTING.md) for bug reports and pull requests.

## Privacy

Downloads and update checks use GitHub. T+ does not use the developer's computer as a server, and it does not send project source, local file paths, or device identifiers with update requests. See [PRIVACY.md](PRIVACY.md) for details.

## License

T+ is licensed under [MIT](LICENSE). See [third-party notices](THIRD_PARTY_NOTICES.md) for bundled build tooling.
