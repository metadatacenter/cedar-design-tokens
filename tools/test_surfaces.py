import json
import re
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

    def test_scale_debt_names_a_scale_property_value_and_reason(self):
        surface = self.registry['surfaces'][0]
        surface['scaleDebt'] = [{'property': 'font-size', 'value': '13px', 'reason': 'Material calendar header, pending adoption'}]
        self.save()
        self.assertEqual(validate(self.repo), [])
        for bad in ([{'property': 'padding', 'value': '6px', 'reason': 'spacing is not a scale property'}],
                    [{'property': 'font-size', 'value': '13px'}],
                    [{'property': 'font-size', 'value': '13px', 'reason': 'one'}, {'property': 'font-size', 'value': '13px', 'reason': 'two'}]):
            surface['scaleDebt'] = bad
            self.save()
            self.assertTrue(any('scale debt' in error for error in validate(self.repo)), bad)

    def test_scale_debt_cannot_grow_against_base(self):
        subprocess.run(['git', '-C', str(self.repo), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(self.repo), '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'base'], check=True)
        self.registry['surfaces'][0]['scaleDebt'] = [{'property': 'color', 'value': 'rgb(1, 2, 3)', 'reason': 'Added in a feature change'}]
        self.save()
        self.assertTrue(any('cannot add scale debt' in f['value'] for f in findings(self.repo, 'HEAD')))

    def test_moving_to_a_new_walk_may_record_existing_findings_once(self):
        helper = self.repo / self.registry['browserHelper']
        current = helper.read_text()
        helper.write_text(re.sub(r'^// Walk \d+\.$', '// Walk 1.', current, flags=re.M))
        commit = ['git', '-C', str(self.repo), '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm']
        subprocess.run(['git', '-C', str(self.repo), 'add', '.'], check=True)
        subprocess.run(commit + ['base'], check=True)
        sync(self.repo)
        self.registry['surfaces'][0]['scaleDebt'] = [{'property': 'box-shadow', 'value': 'rgba(0, 0, 0, 0.14)', 'reason': 'Material elevation, found when the walk read shadows'}]
        self.save()
        self.assertFalse(any('cannot add scale debt' in f['value'] for f in findings(self.repo, 'HEAD')))
        subprocess.run(['git', '-C', str(self.repo), 'add', '.'], check=True)
        subprocess.run(commit + ['migrated'], check=True)
        self.registry['surfaces'][0]['scaleDebt'].append({'property': 'color', 'value': 'rgb(1, 2, 3)', 'reason': 'Added in a later feature change'})
        self.save()
        self.assertTrue(any('cannot add scale debt' in f['value'] for f in findings(self.repo, 'HEAD')))

    def commit_base(self):
        subprocess.run(['git', '-C', str(self.repo), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(self.repo), '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'base'], check=True)

    def test_a_contract_stays_while_its_source_remains(self):
        self.commit_base()
        del self.registry['surfaces'][0]['contract']
        self.save()
        self.assertTrue(any('keeps a rendered contract' in f['value'] for f in findings(self.repo, 'HEAD')))
        self.registry['surfaces'] = []
        self.save()
        (self.repo / 'src/view.html').write_text('<p>No dialog any more</p>')
        self.assertFalse(any('keeps a rendered contract' in f['value'] for f in findings(self.repo, 'HEAD')))

    def test_a_contract_matches_the_kind_of_element_it_checks(self):
        (self.repo / 'src/view.html').write_text('<div role="menu" aria-label="Rename"></div>')
        self.assertTrue(any('menu registered under' in error for error in validate(self.repo)))
        self.registry['surfaces'][0]['contract'] = 'menu'
        self.save()
        self.assertFalse(any('registered under' in error for error in validate(self.repo)))

    def test_paths_must_stay_in_repository(self):
        self.registry['surfaces'][0]['source'][0]['file'] = '../outside.html'
        self.save()
        with self.assertRaises(ValueError):
            validate(self.repo)

    def test_discovery_in_inline_angular_templates(self):
        parser = Surfaces()
        parser.feed('template: `<details class="validation-summary"><summary>Error</summary></details><mat-menu></mat-menu>`')
        self.assertEqual([s['kind'] for s in parser.found], ['summary', 'menu'])

    def openview_registry(self):
        # The CI checkout is named "consumer" and may have no root package.
        (self.repo / 'package.json').write_text('{}')
        nested = self.repo / 'cedar-openview-src'
        nested.mkdir()
        (nested / 'package.json').write_text('{"name":"cedar-openview"}')
        (nested / 'src').mkdir()
        (nested / 'src/app-routing.module.ts').write_text("const routes = [{path: 'templates/:id', component: Template}];")
        self.registry = {'schema': 1, 'repo': 'cedar-openview', 'surfaces': [{
            'id': 'openview.template', 'name': 'Template', 'section': 'OpenView',
            'source': [{'file': 'cedar-openview-src/src/app-routing.module.ts',
                        'anchor': "path: 'templates/:id'"}]}]}
        (self.repo / 'src/view.html').unlink()
        self.save()
        return nested

    def test_nested_host_inventory_needs_no_unused_browser_helper(self):
        self.openview_registry()
        self.assertEqual(validate(self.repo), [])
        sync(self.repo)

    def test_nested_host_missing_registry_fails_in_ci_checkout(self):
        self.openview_registry()
        (self.repo / MANIFEST).unlink()
        (self.repo / 'package.json').unlink()
        self.assertIn('Missing', validate(self.repo)[0])

    def test_monitoring_and_bridging_register_their_routes_as_openview_does(self):
        nested = self.openview_registry()
        for name in ('cedar-monitoring', 'cedar-bridging'):
            (nested / 'package.json').write_text(json.dumps({'name': name}))
            self.registry['repo'] = name
            self.save()
            (nested / 'src/extra-routing.module.ts').write_text("const routes = [{path: 'logs', component: Logs}];")
            self.assertTrue(any("unregistered route 'logs'" in e for e in validate(self.repo)), name)
            (nested / 'src/extra-routing.module.ts').unlink()
            self.assertEqual(validate(self.repo), [], name)

    def test_nested_host_stray_routes_menus_and_dialogs_fail(self):
        nested = self.openview_registry()
        (nested / 'src/extra-routing.module.ts').write_text("const routes = [{path: 'new', component: New}];")
        (nested / 'src/new.html').write_text('<dialog></dialog><mat-menu></mat-menu>')
        errors = validate(self.repo)
        for kind in ('route', 'dialog', 'menu'):
            self.assertTrue(any('unregistered ' + kind in e for e in errors), errors)

    def test_nested_host_stale_route_fails(self):
        nested = self.openview_registry()
        (nested / 'src/app-routing.module.ts').write_text('const routes = [];')
        self.assertTrue(any('stale source' in e for e in validate(self.repo)))

    def test_rendered_contract_cannot_omit_helper(self):
        del self.registry['browserHelper']
        self.save()
        with self.assertRaises(ValueError):
            validate(self.repo)


if __name__ == '__main__':
    unittest.main()
