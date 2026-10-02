import json
import unittest
from check_native_choices import findings


class NativeChoicesTest(unittest.TestCase):
    def setUp(self):
        self.files = {
            'package.json': '{"name":"cedar-workspace"}',
            'src/index.html': '<cedar-workspace class="cedar-native-choices"></cedar-workspace>',
            'angular.json': json.dumps({'projects': {'workspace': {'architect': {'build': {'options': {'styles': ['src/styles.scss']}}}}}}),
            'src/styles.scss': '@import "@org.metadatacenter/cedar-design-tokens/native-choices.css";',
        }

    def check(self):
        return list(findings(self.files.__getitem__))

    def test_loaded_global_theme_and_opted_in_root(self):
        self.assertEqual([], self.check())

    def test_missing_root_class_or_loaded_stylesheet_fails(self):
        self.files['src/index.html'] = '<cedar-workspace></cedar-workspace>'
        self.assertEqual(['src/index.html'], [r['file'] for r in self.check()])
        self.files['src/styles.scss'] = ''
        self.assertEqual(2, len(self.check()))

    def test_comments_scoped_imports_and_noninjected_styles_do_not_pass(self):
        original = self.files['src/styles.scss']
        for source in [f'/* {original} */', f'.a {{ {original} }}']:
            self.files['src/styles.scss'] = source
            self.assertEqual(1, len(self.check()))
        self.files['src/styles.scss'] = original
        self.files['angular.json'] = self.files['angular.json'].replace('"src/styles.scss"', '{"input":"src/styles.scss","inject":false}')
        self.assertEqual(1, len(self.check()))

    def test_legacy_and_embedded_consumers_are_not_opted_in(self):
        for name in ['cedar-template-editor', 'cedar-embeddable-editor']:
            self.files = {'package.json': json.dumps({'name': name})}
            self.assertEqual([], self.check())

    def test_repository_with_only_a_nested_frontend_is_untouched(self):
        def read(path):
            raise FileNotFoundError(path)
        self.assertEqual([], list(findings(read)))
