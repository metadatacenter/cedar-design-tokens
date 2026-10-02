// The complete shared vocabulary. A token joins this list only for a role no existing token covers,
// and together with the consumer that needs it: `cedarcli check design-tokens --strict` fails on a
// token that nothing reads. A consumer that wants a value between two of these uses the nearer one.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const inventory = {
  typography: [
    'font-family',
    'font-family-monospace',
    'font-weight-regular',
    'font-weight-medium',
    'font-size-small',
    'font-size',
    'font-size-element-heading',
    'font-size-heading',
    'font-size-artifact-title',
    'line-height-heading',
  ],
  colour: [
    'color-primary',
    'color-primary-strong',
    'color-on-primary',
    'text-primary',
    'text-muted',
    'text-title',
    'border-rule',
    'control-border-default',
    'surface-raised',
    'surface-subtle',
    'surface-selected',
    'status-error-text',
    'status-error-surface',
    'status-warning-text',
    'status-warning-surface',
    'status-success-text',
    'status-success-surface',
    'status-unsaved-dot',
    'dialog-backdrop',
  ],
  controls: [
    'control-height-default',
    'control-height-authoring',
    'control-line-height-default',
    'control-line-height-authoring',
    'control-disabled-opacity',
    'textarea-min-rows-default',
    'focus-ring-width',
    'focus-ring-offset',
    'row-height-compact',
    'table-row-height',
  ],
  space: ['space-1', 'space-2', 'space-3', 'space-4', 'space-6'],
  shape: [
    'radius',
    'radius-pill',
    'icon-size-small',
    'icon-size-default',
    'icon-size-large',
    'shadow-overlay',
    'shadow-dialog',
  ],
  motion: [
    'motion-duration-fast',
    'motion-duration-normal',
    'motion-duration-spinner',
    'motion-ease-standard',
    'motion-ease-enter',
  ],
  layers: ['layer-sticky', 'layer-menu', 'layer-modal', 'layer-overlay', 'layer-tooltip'],
};

const emitted = [
  ...readFileSync(new URL('../dist/custom-properties.css', import.meta.url), 'utf8').matchAll(/--cedar-([\w-]+)\s*:/g),
].map((match) => match[1]);

test('the emitted tokens are exactly the reviewed inventory', () => {
  assert.deepEqual([...emitted].sort(), Object.values(inventory).flat().sort());
});

test('the type scale has five sizes and two weights', () => {
  assert.equal(inventory.typography.filter((name) => name.startsWith('font-size')).length, 5);
  assert.equal(inventory.typography.filter((name) => name.startsWith('font-weight')).length, 2);
});

test('there is one theme colour, three text colours and three surfaces', () => {
  assert.equal(inventory.colour.filter((name) => /^color-primary/.test(name)).length, 2);
  assert.equal(inventory.colour.filter((name) => name.startsWith('text-')).length, 3);
  assert.equal(inventory.colour.filter((name) => name.startsWith('surface-')).length, 3);
});

test('retired names stay retired', () => {
  const retired = JSON.parse(readFileSync(new URL('../tools/retired-tokens.json', import.meta.url), 'utf8'));
  for (const name of Object.keys(retired)) assert.ok(!emitted.includes(name), `${name} was retired`);
});
