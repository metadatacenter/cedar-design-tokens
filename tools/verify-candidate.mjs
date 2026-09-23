// Run from the consumer's package directory after installing the candidate tarball.
// A version match alone cannot distinguish a candidate from an older published build.
import { readFileSync, readdirSync } from 'node:fs';
import { resolve, join } from 'node:path';
import assert from 'node:assert/strict';

export function verifyCandidate(candidate, installed) {
  const manifest = JSON.parse(readFileSync(join(candidate, 'package.json'), 'utf8'));
  const actual = JSON.parse(readFileSync(join(installed, 'package.json'), 'utf8'));
  assert.equal(actual.name, manifest.name);
  assert.equal(actual.version, manifest.version);
  function compare(relative) {
    const source = join(candidate, relative);
    if (relative.endsWith('/')) {
      for (const entry of readdirSync(source, { withFileTypes: true }))
        compare(relative + entry.name + (entry.isDirectory() ? '/' : ''));
    } else {
      assert.deepEqual(readFileSync(join(installed, relative)), readFileSync(source), relative);
    }
  }
  for (const entry of manifest.files) compare(entry);
}

if (process.argv[1] && resolve(process.argv[1]) === new URL(import.meta.url).pathname) {
  verifyCandidate(resolve(process.argv[2]), resolve('node_modules/@org.metadatacenter/cedar-design-tokens'));
  console.log('Installed candidate matches every published file byte for byte.');
}
