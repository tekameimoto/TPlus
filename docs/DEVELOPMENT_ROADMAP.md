# Development roadmap

T+ is an experimental general-purpose language made by Tekameimoto. This plan builds on the Python frontend, typed syntax, C++17 backend, `.teka` files, `teka` command, and existing IntelliJ plugin. It does not describe features already available in a release.

## Working rules

Each phase uses a feature branch and a focused pull request with regression tests, compatibility notes, and exact validation results. Merge and release publication require maintainer approval. Keep compiler checks and completion local, preserve MIT and genuine third-party notices, and do not upload user code or device information.

Do not remove working syntax or replace the compiler with a Python interpreter. Preserve `compile_source`, the CLI diagnostic JSON shape, `teka.toml`, and plugin identity `dev.teka.lang` while introducing internal interfaces incrementally.

## A — Stabilization

First pull request:

- Establish the existing test baseline and feature inventory.
- Prevent build output from replacing source files; stage builds so linker failure preserves previous output.
- Turn excessive expression nesting into a structured diagnostic.
- Generate doctor module names from the real registry.
- Validate updater settings, local feed filenames, and nested plugin archives before installation.
- Derive local installer versions from `teka.py`; let Windows editor lookup follow the installed launcher.
- Correct project documentation and retain working offline tooling.

Follow-up stabilization work must use separate reproductions and tests: precise source columns after English normalization, checked integer arithmetic and division, runtime conversion limits, buffered file I/O failures, interruption-safe installation, updater rollback under filesystem failure, and broader malformed-input coverage. The first PR is not a claim that all compiler or security defects are resolved.

## B — Distribution

Implemented on the development branches: [installation ownership, removal, and source-install recovery](INSTALLATION_LIFECYCLE.md), plus [versioned release candidate packaging](RELEASES.md). Updater process-death recovery, reviewed-tag release drafts, and package-manager integration remain follow-up work. These changes are not yet in the published v0.9.0 downloads.

1. Define one release-version contract across compiler, plugin build, packaging, and download scripts. Keep the published v0.9.0 installers reproducible until a successor is approved.
2. Design a shared installation manifest and explicit upgrade/rollback policy. Test power loss, partial writes, permissions, existing launchers, symlinks, and paths with spaces. An in-place update currently keeps the original directory name.
3. Add safe uninstall limited to owned files. Preserve project files and unrelated PATH entries.
4. Restore a maintained packaging workflow: build from reviewed tags, test first, validate archives and checksums, then prepare a draft. Publication remains a separate approval.
5. Test clean installs on Windows, macOS, and Linux. Record architecture and runtime dependencies; do not infer Intel/ARM or cross-compilation support from one runner.
6. Prepare a Homebrew tap and evaluate Scoop/Winget. Document working commands only after the repositories and package definitions exist and have been tested. Investigate self-contained Python packaging without hiding the C++ toolchain requirement.

Acceptance: verified artifacts, install/update/uninstall tests, clear dependencies, and a reviewable release draft. No automatic public release.

## C — Editor tooling

1. Stabilize the compiler's diagnostics and standard-library metadata interfaces.
2. Add a VS Code extension with `.teka` association, highlighting, snippets, local completion, diagnostics, and run/build/check commands using argument arrays. Produce a tested `.vsix`; do not claim marketplace publication.
3. Improve IntelliJ completion and navigation while preserving offline inline suggestions and compatibility identity. Test supported IDE versions explicitly.
4. Define reusable semantic queries for a language server. Opening a file must not run project programs or perform native builds.

Acceptance: working editor artifacts, automated tests, and documented support limits. Marketplace submission needs separate authorization.

## D — Language completeness

Implement local `.teka` imports first: specify project boundaries, namespaces, aliases, exports, dependency graphs, and cycle diagnostics. Then add typed maps, sets, tuples and optionals, defined copying/mutation semantics, structured errors, and improvements to functions/classes. Full JSON parsing follows suitable data types.

Extract compiler modules behind existing APIs only as needed. Add source mapping before claiming accurate rewritten columns; introduce an IR only if it solves a demonstrated problem. Specify overflow, conversions, division, bounds, Unicode, and cleanup behavior before expanding the language. Keep English syntax deterministic. Interpolation and `ask ... -> name` remain proposals.

Acceptance: documented semantics, positive/negative tests, native output tests, compatibility coverage, and practical examples for each new feature.

## E — General-purpose libraries

Start with paths, logging, encoding, CSV, regex, dates, and explicit subprocess APIs. Add SQLite with parameterized queries and transactions. Then introduce HTTP/TLS and sockets with timeouts, verified certificates, bounded responses, and cleanup.

Use maintained libraries for networking and cryptography. Keep GUI/graphics optional; investigate a cross-platform approach before promising desktop application support. Add API clients or web service examples only after the relevant APIs work.

Acceptance: documented APIs, offline unit tests, controlled integration tests, and real applications on every claimed platform.

## F — Ecosystem

Design TekaPack around a documented `teka.toml` schema, local dependencies first, then integrity-checked Git dependencies and reproducible lockfiles. No arbitrary installation scripts. A hosted registry and `teka publish` require a functioning permission and distribution model.

Expand the LSP, prepare marketplace submissions, build an accessible static documentation site, and measure compiler performance before adding caching or parallelism. Keep `llms.txt` accurate; search-engine or external AI discovery is not guaranteed.

FFI, shared libraries, WebAssembly, cross-compilation, async, threads, generics, macros, profiling, and debugging require separate designs after the core is dependable.

## Next sequence

Review and validate Phase A; merge only with approval. Next split Phase B into installation lifecycle, version/release automation, and package-manager integration PRs. Do not start a broad language rewrite or bundle later phases into the stabilization PR.
