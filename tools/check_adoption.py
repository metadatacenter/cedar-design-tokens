#!/usr/bin/env python3
"""Offline design-token adoption report. Python stdlib only; also used by cedarcli/CI."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from check_icons import scan as icon_findings
from style_sources import sources, style_properties
from check_spellcheck import findings as spellcheck_findings
from check_native_choices import findings as native_choice_findings
from check_surfaces import findings as surface_findings, sync as sync_surfaces, markdown as surface_markdown, load as load_surfaces

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
# CSS named colours, including aliases; transparent/currentColor are semantic, not palette values.
NAMED_COLORS = set('aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond blue blueviolet brown burlywood cadetblue chartreuse chocolate coral cornflowerblue cornsilk crimson cyan darkblue darkcyan darkgoldenrod darkgray darkgrey darkgreen darkkhaki darkmagenta darkolivegreen darkorange darkorchid darkred darksalmon darkseagreen darkslateblue darkslategray darkslategrey darkturquoise darkviolet deeppink deepskyblue dimgray dimgrey dodgerblue firebrick floralwhite forestgreen fuchsia gainsboro ghostwhite gold goldenrod gray grey green greenyellow honeydew hotpink indianred indigo ivory khaki lavender lavenderblush lawngreen lemonchiffon lightblue lightcoral lightcyan lightgoldenrodyellow lightgray lightgrey lightgreen lightpink lightsalmon lightseagreen lightskyblue lightslategray lightslategrey lightsteelblue lightyellow lime limegreen linen magenta maroon mediumaquamarine mediumblue mediumorchid mediumpurple mediumseagreen mediumslateblue mediumspringgreen mediumturquoise mediumvioletred midnightblue mintcream mistyrose moccasin navajowhite navy oldlace olive olivedrab orange orangered orchid palegoldenrod palegreen paleturquoise palevioletred papayawhip peachpuff peru pink plum powderblue purple rebeccapurple red rosybrown royalblue saddlebrown salmon sandybrown seagreen seashell sienna silver skyblue slateblue slategray slategrey snow springgreen steelblue tan teal thistle tomato turquoise violet wheat white whitesmoke yellow yellowgreen'.split())
NAMED_COLOR = re.compile(r'(?<![\w$@.-])(?:' + '|'.join(sorted(NAMED_COLORS)) + r')(?![\w-])', re.I)
DIMENSION = re.compile(r'(?<![\w.-])(?:\d*\.)?\d+(?:px|rem|em)\b')
# Policy 3 also reads a negative length, which policy 2 skipped: `margin-top: -48px` is a literal too.
SIGNED_DIMENSION = re.compile(r'(?<![\w.])-?(?:\d*\.)?\d+(?:px|rem|em)\b')
POLICIES = (1, 2, 3)
LATEST_POLICY = POLICIES[-1]
EXACT_VERSION = re.compile(r'\d+\.\d+\.\d+(?:-[\w.-]+)?(?:\+[\w.-]+)?')
TOKEN_LITERALS = dict(re.findall(r'^\$([\w-]+):\s*([^;]+);',
                                (Path(__file__).resolve().parents[1] / '_tokens.scss').read_text(), re.M))


def literal_typography(prop, value, policy=2):
    # Remove references, retaining var() fallbacks so literal defaults still gate.
    def compatibility(match):
        name, fallback = match.groups()
        canonical = TOKEN_LITERALS.get(name)
        return '' if canonical and ' '.join(fallback.split()) == ' '.join(canonical.split()) else match[0]
    value = re.sub(r'var\(\s*--cedar-([\w-]+)\s*,\s*([^()]+)\)', compatibility, value)
    inspected = re.sub(r'var\(\s*--[\w-]+\s*\)', '', value)
    inspected = re.sub(r'var\(\s*--[\w-]+\s*,', '(', inspected)
    inspected = re.sub(r'(?:[\w-]+\.)?\$[\w-]+|@[\w-]+', '', inspected)
    if re.search(r'(?<![\w.-])(?:\d*\.)?\d+(?:[a-z%]+)?' if policy < 3 else r'(?<![\w.])-?(?:\d*\.)?\d+(?:[a-z%]+)?', inspected, re.I):
        return True
    if prop in ('font-weight', 'font-size', 'font-stretch'):
        return bool(re.search(r'\b(?:bold|bolder|lighter|small|medium|large|larger|smaller|condensed|expanded)\b', inspected))
    if prop in ('font', 'font-family'):
        inspected = re.sub(r'!important|\b(?:inherit|initial|unset|revert|revert-layer|normal)\b', '', inspected)
        return bool(re.search(r'[a-zA-Z]', inspected))
    return False


def policy_3_rule(prop, value):
    """What policy 3 adds: focus outlines, single corners, opacity, easing, a z-index marked important
    and negative lengths, each of which has a token or is a geometry literal like the rest."""
    plain = re.sub(r'\s*!important$', '', value, flags=re.I).strip()
    if re.fullmatch(r'outline(?:-width|-offset)?|border-(?:top|bottom|start|end)-(?:left|right|start|end)-radius|height|min-height|border-radius|box-shadow|text-shadow', prop) and SIGNED_DIMENSION.search(value):
        return 'geometry'
    if prop == 'z-index' and re.fullmatch(r'-?\d+', plain):
        return 'geometry'
    # Fully hidden and fully shown are states, not values; anything between is the disabled token's job.
    if prop == 'opacity' and re.fullmatch(r'\d*\.?\d+%?', plain) and float(plain.rstrip('%')) not in (0, 1, 100):
        return 'geometry'
    # A constant rotation and a stepped animation carry no design value; a curve or keyword easing does.
    if re.fullmatch(r'(?:transition|animation)(?:-timing-function)?', prop) and re.search(r'\bcubic-bezier\s*\(|(?<![\w-])ease(?:-in|-out|-in-out)?(?![\w-])', plain):
        return 'motion'
    return None


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True)


def upstream_ref(repo):
    """The revision CI compares a push with: the upstream branch's head, once it holds a baseline."""
    def quiet(*args):
        return subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True)
    revision = quiet('rev-parse', '--verify', '--quiet', '@{upstream}')
    if revision.returncode or quiet('cat-file', '-e', f'{revision.stdout.strip()}:{BASELINE}').returncode:
        return None
    return revision.stdout.strip()


