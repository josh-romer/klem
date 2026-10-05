import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {readFile, writeFile} from 'node:fs/promises';

const root = process.env.KLEM_ROOT || fileURLToPath(new URL('../..', import.meta.url));
const url = process.env.KLEM_WEB_URL, cli = process.env.KLEM_BIN;
const db = process.env.KLEM_DICTIONARY || root + '/data/dictionaries/krdict/krdict.db';
const prefix = process.env.KLEM_BROWSER_OUTPUT_PREFIX || '/tmp/klem-hada-remaining';
assert.ok(url && cli, 'Set KLEM_WEB_URL and KLEM_BIN to the matching local server and CLI.');
const fixturePath = root + '/tests/fixtures/hada-remaining-sources.json';
const fixture = JSON.parse(await readFile(fixturePath, 'utf8'));
const contextual = {듯:'먹을듯하다', 법:'먹을법하다', 뻔:'먹을뻔하다', 양:'학생인양하다', 척:'먹은척하다', 체:'먹은체하다'};
const kinds = {adverbial:'adverbial', root:'root', bound_noun:'nominal'};
const selected = fixture.owners.map(owner => ({owner, word:contextual[owner.base] || owner.whole_head}));
const {chromium} = createRequire(root + '/web/package.json')('playwright');
const browser = await chromium.launch({executablePath:process.env.CHROMIUM_PATH, args:['--no-sandbox']});
const responses = [], checks = [], diagrams = [], errors = [];
try {
  const page = await browser.newPage({viewport:{width:1440, height:1000}, acceptDownloads:true});
  page.on('pageerror', error => errors.push(String(error)));
  await page.goto(url);
  for (const encoding of ['NFC', 'NFD']) {
    const text = selected.map(c => c.word).join(' ').normalize(encoding);
    await page.getByLabel('Your sentence', {exact:true}).fill(text);
    const wait = page.waitForResponse(r => r.url().endsWith('/api/analyze'));
    await page.getByRole('button', {name:'Analyze sentence', exact:true}).click();
    const response = await wait;
    assert.equal(response.status(), 200);
    const api = await response.json();
    responses.push({encoding, request:{text}, response:api});
    await page.waitForFunction(t => document.querySelector('.sentence')?.textContent === t, text);
    for (const [mode, flag] of [['raw', null], ['headword', '--dict-only'], ['compatible', '--dict-compatible']]) {
      if (flag) {
        await page.getByLabel('Dictionary matches only').check();
        if (mode === 'compatible') await page.getByLabel('Exclude known grammar conflicts').check();
        else await page.getByLabel('Exclude known grammar conflicts').uncheck();
      } else await page.getByLabel('Dictionary matches only').uncheck();
      const records = execFileSync(cli, ['text', '-', '--dictionary', db, ...(flag ? [flag] : [])], {input:text, encoding:'utf8'}).trim().split('\n').map(JSON.parse);
      const download = page.waitForEvent('download');
      await page.getByRole('button', {name:'Export JSON', exact:true}).click();
      const exported = JSON.parse(await readFile(await (await download).path(), 'utf8'));
      assert.deepEqual(exported.records, records);
      checks.push({encoding, mode, cli_records:records, exported_records:exported.records});
    }
    await page.getByLabel('Dictionary matches only').uncheck();
    const sentence = page.getByRole('region', {name:'Sentence breakdown', exact:true});
    for (const {owner, word} of selected) {
      const record = api.records.find(r => r.analysis?.normalized === word);
      const li = owner.base_role === 'bound_noun' ? 1 : 0;
      const mi = li;
      const index = record.analysis.analyses.findIndex(a => a.lemmas[li]?.text === owner.base && a.lemmas[li]?.kind === kinds[owner.base_role] && a.morphemes[mi]?.form === '하다' && a.morphemes[mi]?.kind === 'suffix');
      const wholeIndex = record.analysis.analyses.findIndex(a => a.lemmas[li]?.text === owner.whole_head && ['predicate', 'auxiliary'].includes(a.lemmas[li]?.kind));
      assert.ok(index >= 0 && wholeIndex >= 0, word + ' retains both sourced and whole-head alternatives');
      const part = sentence.locator('.breakdown-word').filter({has:page.locator('.breakdown-surface > span', {hasText:new RegExp('^' + word.normalize(encoding) + '$')})});
      await part.locator('select').selectOption(String(wholeIndex));
      await part.locator('select').selectOption(String(index));
      const analysis = record.analysis.analyses[index];
      const order = api.breakdowns[api.records.indexOf(record)][index];
      const position = order.findIndex(c => c.lemma === li);
      const stem = part.locator('.breakdown-part').nth(position);
      assert.equal(await stem.locator('.part-form').textContent(), owner.base);
      const suffix = part.locator('.breakdown-part').nth(position + 1);
      assert.equal(await suffix.locator('.part-form').textContent(), '하');
      const rules = owner.supported_predicate_classes.map(pos => (owner.sense_id === '6' ? 'suffix.auxiliary.' : 'suffix.') + (pos.includes('형용사') ? 'adjective.hada' : 'verb.hada')).filter(rule => analysis.rules.includes(rule));
      const adjective = rules.some(r => r.includes('.adjective.')), verb = rules.some(r => r.includes('.verb.'));
      const expected = owner.sense_id === '6'
        ? adjective && verb ? 'Auxiliary verb / adjective formation' : adjective ? 'Auxiliary adjective formation' : 'Auxiliary verb formation'
        : adjective && verb ? 'Verb / adjective formation' : adjective ? 'State / adjective formation' : 'Action / verb formation';
      assert.equal(await suffix.locator('.part-gloss').textContent(), expected);
      const title = await suffix.getAttribute('title');
      assert.ok(title.includes('sense ' + owner.sense_id));
      assert.equal(title.includes('Root status does not assert a standalone dictionary entry.'), owner.base_role === 'root');
      assert.ok(title.includes('Context and other -하다 senses remain open'));
      await suffix.click();
      await page.locator('.entry-content a[href*="ParaWordNo=88475"]').waitFor();
      diagrams.push({encoding, word, source_owner:owner, selected:index, whole_selected:wholeIndex, lemma_index:li, morpheme_index:mi, order, formation_label:expected, formation_title:title, parts:await part.locator('.part-form').allTextContents()});
    }
    if (encoding === 'NFC') {
      await page.screenshot({path:prefix + '-desktop.png', fullPage:true});
      await page.setViewportSize({width:390, height:844});
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      await page.screenshot({path:prefix + '-mobile.png', fullPage:true});
      await page.setViewportSize({width:1440, height:1000});
    }
  }
  assert.deepEqual(errors, []);
  const hash = async p => createHash('sha256').update(await readFile(p)).digest('hex');
  await writeFile(prefix + '-browser.json', JSON.stringify({schema_version:1, checklist:'COV-022t', cli_sha256:await hash(cli), dictionary_sha256:await hash(db), fixture_sha256:await hash(fixturePath), producer_sha256:await hash(fileURLToPath(import.meta.url)), responses, checks, diagrams, browser_errors:errors}, null, 2) + '\n');
  console.log('Verified 34 source-specific diagrams, retained whole alternatives, six CLI/export comparisons, source clicks, Unicode and mobile layout.');
} finally {
  await browser.close();
}
