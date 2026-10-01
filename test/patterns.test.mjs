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
  'menu-icon',
  'menu-text',
  'menu-surface',
  'menu-item',
  'field-label',
  'field-help',
  'field-error',
  'toolbar',
  'tabs',
  'table-cell',
  'empty-state',
  'info-description-resize',
  'required-mark',
  'breadcrumbs',
  'breadcrumb-separator',
  'resource-grid',
  'resource-card',
  'resource-card-heading',
  'resource-card-icon',
  'resource-card-name',
  'resource-card-meta',
];
for (const name of names) {
  test(`${name} uses registered shared roles and stays opt-in`, () => {
    const css = sass.compileString(`@use 'patterns'; .consumer { @include patterns.${name}; }`, {
      loadPaths: [process.cwd()],
    }).css;
    for (const role of css.matchAll(/var\((--cedar-[\w-]+)/g))
      assert.ok(roles.has(role[1]), `Unknown role: ${role[1]}`);
    assert.match(css, /^\.consumer/);
    if (!name.startsWith('menu-')) assert.doesNotMatch(css, /#(?:[\da-f]{3})\b|rgb\(/i);
  });
}
test('recipes emit nothing until used', () => {
  assert.equal(sass.compileString("@use 'patterns';", { loadPaths: [process.cwd()] }).css, '');
});

for (const name of ['field-label', 'field-help', 'field-error']) {
  test(`${name} body variant preserves the default recipe except its type role`, () => {
    const compile = (args) =>
      sass.compileString(`@use 'patterns'; .consumer { @include patterns.${name}${args}; }`, {
        loadPaths: [process.cwd()],
      }).css;
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

test('Info descriptions resize vertically without allowing width changes', () => {
  const css = sass.compileString("@use 'patterns'; .description { @include patterns.info-description-resize; }", {
    loadPaths: [process.cwd()],
  }).css;
  assert.match(css, /resize: vertical;/);
});

test('dialog content can own padding while retaining the shared surface', () => {
  const compile = (args) =>
    sass.compileString(`@use 'patterns'; .dialog { @include patterns.dialog-surface${args}; }`, {
      loadPaths: [process.cwd()],
    }).css;
  assert.equal(compile('($padding: 0)'), compile('').replace('padding: var(--cedar-dialog-padding);', 'padding: 0;'));
});

for (const name of ['specification-box', 'specification-separator', 'specification-link']) {
  test(`${name} has registered host-overridable roles with standalone fallbacks`, () => {
    const css = sass.compileString(`@use 'patterns'; .reader { @include patterns.${name}; }`, {
      loadPaths: [process.cwd()],
    }).css;
    for (const role of css.matchAll(/var\((--cedar-[\w-]+)/g)) {
      assert.ok(
        roles.has(role[1]) ||
          ['--cedar-control-height', '--cedar-control-border', '--cedar-control-radius'].includes(role[1]),
        role[1],
      );
    }
    if (name === 'specification-box') {
      assert.match(css, /min-height: var/);
      assert.match(css, /flex-wrap: wrap/);
      assert.match(css, /overflow-wrap: anywhere/);
      assert.doesNotMatch(css, /(?:^|[;{])\s*height:/);
    }
  });
}

test('a required mark is raised without enlarging the line box of its label', () => {
  const css = sass.compileString(`@use 'patterns'; sup { @include patterns.required-mark; }`, {
    loadPaths: [process.cwd()],
  }).css;
  assert.match(css, /line-height: 0/);
  assert.match(css, /vertical-align: baseline/);
  assert.match(css, /position: relative/);
  assert.match(css, /inset-block-start: -0\.4em/);
});

test('breadcrumbs take the element-heading size only when they head a listing', () => {
  const compile = (args) =>
    sass.compileString(`@use 'patterns'; nav { @include patterns.breadcrumbs${args}; }`, {
      loadPaths: [process.cwd()],
    }).css;
  assert.doesNotMatch(compile(''), /font-size/);
  assert.match(compile('($size: heading)'), /font-size: var\(--cedar-font-size-element-heading\)/);
  assert.match(compile(''), /\[aria-current\] \{\s*font-weight: var\(--cedar-font-weight-medium\)/);
  assert.throws(() => compile('($size: huge)'), /Breadcrumb size/);
});

test('resource cards share one minimum width role and clamp names to two lines', () => {
  const css = sass.compileString(
    `@use 'patterns'; ul { @include patterns.resource-grid; } li { @include patterns.resource-card-name; }`,
    { loadPaths: [process.cwd()] },
  ).css;
  assert.match(css, /minmax\(min\(100%, var\(--cedar-resource-card-min-width\)\), 1fr\)/);
  assert.match(css, /-webkit-line-clamp: 2/);
  assert.match(css, /max-height: calc\(2 \* var\(--cedar-font-size-heading\)\)/);
});
