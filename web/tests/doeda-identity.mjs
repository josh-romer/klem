import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {readFile,writeFile} from 'node:fs/promises';
const root=fileURLToPath(new URL('../..',import.meta.url));
const url=process.env.KLEM_WEB_URL,cli=process.env.KLEM_BIN,db=process.env.KLEM_DICTIONARY||root+'/data/dictionaries/krdict/krdict.db';
assert.ok(url&&cli,'Set KLEM_WEB_URL and KLEM_BIN to the running server and corresponding CLI.');
const {chromium}=createRequire(root+'/web/package.json')('playwright');
const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH,args:['--no-sandbox']});
const selected=[{word:'반감됐다',base:'반감'},{word:'결정돼요',base:'결정'},{word:'진동됐다',base:'진동'}];
const checks=[],diagrams=[],errors=[],responses=[];
try {
 const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});page.on('pageerror',e=>errors.push(String(e)));await page.goto(url);
 for(const encoding of ['NFC','NFD']) {
  const text=selected.map(c=>c.word).join(' ').normalize(encoding);
  await page.getByLabel('Your sentence',{exact:true}).fill(text);const wait=page.waitForResponse(r=>r.url().endsWith('/api/analyze'));await page.getByRole('button',{name:'Analyze sentence',exact:true}).click();const response=await wait;assert.equal(response.status(),200);const api=await response.json();responses.push({encoding,request:{text},response:api});await page.waitForFunction(t=>document.querySelector('.sentence')?.textContent===t,text);
  for(const [mode,flag] of [['raw',null],['headword','--dict-only'],['compatible','--dict-compatible']]) {
   if(flag){await page.getByLabel('Dictionary matches only').check();if(mode==='compatible')await page.getByLabel('Exclude known grammar conflicts').check();else await page.getByLabel('Exclude known grammar conflicts').uncheck();}else await page.getByLabel('Dictionary matches only').uncheck();
   const expected=execFileSync(cli,['text','-','--dictionary',db,...(flag?[flag]:[])],{input:text,encoding:'utf8'}).trim().split('\n').map(JSON.parse);
   const download=page.waitForEvent('download');await page.getByRole('button',{name:'Export JSON',exact:true}).click();const exported=JSON.parse(await readFile(await(await download).path(),'utf8'));assert.deepEqual(exported.records,expected);
   checks.push({encoding,mode,records:expected.length,exported_records:exported.records,cli_records:expected});
  }
  await page.getByLabel('Dictionary matches only').uncheck();
  const sentence=page.getByRole('region',{name:'Sentence breakdown',exact:true});
  for(const c of selected) {
   const record=api.records.find(r=>r.analysis?.normalized===c.word);const index=record.analysis.analyses.findIndex(a=>a.lemmas[0]?.text===c.base&&a.rules.includes('suffix.verb.doeda'));
   assert.ok(index>=0);const assessed=record.dictionary.readings[index].lemmas[0].entries;
   assert.ok(assessed.some(e=>e.derivational_identity?.relation==='recorded_difference'));
   const matches=assessed.filter(e=>e.derivational_identity?.relation==='recorded_match');
   const part=sentence.locator('.breakdown-word').filter({has:page.locator('.breakdown-surface > span',{hasText:new RegExp('^'+c.word.normalize(encoding)+'$')})});await part.locator('select').selectOption(String(index));
   const stem=part.locator('.breakdown-part').first();const label=await stem.locator('.part-gloss').textContent();
   if(c.base==='반감'){assert.equal(matches.length,0);assert.equal(label,'No matching source gloss');assert.match(await stem.getAttribute('title'),/different recorded origin/);}
   else{assert.ok(matches.length);assert.equal(label,api.glosses[matches[0].id]);await stem.click();await page.locator('.entry-content a[href*="ParaWordNo='+matches[0].id.split(':')[1]+'"]').waitFor();}
   diagrams.push({encoding,word:c.word,label,matching_entries:matches.map(e=>e.id),difference_entries:assessed.filter(e=>e.derivational_identity?.relation==='recorded_difference').map(e=>e.id)});
  }
  if(encoding==='NFC'){await page.screenshot({path:'/tmp/klem-doeda-identity-desktop.png',fullPage:true});await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:'/tmp/klem-doeda-identity-mobile.png',fullPage:true});await page.setViewportSize({width:1440,height:1000});}
 }
 assert.deepEqual(errors,[]);await writeFile('/tmp/klem-doeda-identity-browser.json',JSON.stringify({schema_version:1,checklist:'COV-022m',cli_sha256:createHash('sha256').update(await readFile(cli)).digest('hex'),dictionary_sha256:createHash('sha256').update(await readFile(db)).digest('hex'),fixture_sha256:createHash('sha256').update(await readFile(root+'/tests/fixtures/doeda-identity-sources.json')).digest('hex'),responses,checks,diagrams,browser_errors:errors},null,2)+'\n');console.log('Verified recorded-origin hints, raw possibilities, six filter exports, Unicode and mobile layout.');
} finally {await browser.close();}
