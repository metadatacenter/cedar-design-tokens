import { expect, test } from '@playwright/test';
import { VIEWPORTS, check, measure } from '../../surfaces/layout-resilience.mjs';

// Each fixture is built to produce exactly one finding, or none. A checker that misses what a fixture
// holds, or reports what it does not, fails here before any component relies on it.

const STATE = 'fixture';

/** Opens `body` at the viewport `check` measures in. */
async function open(page, which, body, css = '') {
  await page.setViewportSize(VIEWPORTS[which]);
  await page.setContent(
    `<!doctype html><html lang="en"><head><style>body { margin: 0; font: 16px/1.4 sans-serif; } ${css}</style>` +
      `</head><body>${body}</body></html>`,
  );
}

/** The findings no exception or region excuses. */
const unexcused = (report) => report.findings.filter((finding) => !finding.excused);

test('reaches native inputs across a scrolling shadow root', async ({ page }) => {
  await open(page, 'resize', '<div id="host"></div>');
  await page.locator('#host').evaluate((host) => {
    host.attachShadow({ mode: 'open' }).innerHTML = Array.from(
      { length: 8 },
      (_, i) => `<div style="height: 300px"><input aria-label="Field ${i}"></div>`,
    ).join('');
  });
  const report = await measure(page, { check: 'resize', state: STATE });
  expect(report.measured.controls).toBe(8);
  expect(report.failures).toEqual([]);
});

test('still rejects a shadow input covered inside or outside its root', async ({ page }) => {
  for (const inside of [true, false]) {
    await open(page, 'resize', '<div id="host" style="position: relative"></div>');
    await page.locator('#host').evaluate((host, inside) => {
      const root = host.attachShadow({ mode: 'open' });
      root.innerHTML = '<input aria-label="Covered">';
      const cover = document.createElement('div');
      cover.className = 'cover';
      cover.style.cssText = 'position: absolute; inset: 0; background: white';
      (inside ? root : host.parentElement).appendChild(cover);
    }, inside);
    const report = await measure(page, { check: 'resize', state: STATE });
    expect(report.failures).toEqual([expect.stringMatching(/^unreachable: .*Covered.*div.cover/)]);
  }
});

test.describe('reflow at 320 CSS px', () => {
  test('fails a page that scrolls sideways', async ({ page }) => {
    await open(page, 'reflow', '<div style="width: 400px">Content wider than the window</div>');
    const report = await measure(page, { check: 'reflow', state: STATE });
    expect(report.failures).toEqual(['page scrolls: the page (400px of content in 320px)']);
  });

  const table =
    '<section class="data" style="overflow-x: auto"><table><tr>' +
    '<td style="white-space: nowrap">A cell whose text is wider than the window</td>' +
    '<td style="white-space: nowrap">Another cell as wide again</td></tr></table></section>';
  const inPlace = { selector: '.data', why: 'A table of cells read across as well as down.' };

  test('passes a table that scrolls in its own region', async ({ page }) => {
    await open(page, 'reflow', table);
    const report = await measure(page, { check: 'reflow', state: STATE, scrollsInPlace: [inPlace] });
    expect(report.failures).toEqual([]);
    expect(report.findings.map(({ kind, excused }) => [kind, excused])).toEqual([['scrolls', true]]);
  });

  test('fails the same region where it is not recorded', async ({ page }) => {
    await open(page, 'reflow', table);
    const report = await measure(page, { check: 'reflow', state: STATE });
    expect(report.failures).toEqual([
      expect.stringMatching(/^scrolls: section\.data "A cell whose .*" \(\d+px of content in 320px\)$/),
    ]);
  });

  test('gives no allowance to a recorded region that holds no table', async ({ page }) => {
    await open(page, 'reflow', '<div class="data" style="overflow-x: auto"><div style="width: 600px">Wide</div></div>');
    const report = await measure(page, { check: 'reflow', state: STATE, scrollsInPlace: [inPlace] });
    expect(report.failures).toEqual(['scrolls: div.data "Wide" (600px of content in 320px)']);
  });

  test('fails a region recorded for a state in which it does not scroll', async ({ page }) => {
    await open(
      page,
      'reflow',
      '<section class="data" style="overflow-x: auto"><table><tr><td>Fits</td></tr></table></section>',
    );
    const report = await measure(page, {
      check: 'reflow',
      state: STATE,
      scrollsInPlace: [{ ...inPlace, states: [STATE] }],
    });
    expect(report.failures).toEqual(['listed as scrolling in place but not scrolling: .data']);
  });
});

