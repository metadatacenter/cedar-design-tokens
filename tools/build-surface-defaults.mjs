// Generated Sass defaults let the Python adoption check stay build-free in consumer CI.
import { readFileSync, writeFileSync } from 'node:fs';
import * as sass from 'sass';
const root = new URL('../', import.meta.url);
const { contracts, scale } = JSON.parse(readFileSync(new URL('surfaces/contracts.json', root), 'utf8'));
const needed = new Set([
  ...Object.values(contracts).flatMap((rules) => Object.values(rules)),
  ...Object.values(scale).flat(),
]);
const css = sass.compile(new URL('tokens.entry.scss', root).pathname).css;
const defaults = Object.fromEntries(
  [...css.matchAll(/(--cedar-[\w-]+):\s*([^;]+);/g)]
    .filter(([, name]) => needed.has(name))
    .map(([, name, value]) => [name, value]),
);
if (Object.keys(defaults).length !== needed.size) throw new Error('Surface contract references an unknown token');
writeFileSync(new URL('surfaces/token-defaults.json', root), JSON.stringify(defaults, null, 2) + '\n');
