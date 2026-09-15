// What the generated stylesheet has to be: the partial, emitted.
//
// The package's claim is that there is one source. A second file holding the same
// values in another syntax is exactly the arrangement that drifted before, so the
// claim needs a test rather than a comment: every literal the partial states has
// to appear in the CSS, and nothing may be declared twice.

import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import assert from 'node:assert/strict';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const scss = readFileSync(join(root, '_tokens.scss'), 'utf8');
const css = readFileSync(join(root, 'dist/custom-properties.css'), 'utf8');

/** Every `$name: value;` the partial states at the top level, less the Sass-only one. */
function scalarTokens() {
  const found = new Map();
  for (const line of scss.split('\n')) {
    const match = /^\$([a-z0-9-]+):\s*(.+);$/.exec(line);
    // A map opens with `(` and closes lines later; `map.get` resolves at compile
    // time and states no literal. Neither can be matched against the output.
    if (!match || match[2].endsWith('(') || match[2].startsWith('map.get')) {
      continue;
    }
    found.set(match[1], match[2]);
  }
  return found;
}

/** Every hex in the two palettes, which are emitted hue by hue. */
function paletteColors() {
  return [...scss.matchAll(/^\s+(?:50|100|200|300|400|500|600|700|800|900|A[1247]00):\s*(#[0-9a-f]{6}),$/gim)].map(
    (match) => match[1],
  );
}

test('the partial states tokens worth emitting', () => {
  // Guards the two readers above: a rename that stops them matching would
  // otherwise leave every assertion below trivially true.
  assert.ok(scalarTokens().size >= 15, `only ${scalarTokens().size} scalar tokens matched`);
  assert.ok(paletteColors().length >= 28, `only ${paletteColors().length} palette colours matched`);
});

test('every scalar token reaches the stylesheet', () => {
  for (const [name, value] of scalarTokens()) {
    if (name === 'font-family-string') {
      // Material's typography config takes one quoted string. It is not a CSS
      // value and has no property to be declared as.
      continue;
    }
    assert.match(css, new RegExp(`--cedar-${name}:`), `--cedar-${name} is not declared`);
    // Quoting is Sass's to decide and carries no meaning in the result, so the
    // comparison is of the values rather than of how each was written.
    const unquoted = (text) => text.replaceAll(/["']/g, '');
    assert.ok(unquoted(css).includes(unquoted(value)), `${name} is declared but not with its own value, ${value}`);
  }
});

test('every palette hue reaches the stylesheet', () => {
  for (const color of paletteColors()) {
    assert.ok(css.includes(color), `${color} is in a palette but not in the stylesheet`);
  }
});

test('no property is declared twice', () => {
  const declared = [...css.matchAll(/^\s*(--cedar-[a-z0-9-]+):/gim)].map((match) => match[1]);
  const duplicated = declared.filter((name, index) => declared.indexOf(name) !== index);
  assert.deepEqual(duplicated, [], `declared more than once: ${duplicated.join(', ')}`);
});

test('the properties are declared for a shadow root as well as a document', () => {
  // A component embedded in someone else's page renders inside a shadow root, and
  // `:root` matches the document element, which is outside it.
  assert.match(css, /:root,\s*\n?:host\s*\{/);
});