test.describe('resize to 640 by 400', () => {
  const name = 'A name far too long for its box';
  const shortened = (attributes = '') =>
    `<p class="name" ${attributes} style="margin: 0; width: 120px; overflow: hidden; white-space: nowrap; ` +
    `text-overflow: ellipsis">${name}</p>`;

  test('fails text cut by an ellipsis that no title holds', async ({ page }) => {
    await open(page, 'resize', shortened());
    const report = await measure(page, { check: 'resize', state: STATE });
    expect(report.failures).toEqual([
      expect.stringMatching(
        /^ellipsis: p\.name "A name far too long for its box" \("A name far too long for its box": \d+x\d+ in 120x\d+, and no title, name or description holds the whole\)$/,
      ),
    ]);
  });

  test('passes the same text where a title holds it whole', async ({ page }) => {
    await open(page, 'resize', shortened(`title="${name}"`));
    expect((await measure(page, { check: 'resize', state: STATE })).failures).toEqual([]);
  });

  test('fails the same text where a title holds only part of it', async ({ page }) => {
    await open(page, 'resize', shortened('title="A name"'));
    const report = await measure(page, { check: 'resize', state: STATE });
    expect(unexcused(report).map(({ kind }) => kind)).toEqual(['ellipsis']);
  });

  test('passes the same text where a description holds it whole', async ({ page }) => {
    await open(page, 'resize', `${shortened('aria-describedby="full"')}<span id="full" hidden>${name}</span>`);
    expect((await measure(page, { check: 'resize', state: STATE })).failures).toEqual([]);
  });

  test('fails a control clipped out of reach by a box that hides its overflow', async ({ page }) => {
    await open(
      page,
      'resize',
      '<div class="frame" style="width: 200px; height: 40px; overflow: hidden"><div style="height: 60px"></div>' +
        '<button class="save" aria-label="Save" style="width: 24px; height: 24px"></button></div>',
    );
    const report = await measure(page, { check: 'resize', state: STATE });
    expect(report.failures).toEqual([
      'unreachable: div.frame > button.save "Save" (it lies outside div.frame, which hides its overflow)',
    ]);
  });

  test('fails a control fixed below the viewport', async ({ page }) => {
    await open(
      page,
      'resize',
      '<div style="position: fixed; top: 420px; left: 0">' +
        '<button class="save" aria-label="Save" style="width: 24px; height: 24px"></button></div>',
    );
    const report = await measure(page, { check: 'resize', state: STATE });
    expect(report.failures).toEqual(['unreachable: button.save "Save" (it cannot be scrolled into view: 0,420 24x24)']);
  });

  test('fails a control that something else covers', async ({ page }) => {
    await open(
      page,
      'resize',
      '<div style="position: relative"><button class="save" aria-label="Save" style="width: 24px; height: 24px">' +
        '</button><div class="cover" style="position: absolute; inset: 0; background: #ffffff"></div></div>',
    );
    const report = await measure(page, { check: 'resize', state: STATE });
    expect(report.failures).toEqual([
      'unreachable: button.save "Save" (no point across it reaches it, and its centre shows div.cover)',
    ]);
  });

  test('passes a control that a dialog covers until it closes', async ({ page }) => {
    await open(
      page,
      'resize',
      '<button class="save" aria-label="Save" style="width: 24px; height: 24px"></button>' +
        '<div role="dialog" aria-label="Notice" style="position: fixed; inset: 0; background: #ffffff">' +
        '<button>Close</button></div>',
    );
    const report = await measure(page, { check: 'resize', state: STATE });
    expect(report.failures).toEqual([]);
    expect(report.measured.controls).toBe(2);
  });

  test('passes a control the page scrolls to', async ({ page }) => {
    await open(page, 'resize', '<div style="height: 900px"></div><button>Further down</button>');
    const report = await measure(page, { check: 'resize', state: STATE });
    expect(report.failures).toEqual([]);
    expect(report.measured.controls).toBe(1);
  });

  const labels = (second) =>
    '<div style="position: relative; height: 40px"><span class="first" style="position: absolute; left: 0; top: 0">' +
    `First label</span><span class="second" style="position: absolute; left: 12px; top: 4px; ${second}">` +
    'Second label</span></div>';

  test('fails text drawn over other text', async ({ page }) => {
    await open(page, 'resize', labels(''));
    const report = await measure(page, { check: 'resize', state: STATE });
    expect(report.failures).toEqual([
      expect.stringMatching(
        /^overlap: span\.first "First label" \([\d.]+x[\d.]+px over span\.second "Second label"\)$/,
      ),
    ]);
  });

  test('passes text that an opaque surface on top hides', async ({ page }) => {
    await open(page, 'resize', labels('background: #ffffff'));
    expect((await measure(page, { check: 'resize', state: STATE })).failures).toEqual([]);
  });
});

