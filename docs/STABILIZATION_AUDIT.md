# Stabilization audit

Baseline: `593a929818a6fdef4ff5d7d283664c46df908113` (v0.9.0 source). This is a source review and targeted regression pass, not a complete security certification.

## Baseline

`python3 -m unittest discover -s tests -v` ran 172 tests: 170 passed, two optional graphics tests skipped, zero failures. Environment: Linux, Python 3.12.14, native C++ compiler available. macOS, Windows, and IntelliJ validation belong to the PR's CI checks; the local Linux run alone does not verify them.

The audit inspected the compiler, normalizer, native module registry, project helpers, updater, POSIX/PowerShell installers and download scripts, launcher, IntelliJ source/build configuration, CI, tests, examples, README, language reference, handbook, privacy statement, contribution instructions, and license.

## Feature inventory

| Area | Status at baseline | Evidence and limitations |
| --- | --- | --- |
| Lexing, parsing, checking, C++ emission | Implemented and tested | `teka.py`; language/class/module/native integration suites. Stages exist as classes but share a large module. |
| English and indentation syntax | Implemented and tested | `python_style.py`, hybrid tests. Normalization preserves lines but inserted/rewritten columns are only partly mapped. |
| Variables, typed functions, recursion, classes, lists | Implemented and tested | Language and class suites, executable examples. No inheritance, maps/sets/tuples, or general Python execution. |
| Library registry and `stdlib --json` | Implemented and tested | Eight native modules; signatures come from `standard_modules.MODULES`. Graphics require a separate native dependency. |
| Strings, numeric operations, runtime I/O | Implemented but insufficiently tested | Bounds use C++ `.at()`; strings use byte-based operations. Integer overflow/division and out-of-range conversions need defined semantics and further tests. File writes need explicit buffered-error coverage. |
| JSON | Partially implemented | String quoting only. No parser or structured JSON values. |
| Project manifests | Implemented and tested | `teka.toml` entry validation, creation, native builds. Generated test files are ordinary programs, not a test framework. |
| Doctor | Broken/incomplete | Only listed math/random despite eight registry entries. Graphics status could be true from a header on a non-macOS host; plugin detection is macOS-only. |
| Build destination handling | Broken | A real native build using the input filename as `-o` overwrote the source. Direct linker output could damage a previous executable on failure. |
| Deep input diagnostics | Broken | 2,000 nested parentheses or a long expression chain raised an uncaught `RecursionError`. |
| Local installation | Partially implemented | Owned-launcher protection and per-user prefixes exist. Versions were duplicated in installers; installation is not a full atomic transaction. |
| Updates | Implemented but insufficiently tested | Stable GitHub discovery, digest/size validation, staging, rollback tests. Invalid configuration could raise `AttributeError`; nested ZIP validation had platform and aggregate-size gaps. Updates retain the original directory name. |
| IntelliJ | Implemented with partial testing | Highlighting, completion, inline suggestions, diagnostics and run actions. Existing tests cover suggestion/member logic. Windows discovery was pinned to a version directory. IDE is configured for 2026.2.3, not verified across all later IDE versions. |
| CI | Implemented | Linux/macOS/Windows compiler jobs and Linux IntelliJ job; optional graphics may skip. Action runtime deprecations need maintenance. |
| Release packaging | Missing maintained workflow | v0.9.0 artifacts exist, but the one-off packaging workflow was removed. Repeatable reviewed-tag packaging is Phase B. |
| Local source imports, package manager, LSP, VS Code, formatter/test runner | Planned but missing | Do not advertise these as supported commands. |
| HTTP, networking, databases, cross-platform GUI | Planned but missing | No application templates should imply these APIs exist yet. |

## Changes in the first stabilization PR

- Build into a temporary directory beside the destination, then replace the output after success. Reject `.teka` destinations, links to the source, and symbolic-link outputs.
- Report excessive parser/checker nesting as `E401` using the existing error JSON shape.
- Derive doctor module names from the registry; do not report graphics available from a header on Linux/Windows.
- Validate updater configuration types/URLs and local filenames consistently across platforms. Reject duplicate/noncanonical/Windows-style paths in nested plugin ZIPs, bound total unpacked content and plugin descriptor size, and convert corrupt-archive failures to updater errors.
- Derive local installer version/directory/ownership marker from `teka.py`; include the privacy document. Windows writes a stable launcher manifest for editor discovery, retains the legacy manifest, and supports `-NoPath` for isolated installation.
- Preserve legacy IntelliJ lookup while preferring the stable manifest and respecting `TEKA_HOME`.
- Pin CI actions to reviewed upstream commits using Node 24 and pin Linux runners to Ubuntu 24.04. Keep read-only permissions and disable checkout credential persistence.
- Generate project examples with `say`. Document general-purpose intent, actual limits, project use, and the staged roadmap.

Local post-change validation: `python3 -m unittest discover -s tests -v` ran 189 tests, 187 passed and two graphics tests skipped; `sh -n install.sh get.sh teka` and `git diff --check` passed. The local environment has Java 17 rather than the required Java 25, so the IntelliJ suite is delegated to the existing CI job.

New tests cover destructive output collisions, failed-linker preservation, deep-input JSON errors, registry agreement, malformed update configuration, archive path/size errors, version changes, reinstall, custom paths, existing-launcher protection, and editor launcher selection. CI runs the same compiler/installer suite on each configured OS.

## Remaining risks and follow-ups

This PR does not implement arithmetic overflow protection, complete Unicode semantics, multi-error recovery, precise normalization source maps, a new installation transaction model, or signed release metadata. SHA-256 checksums do not independently authenticate a publisher. Explicit update/download operations use the network; compilation stays local.

`get.sh` and `get.ps1` deliberately select the published v0.9.0 archive. They must not be pointed at an unpublished version. The plugin build's release version and the legacy Windows fallback also remain 0.9.0; those are compatibility/release references, not claims of a new release. The updated plugin must be built and installed before its new discovery behavior is available to users.

No release artifacts are replaced by this PR. Existing v0.9.0 downloads retain their original code. A future release requires tests, packaging validation, release notes, and explicit publication approval.

The original development project and private backup are outside this branch. No personal email, home-directory path, machine identifier, credential, or downloaded binary belongs in the PR. The public attribution remains Tekameimoto.
