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

# Policy 4 also reads the utility families that set outlines, SVG paint, decoration, carets, accents,
# dividers, gradients, opacity and motion. Their values are Tailwind-shaped (a number, a palette step,
# a keyword or an arbitrary value), so a semantic class such as `outline-row` is not one.
PALETTE = (r'(?:(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|'
           r'indigo|violet|purple|fuchsia|pink|rose)-\d{2,3}(?:/\d+)?|black|white|\[[^]]+\])')
UTILITY_4 = re.compile(r'^(?:!?)(?:(?:[\w-]+|\[[^]]+\]):)*(?:outline(?:-offset)?-(?:\d+|' + PALETTE + r')|'
                       r'(?:fill|caret|accent)-' + PALETTE + r'|stroke-(?:\d+|' + PALETTE + r')|'
                       r'decoration-(?:\d+|solid|double|dotted|dashed|wavy|' + PALETTE + r')|'
                       r'divide-(?:[xy]-\d+|' + PALETTE + r')|(?:from|via|to)-(?:\d+%|' + PALETTE + r')|'
                       r'(?:opacity|duration|delay)-(?:\d+|\[[^]]+\])|ease-(?:in|out|in-out|\[[^]]+\]))!?$')
STRUCTURAL_4 = {'opacity-0', 'opacity-100', 'duration-0', 'delay-0'}


def gated_utility(name, policy=2):
    # Structural/reset utilities introduce no private design value.
    base = name.split(':')[-1]
    if policy >= 4 and (base.lstrip('!') in STRUCTURAL_4):
        return False
    if base in {'h-full', 'h-auto', 'min-h-0', 'mx-auto', 'my-auto', 'm-auto',
                'text-left', 'text-right', 'text-center', 'text-start', 'text-end',
                'bg-transparent', 'border-transparent', 'border-none', 'border-0',
                'border-b', 'border-t', 'border-l', 'border-r', 'border-b-2'}:
        return False
    return bool(UTILITY.match(name) or (policy >= 4 and UTILITY_4.match(name)))


def masked(text):
    return re.sub(r'[^\n]', ' ', text)


def sources(path, source, policy=2):
    """Yield CSS snippets with original line offsets, plus forbidden dynamic declarations."""
    properties = style_properties(policy)
    if Path(path).suffix == '.sass':
        # The indented syntax ends a declaration at the line's end.
        source = source.replace('\n', ';\n')
    if Path(path).suffix in ('.scss', '.css', '.less', '.sass'):
        yield source
        for match in re.finditer(r'@apply\s+([^;]+);', source):
            for extracted in sources(Path('utilities.html'), '<div class="' + match[1] + '"></div>', policy):
                if extracted:
                    yield '\n' * source[:match.start()].count('\n') + extracted
        return
    source = re.sub(r'<!--.*?-->|/\*.*?\*/|(?m:^[ \t]*//[^\n]*)', lambda m: masked(m[0]), source, flags=re.S)
    templates = [(0, source)] if Path(path).suffix in ('.html', '.tsx', '.jsx') else []
    if Path(path).suffix == '.html':
        # A page's own script reaches the document as directly as a component's code does.
        for match in re.finditer(r'<script\b(?![^>]*\bsrc\s*=)[^>]*>(.*?)</script\s*>', source, re.S | re.I):
            yield from sources(Path('inline.js'), _at(source, match.start(1)) + match[1], policy)
    if Path(path).suffix in ('.ts', '.js', '.mjs', '.tsx', '.jsx'):
        if policy >= 4:
            yield from policy_4_script(source, properties)
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
        # A style element is a stylesheet, in a page's head as in a component's template.
        for match in re.finditer(r'<style\b[^>]*>(.*?)</style\s*>', template, re.S | re.I):
            yield _at(source, offset) + _at(template, match.start(1)) + match[1]
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
        if policy >= 4:
            yield from policy_4_template(source, offset, template)
        # Bound class names and literal names inside ngClass/class expressions must
        # receive the same scrutiny as static classes. Ordinary semantic names pass.
        for match in re.finditer(r'\[class\.([^] ]+)\]', template):
            if gated_utility(match[1], policy):
                yield '\n' * (source[:offset].count('\n') + template[:match.start()].count('\n')) + '{utility-style:' + match[1] + ';}'
        for match in re.finditer(r'\[(?:ngClass|class)\]\s*=\s*(["\'])(.*?)\1', template, re.S):
            for literal in re.finditer(LITERAL, match[2]):
                for utility in literal[0][1:-1].split():
                    if gated_utility(utility, policy) and not re.search(r'\[(?:var\(--cedar-[\w-]+\)|--cedar-[\w-]+)\]', utility):
                        yield '\n' * (source[:offset].count('\n') + template[:match.start()].count('\n')) + '{utility-style:' + utility + ';}'
        for match in re.finditer(r'\b(?:class|className)\s*=\s*(["\'])(.*?)\1' if policy >= 4 else r'\bclass\s*=\s*(["\'])(.*?)\1', template, re.S):
            for utility in match[2].split():
                if gated_utility(utility, policy) and not re.search(r'\[(?:var\(--cedar-[\w-]+\)|--cedar-[\w-]+)\]', utility):
                    yield '\n' * (source[:offset].count('\n') + template[:match.start()].count('\n')) + '{utility-style:' + utility + ';}'