def source_files(repo, policy=1, ref=None):
    # Includes new local files but never ignored build products or dependencies.
    names = (git(repo, 'ls-tree', '-rz', '--name-only', ref) if ref else git(repo, 'ls-files', '-z', '--cached', '--others', '--exclude-standard')).split('\0')
    for name in sorted(set(names)):
        path = Path(name)
        parts = path.parts[1:] if path.parts and path.parts[0].endswith('-src') else path.parts
        if (parts and parts[0] in ('src', 'app')
                and (path.suffix in ('.scss', '.css', '.less') or
                     (policy >= 2 and path.suffix in ('.html', '.ts', '.js', '.mjs') and '.spec.' not in name
                      and (parts[0] == 'src' or json.loads((repo / 'package.json').read_text()).get('name') == 'cedar-template-designer')))
                and not EXCLUDED.intersection(path.parts)
                and not path.name.startswith('styles-Material-Icons')
                and (ref or (repo / path).is_file())):
            yield path


def findings(path, source, policy=1):
    # Preserve newlines so diagnostics retain original source locations.
    clean = COMMENT.sub(lambda m: re.sub(r'[^\n]', ' ', m[0]), source)
    clean = re.sub(r'#\{([^{}]*)\}', lambda m: '  ' + m[1] + ' ', clean)
    clean = re.sub(r'''(["'])(?:\\.|(?!\1).)*?\1''',
                   lambda m: re.sub(r'[;{}]', ' ', m[0]), clean)
    for match in DECL.finditer(clean):
        prop, value = match.groups()
        value = ' '.join(value.split())
        # Don't interpret text/URLs as color names (including embedded font payloads).
        inspected = re.sub(r'url\([^)]*\)|[\'"][^\'"]*[\'"]', '', value)
        rule = None
        if prop.lower() == 'resize' and re.sub(r'\s*!important$', '', value, flags=re.I).lower() != 'none':
            rule = 'manual-resize'
        elif prop == 'accent-color' and re.sub(r'\s*!important$', '', value, flags=re.I).strip().lower() in ('auto', 'initial', 'unset', 'revert', 'revert-layer'):
            rule = 'native-choice-reset'
        elif value == 'uninspectable-binding' and not prop.startswith('--'):
            rule = 'dynamic-style'
        elif prop == 'utility-style':
            rule = 'utility-style'
        elif COLOR.search(inspected) or NAMED_COLOR.search(inspected) or (policy >= 3 and re.search(r'\bcolor-mix\s*\(', inspected, re.I)):
            rule = 'color'
        elif prop in ('font', 'font-family', 'font-size', 'font-weight', 'font-stretch', 'line-height', 'letter-spacing'):
            if literal_typography(prop, value, policy):
                rule = 'typography'
        elif re.fullmatch(r'(?:margin|padding)(?:-[\w-]+)?|(?:row-|column-)?gap', prop):
            if (SIGNED_DIMENSION if policy >= 3 else DIMENSION).search(value):
                rule = 'spacing'
            elif re.search(r'\b(?:calc|min|max|clamp)\(|[*/+]|\s-\s', value):
                rule = 'spacing-expression'
            elif re.search(r'(?<![\w.-])(?:\d*\.)?\d+(?:(?:vh|vw|vmin|vmax|ch|ex|cqi|cqw|pt|cm|mm|in)\b|%)', value):
                rule = 'spacing'
        elif prop in ('transition', 'animation', 'transition-duration', 'animation-duration', 'transition-delay', 'animation-delay') and any(float(n) for n in re.findall(r'(?<![\w.-])(\d*\.?\d+)(?:ms|s)\b', value)):
            rule = 'geometry'
        elif prop in ('height', 'min-height', 'border-radius', 'box-shadow', 'text-shadow', 'z-index', 'transition-duration', 'animation-duration') and (DIMENSION.search(value) or (prop == 'z-index' and re.fullmatch(r'-?\d+', value))):
            rule = 'geometry'
        elif policy >= 3:
            rule = policy_3_rule(prop, value)
        if rule:
            identity = f'{path}|{rule}|{prop}|{value}'
            yield {'id': hashlib.sha256(identity.encode()).hexdigest()[:20],
                   'file': str(path), 'line': clean.count('\n', 0, match.start(1)) + 1,
                   'rule': rule, 'property': prop, 'value': value,
                   'severity': 'gate' if policy >= 2 or rule in ('color', 'typography', 'manual-resize', 'native-choice-reset') else 'advisory'}



