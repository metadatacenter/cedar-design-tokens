// Builds dist/font-faces.js, which registers the embedded CEDAR font faces in a document once.
//
// Browsers register an @font-face only from a document, never from a shadow root. A component that
// declared the faces as the styles of an unencapsulated Angular component put them into the document
// and also into every shadow root on the page, where nothing reads them. A component calls this
// module instead, so a page that holds several CEDAR components registers each set of faces once.
import { createHash } from 'node:crypto';
import { mkdir, rm, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import * as sass from 'sass';

const root = new URL('../', import.meta.url);
const { css } = sass.compile(fileURLToPath(new URL('css/fonts.scss', root)), { style: 'compressed' });
// Two components built from different releases may embed different faces, and each set registers.
const set = createHash('sha256').update(css).digest('hex').slice(0, 16);

await mkdir(new URL('dist/', root), { recursive: true });
// Hosted applications let the browser request only the unicode subsets in use. Keep the
// embedded exports below unchanged for standalone components and offline single-file use.
await rm(new URL('dist/fonts/', root), { recursive: true, force: true });
await mkdir(new URL('dist/fonts/', root), { recursive: true });
const fonts = new Map();
const hosted = css.replace(/url\(data:font\/woff2;base64,([^)]+)\)/g, (_, base64) => {
  const bytes = Buffer.from(base64, 'base64');
  const name = createHash('sha256').update(bytes).digest('hex') + '.woff2';
  fonts.set(name, bytes);
  return `url('./fonts/${name}')`;
});
for (const [name, bytes] of fonts) await writeFile(new URL(`dist/fonts/${name}`, root), bytes);
await writeFile(new URL('dist/fonts-hosted.css', root), hosted + '\n');
await writeFile(
  new URL('dist/font-faces.js', root),
  '// Generated from scss/_fonts.scss by tools/build-fonts.mjs.\n' +
    `export const fontFaces = ${JSON.stringify(css)};\n` +
    `export const fontFaceSet = ${JSON.stringify(set)};\n` +
    'export function registerFontFaces(document, nonce) {\n' +
    "  if (document.head.querySelector('style[data-cedar-font-faces=\"' + fontFaceSet + '\"]')) return;\n" +
    "  const style = document.createElement('style');\n" +
    "  style.setAttribute('data-cedar-font-faces', fontFaceSet);\n" +
    "  if (nonce) style.setAttribute('nonce', nonce);\n" +
    '  style.textContent = fontFaces;\n' +
    '  document.head.append(style);\n' +
    '}\n',
);
await writeFile(
  new URL('dist/font-faces.d.ts', root),
  '/** The CEDAR Roboto 400 and 500 faces, as compressed CSS. */\n' +
    'export declare const fontFaces: string;\n' +
    '/** What identifies this set of faces among those a page registers. */\n' +
    'export declare const fontFaceSet: string;\n' +
    '/**\n' +
    " * Registers the faces in the document's head, unless a component has registered the same set\n" +
    ' * already. `nonce` is the nonce of a page whose content security policy requires one.\n' +
    ' */\n' +
    'export declare function registerFontFaces(document: Document, nonce?: string | null): void;\n',
);
console.log(`Built the CEDAR font faces module, set ${set}.`);
