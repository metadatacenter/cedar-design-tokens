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

PACKAGE = '@org.metadatacenter/cedar-design-tokens'
BASELINE = '.design-tokens-baseline.json'
REPOS = ('cedar-embeddable-editor', 'cedar-embeddable-designer',
         'cedar-embeddable-term-picker')
EXCLUDED = {'node_modules', 'bower_components', 'vendor', 'dist', 'dist-bundle',
            'assets', 'fixtures', '__tests__'}
COMMENT = re.compile(r'/\*.*?\*/|(?m:^[ \t]*//[^\n]*)', re.S)
DECL = re.compile(r'(?:^|[;{}])\s*([\w$-]+)\s*:\s*([^;{}]+)', re.M)
COLOR = re.compile(r'#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?|oklch|color)\s*\(|(?<![\w$@.-])(?:white|black|red|blue|gray|grey|orange|yellow|green|teal|purple|pink|hotpink)(?![\w-])', re.I)
DIMENSION = re.compile(r'(?<![\w.-])(?:\d*\.)?\d+(?:px|rem|em)\b')


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True)


def source_files(repo):
    # Includes new local files but never ignored build products or dependencies.
    names = git(repo, 'ls-files', '-z', '--cached', '--others', '--exclude-standard').split('\0')
    for name in sorted(set(names)):
        path = Path(name)
        if (path.parts and path.parts[0] in ('src', 'app')
                and path.suffix in ('.scss', '.css', '.less')
                and not EXCLUDED.intersection(path.parts)
                and not path.name.startswith('styles-Material-Icons')
                and (repo / path).is_file()):
            yield path


def findings(path, source):
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
        if COLOR.search(inspected):
            rule = 'color'
        elif prop in ('font', 'font-family', 'font-size', 'font-weight', 'line-height', 'letter-spacing'):
            if DIMENSION.search(value) or re.fullmatch(r'\d+(?:\.\d+)?(?:\s*!important)?', value):
                rule = 'typography'
            elif prop == 'font-family' and not re.search(r'var\(|\$|@|^(inherit|initial|unset)$', value):
                rule = 'typography'
        elif re.fullmatch(r'(?:margin|padding)(?:-[\w-]+)?|(?:row-|column-)?gap', prop):
            if DIMENSION.search(value):
                rule = 'spacing'
        elif prop in ('height', 'min-height', 'border-radius') and DIMENSION.search(value):
            rule = 'geometry'
        if rule:
            identity = f'{path}|{rule}|{prop}|{value}'
            yield {'id': hashlib.sha256(identity.encode()).hexdigest()[:20],
                   'file': str(path), 'line': clean.count('\n', 0, match.start(1)) + 1,
                   'rule': rule, 'property': prop, 'value': value,
                   'severity': 'gate' if rule in ('color', 'typography') else 'advisory'}


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
    rows = [row for path in source_files(repo) for row in findings(path, (repo / path).read_text())]
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
        row['status'] = ('exception' if key in baseline.get('exceptions', {}) else
                         'existing' if remaining[key] > 0 else 'new')
        remaining[key] -= 1
    package = json.loads((repo / 'package.json').read_text())
    pin = next((package.get(section, {}).get(PACKAGE) for section in
                ('dependencies', 'devDependencies', 'peerDependencies') if PACKAGE in package.get(section, {})), None)
    lockpath = repo / 'package-lock.json'
    locked = None
    if lockpath.exists():
        lock = json.loads(lockpath.read_text())
        locked = lock.get('packages', {}).get('node_modules/' + PACKAGE, {}).get('version')
        locked = locked or lock.get('dependencies', {}).get(PACKAGE, {}).get('version')
    return {'repo': repo.name, 'baseline': exists, 'pin': pin, 'locked': locked,
            'expected': expected, 'versionStatus': 'not adopted' if not pin else
            'matches checkout' if pin == locked == expected else 'differs from checkout/lock',
            'files': len(list(source_files(repo))), 'findings': rows,
            'resolved': sum(max(0, item['count'] - counts[key]) for key, item in baseline['findings'].items())}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--repo', action='append', help='Repository name under root; repeatable')
    parser.add_argument('--strict', action='store_true', help='Fail on new color/typography findings or missing baselines')
    parser.add_argument('--json', action='store_true', help='Machine-readable report')
    parser.add_argument('--all', action='store_true', help='Show existing findings as well as new ones')
    parser.add_argument('--baseline-ref', help='Read baseline/exceptions from a trusted Git revision (CI PR base)')
    action = parser.add_mutually_exclusive_group()
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
            reports.append(report(repo, expected, args.baseline_ref, args.init_baseline, args.prune_baseline))
        except (OSError, ValueError, subprocess.CalledProcessError) as error:
            errors.append(f'{name}: {error}')
    if not reports and not errors:
        errors.append('No frontend repositories found')
    output = {'schema': 1, 'reports': reports, 'errors': errors}
    if args.json:
        print(json.dumps(output, indent=2))
    else:
        print('Design-token adoption (source heuristics; spacing/geometry are advisory)')
        for result in reports:
            rows = result['findings']
            new = sum(r['status'] == 'new' and r['severity'] == 'gate' for r in rows)
            old = sum(r['status'] == 'existing' and r['severity'] == 'gate' for r in rows)
            advisory = sum(r['severity'] == 'advisory' for r in rows)
            print(f"{result['repo']}: {new} new / {old} existing gated; {advisory} advisory; {result['resolved']} resolved")
            print(f"  tokens: {result['pin'] or 'none'}; lock: {result['locked'] or 'none'}; {result['versionStatus']}")
            if not result['baseline']:
                print('  MISSING baseline; review findings before --init-baseline')
            for row in rows:
                if args.all or row['status'] == 'new':
                    print(f"  {row['file']}:{row['line']} [{row['status']}/{row['rule']}] {row['property']}: {row['value']} ({row['id']})")
        for error in errors:
            print(error, file=sys.stderr)
    return 2 if errors else int(args.strict and any(
        not r['baseline'] or any(f['status'] == 'new' and f['severity'] == 'gate' for f in r['findings']) for r in reports))


if __name__ == '__main__':
    sys.exit(main())
