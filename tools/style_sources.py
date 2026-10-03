"""Extract authored CSS from Angular sources without interpreting application strings as CSS.

The guard deliberately rejects dynamic paint/typography bindings: semantic classes or
custom properties make their styling inspectable. Positional layout bindings are local.
"""
import re
from pathlib import Path

LITERAL = r'''(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`)'''
STYLE_PROPERTIES = r'(?:resize|accent-color|color|background(?:-color)?|font(?:-[\w-]+)?|line-height|letter-spacing|border(?:-[\w-]+)?|box-shadow|z-index|padding(?:-[\w-]+)?|margin(?:-[\w-]+)?|(?:row-|column-)?gap|height|min-height|transition(?:-duration)?|animation(?:-duration)?)'
# Policy 3 also inspects focus outlines, opacity and the easing a transition or animation names.
STYLE_PROPERTIES_3 = STYLE_PROPERTIES[:-1] + r'|outline(?:-[\w-]+)?|opacity|transition(?:-timing-function)?|animation(?:-timing-function)?)'


def style_properties(policy):
    return STYLE_PROPERTIES_3 if policy >= 3 else STYLE_PROPERTIES
UTILITY = re.compile(r'^(?:!?)(?:(?:[\w-]+|\[[^]]+\]):)*(?:bg|text|font|leading|tracking|rounded|shadow|ring|border|p[trblxyse]?|m[trblxyse]?|gap(?:-[xy])?|space-[xy]|h|min-h|z)-(.+)$')

def gated_utility(name):
    # Structural/reset utilities introduce no private design value.
    base = name.split(':')[-1]
    if base in {'h-full', 'h-auto', 'min-h-0', 'mx-auto', 'my-auto', 'm-auto',
                'text-left', 'text-right', 'text-center', 'text-start', 'text-end',
                'bg-transparent', 'border-transparent', 'border-none', 'border-0',
                'border-b', 'border-t', 'border-l', 'border-r', 'border-b-2'}:
        return False
    return bool(UTILITY.match(name))


def masked(text):
    return re.sub(r'[^\n]', ' ', text)


