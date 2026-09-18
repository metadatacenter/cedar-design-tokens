import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync, mkdirSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { verifyCandidate } from '../tools/verify-candidate.mjs';

test('candidate verification rejects stale content even with an identical version', () => {
  const root = mkdtempSync(join(tmpdir(), 'cedar-candidate-'));
  try {
    for (const dir of ['candidate', 'installed']) {
      mkdirSync(join(root, dir, 'fonts'), { recursive: true });
      writeFileSync(
        join(root, dir, 'package.json'),
        JSON.stringify({ name: 'tokens', version: '1.0.0', files: ['fonts/'] }),
      );
      writeFileSync(join(root, dir, 'fonts/font.scss'), 'current');
    }
    const source = join(root, 'candidate');
    const installed = join(root, 'installed');
    verifyCandidate(source, installed);
    writeFileSync(join(installed, 'fonts/font.scss'), 'stale');
    assert.throws(() => verifyCandidate(source, installed), /fonts\/font.scss/);
    rmSync(join(installed, 'fonts/font.scss'));
    assert.throws(() => verifyCandidate(source, installed), /ENOENT/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
