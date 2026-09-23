import unittest
from check_spellcheck import findings


class SpellcheckTest(unittest.TestCase):
    def test_requires_false_on_every_control(self):
        for markup in ('<input>', '<textarea></textarea>', '<div contenteditable="true"></div>',
                       '<input spellcheck="true">', '<input spellcheck>',
                       '<input [spellcheck]="false">', '<input [attr.spellcheck]="mode">',
                       '<input spellcheck="false" [spellcheck]="mode">'):
            with self.subTest(markup=markup):
                self.assertEqual(len(list(findings('src/a.html', markup))), 1)

    def test_accepts_only_explicit_disabled_controls(self):
        markup = '''<input spellcheck="false" [value]="a > b"><textarea spellcheck='false'></textarea>
                    <div contenteditable spellcheck="false"></div>'''
        self.assertEqual(list(findings('src/a.html', markup)), [])

    def test_checks_inline_templates_but_not_code_strings_or_comments(self):
        source = '''const example = '<input>'; // <textarea>
        @Component({ template: `<input spellcheck="false"><textarea></textarea>` })'''
        rows = list(findings('src/a.ts', source))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['line'], 2)
        self.assertEqual(list(findings('src/a.html', '<!-- <input> -->')), [])

    def test_rejects_opt_in_on_ancestors(self):
        self.assertEqual(len(list(findings('src/a.html', '<div spellcheck="true">'))), 1)


if __name__ == '__main__':
    unittest.main()