def _at(source, index):
    return '\n' * source[:index].count('\n')


def _decorators(source):
    """The metadata objects of Angular component and directive decorators, with their offsets."""
    for decorator in re.finditer(r'@(?:Component|Directive)\s*\(\s*\{', source):
        depth, end = 1, decorator.end()
        while end < len(source) and depth:
            depth += {'{': 1, '}': -1}.get(source[end], 0)
            end += 1
        yield decorator.end(), source[decorator.end():end - 1]


def policy_4_script(source, properties):
    """Styles that reach a component without passing through a template or a stylesheet."""
    for start, metadata in _decorators(source):
        # Host metadata: a literal style string, bound style properties and a bound style attribute.
        for host in re.finditer(r'\bhost\s*:\s*\{', metadata):
            depth, end = 1, host.end()
            while end < len(metadata) and depth:
                depth += {'{': 1, '}': -1}.get(metadata[end], 0)
                end += 1
            body, base = metadata[host.end():end - 1], start + host.end()
            for match in re.finditer(r'[\'"]style[\'"]\s*:\s*(' + LITERAL + ')', body):
                yield _at(source, base + match.start()) + '{' + match[1][1:-1] + '}'
            for match in re.finditer(r'[\'"]\[style\.([\w-]+)(?:\.(?:px|rem|em|%))?\][\'"]\s*:', body):
                prop = re.sub(r'[A-Z]', lambda m: '-' + m[0].lower(), match[1])
                if not prop.startswith('--') and re.fullmatch(properties, prop):
                    yield _at(source, base + match.start()) + '{' + prop + ':uninspectable-binding;}'
            for match in re.finditer(r'[\'"]\[attr\.style\][\'"]\s*:', body):
                yield _at(source, base + match.start()) + '{dynamic-style:uninspectable-binding;}'
        # A styles entry that is not literal text cannot be inspected.
        for match in re.finditer(r'\bstyles\s*:\s*(?:\[\s*)?(?=[A-Za-z_$])(?!css`)', metadata):
            yield _at(source, start + match.start()) + '{dynamic-style:uninspectable-binding;}'
    # Lit's css tagged templates are stylesheets.
    for match in re.finditer(r'\bcss`((?:\\.|[^`\\])*)`', source):
        yield _at(source, match.start(1)) + re.sub(r'\$\{[^}]*\}', 'uninspectable-binding', match[1])
    # Constructed stylesheets take text no stylesheet scan sees.
    for match in re.finditer(r'\.(?:replaceSync|insertRule)\s*\(', source):
        yield _at(source, match.start()) + '{dynamic-style:uninspectable-binding;}'


def policy_4_template(source, offset, template):
    """Template routes around the style scan: a bound style attribute, Tailwind's arbitrary
    properties and the presentation attributes of SVG text."""
    for match in re.finditer(r'\[attr\.style\]\s*=', template):
        yield _at(source, offset) + _at(template, match.start()) + '{dynamic-style:uninspectable-binding;}'
    for attribute in re.finditer(r'\b(?:class|className)\s*=\s*(["\'])(.*?)\1', template, re.S):
        for match in re.finditer(r'(?:^|\s|:)!?\[([a-z-]+):([^\]\s]+)\]', attribute[2]):
            yield _at(source, offset) + _at(template, attribute.start()) + '{' + match[1] + ':' + match[2].replace('_', ' ') + ';}'
    for element in re.finditer(r'<(?:svg:)?(?:text|tspan)\b([^>]*)>', template):
        for match in re.finditer(r'\b(fill|stroke|font-size|font-weight|font-family)\s*=\s*(["\'])(.*?)\2', element[1]):
            if match[3].strip().lower() not in ('none', 'currentcolor', 'inherit'):
                yield _at(source, offset) + _at(template, element.start()) + '{' + match[1] + ':' + match[3] + ';}'
