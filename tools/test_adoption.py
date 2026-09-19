import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import check_adoption as check


class AdoptionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'consumer'
        self.repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        (self.repo / 'src').mkdir()
        (self.repo / 'package.json').write_text(json.dumps({'devDependencies': {check.PACKAGE: '1.0.0'}}))
        (self.repo / 'package-lock.json').write_text(json.dumps({'packages': {
            'node_modules/' + check.PACKAGE: {'version': '1.0.0'}}}))
        self.style = self.repo / 'src/style.scss'
        self.style.write_text('.a { color: #fff; font-size: 14px; padding: 8px; }')

    def run_report(self, **kwargs):
        return check.report(self.repo, '1.0.0', **kwargs)

    def test_manual_resize_is_always_forbidden_even_in_baselines_and_exceptions(self):
        self.style.write_text('textarea { resize: vertical; }')
        self.run_report(initialize=True)
        baseline_path = self.repo / check.BASELINE
        baseline = json.loads(baseline_path.read_text())
        key = next(iter(baseline['findings']))
        baseline['exceptions'] = {key: 'An obsolete exception must not permit resizing'}
        baseline_path.write_text(json.dumps(baseline))
        row = self.run_report()['findings'][0]
        self.assertEqual(('manual-resize', 'gate', 'new'),
                         (row['rule'], row['severity'], row['status']))

    def test_spellcheck_is_not_baselinable(self):
        (self.repo / 'src/control.html').write_text('<input>')
        self.run_report(initialize=True)
        baseline_path = self.repo / check.BASELINE
        baseline = json.loads(baseline_path.read_text())
        baseline['policy'] = 2
        for row in check.scan_styles(self.repo, 2):
            baseline['findings'][row['id']] = dict(row, count=1)
        baseline_path.write_text(json.dumps(baseline))
        rows = self.run_report()['findings']
        row = next(row for row in rows if row['rule'] == 'spellcheck')
        self.assertEqual((row['severity'], row['status']), ('gate', 'new'))

    def test_only_none_is_allowed_for_resize(self):
        for value in ('both', 'vertical', 'horizontal', 'block', 'inline',
                      'initial', 'inherit', 'unset', 'revert', 'var(--resize)', '$resize'):
            with self.subTest(value=value):
                rows = list(check.findings('x.scss', 'textarea { resize: ' + value + '; }'))
                self.assertEqual(['manual-resize'], [row['rule'] for row in rows])
        for value in ('none', 'none !important', 'NONE'):
            self.assertEqual([], list(check.findings('x.css', 'textarea { resize: ' + value + '; }')))

    def test_nested_frontend_is_scanned_under_a_generic_ci_checkout_name(self):
        nested = self.repo / 'cedar-monitoring-src'
        nested.mkdir()
        for name in ('src', 'package.json', 'package-lock.json'):
            (self.repo / name).rename(nested / name)
        (self.repo / 'package.json').write_text('{"name":"wrapper"}')
        result = self.run_report(initialize=True)
        self.assertTrue(result['dependencyValid'])
        self.assertEqual(1, result['files'])
        self.assertTrue(all(row['file'].startswith('cedar-monitoring-src/src/') for row in result['findings']))
        (nested / 'package.json').write_text(json.dumps({'dependencies': {check.PACKAGE: '^1.0.0'}}))
        self.assertFalse(self.run_report()['dependencyValid'])
        (nested / 'src/style.scss').write_text('a { color: #123456; }')
        self.assertEqual('new', self.run_report()['findings'][0]['status'])

    def test_detects_fallbacks_and_shorthand_but_not_token_references(self):
        rows = list(check.findings('x.scss', '.a { color: var(--x, #fff); border: 1px solid rgb(0,0,0); font: 12px Roboto; padding: tokens.$space-2; color: var(--cedar-color-primary); }'))
        self.assertEqual(['color', 'color', 'typography'], [r['rule'] for r in rows])

    def test_comments_and_data_urls_are_not_findings_and_lines_survive(self):
        rows = list(check.findings('x.css', '/* color: red;\n */\n.a { background: url("data:red;black");\ncolor: #fff; }'))
        self.assertEqual(1, len(rows))
        self.assertEqual(4, rows[0]['line'])

    def test_named_color_tokens_are_not_color_literals(self):
        self.assertEqual([], list(check.findings('x.scss',
            'a { color: $cedar-teal; background: var(--theme-white); color: tokens.$color-error; }')))

    def test_typography_cannot_hide_in_keywords_units_shorthand_or_fallbacks(self):
        for declaration in ('font-weight: bold', 'font-size: medium', 'font-size: 110%',
                            'font-size: 3vw', 'font: var(--cedar-font-size)/1.5 var(--cedar-font-family)',
                            'font: menu', 'font-family: var(--custom, Arial)',
                            'font-weight: var(--cedar-font-weight-medium, 600)',
                            'font-weight: var(--custom, 500)', 'line-height: calc(1em + 2px)'):
            with self.subTest(declaration=declaration):
                self.assertEqual(['typography'], [r['rule'] for r in check.findings('x.css', f'a {{ {declaration}; }}')])

    def test_shared_references_and_matching_compatibility_fallbacks_are_allowed(self):
        for declaration in ('font: inherit', 'line-height: normal', 'font-family: tokens.$font-family',
                            'font: var(--cedar-font-size)/var(--cedar-control-line-height-default) var(--cedar-font-family)',
                            'font-weight: var(--cedar-font-weight-medium, 500)',
                            'font-family: var(--cedar-font-family-monospace, ui-monospace, SFMono-Regular, Menlo, monospace)'):
            with self.subTest(declaration=declaration):
                self.assertEqual([], list(check.findings('x.css', f'a {{ {declaration}; }}')))

    def test_modern_color_functions_are_gated_including_fallbacks(self):
        for color in ('lab(50% 0 0)', 'lch(50% 10 20)', 'oklab(.5 0 0)', 'hwb(90 0% 0%)'):
            self.assertEqual(['color'], [r['rule'] for r in check.findings('x.css', f'a {{ color: var(--custom, {color}); }}')])

    def test_strict_requires_exact_matching_dependency_but_not_latest_checkout(self):
        self.run_report(initialize=True)
        for pin, locked, expected in ((None, None, 1), ('^1.0.0', '1.0.0', 1),
                                      ('1.0.0', '2.0.0', 1), ('1.0.0', None, 1),
                                      ('1.0.0', '1.0.0', 0)):
            (self.repo / 'package.json').write_text(json.dumps({'dependencies': {check.PACKAGE: pin}}))
            (self.repo / 'package-lock.json').write_text(json.dumps({'packages': {
                'node_modules/' + check.PACKAGE: {'version': locked}}}))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(expected, check.main(['--root', str(self.root), '--repo', 'consumer', '--strict']))

    def test_icon_drift_cannot_be_baselined_or_excepted(self):
        self.run_report(initialize=True)
        (self.repo / 'src/control.html').write_text('<mat-icon>help</mat-icon>')
        icon = next(row for row in self.run_report()['findings'] if row['rule'] == 'iconography')
        baseline = json.loads((self.repo / check.BASELINE).read_text())
        baseline['findings'][icon['id']] = {**icon, 'count': 100}
        baseline['exceptions'] = {icon['id']: 'Attempt to bypass the shared icon contract'}
        (self.repo / check.BASELINE).write_text(json.dumps(baseline))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(1, check.main(['--root', str(self.root), '--repo', 'consumer', '--strict']))
        self.assertEqual('new', next(row for row in self.run_report()['findings'] if row['rule'] == 'iconography')['status'])

    def test_malformed_baseline_structure_is_diagnosed(self):
        for data in ([], {'schema': 1, 'findings': {'x': None}},
                     {'schema': 1, 'findings': {}, 'exceptions': []}):
            (self.repo / check.BASELINE).write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                self.run_report()

    def test_baseline_does_not_depend_on_lines_and_counts_duplicates(self):
        self.run_report(initialize=True)
        self.style.write_text('\n\n' + self.style.read_text() + '\n.b { color: #fff; }')
        result = self.run_report()
        self.assertEqual(1, sum(r['status'] == 'new' for r in result['findings']))

    def test_new_value_fails_even_if_total_count_is_unchanged(self):
        self.run_report(initialize=True)
        self.style.write_text('.a { color: #123; }')
        self.assertEqual('new', self.run_report()['findings'][0]['status'])

    def test_pruning_only_decreases_allowances(self):
        self.run_report(initialize=True)
        self.style.write_text('.a { color: #123; }')
        result = self.run_report(prune=True)
        self.assertEqual('new', result['findings'][0]['status'])
        self.assertEqual({}, json.loads((self.repo / check.BASELINE).read_text())['findings'])
        with self.assertRaises(ValueError):
            self.run_report(initialize=True)

    def test_vendor_build_and_ignored_files_are_excluded(self):
        (self.repo / '.gitignore').write_text('src/generated.css\n')
        for name in ('src/vendor/lib.css', 'src/generated.css', 'dist/out.css', 'app/bower_components/x/x.css'):
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('x { color: red; }')
        self.assertEqual([Path('src/style.scss')], list(check.source_files(self.repo)))

    def test_dependency_and_lock_are_compared_separately(self):
        self.assertEqual('matches checkout', self.run_report()['versionStatus'])
        (self.repo / 'package-lock.json').unlink()
        self.assertEqual('differs from checkout/lock', self.run_report()['versionStatus'])

    def test_reasoned_exceptions_apply_to_exact_finding(self):
        self.run_report(initialize=True)
        self.style.write_text('a { color: red; color: blue; }')
        result = self.run_report()
        path = self.repo / check.BASELINE
        baseline = json.loads(path.read_text())
        baseline['exceptions'] = {result['findings'][0]['id']: 'External vocabulary swatch must retain its supplied color'}
        path.write_text(json.dumps(baseline))
        self.assertEqual(['exception', 'new'], [r['status'] for r in self.run_report()['findings']])
        baseline['exceptions'][result['findings'][0]['id']] = ''
        path.write_text(json.dumps(baseline))
        with self.assertRaises(ValueError):
            self.run_report()

    def test_trusted_revision_prevents_baseline_expansion_in_pr(self):
        self.run_report(initialize=True)
        subprocess.run(['git', '-C', str(self.repo), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(self.repo), '-c', 'user.name=Test', '-c', 'user.email=test@example.org', 'commit', '-qm', 'baseline'], check=True)
        self.style.write_text('a { color: purple; }')
        (self.repo / check.BASELINE).unlink()
        self.run_report(initialize=True)
        with self.assertRaisesRegex(ValueError, 'allowance increased'):
            self.run_report(ref='HEAD')

    def commit(self):
        subprocess.run(['git', '-C', str(self.repo), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(self.repo), '-c', 'user.name=Test', '-c', 'user.email=test@example.org', 'commit', '-qm', 'fixture'], check=True)

    def test_policy_upgrade_only_accepts_historical_debt(self):
        (self.repo / 'src/component.ts').write_text('@Component({styles: [`a { height: 37px; }`]})')
        self.run_report(initialize=True)
        self.commit()
        check.upgrade_policy(self.repo)
        self.assertTrue(all(r['status'] == 'existing' for r in self.run_report(ref='HEAD')['findings']))
        self.style.write_text('a { gap: 99px; }')
        self.assertTrue(any(r['status'] == 'new' for r in self.run_report(ref='HEAD')['findings']))

    def test_policy_scan_needs_no_generated_output(self):
        read = Path.read_text
        def without_dist(path, *args, **kwargs):
            if 'dist' in path.parts:
                raise FileNotFoundError('Clean checkouts have no dist')
            return read(path, *args, **kwargs)
        self.style.write_text('a { color: var(--cedar-text-primary); background: var(--cedar-primary-50); border-color: var(--cedar-on-accent-A200); }')
        with patch.object(Path, 'read_text', without_dist):
            self.assertEqual([], list(check.scan_styles(self.repo, 2)))

    def test_unknown_tokens_cannot_be_excepted_or_baselined(self):
        self.run_report(initialize=True)
        self.commit()
        check.upgrade_policy(self.repo)
        self.style.write_text('a { color: var(--cedar-typo); }')
        row = self.run_report()['findings'][0]
        self.assertEqual('unknown-token', row['rule'])
        path = self.repo / check.BASELINE
        baseline = json.loads(path.read_text())
        baseline['findings'][row['id']] = dict(row, count=1)
        baseline['exceptions'][row['id']] = 'An invalid token should never be permitted'
        path.write_text(json.dumps(baseline))
        self.assertEqual('new', self.run_report()['findings'][0]['status'])

    def test_unused_budget_increase_is_rejected(self):
        self.run_report(initialize=True)
        self.commit()
        path = self.repo / check.BASELINE
        baseline = json.loads(path.read_text())
        next(iter(baseline['findings'].values()))['count'] += 1
        path.write_text(json.dumps(baseline))
        self.style.write_text('a {}')
        with self.assertRaisesRegex(ValueError, 'allowance increased'):
            self.run_report(ref='HEAD')

    def test_default_scan_includes_modern_workspace(self):
        self.repo.rename(self.root / 'cedar-workspace')
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(0, check.main(['--root', str(self.root), '--json']))
        result = json.loads(output.getvalue())
        self.assertEqual(['cedar-workspace'], [r['repo'] for r in result['reports']])
        self.assertTrue(result['reports'][0]['findings'])

    def test_cli_exit_codes_and_json(self):
        def invoke(*args):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                code = check.main(['--root', str(self.root), '--repo', 'consumer', '--json', *args])
            return code, json.loads(output.getvalue())
        self.assertEqual(1, invoke('--strict')[0])
        self.assertEqual(0, invoke('--init-baseline', '--strict')[0])
        self.style.write_text(self.style.read_text() + 'b { margin: 12px; }')
        self.assertEqual(0, invoke('--strict')[0])
        self.style.write_text(self.style.read_text() + 'b { color: red; }')
        self.assertEqual(1, invoke('--strict')[0])
        (self.repo / check.BASELINE).write_text('invalid')
        self.assertEqual(2, invoke()[0])


if __name__ == '__main__':
    unittest.main()
