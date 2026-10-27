"""Every CEDAR application and component draws the shared focus ring at each of its roots.

A browser draws its own ring on any focused element that no stylesheet styles, and Chrome on macOS
paints it in the system accent blue. `controls.focus-states`, or the compiled `focus.css`, replaces
it. A stylesheet reaches only the document or shadow tree that loads it, so a component that renders
into its own shadow root includes the recipe there, and an application includes it in a global
build stylesheet. A component whose shadow root takes a stylesheet from a host directive, rather than
from its own `styleUrls`, counts that stylesheet as its own: the directive names it with a
`@stylesheet` tag, relative to the directive's file. This is a static contract; the rendered surface
walk reports any browser ring that remains.
"""
import hashlib
import json
import posixpath
import re

PACKAGE = '@org.metadatacenter/cedar-design-tokens'
# The applications and components that share the tokens' focus ring. The legacy Template Editor
# keeps Bootstrap's own.
CONSUMERS = ('cedar-workspace', 'cedar-embeddable-designer', 'cedar-embeddable-editor', 'cedar-template-designer',
             'cedar-openview', 'cedar-embeddable-term-picker', 'cedar-monitoring', 'cedar-bridging')
# A consumer that is neither an Angular application nor a shadow-rooted component names its root.
STATIC_ROOTS = {'cedar-template-designer': ('app/styles/host.css',)}
# A consumer without npm vendors the compiled stylesheets beside this manifest, and each page that
# links them is a root of its own.
VENDORED = re.compile(r'(?:[^/]+/)*vendor/cedar-design-tokens/manifest\.json')
LINK = re.compile(r'<link\b[^>]*\bhref\s*=\s*["\']([^"\']+)["\']', re.I)
HTML_COMMENT = re.compile(r'<!--.*?-->', re.S)
COMMENT = re.compile(r'/\*.*?\*/|(?m:^[ \t]*//[^\n]*)', re.S)
SHADOW = re.compile(r'encapsulation\s*:\s*ViewEncapsulation\.ShadowDom')
STYLE_URLS = re.compile(r'styleUrls?\s*:\s*(\[[^\]]*\]|[\'"][^\'"]+[\'"])')
QUOTED = re.compile(r'[\'"]([^\'"]+)[\'"]')
HOST_DIRECTIVES = re.compile(r'hostDirectives\s*:\s*\[([^\]]*)\]')
DIRECTIVE = re.compile(r'(?:directive\s*:\s*)?\b([A-Z]\w*)\b')
NAMED_IMPORT = re.compile(r'import\s*\{([^}]*)\}\s*from\s*[\'"](\.[^\'"]+)[\'"]')
STYLESHEET_TAG = re.compile(r'@stylesheet\s+(\S+)')
LOADS = re.compile(r'@(use|forward|import)\s+[\'"]([^\'"]+)[\'"](?:\s+as\s+([\w-]+))?')


def top_level(source, start):
    prefix = source[:start]
    return prefix.count('{') == prefix.count('}')


def resolve(target, directory, names, base):
    """A local Sass or CSS module, relative to its user or to the source root the build searches."""
    for root in (directory, posixpath.join(base, 'src')):
        stem = posixpath.normpath(posixpath.join(root, target))
        head, tail = posixpath.split(stem)
        for candidate in (stem, f'{stem}.scss', posixpath.join(head, f'_{tail}.scss'), f'{stem}.css',
                          posixpath.join(stem, '_index.scss'), posixpath.join(stem, 'index.scss')):
            if candidate in names:
                return candidate
    return None


def includes(path, read, names, base, seen=frozenset()):
    """True when the stylesheet emits the recipe at its top level, directly or through a local module."""
    if path in seen or path not in names:
        return False
    source = COMMENT.sub('', read(path))
    controls = set()
    for match in LOADS.finditer(source):
        if not top_level(source, match.start()):
            continue
        kind, target, alias = match.groups()
        if target.endswith('focus.css') and kind == 'import' and (
                target == f'{PACKAGE}/focus.css' or not target.startswith('@')):
            return True
        if kind == 'use' and target == f'{PACKAGE}/controls':
            controls.add(alias or 'controls')
        elif not target.startswith(('@', 'sass:', '~', 'http')) and kind in ('use', 'forward', 'import'):
            local = resolve(target, posixpath.dirname(path), names, base)
            if local and includes(local, read, names, base, seen | {path}):
                return True
    return any(top_level(source, match.start()) and match[1] in controls
               for match in re.finditer(r'@include\s+([\w-]+)\.focus-states\b', source))


