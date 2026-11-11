"""A component's recorded accessibility exceptions may shrink, never grow.

Each component's accessibility and layout suites fail on anything they measure, unless the finding
is recorded as an exception: an entry in a list such as `EXCEPTIONS`, `PENDING` or
`KNOWN_VIOLATIONS`, an axe rule switched off, or a template accessibility lint rule disabled on a
line. An exception keeps a suite green while the failure stays on the page, so a change that adds
one passes every gate it was meant to face. This check compares the exceptions a repository records
with those at a trusted revision, the one the adoption check compares with, and reports each one the
revision does not have. Removing an exception, or fixing what it covered, always passes.

The check reads source text and does not run a suite. It recognises an exception list by its
declared name, so a list that takes another name is outside it.
"""
from collections import Counter
from pathlib import Path, PurePosixPath
import re
import subprocess

EXCLUDED = {'node_modules', 'bower_components', 'vendor', 'dist', 'dist-bundle', 'dist-npm', 'test-results',
            'test-results-container', 'playwright-report', 'coverage', '.angular'}
# The browser suites' sources: whatever sits under a `tests` directory, such as browser/tests or
# visual/tests. Unit specs beside the source are not where a page's findings are excused.
TEST_SOURCE = re.compile(r'(?:^|/)tests/[^\n]*\.(?:ts|mts|js|mjs)$')
# Application sources whose templates the accessibility lint rules read.
APP_SOURCE = re.compile(r'^(?:[\w.-]+-src/)?(?:src|app)/[^\n]*\.(?:html|ts)$')
# A declared list of findings a suite lets pass. A region declared to scroll in place is not one:
# the shared layout checker accepts it only when it holds a table, which is the two-dimensional
# content WCAG 1.4.10 lets scroll, so the checker rather than this count holds it to that.
LIST = re.compile(r'^\s*(?:export\s+)?(?:const|let|var)\s+'
                  r'([A-Za-z_]*(?:EXCEPTIONS?|Exceptions?|exceptions?|PENDING|KNOWN_VIOLATIONS|WAIVERS?)'
                  r'[A-Za-z_]*)\b[^=\n]*=\s*\[', re.M)
# Switching an axe rule off, by name or through its options.
AXE_OFF = re.compile(r'\.disableRules\s*\(|\benabled\s*:\s*false\b')
# The template rules angular-eslint groups as accessibility rules.
A11Y_RULES = ('alt-text', 'button-has-type', 'click-events-have-key-events', 'elements-content',
              'interactive-supports-focus', 'label-has-associated-control', 'mouse-events-have-key-events',
              'no-autofocus', 'no-distracting-elements', 'no-positive-tabindex', 'role-has-required-aria',
              'table-scope', 'valid-aria')
LINT_OFF = re.compile(r'eslint-disable(?:-next-line|-line)?\b([^\n]*)')
A11Y_RULE = re.compile(r'@angular-eslint/template/(' + '|'.join(A11Y_RULES) + r')\b')
COMMENT = re.compile(r'/\*.*?\*/|//[^\n]*', re.S)


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True)


def files(repo, ref=None):
    """Tracked and new files at `ref`, or in the working tree, outside build output and dependencies."""
    listing = git(repo, 'ls-tree', '-rz', '--name-only', ref) if ref else git(
        repo, 'ls-files', '-z', '--cached', '--others', '--exclude-standard')
    for name in sorted(set(filter(None, listing.split('\0')))):
        if EXCLUDED.intersection(PurePosixPath(name).parts):
            continue
        if ref is None and not (repo / name).is_file():
            continue
        yield name


def read(repo, name, ref=None):
    if ref is None:
        return (repo / name).read_text(errors='replace')
    return git(repo, 'show', f'{ref}:{name}')


def array_elements(text, start):
    """The top-level elements of the array literal whose `[` is at `start`, with their offsets.

    Strings, template literals and comments are skipped, so a bracket or comma inside one does not
    end an element. Each element comes back with its comments removed and its whitespace collapsed,
    so a reflowed or recommented entry is the same entry.
    """
    depth, index, element_start, elements = 0, start, start + 1, []
    quote = None
    while index < len(text):
        char = text[index]
        if quote:
            if char == '\\':
                index += 2
                continue
            if char == quote:
                quote = None
        elif char in '\'"`':
            quote = char
        elif text.startswith('//', index):
            index = text.find('\n', index)
            if index < 0:
                break
            continue
        elif text.startswith('/*', index):
            index = text.find('*/', index) + 2
            if index < 2:
                break
            continue
        elif char in '([{':
            depth += 1
        elif char in ')]}':
            depth -= 1
            if depth == 0:
                elements.append((element_start, text[element_start:index]))
                break
        elif char == ',' and depth == 1:
            elements.append((element_start, text[element_start:index]))
            element_start = index + 1
        index += 1
    for offset, raw in elements:
        clean = ' '.join(COMMENT.sub(' ', raw).split())
        if clean:
            yield offset + len(raw) - len(raw.lstrip()), clean


def exceptions(repo, ref=None):
    """Each recorded exception: (key, file, line, kind, text). Equal keys are counted, not merged."""
    for name in files(repo, ref):
        is_test = bool(TEST_SOURCE.search(name))
        is_template = bool(APP_SOURCE.match(name)) and not name.endswith(('.spec.ts', '.test.ts'))
        if not (is_test or is_template):
            continue
        try:
            text = read(repo, name, ref)
        except (OSError, subprocess.CalledProcessError):
            continue
        line_of = lambda offset: text.count('\n', 0, offset) + 1
        if is_test:
            for match in LIST.finditer(text):
                for offset, entry in array_elements(text, match.end() - 1):
                    yield f'{name}|{match.group(1)}|{entry}', name, line_of(offset), match.group(1), entry
            # Only a file that drives axe can switch one of its rules off.
            for match in AXE_OFF.finditer(text) if 'AxeBuilder' in text or 'axe-core' in text else ():
                statement = ' '.join(text[match.start():text.find('\n', match.start())].split())
                yield f'{name}|axe|{statement}', name, line_of(match.start()), 'axe rule off', statement
        if is_template:
            for match in LINT_OFF.finditer(text):
                for rule in A11Y_RULE.findall(match.group(1)):
                    yield f'{name}|lint|{rule}', name, line_of(match.start()), 'template lint off', rule


def findings(repo, ref=None):
    """Adoption-report rows for the exceptions `ref` does not record. Without `ref` none are new.

    A suite the revision does not have may record the failures it finds on its first commit. Its
    exceptions excuse only its own checks, so they cannot hide a finding an existing suite reports,
    and adding the suite widens what is measured.
    """
    repo = Path(repo)
    base = Counter(key for key, *_ in exceptions(repo, ref)) if ref else None
    base_files = set(files(repo, ref)) if ref else set()
    seen = Counter()
    for key, name, line, kind, text in exceptions(repo):
        seen[key] += 1
        first_commit = kind != 'template lint off' and name not in base_files
        status = 'new' if base is not None and seen[key] > base[key] and not first_commit else 'existing'
        yield {'id': f'accessibility:{key}', 'file': name, 'line': line, 'rule': 'accessibility-exception',
               'property': kind, 'value': text if len(text) <= 100 else text[:97] + '...',
               'severity': 'gate', 'status': status}
