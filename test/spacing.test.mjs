import test from 'node:test';
import assert from 'node:assert/strict';
import * as sass from 'sass';
import { readFileSync } from 'node:fs';

const compile = (body) => sass.compileString(`@use 'spacing'; ${body}`, { loadPaths: [process.cwd()] }).css;

test('spacing recipes emit nothing until selected and reject arbitrary values and token assignments', () => {
  assert.equal(compile(''), '');
  for (const args of ['padding, 13px', 'padding, invented', '--cedar-space-1, compact', 'color, compact'])
    assert.throws(() => compile(`a { @include spacing.apply(${args}); }`));
});

test('every finite spacing recipe compiles without consumer Sass variables', () => {
  const source = readFileSync('_spacing.scss', 'utf8');
  const names = [...source.matchAll(/^  ([\w-]+):/gm)].map((m) => m[1]);
  assert.ok(names.length > 0);
  for (const name of names) assert.ok(compile(`a { @include spacing.apply(padding, ${name}); }`).includes('padding:'));
});

test('control alignment retains the existing geometry without local arithmetic', () => {
  assert.match(compile('a { @include spacing.apply(padding, view-switch); }'), /space-1\) \* 1.25/);
  assert.match(compile('a { @include spacing.apply(padding, compact); }'), /padding: 2px/);
  assert.doesNotMatch(compile('a { @include spacing.apply(padding, compact-row); }'), /var\(/);
  assert.match(compile('a { @include spacing.apply(padding, preview-select); }'), /space-2\) \* 3.75/);
});
