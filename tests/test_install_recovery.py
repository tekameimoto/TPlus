"""Failure and process-death tests using isolated installation prefixes."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import project_tools as install
from updater import ALL_COMPILER, Updater, UpdateError

ROOT = Path(__file__).resolve().parents[1]


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='teka recovery ')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.source = self.base / 'source'
        self.source.mkdir()
        for name in ALL_COMPILER:
            if (ROOT / name).is_file():
                shutil.copy2(ROOT / name, self.source / name)
        self.prefix = self.base / 'installed'
        self.layout = 'windows' if os.name == 'nt' else 'posix'
        self.root = install.install_local(self.source, self.prefix, self.layout)
        self.old = self.snapshot()
        with (self.source / 'teka.py').open('a') as stream:
            stream.write('\n# replacement compiler\n')

    def snapshot(self):
        return {p.relative_to(self.prefix).as_posix(): p.read_bytes()
                for p in self.prefix.rglob('*') if p.is_file() and p.name != install.LOCK}

    def recover(self):
        with install.lifecycle_lock(self.prefix):
            install.recover_install(self.prefix)

    def crash(self, point='target'):
        code = r'''
import os, sys
from pathlib import Path
import project_tools as p
source, prefix, target = map(Path, sys.argv[1:4])
layout, point = sys.argv[4:]
original = p.atomic_file
def interrupted(path, data, mode=0o644):
    original(path, data, mode)
    if (point == 'target' and path == target) or (point == 'prepare' and path.name == '0' and path.parent.name == 'after'):
        os._exit(73)
p.atomic_file = interrupted
if point == 'committed':
    p.clean_transaction = lambda prefix: os._exit(73)
p.install_local(source, prefix, layout)
'''
        result = subprocess.run([sys.executable, '-c', code, str(self.source), str(self.prefix),
                                 str(self.root / 'teka.py'), self.layout, point],
                                cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 73, result.stdout + result.stderr)

    def test_exception_restores_existing_install_and_project(self):
        project = self.root / 'keep.teka'
        project.write_text('say "keep"')
        expected = self.snapshot()
        original = install.atomic_file
        failed = False
        def fail_once(path, data, mode=0o644):
            nonlocal failed
            original(path, data, mode)
            if path == self.root / 'teka.py' and not failed:
                failed = True
                raise OSError('simulated disk failure')
        with patch.object(install, 'atomic_file', fail_once):
            with self.assertRaisesRegex(OSError, 'simulated'):
                install.install_local(self.source, self.prefix, self.layout)
        self.assertTrue(failed)
        self.assertEqual(self.snapshot(), expected)

    def test_process_death_then_retry_installs_and_runs(self):
        self.crash()
        self.assertTrue((self.prefix / install.TRANSACTION).exists())
        install.install_local(self.source, self.prefix, self.layout)
        self.assertFalse((self.prefix / install.TRANSACTION).exists())
        self.assertEqual((self.root / 'teka.py').read_bytes(), (self.source / 'teka.py').read_bytes())
        result = subprocess.run([sys.executable, str(self.root / 'teka.py'), '--version'],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('T+ ', result.stdout)

    def test_process_death_before_journal_leaves_install_unchanged(self):
        self.crash('prepare')
        self.recover()
        self.assertEqual(self.snapshot(), self.old)

    def test_committed_cleanup_preserves_new_files_and_later_edits(self):
        self.crash('committed')
        edited = self.root / 'teka.py'
        edited.write_text('# intentional edit after successful commit\n')
        self.recover()
        self.assertEqual(edited.read_text(), '# intentional edit after successful commit\n')
        self.assertFalse((self.prefix / install.TRANSACTION).exists())

    def test_conflict_stops_before_restoring_any_file(self):
        self.crash()
        (self.root / 'python_style.py').write_text('# edited after interruption\n')
        before = self.snapshot()
        with self.assertRaisesRegex(install.InstallationError, 'File changed'):
            self.recover()
        self.assertEqual(self.snapshot(), before)

    def test_corrupt_backup_stops_before_restoring_any_file(self):
        self.crash()
        (self.prefix / install.TRANSACTION / 'before/0').write_bytes(b'corrupt')
        before = self.snapshot()
        with self.assertRaisesRegex(install.InstallationError, 'checksum'):
            self.recover()
        self.assertEqual(self.snapshot(), before)

    def test_traversal_in_journal_is_rejected(self):
        self.crash()
        path = self.prefix / install.TRANSACTION / 'journal.json'
        journal = json.loads(path.read_text())
        journal['entries'][0]['path'] = '../outside.txt'
        path.write_text(json.dumps(journal))
        before = self.snapshot()
        with self.assertRaisesRegex(install.InstallationError, 'Invalid installation journal'):
            self.recover()
        self.assertEqual(self.snapshot(), before)

    def test_recovery_can_itself_be_interrupted(self):
        self.crash()
        original = install.atomic_file
        def fail(path, data, mode=0o644):
            original(path, data, mode)
            if path == self.root / 'teka.py':
                raise OSError('interrupted rollback')
        with patch.object(install, 'atomic_file', fail):
            with self.assertRaises(OSError):
                self.recover()
        self.recover()
        self.assertEqual(self.snapshot(), self.old)

    def test_cleanup_after_rollback_can_be_retried_without_backups(self):
        self.crash()
        def partial_cleanup(prefix):
            (prefix / install.TRANSACTION / 'before/0').unlink()
            raise OSError('interrupted cleanup')
        with patch.object(install, 'clean_transaction', partial_cleanup):
            with self.assertRaises(OSError):
                self.recover()
        self.recover()
        self.assertEqual(self.snapshot(), self.old)

    def test_unknown_recovery_file_is_preserved(self):
        self.crash('prepare')
        unknown = self.prefix / install.TRANSACTION / 'notes.txt'
        unknown.write_text('keep')
        with self.assertRaisesRegex(install.InstallationError, 'Unexpected recovery file'):
            self.recover()
        self.assertEqual(unknown.read_text(), 'keep')

    def test_lock_blocks_install_update_and_uninstall_and_releases_on_death(self):
        code = 'import sys; from pathlib import Path; import project_tools as p\nwith p.lifecycle_lock(Path(sys.argv[1])):\n print("locked", flush=True)\n sys.stdin.read()\n'
        child = subprocess.Popen([sys.executable, '-c', code, str(self.prefix)], cwd=ROOT,
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(), 'locked')
            with self.assertRaisesRegex(install.InstallationError, 'Another T+'):
                install.install_local(self.source, self.prefix, self.layout)
            with self.assertRaisesRegex(install.InstallationError, 'Another T+'):
                install.uninstall(self.root, True)
            updater = Updater(self.root, self.base / 'plugin', self.base / 'config.json')
            with self.assertRaisesRegex(UpdateError, 'Another T+'):
                updater.install()
            self.assertEqual(self.snapshot(), self.old)
        finally:
            child.kill()
            child.communicate(timeout=10)
        install.install_local(self.source, self.prefix, self.layout)

    def test_preview_during_pending_recovery_does_not_write(self):
        self.crash()
        before = self.snapshot()
        with self.assertRaisesRegex(install.InstallationError, 'needs recovery'):
            install.uninstall(self.root)
        self.assertEqual(self.snapshot(), before)

    def test_recovery_requires_fresh_source_outside_prefix(self):
        self.crash()
        before = self.snapshot()
        with self.assertRaisesRegex(install.InstallationError, 'fresh source'):
            install.install_local(self.root, self.prefix, self.layout)
        self.assertEqual(self.snapshot(), before)

    def test_fresh_install_failure_removes_only_new_files(self):
        fresh = self.base / 'fresh'
        (fresh / 'bin').mkdir(parents=True)
        unrelated = fresh / 'bin/other-tool'
        unrelated.write_text('keep')
        original = install.atomic_file
        failed = False
        def fail_once(path, data, mode=0o644):
            nonlocal failed
            original(path, data, mode)
            if path.name == 'teka.py' and not failed:
                failed = True
                raise OSError('failed fresh install')
        with patch.object(install, 'atomic_file', fail_once):
            with self.assertRaises(OSError):
                install.install_local(self.source, fresh, self.layout)
        self.assertEqual(unrelated.read_text(), 'keep')
        self.assertFalse((fresh / install.TRANSACTION).exists())
        relative, _ = install.install_paths(self.layout, '0.9.0')
        self.assertFalse((fresh / relative).exists())
