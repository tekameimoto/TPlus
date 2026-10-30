# Privacy

T+ runs the compiler and your programs on your own computer.

## Installation and updates

The installers download release files from the TPlus repository on GitHub. The updater reads the latest published stable release, downloads its checksum file and ZIP, and verifies the ZIP before installing it.

These requests do not include project source, local paths, device identifiers, analytics events, or a T+ account. Like other HTTPS downloads, GitHub and its download providers receive normal network request information, including your IP address. GitHub's own privacy policy applies to that service.

The developer's computer is not used to host downloads, serve update metadata, or process requests from installed copies of T+.

## IntelliJ plugin

Highlighting, completion, and diagnostics run locally. The plugin invokes your locally installed T+ compiler to check code. It can check GitHub for updates at IDE startup; installing an update requires the update action.

## Local files

Installation creates the T+ program files and command launcher. Updates keep backups within the T+ installation folder so files can be restored if an update fails. Windows installation adds the launcher folder to the current user's PATH.

Compiler diagnostics may show paths on the computer where the command runs. Those diagnostics are printed locally; T+ does not upload them.

## Programs you run

T+ programs can read or write files and use the system features exposed by the language. Run source code you trust.

## Repository identity

The repository is published under the maintainer's GitHub account. That account identifies the project's author; installed copies do not connect to the author's device.
