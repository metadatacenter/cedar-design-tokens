"""Shared input behavior contract: browser spelling is off on authored controls."""
import hashlib
from html.parser import HTMLParser
from pathlib import Path
import re
from style_sources import LITERAL


def findings(path, source):
    if Path(path).suffix not in ('.html', '.ts'):
        return
    source = re.sub(r'<!--.*?-->|/\*.*?\*/|(?m:^[ \t]*//[^\n]*)',
                    lambda m: re.sub(r'[^\n]', ' ', m[0]), source, flags=re.S)
    templates = [(0, source)] if Path(path).suffix == '.html' else [
        (m.start(1) + 1, m[1][1:-1]) for m in re.finditer(r'\btemplate\s*:\s*(' + LITERAL + ')', source)]
    for offset, template in templates:
        rows = []

        class Controls(HTMLParser):
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                editable = tag in ('input', 'textarea') or any('contenteditable' in a for a in attrs)
                spelling = [a for a in attrs if 'spellcheck' in a]
                if not editable and not spelling:
                    return
                if (attrs.get('spellcheck') or '').lower() == 'false' and spelling == ['spellcheck']:
                    return
                value = self.get_starttag_text()
                rows.append({
                    'id': hashlib.sha256(f'{path}|spellcheck|{value}'.encode()).hexdigest()[:20],
                    'file': str(path), 'line': source[:offset].count('\n') + self.getpos()[0],
                    'rule': 'spellcheck', 'property': 'spellcheck',
                    'value': 'Controls must explicitly set spellcheck="false"; opt-ins are not approved.',
                    'severity': 'gate',
                })

        Controls().feed(template)
        yield from rows