def sources(path, source, policy=2):
    """Yield CSS snippets with original line offsets, plus forbidden dynamic declarations."""
    properties = style_properties(policy)
    if Path(path).suffix in ('.scss', '.css', '.less'):
        yield source
        for match in re.finditer(r'@apply\s+([^;]+);', source):
            for extracted in sources(Path('utilities.html'), '<div class="' + match[1] + '"></div>', policy):
                if extracted:
                    yield '\n' * source[:match.start()].count('\n') + extracted
        return
    source = re.sub(r'<!--.*?-->|/\*.*?\*/|(?m:^[ \t]*//[^\n]*)', lambda m: masked(m[0]), source, flags=re.S)
    templates = [(0, source)] if Path(path).suffix == '.html' else []
    if Path(path).suffix in ('.ts', '.js', '.mjs'):
        # Whole style objects/text and computed property names cannot be proven to
        # respect the token boundary. Positional setters with literal names still pass.
        for match in re.finditer(r"""(?:\.setAttribute\(\s*['"]style['"]\s*,|Object\.assign\(\s*[^,;]+\.style\s*,|\.style\[\s*(?!['"])[^]\n]+\]\s*=(?!=)|@HostBinding\(\s*['"]style['"]\s*\))""", source):
            yield '\n' * source[:match.start()].count('\n') + '{dynamic-style:uninspectable-binding;}'
        # Angular host metadata uses quoted binding names rather than template attributes.
        for match in re.finditer(r"""['"]\[style\.(--[\w-]+)(?:\.(?:px|rem|em|%))?\]['"]\s*:""", source):
            yield '\n' * source[:match.start()].count('\n') + '{' + match[1] + ':uninspectable-binding;}'
        for match in re.finditer(r"""(?:\.style\.setProperty\(\s*|\.setStyle\(\s*[^,]+,\s*)([^,]+),""", source):
            name = match[1].strip()
            literal = re.fullmatch(LITERAL, name)
            prop = name[1:-1] if literal else 'dynamic-style'
            if prop.startswith('--') or re.fullmatch(properties, prop) or not literal:
                yield '\n' * source[:match.start()].count('\n') + '{' + prop + ':uninspectable-binding;}'
        for match in re.finditer(r"""\.style(?:\.(\w+)|\[\s*(['"])(.*?)\2\s*\])\s*=(?!=)""", source):
            prop = match[1] or match[3]
            prop = re.sub(r'[A-Z]', lambda m: '-' + m[0].lower(), prop)
            if prop.startswith('--') or prop == 'css-text' or re.fullmatch(properties, prop):
                yield '\n' * source[:match.start()].count('\n') + '{' + ('dynamic-style' if prop == 'css-text' else prop) + ':uninspectable-binding;}'
        for match in re.finditer(r"""@HostBinding\(\s*(['"])style\.(.*?)\1\s*\)""", source):
            prop = match[2]
            if prop.startswith('--') or re.fullmatch(properties, prop):
                yield '\n' * source[:match.start()].count('\n') + '{' + prop + ':uninspectable-binding;}'
        for match in re.finditer(r'\b(styles|template)\s*:\s*(\[(?:'+LITERAL+r'|[^\]"\'`])*\]|'+LITERAL+r')', source):
            for literal in re.finditer(LITERAL, match[2]):
                offset = match.start(2) + literal.start() + 1
                text = literal[0][1:-1]
                if match[1] == 'styles':
                    yield '\n' * source[:offset].count('\n') + text
                else:
                    templates.append((offset, text))
    for offset, template in templates:
        for match in re.finditer(r"""\[style\.(--[\w-]+)(?:\.(?:px|rem|em|%))?\]\s*=\s*(["'])(.*?)\2""", template, re.S):
            yield '\n' * (source[:offset].count('\n') + template[:match.start()].count('\n')) + '{' + match[1] + ':uninspectable-binding;}'
        # Check resize utilities in literal and bound class attributes only.
        for attribute in re.finditer(r"""(?:\[?(?:class|ngClass)\]?\s*=\s*(["'])(.*?)\1|\[class\.([^] ]+)\])""", template, re.S):
            classes = attribute[2] if attribute[2] is not None else attribute[3]
            for match in re.finditer(r'(?<![\w-])(?:(?:[\w-]+|\[[^]]+\]):)*!?(?:resize(?:-[\w]+)?|\[resize:[^]]+\])!?', classes):
                utility = match[0]
                if re.search(r'resize-none!?$', utility) or re.search(r'\[resize:none\]!?$', utility):
                    continue
                yield '\n' * (source[:offset].count('\n') + template[:attribute.start()].count('\n')) + '{resize:forbidden-utility;}'
        for match in re.finditer(r'(?<![\w\[-])style\s*=\s*(["\'])(.*?)\1', template, re.S):
            yield '\n' * (source[:offset].count('\n') + template[:match.start(2)].count('\n')) + '{' + match[2] + '}'
        for match in re.finditer(r'\[style\.([\w-]+)(?:\.(px|rem|em|%))?\]\s*=\s*(["\'])(.*?)\3', template, re.S):
            prop = re.sub(r'[A-Z]', lambda m: '-' + m[0].lower(), match[1])
            if not re.fullmatch(properties, prop):
                continue
            value = match[4].strip()
            literal = re.fullmatch(LITERAL, value)
            value = value[1:-1] if literal else value + (match[2] or '')
            if not literal and not re.fullmatch(r'[\d.]+(?:px|rem|em|%)?', value):
                value = 'uninspectable-binding'
            yield '\n' * (source[:offset].count('\n') + template[:match.start()].count('\n')) + '{' + prop + ':' + value + ';}'
        for match in re.finditer(r'\[(?:ngStyle|style)\]\s*=\s*(["\'])(.*?)\1', template, re.S):
            yield '\n' * (source[:offset].count('\n') + template[:match.start()].count('\n')) + '{dynamic-style:uninspectable-binding;}'
        # Bound class names and literal names inside ngClass/class expressions must
        # receive the same scrutiny as static classes. Ordinary semantic names pass.
        for match in re.finditer(r'\[class\.([^] ]+)\]', template):
            if gated_utility(match[1]):
                yield '\n' * (source[:offset].count('\n') + template[:match.start()].count('\n')) + '{utility-style:' + match[1] + ';}'
        for match in re.finditer(r'\[(?:ngClass|class)\]\s*=\s*(["\'])(.*?)\1', template, re.S):
            for literal in re.finditer(LITERAL, match[2]):
                for utility in literal[0][1:-1].split():
                    if gated_utility(utility) and not re.search(r'\[(?:var\(--cedar-[\w-]+\)|--cedar-[\w-]+)\]', utility):
                        yield '\n' * (source[:offset].count('\n') + template[:match.start()].count('\n')) + '{utility-style:' + utility + ';}'
        for match in re.finditer(r'\bclass\s*=\s*(["\'])(.*?)\1', template, re.S):
            for utility in match[2].split():
                if gated_utility(utility) and not re.search(r'\[(?:var\(--cedar-[\w-]+\)|--cedar-[\w-]+)\]', utility):
                    yield '\n' * (source[:offset].count('\n') + template[:match.start()].count('\n')) + '{utility-style:' + utility + ';}'
