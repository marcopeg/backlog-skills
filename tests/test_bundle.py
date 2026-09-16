"""Portable smoke and regression tests. All writes use disposable projects."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / 'plugins/backlog-skills/skills'
sys.path.insert(0, str(SKILLS / 'backlog-core/scripts'))
from backlog_lib import read_markdown, resolve_task, transition_task, rebuild_active_index


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='backlog-test-')
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.backlog = self.project / 'docs/backlog'

    def run_script(self, relative, *args, ok=True):
        result = subprocess.run([sys.executable, str(ROOT / relative), *map(str, args)], cwd=self.project, input='', capture_output=True, text=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result

    def draft(self, task_id='AB12'):
        self.run_script('plugins/backlog-skills/skills/backlog-draft/scripts/scaffold_draft.py', '--title', 'Readable café export', '--task-id', task_id)
        return resolve_task(self.backlog, task_id)

    def test_lifecycle_keeps_paths_and_custom_content(self):
        original = self.draft()
        path = original.task_file
        path.write_text(path.read_text().replace('status: draft', 'status: draft\ncustom: preserved'))
        sidecar = original.folder / 'AB12.notes.md'
        sidecar.write_text('# Notes\n\nKeep this decision.\n')
        for state in ('refining', 'refined', 'planned', 'wip'):
            record = transition_task(self.backlog, 'AB12', state)
            self.assertEqual(record.task_file, path)
        self.run_script('plugins/backlog-skills/skills/backlog-complete/scripts/complete_task.py', 'AB12')
        meta, body = read_markdown(path)
        self.assertEqual(meta['custom'], 'preserved')
        self.assertEqual(meta['status'], 'completed')
        self.assertIn('completedAt', meta)
        self.assertIn('café', body)
        self.assertEqual(sidecar.read_text(), '# Notes\n\nKeep this decision.\n')
        self.assertEqual((self.backlog / 'BACKLOG.md').read_text().count('](./tasks/AB12-'), 1)
        before = (self.backlog / 'BACKLOG.md').read_bytes()
        rebuild_active_index(self.backlog)
        self.assertEqual(before, (self.backlog / 'BACKLOG.md').read_bytes())

    def test_reasons_and_completion_gate(self):
        record = self.draft()
        before = record.task_file.read_bytes()
        with self.assertRaises(ValueError):
            transition_task(self.backlog, 'AB12', 'blocked')
        self.assertEqual(before, record.task_file.read_bytes())
        self.run_script('plugins/backlog-skills/skills/backlog-complete/scripts/complete_task.py', 'AB12', ok=False)
        record = transition_task(self.backlog, 'AB12', 'blocked', reason='Awaiting sample', review_after='2026-10-01')
        self.assertEqual(record.meta['blockedFrom'], 'draft')
        record = transition_task(self.backlog, 'AB12', 'archived', reason='Superseded')
        self.assertEqual(record.meta['archivedFrom'], 'blocked')
        self.assertNotIn('reviewAfter', record.meta)

    def test_install_handles_spaces_and_refuses_overwrite(self):
        target = self.project / 'Project with spaces'
        self.run_script('scripts/install.py', '--project', target, '--dry-run')
        self.assertFalse(target.exists())
        self.run_script('scripts/install.py', '--project', target)
        self.assertEqual(len(list((target / '.agents/skills').glob('*/SKILL.md'))), 13)
        result = subprocess.run([sys.executable, str(target / '.agents/skills/backlog-draft/scripts/scaffold_draft.py'), '--title', 'Installed helper'], cwd=target, input='', capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.run_script('scripts/install.py', '--project', target, ok=False)

    def test_doctor_detects_drift_without_writing(self):
        self.draft()
        (self.backlog / 'BACKLOG.md').write_text('stale')
        before = {str(p): p.read_bytes() for p in self.backlog.rglob('*') if p.is_file()}
        result = self.run_script('plugins/backlog-skills/skills/backlog-doctor/scripts/doctor_backlog.py', '--dry-run', ok=False)
        self.assertIn('stale-generated-file', result.stdout)
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.backlog.rglob('*') if p.is_file()})
        self.run_script('plugins/backlog-skills/skills/backlog-doctor/scripts/doctor_backlog.py')
        self.run_script('plugins/backlog-skills/skills/backlog-doctor/scripts/doctor_backlog.py', '--dry-run')

    def test_migration_preserves_flat_content(self):
        source = self.backlog / 'ready/AB12-export'
        source.mkdir(parents=True)
        (source / 'AB12.task.md').write_text('---\ntaskId: AB12\nstatus: planned\n---\n# Export\n')
        (source / 'sample.bin').write_bytes(b'\x00sample\xff')
        self.run_script('plugins/backlog-skills/skills/backlog-migrate/scripts/migrate_backlog.py', '--dry-run')
        self.assertTrue(source.exists())
        self.run_script('plugins/backlog-skills/skills/backlog-migrate/scripts/migrate_backlog.py')
        record = resolve_task(self.backlog, 'AB12')
        self.assertEqual((record.folder / 'sample.bin').read_bytes(), b'\x00sample\xff')
        self.assertEqual(record.state, 'planned')
        self.assertFalse(source.exists())

    def test_migration_rejects_nested_and_loose_files(self):
        source = self.backlog / 'draft/AB12-export'
        (source / 'assets').mkdir(parents=True)
        task = source / 'AB12.task.md'
        task.write_text('---\ntaskId: AB12\nstatus: draft\n---\n# Export\n')
        asset = source / 'assets/sample.txt'
        asset.write_text('Keep nested content')
        loose = source.parent / 'unfiled.md'
        loose.write_text('Keep loose content')
        result = self.run_script('plugins/backlog-skills/skills/backlog-migrate/scripts/migrate_backlog.py', ok=False)
        self.assertIn('abortedBeforeWrite', result.stdout)
        self.assertEqual(asset.read_text(), 'Keep nested content')
        self.assertEqual(loose.read_text(), 'Keep loose content')
        self.assertTrue(task.exists())
        self.assertFalse((self.backlog / 'tasks').exists())

    def test_compression_age_uses_latest_update(self):
        record = self.draft()
        transition_task(self.backlog, 'AB12', 'completed', timestamp='2026-01-01T00:00:00+00:00')
        result = self.run_script('plugins/backlog-skills/skills/backlog-compress/scripts/list_candidates.py', 'AB 12', '--as-of', '2026-01-15T00:00:00+00:00', '--json')
        self.assertTrue(json.loads(result.stdout)[0]['eligible'])
        record.task_file.write_text(record.task_file.read_text().replace('updatedAt: 2026-01-01', 'updatedAt: 2026-01-14'))
        result = self.run_script('plugins/backlog-skills/skills/backlog-compress/scripts/list_candidates.py', 'AB12', '--as-of', '2026-01-15T00:00:00+00:00', '--json')
        self.assertFalse(json.loads(result.stdout)[0]['eligible'])

    def test_compression_helpers_support_custom_roots_and_common_source_paths(self):
        custom_backlog = self.project / 'planning/backlog'
        draft = 'plugins/backlog-skills/skills/backlog-draft/scripts/scaffold_draft.py'
        self.run_script(draft, '--backlog-root', custom_backlog, '--title', 'Service entry point', '--task-id', 'AB12')
        self.run_script(draft, '--backlog-root', custom_backlog, '--title', 'Service consumer', '--task-id', 'CD34')
        source = resolve_task(custom_backlog, 'AB12').task_file
        related = resolve_task(custom_backlog, 'CD34').task_file
        source.write_text(source.read_text() + '\nImplementation anchors: `backend/main.go`, `lib/service.ts`, `src/main.py`.\n')
        related.write_text(related.read_text() + '\nDepends on `backend/main.go` and `lib/service.ts`.\n')
        result = self.run_script(
            'plugins/backlog-skills/skills/backlog-compress/scripts/find_anchor_references.py',
            'AB12', '--backlog-root', custom_backlog,
        )
        self.assertIn('CD34', result.stdout)
        transition_task(custom_backlog, 'AB12', 'completed', timestamp='2026-01-01T00:00:00+00:00')
        result = self.run_script(
            'plugins/backlog-skills/skills/backlog-compress/scripts/list_candidates.py',
            'AB12', '--backlog-root', custom_backlog,
            '--as-of', '2026-01-15T00:00:00+00:00', '--json',
        )
        self.assertTrue(json.loads(result.stdout)[0]['eligible'])

    def test_all_cli_entrypoints_load(self):
        for script in SKILLS.glob('*/scripts/*.py'):
            if script.name == 'backlog_lib.py':
                continue
            with self.subTest(script=script.name):
                self.run_script(script.relative_to(ROOT), '--help')


if __name__ == '__main__':
    unittest.main()
