# Release builds

The literal `VERSION` assignment in `teka.py` is the release version. The compiler reports it; source installers and package names read it; the IntelliJ Gradle build reads the same assignment. Do not add a second version file. The packaging command rejects a tag that differs from this version and rejects a plugin ZIP whose JAR name or descriptor disagrees.

`get.sh`, `get.ps1`, and the README download links remain pinned to the approved **v0.9.0** release. They are distribution pointers, not the development version. Change them only when a successor has been approved and its downloads verified. Building this branch does not replace v0.9.0.

## Build locally

Requirements: Python 3.11+, the Java version used by CI (currently 25), and the Gradle wrapper. Gradle needs network access to resolve uncached build dependencies. Installed compiler checks remain offline; running/building programs additionally requires a C++17 compiler.

From the repository root, build and test the plugin:

```sh
cd intellij-plugin
./gradlew test buildPlugin
cd ..
```

On Windows, use `gradlew.bat`. Pass the generated plugin ZIP to the packager (substitute its actual filename):

```sh
python tools/package_release.py --plugin intellij-plugin/build/distributions/TekaLang-IntelliJ-0.9.0.zip --output dist --tag v0.9.0
python tools/package_release.py --output dist --verify
```

Choose an output directory that does not already exist. The tool never overwrites an existing release folder. If writing fails, preserve or inspect the incomplete folder and retry into a new one.

Outputs are `TPlus-v<version>.zip`, `TPlus-IntelliJ-v<version>.zip`, and `SHA256SUMS.txt`. The compiler bundle contains only the fixed updater-compatible allowlist and the plugin ZIP. Tests, examples, plugin sources, and other development files stay in the Git repository; this is an install bundle, not a replacement source archive. MIT and privacy notices are included.

## Validation and reproducibility

The packager validates archive paths, sizes, compiler version, plugin descriptor, and checksums using the updater validator. The standalone plugin must exactly match the bundled plugin. Compiler ZIP entries have fixed timestamps, sorted names, normalized permissions, and no host metadata. The outer ZIP uses stored entries to avoid compression-library variation. Gradle archive tasks also use sorted entries and fixed timestamps.

Given identical source and plugin bytes, packaging produces identical output bytes. CI checks that property. This does not establish that independent plugin builds on different machines or toolchains produce identical bytes; dependency locking and independent rebuild comparison remain future work.

CI builds the real plugin, produces a candidate artifact, verifies it, and installs/checks/uninstalls the packaged compiler on Windows, macOS, and Linux after the existing compiler and plugin jobs pass. Artifacts expire after 14 days. These are development candidates, not releases. The workflow has read-only repository permissions and cannot publish a GitHub release.

## Before publication

Review the exact commit and matching version tag, require all CI jobs to pass, and inspect the candidate files. Get maintainer approval before creating a release or updating public download pointers. A reviewed-tag workflow that prepares a GitHub release draft, package-manager definitions, full updater crash recovery, and self-contained runtime packaging remain unfinished. No Homebrew, Scoop, or Winget install command is provided yet.
