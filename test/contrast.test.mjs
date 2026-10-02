import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const css = readFileSync(new URL('../dist/custom-properties.css', import.meta.url), 'utf8');
const tokens = new Map([...css.matchAll(/--cedar-([\w-]+):\s*([^;]+);/g)].map((m) => [m[1], m[2].trim()]));
// Composite a translucent black text colour over its surface before measuring it.
function rgb(value, under = [255, 255, 255]) {
  const alpha = value.match(/^rgba\(0, 0, 0, ([\d.]+)\)$/);
  if (alpha) return under.map((c) => c * (1 - Number(alpha[1])));
  assert.match(value, /^#[\da-f]{3}(?:[\da-f]{3})?$/i);
  let hex = value.slice(1);
  if (hex.length === 3) hex = [...hex].map((x) => x + x).join('');
  return [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16));
}
function luminance(channels) {
  return channels.reduce((sum, value, i) => {
    const c = value / 255;
    return sum + [0.2126, 0.7152, 0.0722][i] * (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
  }, 0);
}
// Every text role on every surface it is drawn on reaches normal-text AA contrast.
const pairs = [
  ['status-error-text', 'status-error-surface'],
  ['status-warning-text', 'status-warning-surface'],
  ['status-success-text', 'status-success-surface'],
  ['color-primary-strong', 'surface-selected'],
  ['color-primary', 'surface-raised'],
  ['color-on-primary', 'color-primary'],
  ['color-on-primary', 'color-primary-strong'],
  ['text-primary', 'surface-subtle'],
  ['text-primary', 'surface-selected'],
  ['text-muted', 'surface-raised'],
  ['text-muted', 'surface-subtle'],
  ['text-muted', 'surface-selected'],
  ['text-title', 'surface-raised'],
];
for (const [text, surface] of pairs) {
  test(`${text} on ${surface} meets normal-text AA contrast`, () => {
    const under = rgb(tokens.get(surface));
    const values = [luminance(rgb(tokens.get(text), under)), luminance(under)];
    const ratio = (Math.max(...values) + 0.05) / (Math.min(...values) + 0.05);
    assert.ok(ratio >= 4.5, `${text} on ${surface}: ${ratio.toFixed(2)}`);
  });
}