test.describe('text spacing at 1280 CSS px', () => {
  // Monospace advances about 0.6em a character, so twenty fit in 13.2em until the spacing adds 0.12em
  // to each and the line wraps into a box one line high.
  const box = (height) =>
    `<div class="tight" style="font: 16px monospace; width: 13.2em; height: ${height}; overflow: hidden">` +
    'Spacing wraps around</div>';

  test('fails text that the spacing pushes out of its box', async ({ page }) => {
    await open(page, 'spacing', box('26px'));
    const report = await measure(page, { check: 'spacing', state: STATE });
    expect(report.failures).toEqual([
      expect.stringMatching(
        /^clipped: div\.tight "Spacing wraps around" \("Spacing wraps around": \d+x\d+ in \d+x26\)$/,
      ),
    ]);
  });

  test('passes the same box without the spacing', async ({ page }) => {
    await open(page, 'resize', box('26px'));
    expect((await measure(page, { check: 'resize', state: STATE })).failures).toEqual([]);
  });

  test('passes a box that grows with its text', async ({ page }) => {
    await open(page, 'spacing', box('auto'));
    expect((await measure(page, { check: 'spacing', state: STATE })).failures).toEqual([]);
  });

  test('fails text that a more specific rule keeps from the spacing', async ({ page }) => {
    await open(page, 'spacing', '<p class="fixed">Spacing set apart</p>', '.fixed { letter-spacing: 0 !important; }');
    const report = await measure(page, { check: 'spacing', state: STATE });
    expect(report.failures).toEqual([
      'text spacing does not reach: p.fixed "Spacing set apart" (line height 24px, letter spacing normal, word spacing 2.56px at 16px)',
    ]);
  });
});

test.describe('recorded exceptions', () => {
  const shortened =
    '<p class="name" style="margin: 0; width: 120px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis">' +
    'A name far too long for its box</p>';
  const exception = { check: 'resize', kind: 'ellipsis', selector: 'p.name', states: [STATE], why: 'Waits on a wrap.' };

  test('excuse the finding they match', async ({ page }) => {
    await open(page, 'resize', shortened);
    const report = await measure(page, { check: 'resize', state: STATE, exceptions: [exception] });
    expect(report.failures).toEqual([]);
    expect(report.findings.map(({ kind, excused }) => [kind, excused])).toEqual([['ellipsis', true]]);
  });

  test('fail once they match nothing', async ({ page }) => {
    await open(page, 'resize', '<p>Nothing to excuse</p>');
    const report = await measure(page, { check: 'resize', state: STATE, exceptions: [exception] });
    expect(report.failures).toEqual(['listed but not found: ellipsis at p.name']);
  });

  test('apply only to their own check and states', async ({ page }) => {
    await open(page, 'resize', shortened);
    const report = await measure(page, {
      check: 'resize',
      state: STATE,
      exceptions: [
        { ...exception, states: ['another state'] },
        { ...exception, check: 'spacing' },
      ],
    });
    expect(unexcused(report).map(({ kind }) => kind)).toEqual(['ellipsis']);
  });

  test('cannot excuse a page that scrolls sideways, and must say why', async ({ page }) => {
    await open(page, 'reflow', '<p>Text</p>');
    for (const invalid of [
      { ...exception, check: 'reflow', kind: 'page scrolls' },
      { ...exception, why: '' },
      { ...exception, states: [] },
      { ...exception, kind: 'focus' },
    ])
      await expect(measure(page, { check: 'reflow', state: STATE, exceptions: [invalid] })).rejects.toThrow(TypeError);
  });
});

test.describe('placeholder contrast', () => {
  const field = (colour) => [
    '<input aria-label="Search" placeholder="Search">',
    `input::placeholder { color: ${colour}; opacity: 1; }`,
  ];

  test('fails a placeholder under 4.5:1', async ({ page }) => {
    await open(page, 'placeholder', ...field('#bbbbbb'));
    const report = await measure(page, { check: 'placeholder', state: STATE });
    expect(report.failures).toEqual([
      'placeholder: input "Search" ("Search" is rgb(187, 187, 187) on rgb(255, 255, 255), 1.92:1)',
    ]);
    expect(report.measured.placeholder).toBe(1);
  });

  test('passes a placeholder at 4.5:1', async ({ page }) => {
    await open(page, 'placeholder', ...field('#757575'));
    expect((await measure(page, { check: 'placeholder', state: STATE })).failures).toEqual([]);
  });
});

test.describe('field boundaries', () => {
  test('fails a boundary under 3:1', async ({ page }) => {
    await open(page, 'boundary', '<input aria-label="Name" style="border: 1px solid #cccccc; background: #ffffff">');
    const report = await measure(page, { check: 'boundary', state: STATE });
    expect(report.failures).toEqual([
      'boundary: input "Name" (boundary is rgb(204, 204, 204) on rgb(255, 255, 255), 1.61:1)',
    ]);
  });

  test('passes a boundary at 3:1', async ({ page }) => {
    await open(page, 'boundary', '<input aria-label="Name" style="border: 1px solid #767676; background: #ffffff">');
    const report = await measure(page, { check: 'boundary', state: STATE });
    expect(report.failures).toEqual([]);
    expect(report.measured.boundary).toBe(1);
  });
});

