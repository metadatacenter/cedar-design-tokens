from pathlib import Path
import subprocess
import tempfile
import unittest
from check_accessibility_exceptions import findings

SPEC = 'browser/tests/layout-resilience.spec.ts'
TEMPLATE = 'src/app/row.component.html'


class AccessibilityExceptionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        self.write(SPEC, "const EXCEPTIONS: readonly Exception[] = [\n  { check: 'reflow', selector: '.history' },\n];\n")
        self.write(TEMPLATE, '<!-- eslint-disable-next-line @angular-eslint/template/interactive-supports-focus -->\n'
                             '<div (click)="open()"></div>\n')
        self.base = self.commit()

    def write(self, name, text):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def commit(self):
        subprocess.run(['git', '-C', str(self.repo), 'add', '-A'], check=True)
        subprocess.run(['git', '-C', str(self.repo), '-c', 'user.name=t', '-c', 'user.email=t@example.org',
                        'commit', '-qm', 'base'], check=True)
        return subprocess.check_output(['git', '-C', str(self.repo), 'rev-parse', 'HEAD'], text=True).strip()

    def new(self):
        return [row for row in findings(self.repo, self.base) if row['status'] == 'new']

    def test_the_recorded_exceptions_pass(self):
        rows = list(findings(self.repo, self.base))
        self.assertEqual(sorted(row['property'] for row in rows), ['EXCEPTIONS', 'template lint off'])
        self.assertTrue(all(row['status'] == 'existing' and row['severity'] == 'gate' for row in rows))

    def test_an_added_list_entry_is_new(self):
        self.write(SPEC, "const EXCEPTIONS: readonly Exception[] = [\n  { check: 'reflow', selector: '.history' },\n"
                         "  { check: 'resize', selector: '.about' },\n];\n")
        [row] = self.new()
        self.assertEqual((row['file'], row['line'], row['property']), (SPEC, 3, 'EXCEPTIONS'))
        self.assertIn(".about", row['value'])

    def test_a_reflowed_or_recommented_entry_is_the_same_entry(self):
        self.write(SPEC, "const EXCEPTIONS: readonly Exception[] = [\n  // Waits on a visible change.\n"
                         "  {\n    check: 'reflow',\n    selector: '.history'\n  },\n];\n")
        self.assertEqual(self.new(), [])

    def test_removing_an_exception_passes(self):
        self.write(SPEC, 'const EXCEPTIONS: readonly Exception[] = [];\n')
        self.write(TEMPLATE, '<button (click)="open()"></button>\n')
        self.assertEqual(self.new(), [])

    def test_a_list_under_another_recognised_name_is_read(self):
        self.write('visual/tests/accessibility.spec.ts', 'const KNOWN_VIOLATIONS = [];\n')
        self.base = self.commit()
        self.write('visual/tests/accessibility.spec.ts', "const KNOWN_VIOLATIONS = [{ rule: 'target-size' }];\n")
        self.assertEqual([row['property'] for row in self.new()], ['KNOWN_VIOLATIONS'])

    def test_brackets_and_commas_inside_strings_do_not_split_an_entry(self):
        self.write(SPEC, "const EXCEPTIONS = [\n  { check: 'reflow', selector: '.history' },\n"
                         "  { finding: /^value is clipped: \"(a, b]\"/, why: 'a [bracket], and a comma' },\n];\n")
        [row] = self.new()
        self.assertIn('a [bracket], and a comma', row['value'])

    def test_a_second_disable_of_the_same_rule_is_new(self):
        self.write(TEMPLATE, '<!-- eslint-disable-next-line @angular-eslint/template/interactive-supports-focus -->\n'
                             '<div (click)="open()"></div>\n'
                             '<!-- eslint-disable-next-line @angular-eslint/template/interactive-supports-focus -->\n'
                             '<div (click)="close()"></div>\n')
        [row] = self.new()
        self.assertEqual((row['property'], row['value'], row['line']), ('template lint off', 'interactive-supports-focus', 3))

    def test_a_disabled_lint_rule_outside_accessibility_is_not_an_exception(self):
        self.write(TEMPLATE, '<!-- eslint-disable-next-line @angular-eslint/template/no-call-expression -->\n<p>{{ f() }}</p>\n')
        self.assertEqual(self.new(), [])

    def test_switching_an_axe_rule_off_is_new_only_where_axe_runs(self):
        self.write('browser/tests/accessibility.spec.ts',
                   "import AxeBuilder from '@axe-core/playwright';\nnew AxeBuilder({ page });\n")
        self.write('browser/tests/flags.spec.ts', 'const flags = {};\n')
        self.base = self.commit()
        self.write('browser/tests/accessibility.spec.ts',
                   "import AxeBuilder from '@axe-core/playwright';\nnew AxeBuilder({ page }).disableRules(['target-size']);\n")
        self.write('browser/tests/flags.spec.ts', 'const flags = { preview: { enabled: false } };\n')
        [row] = self.new()
        self.assertEqual((row['file'], row['property']), ('browser/tests/accessibility.spec.ts', 'axe rule off'))

    def test_unit_specs_and_build_output_are_not_read(self):
        self.write('src/app/thing.spec.ts', "const EXCEPTIONS = [{ rule: 'x' }];\n")
        self.write('browser/node_modules/pkg/tests/a.spec.ts', "const EXCEPTIONS = [{ rule: 'x' }];\n")
        self.assertEqual(self.new(), [])

    def test_a_new_suite_may_record_the_failures_it_finds(self):
        self.write('browser/tests/new-suite.spec.ts', "const EXCEPTIONS = [{ check: 'reflow', selector: '.wide' }];\n")
        self.assertEqual(self.new(), [])

    def test_a_template_disable_counts_even_beside_a_new_suite(self):
        self.write('src/app/new.component.html', '<!-- eslint-disable-next-line @angular-eslint/template/alt-text -->\n<img src="x">\n')
        [row] = self.new()
        self.assertEqual(row['value'], 'alt-text')

    def test_without_a_revision_nothing_is_new(self):
        self.write(SPEC, "const EXCEPTIONS = [{ check: 'resize' }];\n")
        self.assertTrue(all(row['status'] == 'existing' for row in findings(self.repo)))


if __name__ == '__main__':
    unittest.main()
