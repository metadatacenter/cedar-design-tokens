import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from check_surfaces import Surfaces, validate, sync, MANIFEST, findings


class SurfaceCoverageTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        (self.repo / 'package.json').write_text(json.dumps({'name': 'cedar-workspace'}))
        (self.repo / 'src').mkdir()
        (self.repo / 'src/view.html').write_text('<dialog aria-label="Rename"></dialog>')
        (self.repo / 'browser').mkdir()
        (self.repo / 'browser/surface.spec.mjs').write_text('surfaceCases(registry, scenarios); checkSurface(page);')
        self.registry = {'schema': 1, 'repo': 'cedar-workspace', 'browserHelper': 'browser/tests/surface-contracts.generated.mjs', 'surfaces': [
            {'id': 'workspace.rename', 'name': 'Rename', 'section': 'Resource Dialogs', 'contract': 'dialog',
             'selector': 'dialog', 'scenario': 'rename', 'states': ['open'],
             'source': [{'file': 'src/view.html', 'anchor': 'aria-label="Rename"'}], 'test': 'browser/surface.spec.mjs'}]}
        self.save()
        sync(self.repo)

    def save(self):
        (self.repo / MANIFEST).write_text(json.dumps(self.registry))

    def test_valid_registration(self):
        self.assertEqual(validate(self.repo), [])

    def test_non_node_consumer_without_registry_is_outside_scope(self):
        (self.repo / MANIFEST).unlink()
        (self.repo / 'package.json').unlink()
        self.assertEqual(list(findings(self.repo)), [])

    def test_registry_without_package_still_fails(self):
        (self.repo / 'package.json').unlink()
        self.assertTrue(list(findings(self.repo)))

    def test_missing_registry_cannot_silence_gate(self):
        (self.repo / MANIFEST).unlink()
        self.assertIn('Missing', validate(self.repo)[0])

    def test_checker_needs_no_compiled_dist_or_node(self):
        import check_surfaces
        with tempfile.TemporaryDirectory() as directory:
            isolated = Path(directory)
            (isolated / 'surfaces').mkdir()
            for name in ('browser.mjs', 'browser.d.mts', 'token-defaults.json'):
                (isolated / 'surfaces' / name).write_text((check_surfaces.HOME / 'surfaces' / name).read_text())
            with patch('check_surfaces.HOME', isolated):
                sync(self.repo)
                self.assertEqual(validate(self.repo), [])

    def test_summary_cannot_drop_expanded_state(self):
        self.registry['surfaces'][0]['contract'] = 'error-summary'
        self.save()
        self.assertTrue(any('applicable states' in e for e in validate(self.repo)))

    def test_new_dialog_without_registration(self):
        with (self.repo / 'src/view.html').open('a') as output:
            output.write('<div role="dialog" aria-label="Copy"></div>')
        self.assertTrue(any('unregistered dialog' in e for e in validate(self.repo)))

    def test_missing_test_and_stale_source_fail(self):
        (self.repo / 'src/view.html').write_text('')
        (self.repo / 'browser/surface.spec.mjs').unlink()
        errors = validate(self.repo)
        self.assertTrue(any('stale source' in e for e in errors))
        self.assertTrue(any('missing registry-driven browser test' in e for e in errors))

    def test_generated_helper_cannot_be_weakened_locally(self):
        (self.repo / 'browser/tests/surface-contracts.generated.mjs').write_text('export function checkSurface() {}')
        self.assertTrue(any('helper is stale' in e for e in validate(self.repo)))

    def test_duplicate_unknown_contract_and_cycle(self):
        node = self.registry['surfaces'][0]
        node.update(contract='anything', parent=node['id'])
        self.registry['surfaces'].append(dict(node))
        self.save()
        errors = validate(self.repo)
        self.assertTrue(any('duplicate' in e for e in errors))
        self.assertTrue(any('unknown contract' in e for e in errors))
        self.assertTrue(any('cycle' in e for e in errors))

    def test_rendered_debt_cannot_expand_against_base(self):
        subprocess.run(['git', '-C', str(self.repo), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(self.repo), '-c', 'user.name=Test', '-c', 'user.email=test@example.org', 'commit', '-qm', 'Initial registration'], check=True)
        self.registry['surfaces'][0]['debt'] = {'border-top-left-radius': {
            'actual': '8px', 'expected': '4px', 'reason': 'Unreviewed increase'}}
        self.save()
        self.assertTrue(any('cannot add or expand' in row['value'] for row in findings(self.repo, 'HEAD')))

    def test_paths_must_stay_in_repository(self):
        self.registry['surfaces'][0]['source'][0]['file'] = '../outside.html'
        self.save()
        with self.assertRaises(ValueError):
            validate(self.repo)

    def test_discovery_in_inline_angular_templates(self):
        parser = Surfaces()
        parser.feed('template: `<details class="validation-summary"><summary>Error</summary></details><mat-menu></mat-menu>`')
        self.assertEqual([s['kind'] for s in parser.found], ['summary', 'menu'])


if __name__ == '__main__':
    unittest.main()