test.describe('icons, focus indicators and selection marks', () => {
  const options = (selected) =>
    '<ul role="listbox" aria-label="Choices" style="list-style: none; padding: 0">' +
    `<li role="option" aria-selected="true" style="${selected}">One</li>` +
    '<li role="option" aria-selected="false">Two</li></ul>';

  test('fails a selection marked by a tint alone', async ({ page }) => {
    await open(page, 'indicators', options('background: #e4f1f1'));
    const report = await measure(page, { check: 'indicators', state: STATE });
    expect(report.failures).toEqual(['selection: li "One" (fill is rgb(228, 241, 241) on rgb(255, 255, 255), 1.16:1)']);
  });

  test('measures a color(srgb ...) tint as the light colour it is', async ({ page }) => {
    await open(page, 'indicators', options('background: color(srgb 0.894 0.945 0.945)'));
    const report = await measure(page, { check: 'indicators', state: STATE });
    expect(report.failures).toEqual(['selection: li "One" (fill is rgb(228, 241, 241) on rgb(255, 255, 255), 1.16:1)']);
  });

  test('fails a selection outline under 3:1', async ({ page }) => {
    await open(page, 'indicators', options('outline: 2px solid #dddddd'));
    const report = await measure(page, { check: 'indicators', state: STATE });
    expect(report.failures).toEqual([
      'selection: li "One" (outline is rgb(221, 221, 221) on rgb(255, 255, 255), 1.36:1)',
    ]);
  });

  test('passes a selection framed at 3:1', async ({ page }) => {
    await open(page, 'indicators', options('outline: 2px solid color(srgb 0.06 0.46 0.53)'));
    const report = await measure(page, { check: 'indicators', state: STATE });
    expect(report.failures).toEqual([]);
    expect(report.measured.selection).toBe(1);
  });

  const button = '<button class="go" style="background: #ffffff; border: 1px solid #767676">Go</button>';

  test('fails a focus ring under 3:1', async ({ page }) => {
    await open(page, 'indicators', button, '.go:focus-visible { outline: 2px solid #cccccc; outline-offset: 2px; }');
    const report = await measure(page, { check: 'indicators', state: STATE });
    expect(report.failures).toEqual([
      'focus: button.go "Go" (outline is rgb(204, 204, 204) on rgb(255, 255, 255), 1.61:1)',
    ]);
  });

  test('measures a focus ring drawn as a color(srgb ...) shadow', async ({ page }) => {
    await open(
      page,
      'indicators',
      button,
      '.go:focus-visible { outline: none; box-shadow: 0 0 0 2px color(srgb 0.06 0.46 0.53); }',
    );
    const report = await measure(page, { check: 'indicators', state: STATE });
    expect(report.failures).toEqual([]);
    expect(report.measured.focus).toBe(1);
  });

  test('fails a focus that changes nothing it draws', async ({ page }) => {
    await open(page, 'indicators', button, '.go:focus-visible { outline: none; }');
    const report = await measure(page, { check: 'indicators', state: STATE });
    expect(report.failures).toEqual(['focus: button.go "Go" (changes no outline, border or shadow when focused)']);
  });

  test('fails an icon that alone names its control under 3:1', async ({ page }) => {
    await open(
      page,
      'indicators',
      '<button class="close" aria-label="Close" style="background: #ffffff; border: 1px solid #767676">' +
        '<svg width="16" height="16" viewBox="0 0 16 16"><path d="M2 2 14 14" stroke="#cccccc" stroke-width="2"/></svg>' +
        '</button>',
      '.close:focus-visible { outline: 2px solid #0f7686; }',
    );
    const report = await measure(page, { check: 'indicators', state: STATE });
    expect(report.failures).toEqual([
      'icon: button.close "Close" (is rgb(204, 204, 204) on rgb(255, 255, 255), 1.61:1)',
    ]);
  });
});

test.describe('scope and excluded hosts', () => {
  const shortened = (classes) =>
    `<div class="${classes}"><p style="margin: 0; width: 120px; overflow: hidden; white-space: nowrap; ` +
    'text-overflow: ellipsis">A name far too long for its box</p></div>';

  test('measure only within the scope', async ({ page }) => {
    await open(page, 'resize', shortened('mine') + shortened('theirs'));
    const report = await measure(page, { check: 'resize', state: STATE, scope: '.mine' });
    expect(report.failures).toEqual([expect.stringMatching(/^ellipsis: div\.mine > p /)]);
  });

  test('leave out the content of an excluded host', async ({ page }) => {
    await open(page, 'resize', shortened('embedded'));
    expect((await measure(page, { check: 'resize', state: STATE, exclude: ['.embedded'] })).failures).toEqual([]);
  });

  test('refuse a scope that matches nothing, and a viewport of another size', async ({ page }) => {
    await open(page, 'resize', '<p>Text</p>');
    await expect(measure(page, { check: 'resize', state: STATE, scope: '.absent' })).rejects.toThrow(
      'The scope .absent matches nothing',
    );
    await expect(measure(page, { check: 'reflow', state: STATE })).rejects.toThrow('reflow measures at 320 by 640');
  });
});

