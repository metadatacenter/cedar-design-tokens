import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const css = readFileSync(new URL('../dist/custom-properties.css', import.meta.url), 'utf8');
const tokens = new Map([...css.matchAll(/--cedar-([\w-]+):\s*([^;]+);/g)].map((m) => [m[1], m[2].trim()]));
// Composite a translucent black colour over its surface before measuring it.
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
function contrast(foreground, surface) {
  const under = rgb(tokens.get(surface));
  const values = [luminance(rgb(tokens.get(foreground), under)), luminance(under)];
  return (Math.max(...values) + 0.05) / (Math.min(...values) + 0.05);
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
    const ratio = contrast(text, surface);
    assert.ok(ratio >= 4.5, `${text} on ${surface}: ${ratio.toFixed(2)}`);
  });
}
// WCAG 1.4.11 requires 3:1 contrast between a control's boundary, a state indicator or an icon and
// the colours adjacent to it. Each pair is a role documented as one of those and a surface it is
// drawn on. Rules are absent because they divide content rather than frame a control, and the
// backdrop is absent because a scrim is neither a boundary nor an indicator.
const nonTextPairs = [
  // Control outlines frame what a person can edit. Controls sit on the raised surface of a page,
  // card, menu or dialog, and on the subtle surface of a panel.
  ['control-border-default', 'surface-raised'],
  ['control-border-default', 'surface-subtle'],
  // The focus ring, icons and selection marks take the theme colour on every surface. An active
  // filter chip's outline and chevron lie on the selection surface, as does a hovered action's icon.
  ['color-primary', 'surface-raised'],
  ['color-primary', 'surface-subtle'],
  ['color-primary', 'surface-selected'],
  // A filled action's icons take the on-primary colour, at rest and when hovered.
  ['color-on-primary', 'color-primary'],
  ['color-on-primary', 'color-primary-strong'],
  // An information notice's icon takes the strong theme colour on the selection surface.
  ['color-primary-strong', 'surface-selected'],
  // Icons take a status colour on its own surface, in notices and validation summaries, and on the
  // raised and subtle surfaces. An invalid control's border, an invalid card's outline and the
  // save-state mark take one on those two surfaces as well.
  ['status-error-text', 'status-error-surface'],
  ['status-error-text', 'surface-raised'],
  ['status-error-text', 'surface-subtle'],
  ['status-warning-text', 'status-warning-surface'],
  ['status-warning-text', 'surface-raised'],
  ['status-warning-text', 'surface-subtle'],
  ['status-success-text', 'status-success-surface'],
  ['status-success-text', 'surface-raised'],
  ['status-success-text', 'surface-subtle'],
];
// These pairs fall short of 3:1 today, and each carries the reason its value stays. A recorded pair
// must still fail, so changing an approved value means removing its record.
const outlineReason =
  "A darker control outline would change every consumer's controls, and that visual change awaits a design decision.";
const knownNonTextFailures = new Map([
  ['control-border-default on surface-raised', outlineReason],
  ['control-border-default on surface-subtle', outlineReason],
]);
for (const [part, surface] of nonTextPairs) {
  const pair = `${part} on ${surface}`;
  const reason = knownNonTextFailures.get(pair);
  if (reason) {
    test(`${pair} remains a recorded non-text contrast failure`, (t) => {
      t.diagnostic(reason);
      const ratio = contrast(part, surface);
      assert.ok(ratio < 3, `${pair} now reaches ${ratio.toFixed(2)}. Remove its record.`);
    });
  } else {
    test(`${pair} meets non-text contrast`, () => {
      const ratio = contrast(part, surface);
      assert.ok(ratio >= 3, `${pair}: ${ratio.toFixed(2)}`);
    });
  }
}
test('every recorded non-text failure is a checked pair', () => {
  const checked = new Set(nonTextPairs.map(([part, surface]) => `${part} on ${surface}`));
  assert.deepEqual(
    [...knownNonTextFailures.keys()].filter((pair) => !checked.has(pair)),
    [],
  );
});
