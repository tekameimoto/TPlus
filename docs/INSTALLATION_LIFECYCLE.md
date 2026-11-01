# Installation ownership and removal

This describes the first distribution improvement after Phase A. It applies to installations made with the source installers on this branch. The published v0.9.0 ZIP and download commands have not been replaced.

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

## Recovery limits and next work

The ownership record is written with a temporary file and atomic replacement, but the complete installer and uninstaller are not yet atomic transactions. A filesystem error, concurrent install/update/uninstall, or power loss can leave a partial operation. Do not run lifecycle operations concurrently. An interrupted uninstall retains its record when a deletion fails; reinstalling or recovering may still be necessary if compiler files were already removed.

If installation fails after copying begins, preserve the directory and check the error before retrying. A stale ownership record can cause preflight to reject partially changed files. Choose a fresh prefix to regain a working command without deleting the failed installation.

The next distribution PR should add a shared lifecycle lock, durable recovery journal, staged replacement, and interruption tests. Then add maintained release packaging, verified installation artifacts, and package-manager integration. These remain unfinished; this PR establishes safe file ownership and explicit removal first.