test('a well-formed page passes every check', async ({ page }) => {
  const body =
    '<main style="padding: 8px"><h1 style="font-size: 20px">A heading</h1>' +
    '<p>A paragraph long enough to wrap onto further lines at 320 CSS px, as text in a narrow host must.</p>' +
    '<label>Name <input placeholder="Your name"></label>' +
    '<button class="close" aria-label="Close"><svg width="16" height="16" viewBox="0 0 16 16">' +
    '<path d="M2 2 14 14" stroke="#0f7686" stroke-width="2"/></svg></button>' +
    '<ul role="listbox" aria-label="Choices" style="list-style: none; padding: 0">' +
    '<li role="option" aria-selected="true" style="outline: 2px solid #0f7686">One</li>' +
    '<li role="option" aria-selected="false">Two</li></ul></main>';
  const css =
    'input { border: 1px solid #767676; background: #ffffff; } input::placeholder { color: #595959; } ' +
    'button { background: #ffffff; border: 1px solid #767676; } ' +
    ':focus-visible { outline: 2px solid #0f7686; outline-offset: 2px; }';
  for (const which of ['reflow', 'resize', 'spacing', 'placeholder', 'boundary', 'indicators']) {
    await open(page, which, body, css);
    const report = await check(page, expect, { check: which, state: STATE });
    expect(
      Object.values(report.measured).some((count) => count > 0),
      which,
    ).toBe(true);
  }
});

