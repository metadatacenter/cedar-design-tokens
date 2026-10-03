import test from 'node:test';
import assert from 'node:assert/strict';
import * as sass from 'sass';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';

const roles = new Set(
  [...readFileSync('dist/custom-properties.css', 'utf8').matchAll(/(--cedar-[\w-]+)\s*:/g)].map((m) => m[1]),
);
const hosts = JSON.parse(readFileSync('tools/host-properties.json', 'utf8'));
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
  'tabs',
  'tab',
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
  'save-state-dot',
  'save-state-dot-modified',
  'visually-hidden',
  'tooltip-surface',
  'section-heading',
  'notice',
];
for (const name of names) {
  test(`${name} uses registered shared roles and stays opt-in`, () => {
    const css = sass.compileString(`@use 'patterns'; .consumer { @include patterns.${name}; }`, {
      loadPaths: ['scss'],
    }).css;
    for (const role of css.matchAll(/var\((--cedar-[\w-]+)/g))
      assert.ok(roles.has(role[1]), `Unknown role: ${role[1]}`);
    assert.match(css, /^\.consumer/);
    if (!name.startsWith('menu-')) assert.doesNotMatch(css, /#(?:[\da-f]{3})\b|rgb\(/i);
  });
}
test('recipes emit nothing until used', () => {
  assert.equal(sass.compileString("@use 'patterns';", { loadPaths: ['scss'] }).css, '');
});

for (const name of ['field-label', 'field-help', 'field-error']) {
  test(`${name} body variant preserves the default recipe except its type role`, () => {
    const compile = (args) =>
      sass.compileString(`@use 'patterns'; .consumer { @include patterns.${name}${args}; }`, {
        loadPaths: ['scss'],
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
    loadPaths: ['scss'],
  }).css;
  assert.match(css, /resize: vertical;/);
});

test('dialog content can own padding while retaining the shared surface', () => {
  const compile = (args) =>
    sass.compileString(`@use 'patterns'; .dialog { @include patterns.dialog-surface${args}; }`, {
      loadPaths: ['scss'],
    }).css;
  assert.equal(compile('($padding: 0)'), compile('').replace('padding: var(--cedar-space-6);', 'padding: 0;'));
});

for (const name of ['specification-box', 'specification-separator', 'specification-link']) {
  test(`${name} has registered host-overridable roles with standalone fallbacks`, () => {
    const css = sass.compileString(`@use 'patterns'; .reader { @include patterns.${name}; }`, {
      loadPaths: ['scss'],
    }).css;
    for (const role of css.matchAll(/var\((--cedar-[\w-]+)/g)) {
      assert.ok(roles.has(role[1]) || role[1].replace('--', '') in hosts, role[1]);
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
    loadPaths: ['scss'],
  }).css;
  assert.match(css, /line-height: 0/);
  assert.match(css, /vertical-align: baseline/);
  assert.match(css, /position: relative/);
  assert.match(css, /inset-block-start: -0\.4em/);
});

test('breadcrumbs take the large size only when they head a listing, at one weight', () => {
  const compile = (args) =>
    sass.compileString(`@use 'patterns'; nav { @include patterns.breadcrumbs${args}; }`, {
      loadPaths: ['scss'],
    }).css;
  assert.doesNotMatch(compile(''), /font-size/);
  assert.match(compile('($size: heading)'), /font-size: var\(--cedar-font-size-large\)/);
  assert.doesNotMatch(compile(''), /font-weight/);
  assert.throws(() => compile('($size: huge)'), /Breadcrumb size/);
});

test('resource cards share one minimum width and clamp names to two lines', () => {
  const css = sass.compileString(
    `@use 'patterns'; ul { @include patterns.resource-grid; } li { @include patterns.resource-card-name; }`,
    { loadPaths: ['scss'] },
  ).css;
  assert.match(css, /minmax\(min\(100%, 190px\), 1fr\)/);
  assert.match(css, /-webkit-line-clamp: 2/);
  assert.match(css, /line-height: calc\(var\(--cedar-space-4\) \+ var\(--cedar-space-1\)\)/);
  assert.match(css, /max-height: calc\(2 \* \(var\(--cedar-space-4\) \+ var\(--cedar-space-1\)\)\)/);
});

const patterns = (source) => sass.compileString(`@use 'patterns'; ${source}`, { loadPaths: ['scss'] }).css;

test('a trail mutes its ancestors, links included, and colours the current location', () => {
  const css = patterns('.trail { @include patterns.breadcrumbs; }');
  assert.match(css, /\.trail a:not\(\[aria-current\]\) \{\s*color: var\(--cedar-text-muted\)/);
  assert.match(css, /\.trail \[aria-current\] \{\s*color: var\(--cedar-color-primary\)/);
});

test('summary issue lines take no hover fill over a host button rule', () => {
  const css = patterns('.summary { @include patterns.validation-summary; }');
  assert.match(css, /\.summary button:hover:not\(:disabled\):not\(\[aria-disabled=true\]\)[^{]*\{\s*background: none/);
});

test('notices take a status pair or the information roles, and refuse other tones', () => {
  const css = patterns('.a { @include patterns.notice; } .b { @include patterns.notice(error, $boxed: true); }');
  assert.match(
    css,
    /\.a \{[^}]*color: var\(--cedar-color-primary-strong\);[^}]*background: var\(--cedar-surface-selected\)/,
  );
  assert.match(
    css,
    /\.b \{[^}]*border-radius: var\(--cedar-radius\);[^}]*background: var\(--cedar-status-error-surface\)/,
  );
  assert.throws(() => patterns('.c { @include patterns.notice(alarm); }'), /Notice tone/);
});

test('an icon button is a small box for row actions or the control height, nothing else', () => {
  const small = patterns('a { @include patterns.icon-button; }');
  for (const property of ['width', 'min-width', 'height', 'min-height'])
    assert.match(small, new RegExp(`\\b${property}: 24px`));
  assert.match(small, /padding: 0/);
  assert.match(
    patterns('a { @include patterns.icon-button(default); }'),
    /height: var\(--cedar-control-height, var\(--cedar-control-height-default\)\)/,
  );
  assert.doesNotMatch(small, /color|background|border/);
  assert.throws(() => patterns('a { @include patterns.icon-button(large); }'), /Icon button size/);
});

test("a resource card's type icon sits in an icon slot", () => {
  const css = patterns('a { @include patterns.resource-card-heading; } b { @include patterns.resource-card-icon; }');
  assert.match(css, /min-height: var\(--cedar-icon-size-large\)/);
  assert.match(css, /flex: 0 0 var\(--cedar-icon-size-large\)/);
  assert.doesNotMatch(css, /--cedar-space-6/);
});

test('a tooltip keeps the shared surface in a shadow root whose host declares no properties', () => {
  const css = patterns('a { @include patterns.tooltip-surface; }');
  assert.match(css, /background: var\(--cedar-surface-raised, #ffffff\)/);
  assert.match(css, /color: var\(--cedar-text-primary, rgba\(0, 0, 0, 0\.87\)\)/);
  assert.match(css, /border: 1px solid var\(--cedar-border-rule, #d7e0df\)/);
});
