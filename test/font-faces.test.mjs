import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { fontFaces, fontFaceSet, registerFontFaces } from '../dist/font-faces.js';

/** A document as far as registration touches one: a head that holds style elements. */
function documentStub() {
  const head = {
    children: [],
    querySelector(selector) {
      const set = selector.match(/^style\[data-cedar-font-faces="([^"]+)"\]$/)?.[1];
      return this.children.find((style) => style.attributes['data-cedar-font-faces'] === set) ?? null;
    },
    append(style) {
      this.children.push(style);
    },
  };
  return {
    head,
    createElement(tag) {
      return {
        tag,
        attributes: {},
        textContent: '',
        setAttribute(name, value) {
          this.attributes[name] = value;
        },
      };
    },
  };
}

const faces = (css) => [...css.matchAll(/url\(data:font\/woff2;base64,([^)]+)\)/g)].map((match) => match[1]);

test('the module carries the faces fonts.css registers, and nothing else', async () => {
  const linked = await readFile(new URL('../dist/fonts.css', import.meta.url), 'utf8');
  assert.equal(faces(fontFaces).length, 14);
  assert.deepEqual(faces(fontFaces), faces(linked));
  assert.equal(fontFaces.match(/@font-face/g).length, fontFaces.match(/\{/g).length);
  assert.match(fontFaceSet, /^[0-9a-f]{16}$/);
});

test('a document registers a set of faces once, however many components ask', () => {
  const document = documentStub();
  registerFontFaces(document, 'abc123');
  registerFontFaces(document);
  assert.equal(document.head.children.length, 1);
  const [style] = document.head.children;
  assert.equal(style.tag, 'style');
  assert.equal(style.textContent, fontFaces);
  assert.equal(style.attributes['data-cedar-font-faces'], fontFaceSet);
  assert.equal(style.attributes.nonce, 'abc123');
});

test('another set of faces, from a component built on another release, registers beside it', () => {
  const document = documentStub();
  const other = document.createElement('style');
  other.setAttribute('data-cedar-font-faces', '0000000000000000');
  document.head.append(other);
  registerFontFaces(document, null);
  assert.equal(document.head.children.length, 2);
  assert.equal(document.head.children[1].attributes.nonce, undefined);
});
