"""Source guard for CEDAR-owned icons; no baselines can waive icon drift."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
NAMES = set(json.loads((ROOT / 'icons/manifest.json').read_text())) | set(json.loads((ROOT / 'icons/aliases.json').read_text()))
ADAPTERS = {'src/app/icon.ts', 'src/app/shared/components/icon/icon.component.ts'}
# The one inline brand asset is pinned by geometry, not by an easily copied exemption comment.
BRAND_HASH = '1755bc8dd8839f0c70fcd9259a47da3dbad2462fbb20e703588f573e99ad30be'


def violations(path, source):
    source = re.sub(r'/\*.*?\*/|<!--.*?-->|(?m:^[ \t]*//[^\n]*)', lambda m: '\n' * m[0].count('\n'), source, flags=re.S)
    for match in re.finditer(r'<svg\b[^>]*>[\s\S]*?</svg>', source):
        svg = match[0]
        brand = hashlib.sha256(re.sub(r'\s+', '', svg).encode()).hexdigest() == BRAND_HASH
        adapter = str(path) in ADAPTERS and '/cedar-design-tokens/icons' in source and not re.search(r'<(?:path|circle|rect|line|polyline|polygon|ellipse)\b', svg)
        if not brand and not adapter:
            yield match.start(), 'inline-svg', 'Render through the shared icon adapter'
    for match in re.finditer(r'<fa-icon\b', source):
        yield match.start(), 'icon-font', 'Use the shared CEDAR icon adapter'
    for match in re.finditer(r'<mat-icon\b([^>]*)>', source):
        if not re.search(r'\bcedarIcon\b', match[1]):
            yield match.start(), 'icon-font', 'mat-icon must use cedarIcon'
    for match in re.finditer(r'(?:CEE Material Icons|font-family\s*:\s*[\'"]?(?:Material Icons|FontAwesome)|data:image/svg\+xml|from\s+[\'"](?:lucide|@fortawesome)[^\'"]*)', source, re.I):
        yield match.start(), 'local-icon-source', 'Icon sources belong in cedar-design-tokens'
    for match in re.finditer(r'<(?:cedar-icon|cetp-icon|app-icon|mat-icon)\b[^>]*>', source):
        name = re.search(r'(?<![\w\[])\b(?:name|key|cedarIcon)="([^"{}]+)"', match[0])
        if name and name[1] not in NAMES:
            yield match.start(), 'unknown-icon', name[1]
    for match in re.finditer(r'[×✕▾▸▴＋✓]', source):
        yield match.start(), 'text-icon', 'Use a shared semantic SVG instead of a text glyph'


def scan(repo):
    manifest = repo / 'package.json'
    modern_host = manifest.is_file() and json.loads(manifest.read_text()).get('name') == 'cedar-template-designer'
    paths = subprocess.check_output(['git', '-C', str(repo), 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], text=True).split('\0')
    for name in sorted(set(paths)):
        path = Path(name)
        relative = Path(*path.parts[1:]) if path.parts and path.parts[0].endswith('-src') else path
        if not relative.parts or relative.parts[0] not in (('src', 'app') if modern_host else ('src',)) or path.suffix not in ('.html', '.ts', '.scss', '.css'):
            continue
        if {'assets', 'fixtures', '__tests__'}.intersection(path.parts) or '.spec.' in name or not (repo / path).is_file():
            continue
        source = (repo / path).read_text()
        for position, rule, message in violations(relative, source):
            yield {'file': name, 'line': source[:position].count('\n') + 1,
                   'rule': 'iconography', 'property': rule, 'value': message,
                   'id': hashlib.sha256(f'{name}|{rule}|{message}'.encode()).hexdigest()[:20],
                   'severity': 'gate', 'status': 'new'}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    args = parser.parse_args()
    findings = list(scan(args.repo.resolve()))
    for finding in findings:
        print(f"{finding['file']}:{finding['line']}: {finding['property']}: {finding['value']}")
    print(f"Shared icon check: {len(findings)} violation(s)")
    raise SystemExit(bool(findings))
