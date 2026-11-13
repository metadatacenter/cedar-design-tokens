import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';
import test from 'node:test';
import { surfaceRoles } from '../tools/surface-roles.mjs';
import { canonicalStyleValue } from '../surfaces/browser.mjs';
const root = new URL('../', import.meta.url);
test('font serialization preserves names, fallback order and generic-family distinctions', () => {
  const normalize = (value) => canonicalStyleValue('font-family', value);
  assert.equal(
    normalize('"CEDAR Roboto", "Helvetica Neue", sans-serif'),
    normalize('CEDAR Roboto, Helvetica Neue, sans-serif'),
  );
  assert.notEqual(
    normalize('Other Font, Helvetica Neue, sans-serif'),
    normalize('CEDAR Roboto, Helvetica Neue, sans-serif'),
  );
  assert.notEqual(
    normalize('Helvetica Neue, CEDAR Roboto, sans-serif'),
    normalize('CEDAR Roboto, Helvetica Neue, sans-serif'),
  );
  assert.notEqual(normalize('"serif"'), normalize('serif'));
  assert.equal(canonicalStyleValue('line-height', '40.1px'), '40.1px');
});
test('offline opt-in role expectations match their owning Sass recipes', () => {
  assert.deepEqual(JSON.parse(readFileSync(new URL('surfaces/role-values.json', root), 'utf8')), surfaceRoles());
});
test('offline surface defaults match the evaluated central tokens exactly', () => {
  const { contracts, scale } = JSON.parse(readFileSync(new URL('surfaces/contracts.json', root), 'utf8'));
  const needed = new Set([
    ...Object.values(contracts).flatMap((rules) => Object.values(rules)),
    ...Object.values(scale).flat(),
  ]);
  const css = readFileSync(new URL('dist/custom-properties.css', root), 'utf8');
  const expected = Object.fromEntries(
    [...css.matchAll(/(--cedar-[\w-]+):\s*([^;]+);/g)]
      .filter(([, name]) => needed.has(name))
      .map(([, name, value]) => [name, value]),
  );
  assert.equal(Object.keys(expected).length, needed.size, 'Unknown surface token');
  assert.deepEqual(
    JSON.parse(readFileSync(new URL('surfaces/token-defaults.json', root), 'utf8')),
    expected,
    'Run npm run surfaces:defaults after changing shared roles',
  );
});
