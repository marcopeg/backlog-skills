"""Verify marketplace roots and the installed package boundary."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def test_marketplaces_resolve_same_complete_plugin(self):
        codex = json.loads((ROOT / '.agents/plugins/marketplace.json').read_text())
        claude = json.loads((ROOT / '.claude-plugin/marketplace.json').read_text())
        roots = [ROOT / codex['plugins'][0]['source']['path'], ROOT / claude['plugins'][0]['source']]
        self.assertEqual(roots[0].resolve(), roots[1].resolve())
        plugin = roots[0]
        self.assertEqual(len(list((plugin / 'skills').glob('*/SKILL.md'))), 13)
        manifests = [json.loads((plugin / name / 'plugin.json').read_text()) for name in ('.codex-plugin', '.claude-plugin')]
        self.assertEqual(manifests[0]['version'], manifests[1]['version'])
        self.assertEqual(manifests[0]['name'], plugin.name)
        self.assertEqual(manifests[0]['author']['name'], 'Backlog Skills contributors')
        self.assertNotIn('url', manifests[0]['author'])
        self.assertEqual((plugin / 'LICENSE').read_bytes(), (ROOT / 'LICENSE').read_bytes())

    def test_cached_plugin_runs_without_repository_files(self):
        with tempfile.TemporaryDirectory(prefix='backlog-plugin-boundary-') as tmp:
            directory = Path(tmp)
            cache = directory / 'plugin cache'
            shutil.copytree(ROOT / 'plugins/backlog-skills', cache)
            project = directory / 'target project'
            project.mkdir()
            helper = cache / 'skills/backlog-draft/scripts/scaffold_draft.py'
            result = subprocess.run([sys.executable, str(helper), '--title', 'Cached helper', '--task-id', 'EF56'], cwd=project, input='', capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((project / 'docs/backlog/BACKLOG.md').exists())
            self.assertFalse((cache / 'docs').exists())


if __name__ == '__main__':
    unittest.main()
