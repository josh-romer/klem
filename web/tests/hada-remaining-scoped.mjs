import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {readFile, writeFile} from 'node:fs/promises';

const root = process.env.KLEM_ROOT || fileURLToPath(new URL('../..', import.meta.url));
const {chromium} = createRequire(root + '/web/package.json')('playwright');
const cases = [
  {word:'먹는양하는양하다', bases:['양','양'], labels:['Auxiliary verb formation','Auxiliary verb / adjective formation']},
  {word:'먹는양하는듯하다', bases:['양','듯'], labels:['Auxiliary verb formation','Auxiliary adjective formation']},
  {word:'먹는양했던양하다', bases:['양','양'], labels:['Auxiliary verb / adjective formation','Auxiliary verb / adjective formation']},
];
const browser = await chromium.launch({executablePath:process.env.CHROMIUM_PATH, args:['--no-sandbox']});
const checks = [], errors = [];
try {
  const page = await browser.newPage();
  page.on('pageerror', error => errors.push(String(error)));
  await page.goto(process.env.KLEM_WEB_URL);
  for (const encoding of ['NFC','NFD']) {
    for (const c of cases) {
      const text = c.word.normalize(encoding);
      await page.getByLabel('Your sentence', {exact:true}).fill(text);
      const wait = page.waitForResponse(r => r.url().endsWith('/api/analyze'));
      await page.getByRole('button', {name:'Analyze sentence', exact:true}).click();
      const response = await wait;
      assert.equal(response.status(), 200);
      const api = await response.json();
      const db = process.env.KLEM_DICTIONARY || root + '/data/dictionaries/krdict/krdict.db';
      const cliRecords = execFileSync(process.env.KLEM_BIN, ['text','-','--dictionary',db], {input:text, encoding:'utf8'}).trim().split('\n').map(JSON.parse);
      assert.deepEqual(api.records, cliRecords);
      const record = api.records.find(r => r.analysis);
      const index = record.analysis.analyses.findIndex(a => a.lemmas.length === 3 && a.lemmas[0].text === '먹다' && c.bases.every((base,i) => a.lemmas[i+1].text === base && a.lemmas[i+1].kind === 'nominal') && a.rules.includes('suffix.auxiliary.adjective.hada') && a.rules.includes('suffix.auxiliary.verb.hada'));
      assert.ok(index >= 0, c.word + ' preserves the independently licensed nested reading');
      await page.waitForFunction(t => document.querySelector('.sentence')?.textContent === t, text);
      const part = page.getByRole('region', {name:'Sentence breakdown', exact:true}).locator('.breakdown-word');
      await part.locator('select').selectOption(String(index));
      const order = api.breakdowns[api.records.indexOf(record)][index];
      const actual = [];
      for (let li = 1; li <= 2; li++) {
        const position = order.findIndex(component => component.lemma === li);
        actual.push(await part.locator('.breakdown-part').nth(position + 1).locator('.part-gloss').textContent());
      }
      checks.push({encoding, surface:text, request:{text}, response:api, cli_records:cliRecords, selected:index, labels:actual});
      assert.deepEqual(actual, c.labels, c.word + ': classes are scoped to each suffix owner');
    }
  }
  assert.deepEqual(errors, []);
  const hash = async path => createHash('sha256').update(await readFile(path)).digest('hex');
  await writeFile(process.env.KLEM_SCOPED_OUTPUT || '/tmp/klem-hada-remaining-scoped-browser.json', JSON.stringify({checks, errors, producer_sha256:await hash(fileURLToPath(import.meta.url)), frontend_sha256:await hash(root + '/web/src/breakdown.ts'), cli_sha256:await hash(process.env.KLEM_BIN)}, null, 2) + '\n');
  console.log('Verified six nested suffix diagrams: bare present excludes adjective labels; past-prefinal alternatives remain.');
} finally {
  await browser.close();
}