PACKAGE_ROOT = Path(__file__).resolve().parents[1]
RETIRED = json.loads((Path(__file__).parent / 'retired-tokens.json').read_text())
HOSTS = {name.removeprefix('cedar-') for name in json.loads((Path(__file__).parent / 'host-properties.json').read_text())}



# The only host adapter allowed to redirect shared defaults. Names and owning file are exact.
CETP_BRIDGE = {shared: 'var(--cetp-' + host + ')' for shared, host in {
    'color-primary': 'color-primary', 'color-on-primary': 'color-on-primary',
    'text-title': 'color-heading', 'text-primary': 'color-text', 'text-muted': 'color-muted',
    'surface-subtle': 'color-surface', 'border-rule': 'color-border',
    'status-warning-text': 'color-warning', 'font-family': 'font-family',
    'font-size': 'font-size', 'font-size-small': 'font-size-small',
}.items()}

def token_names(text):
    source = COMMENT.sub('', text)
    return {name for name, value in re.findall(r'^\$([\w-]+):\s*(.)', source, re.M)
            if value != '(' and name != 'font-family-string'}


def shared_tokens():
    """Every scalar of the Sass module, which tokens.entry.scss emits under its own name."""
    return token_names((PACKAGE_ROOT / '_tokens.scss').read_text())


