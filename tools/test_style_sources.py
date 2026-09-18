import unittest
from pathlib import Path
from style_sources import sources
from check_adoption import findings

class EmbeddedStylesTest(unittest.TestCase):
    def rules(self, path, source):
        return [r for css in sources(Path(path), source) for r in findings(path, css, 2)]

    def test_component_styles_and_template_preserve_locations(self):
        source = '''// color: red;
@Component({styles: [`a { padding: 7px; }`],
 template: `<div style="color: #fff" [style.font-size.px]="17"></div>`})'''
        rows = self.rules('x.ts', source)
        self.assertEqual(['spacing', 'color', 'typography'], [r['rule'] for r in rows])
        self.assertEqual([2, 3, 3], [r['line'] for r in rows])
        self.assertTrue(all(r['severity'] == 'gate' for r in rows))

    def test_business_strings_are_not_styles(self):
        self.assertEqual([], self.rules('x.ts', "const text = 'color: red'; const payload = {color: 'blue'};"))

    def test_bindings_cannot_hide_dynamic_paint(self):
        for attribute in ['[style.color]="color"', '[ngStyle]="theme"', '[style]="theme"']:
            self.assertEqual('dynamic-style', self.rules('x.html', '<div '+attribute+'></div>')[0]['rule'])
        self.assertEqual([], self.rules('x.html', '<div [style.left.px]="position"></div>'))

    def test_utilities_require_shared_values(self):
        rows = self.rules('x.html', '<div class="flex hover:bg-red-500 p-4 rounded-lg text-[var(--cedar-font-size)]"></div>')
        self.assertEqual(3, len(rows))
        self.assertTrue(all(r['rule'] == 'utility-style' for r in rows))

    def test_geometry_elevation_layers_and_spacing_gate(self):
        rows = self.rules('x.scss', 'a { height: 33px; box-shadow: 0 1px 4px; z-index: 999; gap: 7px; border-radius: 9px; }')
        self.assertEqual(5, len(rows))
        self.assertTrue(all(r['severity'] == 'gate' for r in rows))

    def test_comments_and_semantic_tokens_pass(self):
        self.assertEqual([], self.rules('x.html', '<!-- <div style="color:red"> --> <div style="color:var(--cedar-color-primary)"></div>'))
