"""Modern Workspace must load the shared native-choice theme at its app root.

This is an integration contract, not a CSS cascade evaluator. Rendered consumer
checks prove each control's effective colour. Legacy hosts are intentionally excluded.
"""
import hashlib
from html.parser import HTMLParser
import json
import re
import subprocess


def findings(read):
    try:
        package = json.loads(read('package.json'))
    except (FileNotFoundError, subprocess.CalledProcessError):
        # Some estate repositories contain only a nested frontend package.
        return
    if package.get('name') != 'cedar-workspace':
        return
    errors = []

    class Root(HTMLParser):
        themed = False
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == 'cedar-workspace':
                self.themed = 'cedar-native-choices' in attrs.get('class', '').split()

    root = Root()
    root.feed(read('src/index.html'))
    if not root.themed:
        errors.append(('src/index.html', 'The Workspace root must opt into cedar-native-choices.'))
    projects = json.loads(read('angular.json')).get('projects', {})
    styled = False
    for project in projects.values():
        build = project.get('architect', {}).get('build', {}).get('options', {})
        for entry in build.get('styles', []):
            name = entry if isinstance(entry, str) else entry.get('input') if entry.get('inject', True) else None
            if not name:
                continue
            source = re.sub(r'/\*.*?\*/|(?m:^[ \t]*//[^\n]*)', '', read(name), flags=re.S)
            # Require a top-level import in a stylesheet actually included in the build.
            for match in re.finditer(r'@import\s+[\'"]@org\.metadatacenter/cedar-design-tokens/native-choices\.css[\'"]\s*;', source):
                prefix = source[:match.start()]
                if prefix.count('{') == prefix.count('}'):
                    styled = True
    if not styled:
        errors.append(('angular.json', 'A global build stylesheet must import the shared native-choices.css.'))
    for path, message in errors:
        yield {'id': hashlib.sha256(f'{path}|native-choice-coverage|{message}'.encode()).hexdigest()[:20],
               'file': path, 'line': 1, 'rule': 'native-choice-coverage',
               'property': 'native choices', 'value': message, 'severity': 'gate'}
