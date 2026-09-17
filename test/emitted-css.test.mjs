import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import assert from 'node:assert/strict';
import * as sass from 'sass';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const css = readFileSync(join(root, 'dist/custom-properties.css'), 'utf8');

// Ask Sass for the module's evaluated values. This covers derived scalars and
// every palette/contrast entry without a regex tied to the source's formatting.
const expected = new Map();
sass.compileString(
  `@use 'sass:meta';
   @use 'sass:string';
   @use 'tokens';
   @each $name, $value in meta.module-variables('tokens') {
     @if $name == 'font-family-string' {
       // Material-only representation, not a CSS property.
     } @else if meta.type-of($value) == 'map' {
       $palette: string.slice($name, 7);
       @each $hue, $color in $value {
         @if $hue == contrast {
           @each $step, $on-color in $color {
             $_: audit-token('on-#{$palette}-#{$step}', meta.inspect($on-color));
           }
         } @else {
           $_: audit-token('#{$palette}-#{$hue}', meta.inspect($color));
         }
       }
     } @else {
       $_: audit-token($name, meta.inspect($value));
     }
   }`,
  {
    loadPaths: [root],
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

test('every evaluated token and contrast entry is emitted under its own name', () => {
  assert.ok(expected.size >= 70, 'the Sass module must expose the complete token set');
  assertTokens(css);
});

test('swapped sizes cannot pass by appearing elsewhere in the stylesheet', () => {
  const swapped = css
    .replace('--cedar-font-size: 14px', '--cedar-font-size: 12px')
    .replace('--cedar-font-size-small: 12px', '--cedar-font-size-small: 14px');
  assert.notEqual(swapped, css);
  assert.throws(() => assertTokens(swapped));
});

test('a missing derived value or contrast entry is detected', () => {
  for (const name of ['color-primary', 'on-primary-500']) {
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
  const fonts = sass.compile(join(root, '_fonts.scss')).css;
  assert.equal((fonts.match(/@font-face/g) || []).length, 21);
  assert.equal((fonts.match(/data:font\/woff2;base64,/g) || []).length, 21);
  assert.doesNotMatch(fonts, /url\(https?:/);
  assert.doesNotMatch(
    fonts
      .replace(/@font-face\s*\{[^}]*\}/g, '')
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .trim(),
    /\S/,
  );
});