def known_css_properties():
    return shared_tokens() | HOSTS


def scan_styles(repo, policy=1, ref=None):
    # A nested frontend has no package.json at the root; asking a revision for one is expected to fail quietly.
    yield from native_choice_findings(lambda name: subprocess.check_output(['git', '-C', str(repo), 'show', f'{ref}:{name}'], text=True, stderr=subprocess.DEVNULL)
                                      if ref else (repo / name).read_text())
    known = known_css_properties()
    authored = []
    for path in source_files(repo, max(policy, 2), ref):
        source = git(repo, 'show', f'{ref}:{path}') if ref else (repo / path).read_text()
        authored.append((path, source, [re.sub(r'#\{([^{}]*)\}', lambda m: '  ' + m[1] + ' ', COMMENT.sub(lambda m: re.sub(r'[^\n]', ' ', m[0]), snippet))
                                       for snippet in sources(path, source, policy)]))
    # Local aliases remain valid: their declarations are inspected by the same
    # literal-value rules. Framework defaults are not implicit token contracts.
    local = {match[1] for _, _, snippets in authored for snippet in snippets
             for match in DECL.finditer(snippet) if match[1].startswith('--')}
    definitions = {}
    for path, _, snippets in authored:
        for snippet in snippets:
            for match in DECL.finditer(snippet):
                if match[1].startswith('--'):
                    definitions.setdefault(match[1], []).append((path, match[2], snippet[:match.start(1)].count('\n') + 1))
    checked_aliases = set()
    # Resolve local Sass aliases through their actual @use module, never by trusting
    # a namespace spelling such as "tokens". Ambiguous/missing modules fail closed.
    sass_sources = {str(path): source for path, source, _ in authored if path.suffix == '.scss'}
    sass_reference = re.compile(r'(?:(?P<module>[\w-]+)\.)?\$(?P<name>[\w-]+)')
    properties = style_properties(policy)

    def resolve_sass(path, value, visited=frozenset()):
        source = sass_sources.get(str(path), '')
        def resolve(match):
            module, name = match['module'], match['name']
            key = (str(path), module, name)
            if key in visited:
                return 'unresolved-sass-alias'
            owner = path
            if module:
                imports = re.findall(r"@use\s+['\"]([^'\"]+)['\"](?:\s+as\s+([\w-]+))?", source)
                target = next((target for target, alias in imports
                               if (alias or Path(target).name) == module), None)
                if target and target.startswith(PACKAGE + '/'):
                    return match[0]
                candidates = [p for p in sass_sources if target and
                              (Path(p).stem.lstrip('_') == Path(target).name.lstrip('_') or
                               str(Path(p).with_suffix('')).endswith(target))]
                if len(candidates) != 1:
                    return 'unresolved-sass-alias'
                owner = Path(candidates[0])
            definition = re.findall(r'(?:^|[;{}])\s*\$' + re.escape(name) + r'\s*:\s*([^;]+);',
                                   sass_sources.get(str(owner), ''), re.M)
            return resolve_sass(owner, definition[0], visited | {key}) if len(definition) == 1 else 'unresolved-sass-alias'
        return sass_reference.sub(resolve, value)


    def inspect_alias(name, prop, visited):
        if name in visited:
            return
        for path, value, line in definitions.get(name, []):
            key = (str(path), name, prop, value)
            if key in checked_aliases:
                continue
            checked_aliases.add(key)
            # Literal colors are already checked at their declaration. Inspect
            # numeric aliases in the context of the property consuming them.
            if not list(findings(path, f'{{{name}:{value};}}', policy)):
                expanded = resolve_sass(path, value)
                if 'unresolved-sass-alias' in expanded:
                    yield {'id': hashlib.sha256(f'{path}|sass-alias|{prop}|{value}'.encode()).hexdigest()[:20],
                           'file': str(path), 'line': line, 'rule': 'sass-alias',
                           'property': prop, 'value': value, 'severity': 'gate'}
                for row in findings(path, f'{{{prop}:{expanded};}}', policy):
                    row['line'] = line
                    yield row
            for reference in re.findall(r'var\(\s*(--[\w-]+)', value):
                yield from inspect_alias(reference, prop, visited | {name})

    for path, source, snippets in authored:
        yield from spellcheck_findings(path, source)
        if policy < 2 and path.suffix in ('.html', '.ts', '.js', '.mjs'):
            continue
        for snippet in snippets:
            yield from findings(path, snippet, policy)
            if policy < 2:
                continue
            for declaration in DECL.finditer(snippet):
                prop, value = declaration.groups()
                if re.fullmatch(properties, prop) and sass_reference.search(value):
                    expanded = resolve_sass(path, value)
                    if expanded != value and not list(findings(path, '{' + prop + ':' + value + ';}', policy)):
                        for row in findings(path, '{' + prop + ':' + expanded + ';}', policy):
                            row['line'] = snippet[:declaration.start(1)].count('\n') + 1
                            yield row
                        if 'unresolved-sass-alias' in expanded:
                            yield {'id': hashlib.sha256(f'{path}|sass-alias|{prop}|{value}'.encode()).hexdigest()[:20],
                                   'file': str(path), 'line': snippet[:declaration.start(1)].count('\n') + 1,
                                   'rule': 'sass-alias', 'property': prop, 'value': value, 'severity': 'gate'}
                if not (prop.startswith('--') or re.fullmatch(properties, prop)):
                    continue
                for match in re.finditer(r'var\(\s*(--[\w-]+)', value):
                    name = match[1]
                    if name in local and not prop.startswith('--'):
                        yield from inspect_alias(name, prop, set())
                    if name.startswith('--cedar-') or name in local:
                        continue
                    yield {'id': hashlib.sha256(f'{path}|unknown-variable|{name}'.encode()).hexdigest()[:20],
                           'file': str(path), 'line': snippet[:declaration.start(1)].count('\n') + 1,
                           'rule': 'unknown-variable', 'property': prop, 'value': name, 'severity': 'gate'}
        if policy >= 2:
            clean = COMMENT.sub(lambda m: re.sub(r'[^\n]', ' ', m[0]), source)
            for match in re.finditer(r'var\(\s*--cedar-([\w-]+)', clean):
                if match[1] not in known:
                    value = '--cedar-' + match[1]
                    row = {'id': hashlib.sha256(f'{path}|unknown-token|{value}'.encode()).hexdigest()[:20],
                           'file': str(path), 'line': clean[:match.start()].count('\n') + 1,
                           'rule': 'unknown-token', 'property': 'var', 'value': value, 'severity': 'gate'}
                    if match[1] in RETIRED:
                        row['replacement'] = RETIRED[match[1]]
                    yield row
            # A consumer must not give a shared token a local value: no other surface can see it.
            shared = shared_tokens()
            for exported, module in re.findall(r"@use\s+['\"]" + re.escape(PACKAGE) + r"/([\w-]+)['\"](?:\s+as\s+([\w-]+))?", clean):
                alias = module or exported
                for assignment in re.finditer(re.escape(alias) + r'\.\$([\w-]+)\s*:', clean):
                    value = alias + '.$' + assignment[1]
                    yield {'id': hashlib.sha256(f'{path}|token-override|{value}'.encode()).hexdigest()[:20],
                           'file': str(path), 'line': clean[:assignment.start()].count('\n') + 1,
                           'rule': 'token-override', 'property': value, 'value': value, 'severity': 'gate'}
            for match in re.finditer(r'(?<![\w-])--cedar-([\w-]+)\s*:\s*([^;{}]*)', '\n'.join(snippets)):
                # A component may re-point a shared role to its own documented host property, as the
                # term picker does with `--cetp-*`, so shared recipes follow what an embedder sets.
                if (str(path) == 'src/app/cedar-embeddable-term-picker.scss'
                        and json.loads((repo / 'package.json').read_text()).get('name') == 'cedar-embeddable-term-picker'
                        and CETP_BRIDGE.get(match[1]) == match[2].strip()):
                    continue
                if match[1] in shared or match[1] in RETIRED:
                    value = '--cedar-' + match[1]
                    yield {'id': hashlib.sha256(f'{path}|token-override|{value}'.encode()).hexdigest()[:20],
                           'file': str(path), 'line': clean[:match.start()].count('\n') + 1,
                           'rule': 'token-override', 'property': value, 'value': value, 'severity': 'gate'}