test.describe('nested scroll containers', () => {
  const dialog = (overflow) =>
    `<div class="dialog" style="position: fixed; top: 0; left: 0; width: 300px; height: 200px; overflow: ${overflow}">` +
    '<div style="height: 500px"></div><div class="inner" style="overflow-x: auto; width: 280px">' +
    '<p style="margin: 0">Text the dialog scrolls to</p></div></div>';

  test('pass text that an outer scroller brings into view', async ({ page }) => {
    await open(page, 'resize', dialog('auto'));
    expect((await measure(page, { check: 'resize', state: STATE })).failures).toEqual([]);
  });

  test('fail text that no scroller can bring into view', async ({ page }) => {
    await open(page, 'resize', dialog('hidden'));
    const report = await measure(page, { check: 'resize', state: STATE });
    expect(report.failures).toEqual([
      expect.stringMatching(/^clipped: div\.dialog "Text the dialog scrolls to" \("Text the dialog scrolls to": /),
    ]);
  });
});

test.describe('surfaces that hide text', () => {
  const header = (background) =>
    '<div style="position: relative; height: 60px">' +
    '<span class="label" style="position: absolute; left: 0; top: 10px">Label beneath</span>' +
    `<div class="header" style="position: absolute; left: 0; top: 0; z-index: 10; width: 200px; height: 40px; background: ${background}">` +
    '<span class="version">Version text</span></div></div>' +
    '<div class="backdrop" style="position: fixed; inset: 0; z-index: 1000; background: rgba(0, 0, 0, 0.4)"></div>';

  test('pass text that an opaque surface beneath a translucent backdrop hides', async ({ page }) => {
    await open(page, 'resize', header('#ffffff'));
    expect((await measure(page, { check: 'resize', state: STATE })).failures).toEqual([]);
  });

  test('fail text that a translucent surface leaves showing', async ({ page }) => {
    await open(page, 'resize', header('rgba(255, 255, 255, 0.6)'));
    const report = await measure(page, { check: 'resize', state: STATE });
    expect(unexcused(report).map(({ kind }) => kind)).toEqual(['overlap']);
  });

  test('pass text that an older modal dialog, inert under a newer one, hides', async ({ page }) => {
    await open(
      page,
      'resize',
      '<p class="page" style="margin: 0; position: absolute; top: 20px; left: 20px">Page text under the dialog</p>' +
        '<dialog class="rename" style="margin: 0; inset: 10px auto auto 10px; width: 300px; height: 80px; padding: 0; ' +
        'border: 0; background: #ffffff"><span>Rename this resource</span></dialog>' +
        '<dialog class="confirm" style="margin: 0; inset: 200px auto auto 10px; background: #ffffff">' +
        '<span>Discard changes?</span></dialog>' +
        "<script>document.querySelector('.rename').showModal(); document.querySelector('.confirm').showModal();</script>",
    );
    expect((await measure(page, { check: 'resize', state: STATE })).failures).toEqual([]);
  });

  test('pass text that an opaque panel hides where its own text takes no pointer events', async ({ page }) => {
    await open(
      page,
      'resize',
      '<span class="label" style="position: absolute; left: 0; top: 10px">contributor</span>' +
        '<div class="panel" style="position: absolute; left: 0; top: 0; width: 300px; background: rgb(244, 246, 246)">' +
        '<div class="failure" role="option" aria-disabled="true" style="pointer-events: none">' +
        'Search failed: the lookup is unavailable</div></div>',
    );
    expect((await measure(page, { check: 'resize', state: STATE })).failures).toEqual([]);
  });
});

test.describe('boxes that draw nothing', () => {
  const row = (clip) =>
    '<div class="row" style="position: absolute; width: 1px; height: 1px; min-height: 36px; padding: 0 12px; ' +
    `overflow: hidden; clip-path: ${clip}"><span>Name</span> <span>Modified</span></div>`;

  test('hide text whose clip leaves no visible area, whatever the box measures', async ({ page }) => {
    await open(page, 'resize', row('inset(50%)'));
    expect((await measure(page, { check: 'resize', state: STATE })).failures).toEqual([]);
  });

  test('still cut off text where the clip leaves some area', async ({ page }) => {
    await open(page, 'resize', row('inset(10%)'));
    const report = await measure(page, { check: 'resize', state: STATE });
    expect(unexcused(report).map(({ kind }) => kind)).toEqual(['clipped']);
  });

  test('hide a visually hidden button that a minimum width keeps 64 px wide', async ({ page }) => {
    await open(
      page,
      'resize',
      '<button class="cdk-visually-hidden" style="position: absolute; width: 1px; height: 1px; min-width: 64px; ' +
        'overflow: hidden; clip: rect(0px, 0px, 0px, 0px); white-space: nowrap; border: 0; padding: 0; margin: -1px">' +
        'Close calendar</button>',
    );
    expect((await measure(page, { check: 'resize', state: STATE })).failures).toEqual([]);
  });
});

test.describe('reach', () => {
  test('passes a control whose centre a chip covers by design', async ({ page }) => {
    await open(
      page,
      'resize',
      '<div class="header" role="button" tabindex="0" style="width: 600px; height: 48px; display: flex; ' +
        'align-items: center"><span>Element title</span></div>' +
        '<button class="pager" style="position: absolute; left: 280px; top: 12px; width: 40px; height: 24px">2</button>',
    );
    expect((await measure(page, { check: 'resize', state: STATE })).failures).toEqual([]);
  });

  test('passes a control whose centre falls between its own reachable parts', async ({ page }) => {
    await open(
      page,
      'resize',
      '<div style="position: relative"><div class="chips" role="listbox" tabindex="0" aria-label="Pages" ' +
        'style="display: flex; gap: 8px; width: 58px; height: 34px">' +
        '<span role="option" style="position: relative; z-index: 2; width: 25px; background: #ffffff">1</span>' +
        '<span role="option" style="position: relative; z-index: 2; width: 25px; background: #ffffff">2</span>' +
        '</div><div class="header" style="position: absolute; inset: 0; z-index: 1"></div></div>',
    );
    expect((await measure(page, { check: 'resize', state: STATE })).failures).toEqual([]);
  });
});

test.describe('ellipsis shown whole in a tooltip', () => {
  const header = (outer, inner = '') =>
    `<div class="header ${outer}" role="button" tabindex="0" style="width: 200px"><div><div><div><div><div>` +
    `<span class="title ${inner}" style="display: block; width: 100px; overflow: hidden; white-space: nowrap; ` +
    'text-overflow: ellipsis">An element name too long for the header</span></div></div></div></div></div></div>';

  test('passes where the control holding the text triggers an enabled tooltip', async ({ page }) => {
    await open(page, 'resize', header('mat-mdc-tooltip-trigger'));
    expect((await measure(page, { check: 'resize', state: STATE })).failures).toEqual([]);
  });

  test('fails where the tooltip is disabled', async ({ page }) => {
    await open(page, 'resize', header('mat-mdc-tooltip-trigger mat-mdc-tooltip-disabled'));
    const report = await measure(page, { check: 'resize', state: STATE });
    expect(unexcused(report).map(({ kind }) => kind)).toEqual(['ellipsis']);
  });

  test('fails where the trigger lies beyond the control holding the text', async ({ page }) => {
    await open(
      page,
      'resize',
      '<div class="mat-mdc-tooltip-trigger"><button class="inner" style="display: block; width: 100px">' +
        '<span style="display: block; overflow: hidden; white-space: nowrap; text-overflow: ellipsis">' +
        'An element name too long for the button</span></button></div>',
    );
    const report = await measure(page, { check: 'resize', state: STATE });
    expect(unexcused(report).map(({ kind }) => kind)).toEqual(['ellipsis']);
  });
});

test.describe('placeholders shown only on focus', () => {
  const field = (focused) => [
    '<input aria-label="Search" placeholder="Search" style="border: 1px solid #767676">',
    'input::placeholder { opacity: 0; transition: opacity 150ms; } ' +
      `input:focus::placeholder { opacity: 1; color: ${focused}; } input:focus-visible { outline: 2px solid #0f7686; }`,
  ];

  test('are measured where they are drawn, and pass there at 4.5:1', async ({ page }) => {
    await open(page, 'placeholder', ...field('#595959'));
    const report = await measure(page, { check: 'placeholder', state: STATE });
    expect(report.failures).toEqual([]);
    expect(report.measured.placeholder).toBe(1);
  });

  test('fail where they are faint once drawn', async ({ page }) => {
    await open(page, 'placeholder', ...field('#bbbbbb'));
    const report = await measure(page, { check: 'placeholder', state: STATE });
    expect(report.failures).toEqual([
      'placeholder: input "Search" ("Search" when focused is rgb(187, 187, 187) on rgb(255, 255, 255), 1.92:1)',
    ]);
  });

  test('neither pass nor fail where they are never drawn', async ({ page }) => {
    await open(
      page,
      'placeholder',
      '<input aria-label="Search" placeholder="Search">',
      'input::placeholder { opacity: 0; }',
    );
    const report = await measure(page, { check: 'placeholder', state: STATE });
    expect(report.failures).toEqual([]);
    expect(report.measured.placeholder).toBe(0);
  });
});

test.describe('focus drawn in a field wrapper', () => {
  const field = (css) => [
    '<div class="field" style="display: inline-block; padding: 8px 16px; background: #f4f6f6">' +
      '<input class="input" aria-label="Name" ' +
      'style="border: 0; background: transparent"><div class="ripple"></div></div>',
    ".input:focus-visible { outline: none; } .ripple::after { content: ''; display: block; " +
      'border-bottom: 2px solid #0f7686; opacity: 0; transform: scaleX(0); transition: opacity 150ms; } ' +
      css,
  ];

  test('passes a line a sibling draws when the field is focused', async ({ page }) => {
    await open(
      page,
      'indicators',
      ...field('.field:focus-within .ripple::after { opacity: 1; transform: scaleX(1); }'),
    );
    const report = await measure(page, { check: 'indicators', state: STATE });
    expect(report.failures).toEqual([]);
    expect(report.measured.focus).toBe(1);
  });

  test('fails a field whose wrapper changes nothing on focus', async ({ page }) => {
    await open(page, 'indicators', ...field(''));
    const report = await measure(page, { check: 'indicators', state: STATE });
    expect(report.failures).toEqual([
      'focus: div.field > input.input "Name" (changes no outline, border or shadow when focused)',
    ]);
  });
});

test.describe('focus drawn in a field that holds a clear button', () => {
  // A filled field 68px wider than its textarea, because a clear button sits beside it, with the line
  // drawn three levels above the textarea. Once with Material's names, once with names of its own.
  const markups = {
    Material: {
      outer: 'mat-mdc-form-field',
      field: 'mdc-text-field',
      flex: 'mat-mdc-form-field-flex',
      infix: 'mat-mdc-form-field-infix',
      suffix: 'mat-mdc-form-field-icon-suffix',
      ripple: 'mdc-line-ripple',
    },
    plain: { outer: 'entry', field: 'field', flex: 'row', infix: 'infix', suffix: 'suffix', ripple: 'ripple' },
  };
  const field = (names, css) => [
    `<div class="${names.outer}" style="display: inline-block">` +
      `<div class="${names.field}" style="position: relative; padding: 8px; background: #f4f6f6">` +
      `<div class="${names.flex}" style="display: flex; align-items: center; gap: 12px">` +
      `<div class="${names.infix}"><textarea class="input" aria-label="Resource id" rows="2" ` +
      'style="display: block; width: 200px; margin: 0; border: 0; padding: 0; background: transparent; resize: none">' +
      `</textarea></div><div class="${names.suffix}"><button class="clear" aria-label="Clear" ` +
      'style="display: block; width: 40px; height: 40px; border: 1px solid #767676; background: #ffffff">x</button>' +
      `</div></div><div class="${names.ripple}" style="position: absolute; left: 0; right: 0; bottom: 0"></div>` +
      '</div></div>',
    `.input:focus-visible { outline: none; } .clear:focus-visible { outline: 2px solid #0f7686; outline-offset: 2px; } ` +
      `.${names.ripple}::after { content: ''; display: block; border-bottom: 2px solid #0f7686; opacity: 0; ` +
      `transform: scaleX(0); transition: opacity 150ms; } ${css}`,
  ];

  for (const [which, names] of Object.entries(markups)) {
    test(`passes a line drawn when the field is focused, with ${which} names`, async ({ page }) => {
      await open(
        page,
        'indicators',
        ...field(names, `.${names.field}:focus-within .${names.ripple}::after { opacity: 1; transform: scaleX(1); }`),
      );
      const widths = await page.evaluate(
        (selector) => [selector, 'textarea'].map((one) => document.querySelector(one).getBoundingClientRect().width),
        `.${names.field}`,
      );
      expect(widths[0] - widths[1]).toBe(68);
      const report = await measure(page, { check: 'indicators', state: STATE });
      expect(report.failures).toEqual([]);
      expect(report.measured.focus).toBe(2);
    });

    test(`fails the same field when focus changes nothing, with ${which} names`, async ({ page }) => {
      await open(page, 'indicators', ...field(names, ''));
      const report = await measure(page, { check: 'indicators', state: STATE });
      expect(report.failures).toEqual([
        `focus: div.${names.flex} > div.${names.infix} > textarea.input "Resource id" ` +
          '(changes no outline, border or shadow when focused)',
      ]);
    });
  }
});

test('a line drawn by a box around other controls is no focus indicator', async ({ page }) => {
  await open(
    page,
    'indicators',
    '<form class="panel" style="padding: 8px; background: #f4f6f6">' +
      '<div class="field"><input class="name" aria-label="Name" style="border: 0; background: transparent"></div>' +
      '<div class="field"><input class="email" aria-label="Email" style="border: 0; background: transparent"></div>' +
      '<div class="rule"></div></form>',
    'input:focus-visible { outline: none; } .email:focus-visible { outline: 2px solid #0f7686; outline-offset: 2px; } ' +
      ".rule::after { content: ''; display: block; border-bottom: 2px solid #0f7686; opacity: 0; } " +
      '.panel:focus-within .rule::after { opacity: 1; }',
  );
  const report = await measure(page, { check: 'indicators', state: STATE });
  expect(report.failures).toEqual([
    'focus: form.panel > div.field > input.name "Name" (changes no outline, border or shadow when focused)',
  ]);
});

test('a selection is compared with an item of its kind whatever its first class', async ({ page }) => {
  await open(
    page,
    'indicators',
    '<div role="group" aria-label="Language">' +
      '<button class="on segment" aria-pressed="true" style="background: #e4f1f1; border: 1px solid #767676">Cypher</button>' +
      '<button class="segment" aria-pressed="false" style="background: #ffffff; border: 1px solid #767676">SQL</button>' +
      '</div>',
    'button:focus-visible { outline: 2px solid #0f7686; outline-offset: 2px; }',
  );
  const report = await measure(page, { check: 'indicators', state: STATE });
  expect(report.failures).toEqual([
    'selection: button.on.segment "Cypher" (fill is rgb(228, 241, 241) on rgb(255, 255, 255), 1.16:1)',
  ]);
});

test('text squeezed to no width is cut off whatever its title holds', async ({ page }) => {
  await open(
    page,
    'reflow',
    '<h1 id="title" title="A page heading" style="margin: 0; width: 0; overflow: hidden; white-space: nowrap; ' +
      'text-overflow: ellipsis">A page heading</h1>',
  );
  const report = await measure(page, { check: 'reflow', state: STATE });
  expect(report.failures).toEqual([
    expect.stringMatching(
      /^clipped: h1#title "A page heading" \("A page heading": \d+x\d+ in 0x\d+, and none of it shows\)$/,
    ),
  ]);
});

test.describe('a state layer drawn on focus', () => {
  const link = (opacity) => [
    '<a class="link" href="#target" style="position: relative; display: inline-block; padding: 4px">Open</a>',
    '.link:focus-visible { outline: none; } .link::before { content: ""; position: absolute; inset: 0; ' +
      `background: rgba(0, 0, 0, 0.87); opacity: 0; } .link:focus-visible::before { opacity: ${opacity}; }`,
  ];

  test('fails a layer at 0.12 opacity, which draws a faint tint', async ({ page }) => {
    await open(page, 'indicators', ...link('0.12'));
    const report = await measure(page, { check: 'indicators', state: STATE });
    expect(report.failures).toEqual([
      expect.stringMatching(
        /^focus: a\.link "Open" \(::before fill is rgb\(22\d, 22\d, 22\d\) on rgb\(255, 255, 255\), 1\.2\d:1\)$/,
      ),
    ]);
  });

  test('passes the same layer at full opacity', async ({ page }) => {
    await open(page, 'indicators', ...link('1'));
    const report = await measure(page, { check: 'indicators', state: STATE });
    expect(report.failures).toEqual([]);
    expect(report.measured.focus).toBe(1);
  });
});
