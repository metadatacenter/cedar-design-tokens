#!/usr/bin/env python3
"""Offline design-token adoption report. Python stdlib only; also used by cedarcli/CI."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from check_icons import scan as icon_findings
from style_sources import sources

PACKAGE = '@org.metadatacenter/cedar-design-tokens'
BASELINE = '.design-tokens-baseline.json'
REPOS = ('cedar-embeddable-editor', 'cedar-embeddable-designer',
         'cedar-embeddable-term-picker', 'cedar-workspace', 'cedar-openview',
         'cedar-monitoring', 'cedar-bridging', 'cedar-template-designer')
EXCLUDED = {'node_modules', 'bower_components', 'vendor', 'dist', 'dist-bundle',
            'assets', 'fixtures', '__tests__'}
COMMENT = re.compile(r'/\*.*?\*/|(?m:^[ \t]*//[^\n]*)', re.S)
DECL = re.compile(r'(?:^|[;{}])\s*([\w$-]+)\s*:\s*([^;{}]+)', re.M)
COLOR = re.compile(r'#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\s*\(|(?<![\w$@.-])(?:white|black|red|blue|gray|grey|orange|yellow|green|teal|purple|pink|hotpink)(?![\w-])', re.I)
DIMENSION = re.compile(r'(?<![\w.-])(?:\d*\.)?\d+(?:px|rem|em)\b')
EXACT_VERSION = re.compile(r'\d+\.\d+\.\d+(?:-[\w.-]+)?(?:\+[\w.-]+)?')
TOKEN_LITERALS = dict(re.findall(r'^\$([\w-]+):\s*([^;]+);',
                                (Path(__file__).resolve().parents[1] / '_tokens.scss').read_text(), re.M))


def literal_typography(prop, value):
    # Remove references, retaining var() fallbacks so literal defaults still gate.
    def compatibility(match):
        name, fallback = match.groups()
        canonical = TOKEN_LITERALS.get(name)
        return '' if canonical and ' '.join(fallback.split()) == ' '.join(canonical.split()) else match[0]
    value = re.sub(r'var\(\s*--cedar-([\w-]+)\s*,\s*([^()]+)\)', compatibility, value)
    inspected = re.sub(r'var\(\s*--[\w-]+\s*\)', '', value)
    inspected = re.sub(r'var\(\s*--[\w-]+\s*,', '(', inspected)
    inspected = re.sub(r'(?:[\w-]+\.)?\$[\w-]+|@[\w-]+', '', inspected)
    if re.search(r'(?<![\w.-])(?:\d*\.)?\d+(?:[a-z%]+)?', inspected, re.I):
        return True
    if prop in ('font-weight', 'font-size', 'font-stretch'):
        return bool(re.search(r'\b(?:bold|bolder|lighter|small|medium|large|larger|smaller|condensed|expanded)\b', inspected))
    if prop in ('font', 'font-family'):
        inspected = re.sub(r'!important|\b(?:inherit|initial|unset|revert|revert-layer|normal)\b', '', inspected)
        return bool(re.search(r'[a-zA-Z]', inspected))
    return False


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True)


def source_files(repo, policy=1, ref=None):
    # Includes new local files but never ignored build products or dependencies.
    names = (git(repo, 'ls-tree', '-rz', '--name-only', ref) if ref else git(repo, 'ls-files', '-z', '--cached', '--others', '--exclude-standard')).split('\0')
    for name in sorted(set(names)):
        path = Path(name)
        parts = path.parts[1:] if path.parts and path.parts[0].endswith('-src') else path.parts
        if (parts and parts[0] in ('src', 'app')
                and (path.suffix in ('.scss', '.css', '.less') or
                     (policy >= 2 and path.suffix in ('.html', '.ts') and '.spec.' not in name
                      and (parts[0] == 'src' or json.loads((repo / 'package.json').read_text()).get('name') == 'cedar-template-designer')))
                and not EXCLUDED.intersection(path.parts)
                and not path.name.startswith('styles-Material-Icons')
                and (ref or (repo / path).is_file())):
            yield path


def findings(path, source, policy=1):
    # Preserve newlines so diagnostics retain original source locations.
    clean = COMMENT.sub(lambda m: re.sub(r'[^\n]', ' ', m[0]), source)
    clean = re.sub(r'''(["'])(?:\\.|(?!\1).)*?\1''',
                   lambda m: re.sub(r'[;{}]', ' ', m[0]), clean)
    for match in DECL.finditer(clean):
        prop, value = match.groups()
        value = ' '.join(value.split())
        # Don't interpret text/URLs as color names (including embedded font payloads).
        inspected = re.sub(r'url\([^)]*\)|[\'"][^\'"]*[\'"]', '', value)
        rule = None
        if value == 'uninspectable-binding':
            rule = 'dynamic-style'
        elif prop == 'utility-style':
            rule = 'utility-style'
        elif COLOR.search(inspected):
            rule = 'color'
        elif prop in ('font', 'font-family', 'font-size', 'font-weight', 'font-stretch', 'line-height', 'letter-spacing'):
            if literal_typography(prop, value):
                rule = 'typography'
        elif re.fullmatch(r'(?:margin|padding)(?:-[\w-]+)?|(?:row-|column-)?gap', prop):
            if DIMENSION.search(value):
                rule = 'spacing'
        elif prop in ('height', 'min-height', 'border-radius', 'box-shadow', 'text-shadow', 'z-index', 'transition-duration', 'animation-duration') and (DIMENSION.search(value) or (prop == 'z-index' and re.fullmatch(r'-?\d+', value))):
            rule = 'geometry'
        if rule:
            identity = f'{path}|{rule}|{prop}|{value}'
            yield {'id': hashlib.sha256(identity.encode()).hexdigest()[:20],
                   'file': str(path), 'line': clean.count('\n', 0, match.start(1)) + 1,
                   'rule': rule, 'property': prop, 'value': value,
                   'severity': 'gate' if policy >= 2 or rule in ('color', 'typography') else 'advisory'}



def scan_styles(repo, policy=1, ref=None):
    known = set(re.findall(r'--cedar-([\w-]+)\s*:', (Path(__file__).resolve().parents[1] / 'dist/custom-properties.css').read_text()))
    known.update(name.removeprefix('cedar-') for name in json.loads((Path(__file__).parent / 'host-properties.json').read_text()))
    for path in source_files(repo, policy, ref):
        source = git(repo, 'show', f'{ref}:{path}') if ref else (repo / path).read_text()
        for snippet in sources(path, source):
            yield from findings(path, snippet, policy)
        if policy >= 2:
            for match in re.finditer(r'var\(\s*--cedar-([\w-]+)', source):
                if match[1] not in known:
                    value = '--cedar-' + match[1]
                    yield {'id': hashlib.sha256(f'{path}|unknown-token|{value}'.encode()).hexdigest()[:20],
                           'file': str(path), 'line': source[:match.start()].count('\n') + 1,
                           'rule': 'unknown-token', 'property': 'var', 'value': value, 'severity': 'gate'}


def upgrade_policy(repo):
    """One-time expansion records only debt already committed at HEAD, never working edits."""
    baseline, exists = read_baseline(repo)
    if not exists or baseline.get('policy', 1) != 1:
        raise ValueError('Upgrade requires an existing policy-1 baseline')
    if git(repo, 'status', '--porcelain').strip():
        raise ValueError('Commit or isolate changes before upgrading the style policy')
    rows = list(scan_styles(repo, 2))
    baseline['policy'] = 2
    baseline['findings'] = {row['id']: dict({k: row[k] for k in ('file', 'rule', 'property', 'value')},
                                         count=sum(r['id'] == row['id'] for r in rows)) for row in rows if row['rule'] != 'unknown-token'}
    (repo / BASELINE).write_text(json.dumps(baseline, indent=2) + '\n')

def read_baseline(repo, ref=None):
    if ref:
        try:
            raw = git(repo, 'show', f'{ref}:{BASELINE}')
        except subprocess.CalledProcessError:
            raise ValueError(f'{BASELINE} missing at {ref}; bootstrap the baseline before enabling CI')
    else:
        path = repo / BASELINE
        if not path.exists():
            return {'schema': 1, 'findings': {}, 'exceptions': {}}, False
        raw = path.read_text()
    data = json.loads(raw)
    if not isinstance(data, dict) or data.get('schema') != 1 or not isinstance(data.get('findings'), dict):
        raise ValueError('Invalid adoption baseline schema')
    if not isinstance(data.get('exceptions', {}), dict):
        raise ValueError('Invalid exception map')
    for key, item in data['findings'].items():
        if not isinstance(item, dict) or type(item.get('count')) is not int or item['count'] < 0:
            raise ValueError(f'Invalid count for {key}')
    for key, reason in data.get('exceptions', {}).items():
        if not isinstance(reason, str) or len(reason.strip()) < 12:
            raise ValueError(f'Exception {key} needs a specific written reason')
    return data, True


def report(repo, expected, ref=None, initialize=False, prune=False):
    baseline, exists = read_baseline(repo, ref)
    current, _ = read_baseline(repo)
    policy = current.get('policy', 1)
    if ref and policy < baseline.get('policy', 1):
        raise ValueError('Style policy cannot be downgraded')
    if policy not in (1, 2):
        raise ValueError('Unknown style policy')
    if ref and policy > baseline.get('policy', 1):
        # Only pre-existing source at the trusted base may receive migration allowances.
        historical = list(scan_styles(repo, policy, ref))
        baseline['findings'] = {row['id']: dict(row, count=sum(r['id'] == row['id'] for r in historical))
                                for row in historical if row['rule'] != 'unknown-token'}
    if ref:
        for key, item in current['findings'].items():
            if item['count'] > baseline['findings'].get(key, {}).get('count', 0):
                raise ValueError(f'Baseline allowance increased: {key}')
        if current.get('exceptions', {}) != baseline.get('exceptions', {}):
            raise ValueError('Exception changes require a separately approved policy change')
    rows = list(scan_styles(repo, policy))
    counts = Counter(row['id'] for row in rows)
    if initialize or prune:
        if initialize and exists:
            raise ValueError('Baseline already exists; initialization never overwrites it')
        if prune and not exists:
            raise ValueError('Cannot prune a missing baseline')
        grouped = {row['id']: {k: row[k] for k in ('file', 'rule', 'property', 'value')} for row in rows}
        baseline['findings'] = {
            key: dict(grouped[key], count=count if initialize else min(count, baseline['findings'][key]['count']))
            for key, count in sorted(counts.items()) if initialize or key in baseline['findings']}
        (repo / BASELINE).write_text(json.dumps(baseline, indent=2) + '\n')
        exists = True
    remaining = Counter({key: item['count'] for key, item in baseline['findings'].items()})
    for row in rows:
        key = row['id']
        row['status'] = ('new' if row['rule'] == 'unknown-token' else 'exception' if key in baseline.get('exceptions', {}) else
                         'existing' if remaining[key] > 0 else 'new')
        remaining[key] -= 1
    nested = sorted(repo.glob('*-src/package.json'))
    if len(nested) > 1:
        raise ValueError('Multiple frontend manifests; select an unambiguous consumer')
    package_root = nested[0].parent if nested else repo
    package = json.loads((package_root / 'package.json').read_text())
    pin = next((package.get(section, {}).get(PACKAGE) for section in
                ('dependencies', 'devDependencies', 'peerDependencies') if PACKAGE in package.get(section, {})), None)
    lockpath = package_root / 'package-lock.json'
    locked = None
    if lockpath.exists():
        lock = json.loads(lockpath.read_text())
        locked = lock.get('packages', {}).get('node_modules/' + PACKAGE, {}).get('version')
        locked = locked or lock.get('dependencies', {}).get(PACKAGE, {}).get('version')
    dependency_valid = bool(isinstance(pin, str) and EXACT_VERSION.fullmatch(pin) and pin == locked)
    return {'repo': repo.name, 'baseline': exists, 'pin': pin, 'locked': locked,
            'dependencyValid': dependency_valid,
            'expected': expected, 'versionStatus': 'not adopted' if not pin else
            'matches checkout' if pin == locked == expected else 'differs from checkout/lock',
            'files': len(list(source_files(repo, policy))), 'findings': rows + list(icon_findings(repo)),
            'resolved': sum(max(0, item['count'] - counts[key]) for key, item in baseline['findings'].items())}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--repo', action='append', help='Repository name under root; repeatable')
    parser.add_argument('--strict', action='store_true', help='Fail on new policy violations, missing baselines or invalid dependency pins')
    parser.add_argument('--json', action='store_true', help='Machine-readable report')
    parser.add_argument('--all', action='store_true', help='Show existing findings as well as new ones')
    parser.add_argument('--baseline-ref', help='Read baseline/exceptions from a trusted Git revision (CI PR base)')
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--upgrade-policy', action='store_true', help='Record existing committed debt and enable complete style gates')
    action.add_argument('--init-baseline', action='store_true', help='Create a baseline once; never replace one')
    action.add_argument('--prune-baseline', action='store_true', help='Remove resolved debt; never increase allowances')
    args = parser.parse_args(argv)
    if args.baseline_ref and (args.init_baseline or args.prune_baseline):
        parser.error('Cannot write a baseline while comparing to a revision')
    expected = json.loads((Path(__file__).resolve().parents[1] / 'package.json').read_text())['version']
    reports, errors = [], []
    for name in args.repo or REPOS:
        if Path(name).name != name:
            parser.error('--repo must be a repository name, not a path')
        repo = args.root / name
        if not repo.exists() and not args.repo:
            continue
        try:
            if args.upgrade_policy:
                upgrade_policy(repo)
            reports.append(report(repo, expected, args.baseline_ref, args.init_baseline, args.prune_baseline))
        except (OSError, ValueError, subprocess.CalledProcessError) as error:
            errors.append(f'{name}: {error}')
    if not reports and not errors:
        errors.append('No frontend repositories found')
    output = {'schema': 1, 'reports': reports, 'errors': errors}
    if args.json:
        print(json.dumps(output, indent=2))
    else:
        print('Design-token adoption (policy 2 gates embedded styles, utilities, spacing and geometry)')
        for result in reports:
            rows = result['findings']
            new = sum(r['status'] == 'new' and r['severity'] == 'gate' for r in rows)
            old = sum(r['status'] == 'existing' and r['severity'] == 'gate' for r in rows)
            advisory = sum(r['severity'] == 'advisory' for r in rows)
            print(f"{result['repo']}: {new} new / {old} existing gated; {advisory} advisory; {result['resolved']} resolved")
            print(f"  tokens: {result['pin'] or 'none'}; lock: {result['locked'] or 'none'}; {result['versionStatus']}")
            if not result['baseline']:
                print('  MISSING baseline; review findings before --init-baseline')
            if not result['dependencyValid']:
                print('  INVALID token dependency; use an exact version with a matching lockfile')
            for row in rows:
                if args.all or row['status'] == 'new':
                    print(f"  {row['file']}:{row['line']} [{row['status']}/{row['rule']}] {row['property']}: {row['value']} ({row['id']})")
        for error in errors:
            print(error, file=sys.stderr)
    return 2 if errors else int(args.strict and any(
        not r['baseline'] or not r['dependencyValid'] or any(f['status'] == 'new' and f['severity'] == 'gate' for f in r['findings']) for r in reports))


if __name__ == '__main__':
    sys.exit(main())