def unused_tokens(root):
    """Shared tokens that no consumer and no package recipe references; None unless every consumer is checked out."""
    if not all((root / name).exists() for name in REPOS):
        return None
    texts = [path.read_text() for path in PACKAGE_ROOT.glob('*.scss')
             if path.name not in ('_tokens.scss', 'tokens.entry.scss')]
    for name in REPOS:
        repo = root / name
        texts.extend((repo / path).read_text() for path in source_files(repo, 2))
    used = set()
    for text in texts:
        used.update(re.findall(r'--cedar-([\w-]+)', text))
        used.update(re.findall(r'\b[\w-]+\.\$([\w-]+)', text))
    return sorted(shared_tokens() - used)


def upgrade_policy(repo):
    """Move a baseline to the next policy, recording only debt already committed at HEAD, never working edits."""
    baseline, exists = read_baseline(repo)
    if not exists or baseline.get('policy', 1) >= LATEST_POLICY:
        raise ValueError(f'Upgrade requires an existing baseline below policy {LATEST_POLICY}')
    if git(repo, 'status', '--porcelain').strip():
        raise ValueError('Commit or isolate changes before upgrading the style policy')
    target = baseline.get('policy', 1) + 1
    rows = list(scan_styles(repo, target))
    baseline['policy'] = target
    # Sorted like an initialized or pruned baseline, so a move between policies diffs as additions.
    baseline['findings'] = {row['id']: dict({k: row[k] for k in ('file', 'rule', 'property', 'value')},
                                         count=sum(r['id'] == row['id'] for r in rows))
                            for row in sorted(rows, key=lambda r: r['id']) if row['rule'] != 'unknown-token'}
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


