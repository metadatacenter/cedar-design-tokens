import { readFile, writeFile, mkdir } from 'node:fs/promises';
const root = new URL('../', import.meta.url);
const read = async (path) => JSON.parse(await readFile(new URL(path, root), 'utf8'));
const manifest = await read('icons/manifest.json');
const aliases = await read('icons/aliases.json');
const upstream = await read('node_modules/lucide-static/package.json');
const icons = {};
for (const [name, source] of Object.entries(manifest)) {
  const svg = await readFile(new URL(`node_modules/lucide-static/icons/${source}.svg`, root), 'utf8');
  const body = svg.match(/<svg\b[^>]*>([\s\S]*?)<\/svg>/)?.[1].trim();
  if (!body || /<(?!\/?(?:path|circle|rect|line|polyline|polygon|ellipse)\b)|\b(?:on\w+|href|style)=/i.test(body))
    throw new Error(`Unsafe or unsupported upstream SVG: ${source}`);
  icons[name] = { name, source, body };
}
for (const [alias, name] of Object.entries(aliases)) {
  if (icons[alias] || !icons[name]) throw new Error(`Invalid alias: ${alias}`);
  icons[alias] = icons[name];
}
await mkdir(new URL('dist/', root), { recursive: true });
await writeFile(
  new URL('dist/icons.js', root),
  `// Generated from lucide-static ${upstream.version}; see icons/LICENSE.\n` +
    `const definitions = ${JSON.stringify(Object.fromEntries(Object.keys(manifest).map((name) => [name, icons[name]])))};\n` +
    `for (const [alias, name] of Object.entries(${JSON.stringify(aliases)})) definitions[alias] = definitions[name];\n` +
    `for (const icon of Object.values(definitions)) Object.freeze(icon);\n` +
    `export const icons = Object.freeze(definitions);\n` +
    `export const iconNames = Object.freeze(Object.keys(icons));\n` +
    `export const iconStyle = Object.freeze({viewBox: '0 0 24 24', strokeWidth: 2, small: 16, default: 20, large: 24});\n` +
    `export function getIcon(name) { if (!Object.hasOwn(icons, name)) throw new Error('Unknown CEDAR icon: ' + name); return icons[name]; }\n` +
    `export function iconSvg(name) { return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false" data-cedar-icon="' + getIcon(name).name + '">' + getIcon(name).body + '</svg>'; }\n`,
);
await writeFile(
  new URL('dist/icons.d.ts', root),
  `export type IconName = ${Object.keys(icons).map(JSON.stringify).join(' | ')};\nexport interface IconDefinition { readonly name: IconName; readonly source: string; readonly body: string; }\nexport declare const icons: Readonly<Record<IconName, IconDefinition>>;\nexport declare const iconNames: readonly IconName[];\nexport declare const iconStyle: Readonly<{viewBox: string; strokeWidth: number; small: number; default: number; large: number}>;\nexport declare function getIcon(name: string): IconDefinition;\nexport declare function iconSvg(name: string): string;\n`,
);
await writeFile(new URL('icons/LICENSE', root), await readFile(new URL('node_modules/lucide-static/LICENSE', root)));
console.log(`Built ${Object.keys(manifest).length} CEDAR icons from Lucide ${upstream.version}.`);

// The same registry is available to hosts without a JavaScript module loader.
await writeFile(
  new URL('dist/icons.svg', root),
  '<svg xmlns="http://www.w3.org/2000/svg">' +
    Object.keys(manifest)
      .map(
        (name) =>
          '<symbol id="' +
          name +
          '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
          icons[name].body +
          '</symbol>',
      )
      .join('') +
    '</svg>\n',
);
