# T+ 0.9.0

T+ uses `.teka` files and the `teka` command. This release includes the compiler, standard library, handbook, installers, and IntelliJ plugin.

## Install

Download **TPlus-v0.9.0.zip** and unzip it.

On macOS or Linux, open the `compiler` folder in Terminal and run:

```sh
sh install.sh
```

On Windows, open that folder in PowerShell and run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

Python 3.11+ and a C++17 compiler are required. The [README](https://github.com/tekameimoto/TPlus#install) has compiler setup and copyable online installation commands for each platform.

## Update

```sh
teka update
```

The updater downloads the latest published stable release from GitHub, verifies its checksum, and replaces the installed compiler. An existing IntelliJ plugin is updated when found. Project files are left alone.

Use `teka update check` to check without installing. Restart IntelliJ after a plugin update.

## Downloads

- **TPlus-v0.9.0.zip** — compiler, installers, handbook, and bundled IntelliJ plugin.
- **TPlus-IntelliJ-v0.9.0.zip** — install through **Settings → Plugins → ⚙ → Install Plugin from Disk**.
- **SHA256SUMS.txt** — checksums for both ZIPs.

IntelliJ IDEA 2026.2 or newer is required. Console programs support macOS, Linux, and Windows. Graphics currently require macOS and raylib.

Python packages, inheritance, async, and a debugger are not supported. See the [handbook](https://github.com/tekameimoto/TPlus/blob/main/TPLUS_HANDBOOK.md) for language details.
