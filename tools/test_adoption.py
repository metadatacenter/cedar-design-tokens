import contextlib
import hashlib
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

    def test_native_choice_resets_in_bound_styles_are_gated(self):
        (self.repo / 'src/control.html').write_text('<input spellcheck="false" [style.accent-color]="colour">')
        rows = list(check.scan_styles(self.repo, 2))
        self.assertTrue(any(row['rule'] == 'dynamic-style' for row in rows))
        for value in ['auto', 'revert-layer', 'INITIAL !IMPORTANT']:
            rows = list(check.findings('x.scss', 'input { accent-color: ' + value + '; }'))
            self.assertEqual(('native-choice-reset', 'gate'), (rows[0]['rule'], rows[0]['severity']))

    def test_native_choice_contracts_cannot_be_baselined_or_excepted(self):
        self.style.write_text('input { accent-color: auto; }')
        self.run_report(initialize=True)
        path = self.repo / check.BASELINE
        baseline = json.loads(path.read_text())
        key = next(iter(baseline['findings']))
        baseline['exceptions'] = {key: 'No native browser defaults'}
        path.write_text(json.dumps(baseline))
        self.assertEqual('new', self.run_report()['findings'][0]['status'])
        self.assertEqual('native-choice-reset', self.run_report()['findings'][0]['rule'])

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
        self.assertEqual('differs from lock', self.run_report()['versionStatus'])

    def test_reasoned_exceptions_apply_to_exact_finding(self):
        self.style.write_text('a { color: red; }')
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

    def test_a_local_run_compares_with_the_upstream_branch(self):
        # CI compares a push with the remote's previous head, so a local run refuses what CI would.
        self.run_report(initialize=True)
        self.commit()
        self.assertIsNone(check.upstream_ref(self.repo))
        remote = self.root / 'remote.git'
        subprocess.run(['git', 'init', '-q', '--bare', str(remote)], check=True)
        subprocess.run(['git', '-C', str(self.repo), 'remote', 'add', 'origin', str(remote)], check=True)
        subprocess.run(['git', '-C', str(self.repo), 'push', '-q', '-u', 'origin', 'HEAD:main'], check=True)
        head = subprocess.run(['git', '-C', str(self.repo), 'rev-parse', 'HEAD'], check=True, capture_output=True, text=True)
        self.assertEqual(head.stdout.strip(), check.upstream_ref(self.repo))
        self.style.write_text('a { color: purple; }')
        (self.repo / check.BASELINE).unlink()
        self.run_report(initialize=True)
        errors = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(errors):
            self.assertEqual(2, check.main(['--root', str(self.root), '--repo', 'consumer', '--strict']))
        self.assertIn('allowance increased', errors.getvalue())

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
        self.style.write_text('a { color: var(--cedar-text-primary); background: var(--cedar-surface-selected); border-radius: var(--cedar-radius); }')
        with patch.object(Path, 'read_text', without_dist):
            self.assertEqual([], list(check.scan_styles(self.repo, 2)))

    def test_retired_tokens_name_their_replacement(self):
        self.style.write_text('a { color: var(--cedar-color-component-title); background: var(--cedar-primary-50); }')
        rows = [r for r in check.scan_styles(self.repo, 2) if r['rule'] == 'unknown-token']
        self.assertEqual({'--cedar-color-component-title': 'text-title'},
                         {r['value']: r['replacement'] for r in rows if r['value'].endswith('title')})
        self.assertEqual(2, len(rows))

    def test_consumers_cannot_redefine_shared_tokens(self):
        self.style.write_text('.table { --cedar-space-2: 6px; --cedar-icon-color: var(--cedar-status-error-text); }')
        rows = [r for r in check.scan_styles(self.repo, 2) if r['rule'] == 'token-override']
        self.assertEqual(['--cedar-space-2'], [r['value'] for r in rows])
        self.style.write_text('.a { color: #fff; }')
        self.run_report(initialize=True)
        self.commit()
        check.upgrade_policy(self.repo)
        self.style.write_text('.table { --cedar-space-2: 6px; }')
        row = next(r for r in self.run_report()['findings'] if r['rule'] == 'token-override')
        path = self.repo / check.BASELINE
        baseline = json.loads(path.read_text())
        baseline['findings'][row['id']] = dict(row, count=1)
        path.write_text(json.dumps(baseline))
        self.assertEqual('new', next(r for r in self.run_report()['findings'] if r['rule'] == 'token-override')['status'])

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

    def test_framework_variables_and_undefined_alias_targets_are_rejected(self):
        self.style.write_text('a { color: var(--color-gray-400); --local: var(--missing, var(--cedar-text-muted)); }')
        rows = list(check.scan_styles(self.repo, 2))
        self.assertEqual({'--color-gray-400', '--missing'}, {r['value'] for r in rows})
        self.assertTrue(all(r['rule'] == 'unknown-variable' for r in rows))

    def test_local_aliases_and_documented_host_overrides_are_supported(self):
        self.style.write_text(':root { --local: var(--cedar-text-muted); --alias: var(--local); } '
                              'a { color: var(--alias); height: var(--cedar-control-height); '
                              'grid-template-columns: var(--runtime-columns, 1fr); }')
        self.assertEqual([], list(check.scan_styles(self.repo, 2)))

    def test_numeric_aliases_cannot_hide_literal_typography_or_spacing(self):
        self.style.write_text(':root { --size: 13px; --alias: var(--size); } '
                              'a { font-size: var(--alias); padding: var(--size); }')
        rows = list(check.scan_styles(self.repo, 2))
        self.assertEqual({'typography', 'spacing'}, {r['rule'] for r in rows})

    def test_inline_style_variables_are_checked_and_comments_are_ignored(self):
        self.style.write_text('/* color: var(--ignored); */')
        (self.repo / 'src/view.html').write_text('<div style="color: var(--external)"></div>')
        rows = list(check.scan_styles(self.repo, 2))
        self.assertEqual(['--external'], [r['value'] for r in rows])

    def test_unknown_variables_cannot_be_baselined(self):
        self.run_report(initialize=True)
        self.commit()
        check.upgrade_policy(self.repo)
        self.style.write_text('a { color: var(--external); }')
        row = self.run_report()['findings'][0]
        baseline_path = self.repo / check.BASELINE
        baseline = json.loads(baseline_path.read_text())
        baseline['findings'][row['id']] = dict(row, count=1)
        baseline['exceptions'][row['id']] = 'Must not allow undeclared variables'
        baseline_path.write_text(json.dumps(baseline))
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

    def test_reasoned_exception_cannot_authorize_extra_copies(self):
        result = self.run_report(initialize=True)
        key = next(r['id'] for r in result['findings'] if r['rule'] == 'color')
        path = self.repo / check.BASELINE
        baseline = json.loads(path.read_text())
        baseline['exceptions'] = {key: 'External swatch keeps its source color in this one location'}
        path.write_text(json.dumps(baseline))
        self.style.write_text(self.style.read_text() + '.extra { color: #fff; }')
        colors = [r['status'] for r in self.run_report()['findings'] if r['rule'] == 'color']
        self.assertEqual(['exception', 'new'], colors)

    def test_all_css_named_colours_and_alternative_spacing_units_gate(self):
        for color in ('rebeccapurple', 'aliceblue', 'fuchsia', 'DarkSlateGrey'):
            self.assertEqual(['color'], [r['rule'] for r in check.findings('x.scss', f'a {{ background: {color}; }}', 2)])
        for value in ('3vh', '2ch', '4vw', '1pt'):
            self.assertEqual(['spacing'], [r['rule'] for r in check.findings('x.scss', f'a {{ padding: {value}; }}', 2)])

    def test_sass_aliases_are_resolved_through_local_modules(self):
        for source in ('$size: 17px; a { font-size: $size; }',
                       '$gutter: 13px; a { padding: $gutter; }',
                       '$size: 17px; a { font-size: #{$size}; }',
                       '$size: 14px; $size: 17px; a { font-size: $size; }',
                       '$first: $second; $second: 17px; a { font-size: $first; }'):
            self.style.write_text(source)
            self.assertTrue(list(check.scan_styles(self.repo, 2)), source)
        (self.repo / 'src/_private.scss').write_text('$size: 17px;')
        self.style.write_text("@use 'private' as tokens; a { font-size: tokens.$size; }")
        self.assertTrue(any(r['rule'] == 'typography' for r in check.scan_styles(self.repo, 2)))
        self.style.write_text("@use '@org.metadatacenter/cedar-design-tokens/tokens'; $size: tokens.$font-size; a { font-size: $size; }")
        self.assertEqual([], list(check.scan_styles(self.repo, 2)))

    def test_spacing_arithmetic_is_not_a_baseline_escape(self):
        self.style.write_text('a { padding: calc(var(--cedar-space-1) * 3.25); }')
        self.run_report(initialize=True)
        rows = self.run_report()['findings']
        self.assertEqual(('spacing-expression', 'new'), (rows[0]['rule'], rows[0]['status']))
        self.style.write_text('a { --gap: calc(var(--cedar-space-1) * 3.25); padding: var(--gap); }')
        self.assertTrue(any(r['rule'] == 'spacing-expression' for r in check.scan_styles(self.repo, 2)))

    def test_cetp_bridge_has_exact_owner_file_and_pairs(self):
        self.style.write_text('a { --cedar-space-1: var(--cetp-invented); --cetp-invented: 13px; }')
        self.assertTrue(any(r['rule'] == 'token-override' for r in check.scan_styles(self.repo, 2)))
        self.style.unlink()
        adapter = self.repo / 'src/app/cedar-embeddable-term-picker.scss'
        adapter.parent.mkdir()
        adapter.write_text('a { --cetp-color-primary: var(--cedar-color-primary); --cedar-color-primary: var(--cetp-color-primary); }')
        self.assertTrue(any(r['rule'] == 'token-override' for r in check.scan_styles(self.repo, 2)))
        (self.repo / 'package.json').write_text('{"name":"cedar-embeddable-term-picker"}')
        self.assertEqual([], list(check.scan_styles(self.repo, 2)))
        adapter.write_text('a { --cetp-color-primary: var(--cedar-color-primary); --cedar-space-1: var(--cetp-color-primary); }')
        self.assertTrue(any(r['rule'] == 'token-override' for r in check.scan_styles(self.repo, 2)))

    def test_runtime_token_writes_are_unconditionally_rejected(self):
        self.style.write_text('')
        snippets = [
            ('html', '<div [style.--cedar-space-1]="gutter"></div>'),
            ('html', '<div [style.--cedar-space-1.px]="gutter"></div>'),
            ('ts', "el.style.setProperty('--cedar-space-1', gutter);"),
            ('ts', "renderer.setStyle(el, '--cedar-space-1', gutter);"),
            ('ts', "el.style['--cedar-space-1'] = gutter;"),
            ('ts', "@HostBinding('style.--cedar-space-1') gutter = '13px';"),
            ('ts', "@Component({host: {'[style.--cedar-space-1]': 'gutter'}})"),
        ]
        for extension, source in snippets:
            with self.subTest(source=source):
                p = self.repo / ('src/control.' + extension)
                p.write_text(source)
                self.assertTrue(any(r['rule'] == 'token-override' for r in check.scan_styles(self.repo, 2)))
                p.unlink()

    def test_sass_module_token_assignments_are_rejected(self):
        self.style.write_text("@use '@org.metadatacenter/cedar-design-tokens/tokens' as shared; shared.$font-size: 17px; a { font-size: shared.$font-size; }")
        self.assertTrue(any(r['rule'] == 'token-override' for r in check.scan_styles(self.repo, 2)))

    def test_runtime_local_alias_cannot_hide_dynamic_paint(self):
        self.style.write_text('a { padding: var(--local-gap); }')
        (self.repo / 'src/control.html').write_text('<div [style.--local-gap]="gutter"></div>')
        self.assertTrue(any(r['rule'] == 'dynamic-style' for r in check.scan_styles(self.repo, 2)))
        self.style.write_text('a { grid-template-columns: var(--columns); }')
        (self.repo / 'src/control.html').write_text('<div [style.--columns]="columns"></div>')
        self.assertEqual([], list(check.scan_styles(self.repo, 2)))

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

    def vendor(self, version, files):
        """Replace the npm manifests with a vendored copy of the given files under src."""
        for name in ('package.json', 'package-lock.json'):
            (self.repo / name).unlink()
        folder = self.repo / 'src/main/resources/web' / check.VENDORED
        folder.parent.mkdir(parents=True)
        for name, text in files.items():
            (folder.parent / name).write_text(text)
        folder.write_text(json.dumps({'package': check.PACKAGE, 'version': version, 'files': {
            name: hashlib.sha256(text.encode()).hexdigest() for name, text in files.items()}}))
        return folder.parent

    def test_a_vendored_copy_pins_and_locks_a_consumer_without_npm(self):
        copy = self.vendor('1.0.0', {'custom-properties.css': ':root { --cedar-space-2: 8px; }'})
        result = self.run_report(initialize=True)
        self.assertEqual(('1.0.0', '1.0.0', True), (result['pin'], result['locked'], result['dependencyValid']))
        # The vendored stylesheets are the package's, not the consumer's, and are not scanned.
        self.assertEqual([Path('src/style.scss')], list(check.source_files(self.repo)))
        (copy / 'custom-properties.css').write_text(':root { --cedar-space-2: 9px; }')
        result = self.run_report()
        self.assertEqual(('differs from lock', False), (result['versionStatus'], result['dependencyValid']))
        (copy / 'manifest.json').unlink()
        with self.assertRaisesRegex(ValueError, 'pins no token version'):
            self.run_report()

    def test_a_vendored_copy_declares_the_token_set_its_version_names(self):
        tokens, (head,) = self.token_checkout(['space-2', 'radius'])
        version = f'0.1.0-dev.20260101.{head}'
        with patch.object(check, 'PACKAGE_ROOT', tokens):
            copy = self.vendor(version, {'custom-properties.css': ':root { --cedar-space-2: 8px; --cedar-radius: 4px; }'})
            self.assertTrue(check.report(self.repo, version, initialize=True)['dependencyValid'])
            declared = ':root { --cedar-space-2: 8px; }'
            (copy / 'custom-properties.css').write_text(declared)
            manifest = json.loads((copy / 'manifest.json').read_text())
            manifest['files']['custom-properties.css'] = hashlib.sha256(declared.encode()).hexdigest()
            (copy / 'manifest.json').write_text(json.dumps(manifest))
            self.assertFalse(check.report(self.repo, version)['dependencyValid'])

    def test_a_repository_may_be_named_by_its_path_under_root(self):
        nested = self.root / 'mcp'
        nested.mkdir()
        self.repo.rename(nested / 'consumer')
        self.run_report = lambda **kwargs: check.report(nested / 'consumer', '1.0.0', **kwargs)
        self.run_report(initialize=True)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, check.main(['--root', str(self.root), '--repo', 'mcp/consumer', '--strict']))
        for name in ('../consumer', '/consumer', 'mcp/../consumer'):
            with self.subTest(name=name), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                check.main(['--root', str(self.root), '--repo', name])

    def token_checkout(self, *revisions):
        """A token repository whose commits hold the given token sets, newest last; returns their short names."""
        tokens = self.root / 'tokens'
        tokens.mkdir()
        subprocess.run(['git', 'init', '-q', str(tokens)], check=True)
        (tokens / 'package.json').write_text(json.dumps({'version': '0.1.0-dev.20260101.00000000'}))
        names = []
        for revision in revisions:
            (tokens / 'scss').mkdir(exist_ok=True)
            (tokens / 'scss/_tokens.scss').write_text(''.join(f'${name}: 1px;\n' for name in revision))
            subprocess.run(['git', '-C', str(tokens), 'add', '.'], check=True)
            subprocess.run(['git', '-C', str(tokens), '-c', 'user.name=Test', '-c', 'user.email=test@example.org',
                            'commit', '-qm', 'tokens'], check=True)
            names.append(subprocess.run(['git', '-C', str(tokens), 'rev-parse', '--short=8', 'HEAD'],
                                        capture_output=True, text=True, check=True).stdout.strip())
        return tokens, names

    def pin(self, version):
        (self.repo / 'package.json').write_text(json.dumps({'devDependencies': {check.PACKAGE: version}}))
        (self.repo / 'package-lock.json').write_text(json.dumps({'packages': {'node_modules/' + check.PACKAGE: {'version': version}}}))

    def test_expected_version_is_the_one_the_checkout_head_publishes(self):
        tokens, (old, head) = self.token_checkout(['space-2'], ['space-2', 'radius'])
        with patch.object(check, 'PACKAGE_ROOT', tokens):
            expected = check.published_version()
            self.assertRegex(expected, r'^0\.1\.0-dev\.\d{8}\.' + head + '$')
            self.pin(expected)
            self.assertEqual('matches checkout', check.report(self.repo, expected)['versionStatus'])
            self.pin(expected.replace(head, old))
            result = check.report(self.repo, expected)
            self.assertEqual(('1 token commits behind checkout', []), (result['versionStatus'], result['pinMissingTokens']))

    def test_a_pin_that_lacks_a_token_the_consumer_reads_fails_strict(self):
        tokens, (old, head) = self.token_checkout(['space-2'], ['space-2', 'radius'])
        self.style.write_text('a { border-radius: var(--cedar-radius); padding: var(--cedar-space-2); }')
        with patch.object(check, 'PACKAGE_ROOT', tokens):
            self.pin('0.1.0-dev.20260101.' + old)
            self.assertEqual(['radius'], check.report(self.repo, 'x')['pinMissingTokens'])
            self.pin('0.1.0-dev.202601010000.g' + head + '.t12')
            self.assertEqual([], check.report(self.repo, 'x')['pinMissingTokens'])
            self.pin('0.1.0-dev.20260101.abcdef12')
            self.assertTrue(check.report(self.repo, 'x')['pinUnknown'])
            self.pin('0.1.0-dev.20260101.' + old)
            with contextlib.redirect_stdout(io.StringIO()):
                (self.repo / check.BASELINE).write_text(json.dumps({'schema': 1, 'policy': 2, 'findings': {}}))
                self.assertEqual(1, check.main(['--root', str(self.root), '--repo', 'consumer', '--strict']))

    def test_a_pin_from_before_the_sources_moved_still_names_its_tokens(self):
        tokens, (head,) = self.token_checkout(['space-2', 'radius'])
        subprocess.run(['git', '-C', str(tokens), 'mv', 'scss/_tokens.scss', '_tokens.scss'], check=True)
        subprocess.run(['git', '-C', str(tokens), '-c', 'user.name=Test', '-c', 'user.email=test@example.org',
                        'commit', '-qm', 'former layout'], check=True)
        former = subprocess.run(['git', '-C', str(tokens), 'rev-parse', '--short=8', 'HEAD'],
                                capture_output=True, text=True, check=True).stdout.strip()
        with patch.object(check, 'PACKAGE_ROOT', tokens):
            self.assertEqual((former, {'space-2', 'radius'}), check.pinned_tokens('0.1.0-dev.20260101.' + former))
            self.assertEqual((head, {'space-2', 'radius'}), check.pinned_tokens('0.1.0-dev.20260101.' + head))

    def test_strict_fails_on_allowances_the_code_no_longer_needs(self):
        self.style.write_text('a { color: #123; } b { color: #123; }')
        self.run_report(initialize=True)
        self.style.write_text('a { color: #123; }')
        self.assertEqual(1, self.run_report()['staleAllowances'])
        self.run_report(prune=True)
        self.assertEqual(0, self.run_report()['staleAllowances'])

    def test_policy_three_reads_outlines_opacity_easing_and_negative_lengths(self):
        source = ('a { outline: 3px solid var(--cedar-color-primary); outline-offset: 1px; opacity: .5;'
                  ' transition: color var(--cedar-motion-duration-fast) ease; margin-top: -6px;'
                  ' letter-spacing: -0.3px; z-index: 9999 !important; border-top-left-radius: 7px;'
                  ' background: color-mix(in srgb, var(--cedar-color-primary) 15%, transparent); }')
        self.assertEqual([], list(check.findings('x.scss', source, 2)))
        found = {(r['property'], r['rule']) for r in check.findings('x.scss', source, 3)}
        self.assertEqual({('outline', 'geometry'), ('outline-offset', 'geometry'), ('opacity', 'geometry'),
                          ('transition', 'motion'), ('margin-top', 'spacing'), ('letter-spacing', 'typography'),
                          ('z-index', 'geometry'), ('border-top-left-radius', 'geometry'), ('background', 'color')}, found)
        quiet = ('a { opacity: 0; } b { opacity: 1; } c { animation: spin var(--cedar-motion-duration-spinner) linear infinite; }'
                 ' d { outline: none; outline-offset: var(--cedar-focus-ring-offset); }')
        self.assertEqual([], list(check.findings('x.scss', quiet, 3)))

    def test_policy_three_reads_bound_outline_colours(self):
        (self.repo / 'src/card.html').write_text("<div [style.outline-color]=\"issues ? '#b42318' : null\"></div>")
        self.assertEqual([], [r for r in check.scan_styles(self.repo, 2) if r['file'].endswith('.html')])
        self.assertEqual(['dynamic-style'], [r['rule'] for r in check.scan_styles(self.repo, 3) if r['file'].endswith('.html')])

    def test_policy_upgrade_moves_one_step_and_records_new_debt(self):
        self.style.write_text('a { color: #fff; opacity: .5; }')
        self.run_report(initialize=True)
        path = self.repo / check.BASELINE
        baseline = json.loads(path.read_text())
        baseline['policy'] = 2
        path.write_text(json.dumps(baseline))
        self.commit()
        check.upgrade_policy(self.repo)
        self.assertEqual(3, json.loads(path.read_text())['policy'])
        self.commit()
        self.assertTrue(all(r['status'] == 'existing' for r in self.run_report(ref='HEAD')['findings']))
        while json.loads(path.read_text())['policy'] < check.LATEST_POLICY:
            check.upgrade_policy(self.repo)
            self.commit()
        with self.assertRaises(ValueError):
            check.upgrade_policy(self.repo)

    def test_policy_four_reads_material_inputs(self):
        source = ('.theme { --mat-form-field-container-height: 40px; --mat-menu-item-label-text-weight: 600;'
                  ' --mdc-filled-text-field-label-text-size: 13px; --mat-icon-button-icon-size: 20px;'
                  ' --mat-select-trigger-text-line-height: var(--cedar-control-line-height-default); }'
                  ' @include mat.form-field-overrides((container-text-size: 13px, container-shape: var(--cedar-radius),'
                  ' outlined-outline-width: 1px));')
        self.assertEqual([], [r for r in check.findings('x.scss', source, 3) if r['property'].startswith(('--mat', '--mdc', 'form'))])
        found = {(r['property'], r['rule']) for r in check.findings('x.scss', source, 4)}
        self.assertEqual({('--mat-form-field-container-height', 'geometry'), ('--mat-menu-item-label-text-weight', 'typography'),
                          ('--mdc-filled-text-field-label-text-size', 'typography'),
                          ('form-field-overrides.container-text-size', 'typography')}, found)

    def test_policy_four_reads_styles_that_skip_the_template_scan(self):
        (self.repo / 'src/host.ts').write_text("""
            interface Options { styles: string[] }
            @Component({selector: 'x', host: {style: 'font-size: 13px', '[style.color]': 'tint', '[attr.style]': 'css'},
                        styles: [SHARED], template: '<svg><text font-size="13" fill="#123456">A</text></svg><b class="[font-size:13px] outline-4">B</b>'})
            class Host {}
            const sheet = css`.a { color: #654321; }`;
            new CSSStyleSheet().replaceSync(text);""")
        three = [r for r in check.scan_styles(self.repo, 3) if r['file'].endswith('host.ts')]
        four = [r for r in check.scan_styles(self.repo, 4) if r['file'].endswith('host.ts')]
        self.assertEqual([], [r for r in three if r['rule'] != 'spellcheck'])
        kinds = sorted((r['rule'], r['property']) for r in four if r['rule'] != 'spellcheck')
        self.assertIn(('typography', 'font-size'), kinds)
        self.assertIn(('color', 'fill'), kinds)
        self.assertIn(('color', 'color'), kinds)
        self.assertIn(('utility-style', 'utility-style'), kinds)
        self.assertEqual(4, sum(1 for kind in kinds if kind == ('dynamic-style', 'dynamic-style') or kind == ('dynamic-style', 'color')))

    def test_indirect_overrides_of_shared_tokens_are_refused(self):
        for source in ("a { #{'--cedar-space-2'}: 6px; }",
                       '$name: --cedar-radius;\na { #{$name}: 7px; }',
                       '@property --cedar-radius { syntax: "<length>"; inherits: true; initial-value: 7px; }'):
            self.style.write_text(source)
            rows = [r for r in check.scan_styles(self.repo, 2) if r['rule'] == 'token-override']
            self.assertTrue(rows, source)


if __name__ == '__main__':
    unittest.main()
