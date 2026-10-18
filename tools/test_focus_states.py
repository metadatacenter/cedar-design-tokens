import json
import unittest
from check_focus_states import findings

ELEMENT = """@Component({
  selector: 'cedar-x',
  styleUrls: ['../../styles.css', '../../authoring.scss'],
  encapsulation: ViewEncapsulation.ShadowDom,
})"""


class FocusStatesTest(unittest.TestCase):
    def setUp(self):
        self.files = {
            'package.json': '{"name":"cedar-workspace"}',
            'angular.json': json.dumps({'projects': {'workspace': {'architect': {'build': {'options': {'styles': ['src/styles.scss']}}}}}}),
            'src/styles.scss': "@use '@org.metadatacenter/cedar-design-tokens/controls';\n@include controls.focus-states;",
        }

    def check(self):
        return [row['file'] for row in findings(self.files.__getitem__, self.files)]

    def test_application_global_stylesheet(self):
        self.assertEqual([], self.check())
        self.files['src/styles.scss'] = "@import '@org.metadatacenter/cedar-design-tokens/focus.css';"
        self.assertEqual([], self.check())
        self.files['src/styles.scss'] = "@use '@org.metadatacenter/cedar-design-tokens/controls' as ui;\n@include ui.focus-states(var(--x));"
        self.assertEqual([], self.check())

    def test_missing_commented_scoped_or_unbound_recipe_fails(self):
        recipe = self.files['src/styles.scss']
        for source in ['', f'/* {recipe} */', "@use '@org.metadatacenter/cedar-design-tokens/controls';\n.a { @include controls.focus-states; }",
                       "@use './controls';\n@include controls.focus-states;"]:
            self.files['src/styles.scss'] = source
            self.assertEqual(['angular.json'], self.check(), source)

    def test_noninjected_stylesheet_does_not_count(self):
        self.files['angular.json'] = self.files['angular.json'].replace('"src/styles.scss"', '{"input":"src/styles.scss","inject":false}')
        self.assertEqual(['angular.json'], self.check())

    def test_every_shadow_root_needs_it_through_its_own_stylesheets(self):
        self.files.update({'package.json': '{"name":"cedar-embeddable-designer"}', 'src/app/element/x.element.ts': ELEMENT,
                           'src/styles.css': '', 'src/authoring.scss': "@use './focus';", 'src/_focus.scss': self.files['src/styles.scss']})
        # The global stylesheet serves the demonstration page; only the shadow root counts.
        del self.files['src/styles.scss']
        self.assertEqual([], self.check())
        self.files['src/_focus.scss'] = ''
        self.assertEqual(['src/app/element/x.element.ts'], self.check())

    def test_nested_frontend_and_static_host(self):
        self.files = {f'cedar-bridging-src/{name}': source for name, source in self.files.items()}
        self.files['cedar-bridging-src/package.json'] = '{"name":"cedar-bridging"}'
        self.assertEqual([], self.check())
        self.files = {'package.json': '{"name":"cedar-template-designer"}', 'app/styles/host.css': "@import '../components/motion.css';"}
        self.assertEqual(['app/styles/host.css'], self.check())
        self.files['app/styles/host.css'] += "\n@import '../components/focus.css';"
        self.assertEqual([], self.check())

    def test_other_repositories_are_outside_the_contract(self):
        for files in [{'package.json': '{"name":"cedar-template-editor"}'}, {'pom.xml': ''}]:
            self.files = files
            self.assertEqual([], self.check())


if __name__ == '__main__':
    unittest.main()