def published_version():
    """The development version the token checkout's head publishes under, as `cedarcli publish
    components` names it: the carried base, the UTC date of the head commit and its first eight
    digits. A checkout that is not a Git repository is named by its package.json alone."""
    carried = json.loads((PACKAGE_ROOT / 'package.json').read_text())['version']
    base = re.match(r'\d+\.\d+\.\d+', carried)
    try:
        head = subprocess.run(['git', '-C', str(PACKAGE_ROOT), 'rev-parse', '--short=8', '--verify', 'HEAD'],
                              capture_output=True, text=True, check=True).stdout.strip()
        date = subprocess.run(['git', '-C', str(PACKAGE_ROOT), 'show', '-s', '--format=%cd', '--date=format:%Y%m%d', 'HEAD'],
                              capture_output=True, text=True, check=True, env={'TZ': 'UTC', 'PATH': os.environ.get('PATH', '')}).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return carried
    return f'{base[0]}-dev.{date}.{head}' if base else carried


# A development version names the commit it was built from: `-dev.<date>.<sha>` from a repository's
# own publishing, `-dev.<timestamp>.g<sha>[.t<n>]` from a train.
PIN_COMMIT = re.compile(r'-dev\.\d{8,14}\.g?([0-9a-f]{7,40})(?:\.t\d+)?$')


def pinned_tokens(pin):
    """The commit a pin names and the shared tokens the package held there; (None, None) when the
    version names no commit, (commit, None) when this checkout does not have it."""
    match = PIN_COMMIT.search(pin or '')
    if not match:
        return None, None
    found = subprocess.run(['git', '-C', str(PACKAGE_ROOT), 'show', f'{match[1]}:_tokens.scss'],
                           capture_output=True, text=True)
    if found.returncode:
        return match[1], None
    return match[1], token_names(found.stdout)


