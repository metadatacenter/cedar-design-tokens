import unittest
from pathlib import Path
from check_icons import violations, scan
import tempfile
import subprocess

class IconsTest(unittest.TestCase):
    def check(self, source, path='src/app/example.html'):
        return [rule for _, rule, _ in violations(Path(path), source)]

    def test_semantic_adapters(self):
        self.assertEqual(self.check('<cedar-icon name="permissions"/><app-icon key="orcid"/><mat-icon [cedarIcon]="name"></mat-icon>'), [])

    def test_missing_and_unknown_icons(self):
        self.assertIn('unknown-icon', self.check('<cetp-icon name="made-up"/>'))
        self.assertIn('icon-font', self.check('<mat-icon>help</mat-icon>'))
        self.assertIn('text-icon', self.check('<button>×</button>'))

    def test_local_geometry_and_dependencies(self):
        for source in ['<svg><path d="M1 2"/></svg>', 'background: url("data:image/svg+xml,foo")', "import { X } from 'lucide-angular';", "font-family: 'CEE Material Icons'"]:
            self.assertTrue(self.check(source), source)

    def test_brand_name_cannot_waive_geometry(self):
        self.assertIn('inline-svg', self.check('<svg aria-label="CEDAR"><path d="M1 2"/></svg>'))

    def test_adapter_must_read_registry_and_cannot_own_geometry(self):
        source = "import {getIcon} from '@org.metadatacenter/cedar-design-tokens/icons'; <svg [innerHTML]=\"body\"></svg>"
        self.assertEqual(self.check(source, 'src/app/icon.ts'), [])
        self.assertIn('inline-svg', self.check(source))
        self.assertIn('inline-svg', self.check(source.replace('</svg>', '<path/></svg>'), 'src/app/icon.ts'))

    def test_comments_are_not_icons(self):
        self.assertEqual(self.check('<!-- <mat-icon>×</mat-icon> -->'), [])

    def test_nested_angular_apps_are_scanned_without_legacy_or_build_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            for name in ['cedar-monitoring-src/src/app/example.html', 'app/legacy.html', 'cedar-monitoring-dist/index.html']:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('<fa-icon></fa-icon>')
            findings = list(scan(root))
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0]['file'], 'cedar-monitoring-src/src/app/example.html')
