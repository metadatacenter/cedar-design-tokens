import test from 'node:test';
import assert from 'node:assert/strict';
import * as sass from 'sass';

const compile = (body) => sass.compileString(`@use 'monitoring'; ${body}`, { loadPaths: ['scss'] }).css;

test('Monitoring is opt-in and emits no global declarations', () => {
  assert.equal(compile(''), '');
});

test('each Monitoring category retains its own override and approved default', () => {
  const cases = [
    ['http-method-text(get)', 'http-get-text', '#0f7686'],
    ['http-method-text(post)', 'http-post-text', '#6b4fc4'],
    ['http-method-text(put)', 'http-put-text', '#b45309'],
    ['http-method-text(patch)', 'http-patch-text', '#b45309'],
    ['http-method-text(delete)', 'http-delete-text', '#b42318'],
    ['trace-text(request)', 'trace-request-text', '#0f7686'],
    ['trace-text(cypher)', 'trace-cypher-text', '#6b4fc4'],
    ['trace-bar(request)', 'trace-request-bar', '#0f7686'],
    ['trace-bar(cypher)', 'trace-cypher-bar', '#8c74d8'],
    ['masked-secret-text()', 'masked-secret-text', '#6941c6'],
  ];
  for (const [call, role, value] of cases) {
    const css = compile(`.consumer { color: monitoring.${call}; }`);
    assert.equal(css, `.consumer {\n  color: var(--cedar-monitor-${role}, ${value});\n}`);
  }
  assert.equal(new Set(cases.map(([, role]) => role)).size, cases.length);
});

test('informational emphasis exposes its override without disabled-control coupling', () => {
  for (const [state, value] of Object.entries({
    'count-note': 0.75,
  })) {
    assert.equal(
      compile(`.consumer { opacity: monitoring.state-opacity(${state}); }`),
      `.consumer {\n  opacity: var(--cedar-monitor-${state}-opacity, ${value});\n}`,
    );
  }
});

test('copy feedback has independent surface and text overrides', () => {
  assert.equal(
    compile('.consumer { @include monitoring.copy-toast-colors; }'),
    '.consumer {\n  background: var(--cedar-monitor-copy-toast-surface, #21303f);\n  color: var(--cedar-monitor-copy-toast-text, #ffffff);\n}',
  );
});

test('unknown Monitoring categories and states fail compilation', () => {
  for (const call of [
    'http-method-text(head)',
    'trace-text(other)',
    'trace-bar(other)',
    'state-opacity(disabled)',
    'state-opacity(empty-value)',
  ]) {
    assert.throws(() => compile(`.consumer { color: monitoring.${call}; }`), /Unknown/);
  }
});
