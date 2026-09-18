import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { icons, iconNames, getIcon, iconSvg, iconStyle } from '../dist/icons.js';
const manifest = JSON.parse(await readFile(new URL('../icons/manifest.json', import.meta.url)));
const aliases = JSON.parse(await readFile(new URL('../icons/aliases.json', import.meta.url)));
test('every semantic icon uses the exact pinned Lucide geometry', async () => {
  for (const [name, source] of Object.entries(manifest)) {
    const upstream = await readFile(
      new URL(`../node_modules/lucide-static/icons/${source}.svg`, import.meta.url),
      'utf8',
    );
    assert.equal(getIcon(name).body, upstream.match(/<svg\b[^>]*>([\s\S]*?)<\/svg>/)[1].trim(), name);
    assert.ok(!/script|href=|onload=|url\(/i.test(iconSvg(name)));
  }
});
test('unknown and prototype names fail instead of silently drawing a different meaning', () => {
  for (const name of ['unknown', '', '__proto__', 'constructor', '<script>'])
    assert.throws(() => iconSvg(name), /Unknown CEDAR icon/);
});
test('adapters share one semantic vocabulary with explicit compatibility aliases', () => {
  assert.deepEqual([...iconNames].sort(), Object.keys(icons).sort());
  for (const [alias, canonical] of Object.entries(aliases)) assert.deepEqual(getIcon(alias), getIcon(canonical));
  assert.notEqual(getIcon('populate').body, getIcon('artifact-instance').body);
  assert.equal(getIcon('controlledTerms').body, getIcon('field-controlled').body);
  assert.ok(Object.isFrozen(icons));
  assert.ok(Object.isFrozen(getIcon('info')));
});
test('SVG output is decorative, self-contained and inherits color rather than fonts', () => {
  for (const name of iconNames) {
    const svg = iconSvg(name);
    for (const attribute of [
      'viewBox="0 0 24 24"',
      'stroke="currentColor"',
      'fill="none"',
      'aria-hidden="true"',
      'focusable="false"',
      'stroke-width="2"',
    ])
      assert.ok(svg.includes(attribute), `${name}: ${attribute}`);
    assert.ok(!svg.includes('font-family'));
  }
});
test('icon sizing agrees with the emitted shared style tokens', async () => {
  const css = await readFile(new URL('../dist/custom-properties.css', import.meta.url), 'utf8');
  for (const size of ['small', 'default', 'large'])
    assert.ok(css.includes(`--cedar-icon-size-${size}: ${iconStyle[size]}px;`));
  assert.ok(css.includes(`--cedar-icon-stroke-width: ${iconStyle.strokeWidth};`));
});
test('the packaged icons retain upstream license attribution', async () => {
  assert.equal(
    await readFile(new URL('../icons/LICENSE', import.meta.url), 'utf8'),
    await readFile(new URL('../node_modules/lucide-static/LICENSE', import.meta.url), 'utf8'),
  );
});