def report(repo, expected, ref=None, initialize=False, prune=False):
    baseline, exists = read_baseline(repo, ref)
    current, _ = read_baseline(repo)
    policy = current.get('policy', 1)
    if ref and policy < baseline.get('policy', 1):
        raise ValueError('Style policy cannot be downgraded')
    if policy not in POLICIES:
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
            raise ValueError('Feature changes cannot add or alter style exceptions; use shared semantic roles')
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
        row['status'] = ('new' if row['rule'] in ('sass-alias', 'spacing-expression', 'unknown-token', 'token-override', 'unknown-variable', 'manual-resize', 'spellcheck', 'native-choice-coverage', 'native-choice-reset') else 'exception' if key in baseline.get('exceptions', {}) and remaining[key] > 0 else
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
    # A pinned package that lacks a token this repository reads leaves a custom property unset, which
    # no build reports: the declaration silently falls back.
    pin_commit, pinned = pinned_tokens(pin)
    used = set()
    for path in source_files(repo, max(policy, 2)):
        text = COMMENT.sub('', (repo / path).read_text())
        used.update(re.findall(r'var\(\s*--cedar-([\w-]+)', text))
        used.update(re.findall(r'\btokens\.\$([\w-]+)', text))
    missing = sorted((used & shared_tokens()) - pinned) if pinned is not None else []
    if not pin:
        version_status = 'not adopted'
    elif pin != locked:
        version_status = 'differs from lock'
    elif pin == expected:
        version_status = 'matches checkout'
    elif pin_commit and pinned is None:
        version_status = f'names commit {pin_commit}, which the token checkout does not have; fetch it'
    elif pin_commit:
        behind = subprocess.run(['git', '-C', str(PACKAGE_ROOT), 'rev-list', '--count', f'{pin_commit}..HEAD'],
                                capture_output=True, text=True).stdout.strip()
        version_status = f'{behind} token commits behind checkout' if behind not in ('', '0') else 'differs from checkout'
    else:
        version_status = 'names no commit'
    # The working tree's own baseline may not keep allowances its code no longer needs, or a later
    # change could reintroduce the literal under them.
    stale = sum(max(0, item['count'] - counts[key]) for key, item in current['findings'].items()) if not (initialize or prune) else 0
    surface_registry = load_surfaces(repo) if (repo / '.ui-surfaces.json').exists() else None
    surface_counts = {'registered': len(surface_registry['surfaces']),
                      'contracts': sum(bool(s.get('contract')) for s in surface_registry['surfaces']),
                      'debt': sum(len(s.get('debt', {})) for s in surface_registry['surfaces'])} if surface_registry else None
    return {'surfaces': surface_counts, 'repo': repo.name, 'policy': policy, 'base': ref, 'baseline': exists, 'pin': pin, 'locked': locked,
            'dependencyValid': dependency_valid,
            'expected': expected, 'versionStatus': version_status, 'pinCommit': pin_commit,
            'pinMissingTokens': missing, 'pinUnknown': bool(pin_commit and pinned is None), 'staleAllowances': stale,
            'files': len(list(source_files(repo, policy))), 'findings': rows + list(icon_findings(repo)) + list(surface_findings(repo, ref)),
            'resolved': sum(max(0, item['count'] - counts[key]) for key, item in baseline['findings'].items())}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--repo', action='append', help='Repository name under root; repeatable')
    parser.add_argument('--sync-surfaces', action='store_true', help='Refresh generated browser contracts from the central implementation')
    parser.add_argument('--surface-inventory', type=Path, help='Generate the maintained Markdown surface hierarchy (requires all registered repositories)')
    parser.add_argument('--strict', action='store_true', help='Fail on new policy violations, missing baselines or invalid dependency pins')
    parser.add_argument('--json', action='store_true', help='Machine-readable report')
    parser.add_argument('--all', action='store_true', help='Show existing findings as well as new ones')
    parser.add_argument('--baseline-ref', help='Read baseline/exceptions from a trusted Git revision (CI PR base); defaults to the upstream branch')
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--upgrade-policy', action='store_true', help='Record existing committed debt and enable complete style gates')
    action.add_argument('--init-baseline', action='store_true', help='Create a baseline once; never replace one')
    action.add_argument('--prune-baseline', action='store_true', help='Remove resolved debt; never increase allowances')
    args = parser.parse_args(argv)
    if args.baseline_ref and (args.init_baseline or args.prune_baseline):
        parser.error('Cannot write a baseline while comparing to a revision')
    expected = published_version()
    reports, errors = [], []
    for name in args.repo or REPOS:
        if Path(name).name != name:
            parser.error('--repo must be a repository name, not a path')
        repo = args.root / name
        if not repo.exists() and not args.repo:
            continue
        try:
            if args.sync_surfaces:
                sync_surfaces(repo)
            if args.upgrade_policy:
                upgrade_policy(repo)
            # A run that writes a baseline reads the working tree; any other run compares with the
            # revision CI would, so a refusal CI would give a push appears before the push.
            ref = args.baseline_ref
            if ref is None and not (args.upgrade_policy or args.init_baseline or args.prune_baseline):
                ref = upstream_ref(repo)
            reports.append(report(repo, expected, ref, args.init_baseline, args.prune_baseline))
        except (OSError, ValueError, subprocess.CalledProcessError) as error:
            errors.append(f'{name}: {error}')
    if not reports and not errors:
        errors.append('No frontend repositories found')
    if args.surface_inventory:
        try:
            inventory = surface_markdown(args.root)
            args.surface_inventory.write_text(inventory)
        except (OSError, ValueError, KeyError) as error:
            errors.append(f'Surface inventory: {error}')
    unused = unused_tokens(args.root) if not args.repo else None
    output = {'schema': 1, 'reports': reports, 'errors': errors, 'unusedTokens': unused}
    if args.json:
        print(json.dumps(output, indent=2))
    else:
        print('Design-token adoption (policy 2 gates embedded styles, utilities, spacing and geometry; policy 3 adds outlines, opacity, easing and negative lengths)')
        for result in reports:
            rows = result['findings']
            new = sum(r['status'] == 'new' and r['severity'] == 'gate' for r in rows)
            old = sum(r['status'] == 'existing' and r['severity'] == 'gate' for r in rows)
            advisory = sum(r['severity'] == 'advisory' for r in rows)
            print(f"{result['repo']} (policy {result['policy']}): {new} new / {old} existing gated; {advisory} advisory; {result['resolved']} resolved")
            print(f"  tokens: {result['pin'] or 'none'}; lock: {result['locked'] or 'none'}; {result['versionStatus']}")
            if result['base']:
                print(f"  compared with {result['base'][:12]}")
            if result.get('surfaces'):
                coverage = result['surfaces']
                print(f"  surfaces: {coverage['registered']} inventory entries / {coverage['contracts']} rendered contracts / {coverage['debt']} existing differences; browser execution is a separate gate")
            if not result['baseline']:
                print('  MISSING baseline; review findings before --init-baseline')
            if not result['dependencyValid']:
                print('  INVALID token dependency; use an exact version with a matching lockfile')
            if result['pinMissingTokens']:
                print(f"  PINNED package lacks {', '.join('--cedar-' + t for t in result['pinMissingTokens'])}; advance the pin")
            if result['staleAllowances']:
                print(f"  {result['staleAllowances']} baseline allowances are no longer needed; run --prune-baseline")
            for row in rows:
                if args.all or row['status'] == 'new':
                    hint = f"; use {row['replacement']}" if row.get('replacement') else ''
                    print(f"  {row['file']}:{row['line']} [{row['status']}/{row['rule']}] {row['property']}: {row['value']} ({row['id']}){hint}")
        if unused:
            print(f"Unused shared tokens ({len(unused)}): {', '.join(unused)}; adopt or remove them")
        for error in errors:
            print(error, file=sys.stderr)
    return 2 if errors else int(args.strict and (bool(unused) or any(
        not r['baseline'] or not r['dependencyValid'] or r['pinMissingTokens'] or r['pinUnknown'] or r['staleAllowances']
        or any(f['status'] == 'new' and f['severity'] == 'gate' for f in r['findings']) for r in reports)))


if __name__ == '__main__':
    sys.exit(main())
