import test from 'node:test';
import assert from 'node:assert/strict';
import * as sass from 'sass';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';

const roles = new Set(
  [...readFileSync('dist/custom-properties.css', 'utf8').matchAll(/(--cedar-[\w-]+)\s*:/g)].map((m) => m[1]),
);
const names = [
  'validation-summary',
  'artifact-title',
  'dialog-surface',
  'dialog-actions',
  'menu-surface',
  'menu-item',
  'field-label',
  'field-help',
  'field-error',
  'toolbar',
  'tabs',
  'table-cell',
  'empty-state',
];
for (const name of names) {
  test(`${name} uses registered shared roles and stays opt-in`, () => {
    const css = sass.compileString(`@use 'patterns'; .consumer { @include patterns.${name}; }`, {
      loadPaths: [process.cwd()],
    }).css;
    for (const role of css.matchAll(/var\((--cedar-[\w-]+)/g))
      assert.ok(roles.has(role[1]), `Unknown role: ${role[1]}`);
    assert.match(css, /^\.consumer/);
    assert.doesNotMatch(css, /#(?:[\da-f]{3})\b|rgb\(|font-family:/i);
  });
}
test('recipes emit nothing until used', () => {
  assert.equal(sass.compileString("@use 'patterns';", { loadPaths: [process.cwd()] }).css, '');
});

for (const name of ['field-label', 'field-help', 'field-error']) {
  test(`${name} body variant preserves the default recipe except its type role`, () => {
    const compile = (args) => sass.compileString(
      `@use 'patterns'; .consumer { @include patterns.${name}${args}; }`,
      { loadPaths: [process.cwd()] },
    ).css;
    const defaultCss = compile('');
    assert.equal(compile('($size: small)'), defaultCss);
    assert.equal(
      compile('($size: body)'),
      defaultCss.replace('var(--cedar-font-size-small)', 'var(--cedar-font-size)'),
    );
    assert.throws(() => compile('($size: huge)'), /Form text size must be small or body/);
  });
}

test('offline checker recognizes exactly the generated roles and host overrides', () => {
  const known = JSON.parse(
    execFileSync(
      'python3',
      [
        '-c',
        'import sys,json; sys.path.insert(0,"tools"); from check_adoption import known_css_properties; print(json.dumps(sorted(known_css_properties())))',
      ],
      { encoding: 'utf8' },
    ),
  );
  const hosts = JSON.parse(readFileSync('tools/host-properties.json', 'utf8'));
  assert.deepEqual(
    known,
    [
      ...new Set(
        [...roles].map((r) => r.replace('--cedar-', '')).concat(Object.keys(hosts).map((r) => r.replace('cedar-', ''))),
      ),
    ].sort(),
  );
});
