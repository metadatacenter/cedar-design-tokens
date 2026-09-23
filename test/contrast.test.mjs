import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const css = readFileSync(new URL('../dist/custom-properties.css', import.meta.url), 'utf8');
const tokens = new Map([...css.matchAll(/--cedar-([\w-]+):\s*([^;]+);/g)].map((m) => [m[1], m[2].trim()]));
function luminance(hex) {
  assert.match(hex, /^#[\da-f]{3}(?:[\da-f]{3})?$/i);
  let value = hex.slice(1);
  if (value.length === 3) value = [...value].map((x) => x + x).join('');
  return [0.2126, 0.7152, 0.0722].reduce((sum, weight, i) => {
    const c = parseInt(value.slice(i * 2, i * 2 + 2), 16) / 255;
    return sum + weight * (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
  }, 0);
}
for (const state of ['error', 'warning', 'success', 'info']) {
  test(`${state} status pair meets normal-text AA contrast`, () => {
    const values = ['text', 'surface'].map((role) => luminance(tokens.get(`status-${state}-${role}`)));
    const ratio = (Math.max(...values) + 0.05) / (Math.min(...values) + 0.05);
    assert.ok(ratio >= 4.5, `${state} contrast is ${ratio}`);
  });
}
