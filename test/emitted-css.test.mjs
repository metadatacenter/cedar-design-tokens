import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import assert from 'node:assert/strict';
import * as sass from 'sass';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const css = readFileSync(join(root, 'dist/custom-properties.css'), 'utf8');

// Ask Sass for the module's evaluated values: every scalar is emitted under its own name; the
// palette maps and the Material font string are adapter inputs and are not.
const expected = new Map();
sass.compileString(
  `@use 'sass:meta';
   @use 'tokens';
   @each $name, $value in meta.module-variables('tokens') {
     @if meta.type-of($value) != 'map' and $name != 'font-family-string' {
       $_: audit-token($name, meta.inspect($value));
     }
   }`,
  {
    loadPaths: [join(root, 'scss')],
    functions: {
      'audit-token($name, $value)': ([name, value]) => {
        expected.set(`--cedar-${name.assertString().text}`, value.assertString().text);
        return sass.sassNull;
      },
    },
  },
);

function assertTokens(stylesheet) {
  const declarations = [...stylesheet.matchAll(/(--cedar-[\w-]+)\s*:\s*([^;]+);/g)].map(([, name, value]) => [
    name,
    value.trim(),
  ]);
  const actual = new Map(declarations);
  assert.equal(actual.size, declarations.length, 'duplicate property');
  assert.deepEqual(actual, expected, 'each property must carry its own evaluated Sass value');
}

test('every evaluated token is emitted under its own name, and nothing else is', () => {
  assertTokens(css);
  assert.doesNotMatch(css, /--cedar-(?:primary|accent|on-primary|on-accent)-/, 'palette steps are adapter inputs');
});

test('swapped sizes cannot pass by appearing elsewhere in the stylesheet', () => {
  const swapped = css
    .replace('--cedar-font-size: 14px', '--cedar-font-size: 12px')
    .replace('--cedar-font-size-small: 12px', '--cedar-font-size-small: 14px');
  assert.notEqual(swapped, css);
  assert.throws(() => assertTokens(swapped));
});

test('a missing derived value is detected', () => {
  for (const name of ['color-primary', 'color-primary-strong']) {
    const missing = css.replace(new RegExp(`--cedar-${name}: [^;]+;`), '');
    assert.notEqual(missing, css);
    assert.throws(() => assertTokens(missing));
  }
});

test('the properties reach a shadow root as well as a document', () => {
  assert.match(css, /:root,\s*\n?:host\s*\{/);
});

test('defaults do not shadow the public compact-control override names', () => {
  for (const key of ['height', 'font-size', 'line-height', 'radius', 'border', 'focus', 'error']) {
    assert.doesNotMatch(css, new RegExp(`--cedar-control-${key}\\s*:`));
  }
  assert.match(css, /--cedar-control-height-default: 36px/);
  assert.match(css, /--cedar-control-height-authoring: 32px/);
});

test('shared font export is self-contained and contains only font faces', () => {
  const fonts = sass.compile(join(root, 'scss/_fonts.scss')).css;
  assert.equal((fonts.match(/@font-face/g) || []).length, 14);
  assert.equal((fonts.match(/data:font\/woff2;base64,/g) || []).length, 14);
  assert.doesNotMatch(fonts, /font-weight: 300;/);
  assert.doesNotMatch(fonts, /url\(https?:/);
  assert.doesNotMatch(
    fonts
      .replace(/@font-face\s*\{[^}]*\}/g, '')
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .trim(),
    /\S/,
  );
});

test('each weight covers every script the shared faces are meant to carry', () => {
  // One character from each of the seven subsets. User content, not only the interface, can be in
  // any of these scripts, so a dropped subset would draw them in the host's fallback face.
  const samples = {
    latin: 0x0041,
    'latin-ext': 0x0151, // ő, which Hungarian needs
    cyrillic: 0x0430,
    'cyrillic-ext': 0x0460,
    greek: 0x03b1,
    'greek-ext': 0x1f00,
    vietnamese: 0x1ea0,
  };
  const fonts = sass.compile(join(root, 'scss/_fonts.scss')).css;
  const faces = [...fonts.matchAll(/@font-face\s*\{([^}]*)\}/g)].map(([, body]) => ({
    weight: Number(body.match(/font-weight:\s*(\d+)/)[1]),
    ranges: body
      .match(/unicode-range:\s*([^;]+);/)[1]
      .split(',')
      .map((range) =>
        range
          .trim()
          .replace(/^U\+/i, '')
          .split('-')
          .map((hex) => parseInt(hex, 16)),
      )
      .map(([start, end = start]) => [start, end]),
  }));
  for (const weight of [400, 500]) {
    for (const [subset, codepoint] of Object.entries(samples)) {
      const covering = faces.filter(
        (face) => face.weight === weight && face.ranges.some(([start, end]) => codepoint >= start && codepoint <= end),
      );
      assert.equal(covering.length, 1, `${subset} at ${weight}`);
    }
  }
});

test('individual font exports provide exactly their declared weight', () => {
  const metadata = JSON.parse(readFileSync(join(root, 'package.json'), 'utf8'));
  for (const [name, weight] of [
    ['regular', 400],
    ['medium', 500],
  ]) {
    const fonts = sass.compile(join(root, metadata.exports[`./fonts/${name}`].sass)).css;
    assert.equal((fonts.match(/@font-face/g) || []).length, 7);
    assert.equal((fonts.match(new RegExp(`font-weight: ${weight};`, 'g')) || []).length, 7);
    assert.equal((fonts.match(/data:font\/woff2;base64,/g) || []).length, 7);
    assert.doesNotMatch(fonts, /url\(https?:/);
  }
});