def inserted(source, component, read, names):
    """The stylesheets a component's host directives insert into its shadow root, each named by a tag."""
    imports = {name.strip().split(' as ')[-1].strip(): target for group, target in NAMED_IMPORT.findall(source)
               for name in group.split(',') if name.strip()}
    sheets = []
    for group in HOST_DIRECTIVES.findall(source):
        for name in DIRECTIVE.findall(group):
            if name not in imports:
                continue
            directive = posixpath.normpath(posixpath.join(posixpath.dirname(component), imports[name])) + '.ts'
            if directive in names:
                sheets += [posixpath.normpath(posixpath.join(posixpath.dirname(directive), sheet))
                           for sheet in STYLESHEET_TAG.findall(read(directive))]
    return sheets


def roots(read, names, base):
    """Each root is a list of stylesheets, any one of which may carry the recipe."""
    shadowed = []
    for name in sorted(names):
        if name.startswith(posixpath.join(base, 'src/')) and name.endswith('.ts') and '.spec.' not in name:
            source = read(name)
            if SHADOW.search(source):
                urls = [url for group in STYLE_URLS.findall(source) for url in QUOTED.findall(group)]
                sheets = [posixpath.normpath(posixpath.join(posixpath.dirname(name), url)) for url in urls]
                shadowed.append((name, sheets + inserted(source, name, read, names),
                                 'This component renders into its own shadow root, so one of its stylesheets must include controls.focus-states.'))
    # A shadow-rooted component's global styles belong to its demonstration page, not to the component.
    if shadowed:
        return shadowed
    workspace = posixpath.join(base, 'angular.json')
    projects = json.loads(read(workspace)).get('projects', {}) if workspace in names else {}
    applications = []
    for project, definition in projects.items():
        options = definition.get('architect', {}).get('build', {}).get('options', {})
        styles = [entry if isinstance(entry, str) else entry.get('input') if entry.get('inject', True) else None
                  for entry in options.get('styles', [])]
        applications.append((posixpath.join(base, 'angular.json'),
                             [posixpath.join(base, style) for style in styles if style],
                             f'A global build stylesheet of {project} must include controls.focus-states or import the shared focus.css.'))
    return applications


def vendored_errors(read, names):
    """Every page that links the vendored stylesheets links the vendored focus.css as well."""
    manifest = next((name for name in sorted(names) if VENDORED.fullmatch(name)), None)
    if not manifest:
        return []
    copy = posixpath.dirname(manifest)
    pages = []
    for name in sorted(names):
        if name.endswith('.html'):
            links = [href.split('?')[0] for href in LINK.findall(HTML_COMMENT.sub('', read(name)))]
            if any('/cedar-design-tokens/' in href for href in links):
                pages.append((name, links))
    if not pages:
        return [(manifest, 'No page links the vendored token stylesheets, so none carries the shared focus ring.')]
    errors = [(page, f'{page} links the vendored token stylesheets, so it must link the vendored focus.css as well.')
              for page, links in pages if not any(href.endswith('/cedar-design-tokens/focus.css') for href in links)]
    if posixpath.join(copy, 'focus.css') not in names:
        errors.append((manifest, 'The vendored copy must include focus.css, which every page that links it loads.'))
    return errors


def findings(read, names):
    names = set(names)
    manifest = next((name for name in sorted(names) if name == 'package.json' or re.fullmatch(r'[^/]+-src/package\.json', name)), None)
    if manifest:
        package = json.loads(read(manifest)).get('name')
        if package not in CONSUMERS:
            return
        base = posixpath.dirname(manifest)
        groups = roots(read, names, base) or [
            (path, [path], f'{path} must import the shared focus.css.') for path in STATIC_ROOTS.get(package, ())]
        errors = [(path, message) for path, styles, message in groups
                  if not any(includes(style, read, names, base) for style in styles)]
        if not groups:
            errors.append((manifest, 'No root stylesheet was found to carry the shared focus ring.'))
    else:
        errors = vendored_errors(read, names)
    for path, message in errors:
        yield {'id': hashlib.sha256(f'{path}|focus-coverage|{message}'.encode()).hexdigest()[:20],
               'file': path, 'line': 1, 'rule': 'focus-coverage',
               'property': 'focus ring', 'value': message, 'severity': 'gate'}
