# Installation, recovery, and removal

This applies to installations made with the current source installers. The published v0.9.0 ZIP and download commands have not been replaced and do not include these recovery features.

## Install and reinstall

The existing layout is preserved:

| Platform | Compiler directory | Launcher |
| --- | --- | --- |
| macOS/Linux | `<prefix>/share/teka/<version>` | `<prefix>/bin/teka` |
| Windows | `<prefix>/<version>` | `<prefix>/bin/teka.cmd` |

After a successful install, `.tplus-install.json` records the installed filenames and their SHA-256 hashes, plus hashes of the external launcher files. It stores a schema number and layout name, with no absolute paths or device information. It is local bookkeeping, not a digital signature or protection against a malicious process running as the same user.

Before copying, both installers check the destinations for symlinks/junctions and compare previously recorded files with their saved hashes. Modified or unowned destinations stop the install. Save intentional edits elsewhere or select a fresh prefix; there is no force-overwrite option. Installing the same unmodified source again is supported.

Windows still supports `-NoPath` for isolated installs. Its stable launcher manifest continues to support IntelliJ compiler discovery.

## Preview and remove

```sh
teka uninstall
teka uninstall --json
teka uninstall --yes
```

Without `--yes`, the command only reports proposed removals and preserved files. It does not prompt or delete anything. With `--yes`, it checks file contents again before unlinking each recorded file. It never recursively deletes the installation directory, follows a symlink to delete its target, or removes a filename supplied outside the fixed installation allowlist.

Modified files, unknown files, project sources, caches, and update backups remain. The directory is removed only if empty. A different version's active launcher is preserved when its hash differs from the older version's recorded launcher.

Editor plugins and PATH entries are not removed. The `bin` directory can be shared with other commands. If that directory is no longer used, remove its PATH entry manually through your shell configuration or Windows user environment settings. The uninstaller never edits a shell startup file or deletes the shared `bin` directory.

Use the older installation's full launcher/compiler path to remove that version specifically. Running the active `teka` command removes only the installation it belongs to.

## Updates

For an installation with an ownership record, the updater checks the files it will replace before making changes. If a recorded compiler file was edited, the update stops. After a successful update, the changed files receive fresh hashes. If writing the new record fails, the existing updater rollback also restores the compiler/plugin transaction.

An update keeps the original installation directory name. `teka --version` reports the actual running version. Ownership tracking uses the existing `project_tools.py` file, so no additional compiler filename is needed in the release bundle accepted by the published v0.9.0 updater.

Legacy source updates without an ownership record keep their existing behavior. Unknown package files, bad digests, and unsafe archives are still rejected by the updater.

## Legacy installations and source checkouts

The uninstaller refuses a directory without an ownership record. It does not guess which files in a source checkout are disposable. The old `.tplus-install` marker alone is insufficient for removal.

A marked legacy installation can be registered by reinstalling with the current source installer. Legacy files have no saved hashes, so reinstall still replaces the known compiler files as the older installer did; preserve any local compiler edits first, or choose a separate prefix. Unknown files are not included in the new ownership record. An unrelated existing launcher is still refused.

The original development checkout is not migrated or deleted automatically. No release is published by these operations.

## Recover an interrupted source install

Both source installers stage their files and save the previous contents before replacing the compiler, ownership record, or launchers. A journal in `<prefix>/.tplus-install-transaction` records the operation. Each file is replaced atomically. A caught failure rolls back; an abrupt process exit leaves the journal for the next run.

1. Keep the installation and its recovery directory intact.
2. Extract or check out a fresh copy of this source **outside the installation prefix**.
3. Run its installer with the same prefix as before. For macOS/Linux: `sh install.sh --prefix /path/to/prefix`. For Windows: `powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Prefix C:\path\to\prefix`.
4. Check `teka --version` after it succeeds.

Before retrying, the installer validates every affected file and backup, then restores an unfinished operation. If the previous operation already committed, it only finishes cleanup. Recovery also tolerates an interruption during rollback. Changed destination files, corrupt backups, unsafe paths, or unexpected recovery files stop recovery for inspection. Preserve those files; do not delete the journal to force an overwrite. A separate prefix can restore a usable command while you investigate.

Source installation, owned updates, and applied uninstall share an OS lock in `<prefix>/.tplus-lifecycle.lock`. A competing operation exits with an error. The OS releases the lock when its process exits, including an abrupt termination. The small file remains intentionally; do not delete it while an operation is running. Uninstall preview is read-only and refuses a pending installation recovery.

## Limits and next work

This recovery journal covers **source installation**. Updates retain their existing caught-error rollback, and uninstall still removes files individually; neither has a complete process-death recovery journal. Legacy updaters without ownership records do not use the new lock. Reinstall from fresh source may be necessary after an interrupted update or uninstall.

There is no single atomic switch for the whole compiler: avoid compiling while installation runs. Windows PATH changes happen after the file transaction and are outside rollback. A process killed while writing an individual temporary file can leave a `.teka-write-*` file beside its destination; unknown files are preserved. Tests cover exceptions and process termination, not all filesystem, hardware, or power-loss failures. Recovery is local bookkeeping, not a security boundary against another process with the same account permissions.

Maintained release packaging, verified installation artifacts, and package-manager integration remain future distribution work.
