import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {readFile,writeFile} from 'node:fs/promises';

const root=process.env.KLEM_ROOT || fileURLToPath(new URL('../..',import.meta.url));
const url=process.env.KLEM_WEB_URL,cli=process.env.KLEM_BIN;
assert.ok(url && cli,'Set matching KLEM_WEB_URL and KLEM_BIN.');
const db=process.env.KLEM_DICTIONARY || root+'/data/dictionaries/krdict/krdict.db';
const prefix=process.env.KLEM_BROWSER_OUTPUT_PREFIX || '/tmp/klem-ssik';
const fixturePath=root+'/tests/fixtures/ssik-sources.json';
const fixture=JSON.parse(await readFile(fixturePath,'utf8'));
const selected=['잔씩','사람씩','마리씩','며칠씩','그릇씩','조금씩','하나씩','걸음씩','번씩','고기씩이나','선물씩이나','용돈씩이나'];
const {chromium}=createRequire(root+'/web/package.json')('playwright');
const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH,args:['--no-sandbox']});
const responses=[],checks=[],diagrams=[],native=[],errors=[];
try {
 const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});
 page.on('pageerror',e=>errors.push(String(e)));
 await page.goto(url);
 for(const encoding of ['NFC','NFD']) {
  const text=[...selected,'씩'].join(' ').normalize(encoding);
  await page.getByLabel('Your sentence',{exact:true}).fill(text);
  const wait=page.waitForResponse(r=>r.url().endsWith('/api/analyze'));
  await page.getByRole('button',{name:'Analyze sentence',exact:true}).click();
  const response=await wait;assert.equal(response.status(),200);const api=await response.json();
  responses.push({encoding,request:{text},response:api});
  await page.waitForFunction(t=>document.querySelector('.sentence')?.textContent===t,text);
  for(const [mode,flag] of [['raw',null],['headword','--dict-only'],['compatible','--dict-compatible']]) {
   if(flag) {
    await page.getByLabel('Dictionary matches only').check();
    if(mode==='compatible')await page.getByLabel('Exclude known grammar conflicts').check();
    else await page.getByLabel('Exclude known grammar conflicts').uncheck();
   } else await page.getByLabel('Dictionary matches only').uncheck();
   const records=execFileSync(cli,['text','-','--dictionary',db,...(flag?[flag]:[])],{input:text,encoding:'utf8'}).trim().split('\n').map(JSON.parse);
   const download=page.waitForEvent('download');await page.getByRole('button',{name:'Export JSON',exact:true}).click();
   const exported=JSON.parse(await readFile(await(await download).path(),'utf8'));
   assert.deepEqual(exported.records,records);checks.push({encoding,mode,cli_records:records,exported_records:exported.records});
  }
  await page.getByLabel('Dictionary matches only').uncheck();
  const sentence=page.getByRole('region',{name:'Sentence breakdown',exact:true});
  for(const word of selected) {
   const record=api.records.find(r=>r.analysis?.normalized===word);
   const forms=word.endsWith('이나')?['씩','이나']:['씩'];
   const index=record.analysis.analyses.findIndex(a=>a.rules.includes('suffix.distributive.ssik')&&
    a.morphemes.map(m=>m.form).join(',')===forms.join(','));
   const wholeIndex=record.analysis.analyses.findIndex(a=>a.unchanged&&a.lemmas[0].text===word);
   assert.ok(index>=0 && wholeIndex>=0,word);
   const card=sentence.locator('.breakdown-word').filter({has:page.locator('.breakdown-surface > span',{hasText:new RegExp('^'+word.normalize(encoding)+'$')})});
   await card.locator('select').selectOption(String(wholeIndex));
   await card.locator('select').selectOption(String(index));
   const analysis=record.analysis.analyses[index];
   const mi=analysis.morphemes.findIndex(m=>m.kind==='suffix'&&m.form==='씩');
   const order=api.breakdowns[api.records.indexOf(record)][index];
   const position=order.findIndex(c=>c.morpheme===mi);
   assert.ok(position>=0);
   const suffix=card.locator('.breakdown-part').nth(position);
   assert.equal(await suffix.locator('.part-form').textContent(),'씩');
   assert.equal(await suffix.locator('.part-gloss').textContent(),'Each / unexpected amount');
   const title=await suffix.getAttribute('title');
   assert.ok(title.includes('72043')&&title.includes('Quantity context and speaker expectation are not inferred'));
   await suffix.click();await page.locator('.entry-content a[href*="ParaWordNo=72043"]').waitFor();
   diagrams.push({encoding,word,selected:index,whole_selected:wholeIndex,analysis,order,parts:await card.locator('.part-form').allTextContents(),label:'Each / unexpected amount',title});
  }
  const adverb=api.records.find(r=>r.analysis?.normalized==='씩');
  assert.ok(adverb.dictionary.lemmas.some(l=>l.entries.some(e=>e.id==='krdict:66460')));
  assert.ok(adverb.analysis.analyses.every(a=>!a.morphemes.some(m=>m.kind==='suffix'&&m.form==='씩')));
  if(encoding==='NFC') {
   await sentence.scrollIntoViewIfNeeded();await page.screenshot({path:prefix+'-desktop.png'});
   await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   await sentence.scrollIntoViewIfNeeded();await page.screenshot({path:prefix+'-mobile.png'});
   await page.setViewportSize({width:1440,height:1000});
  }
 }
 for(const [id,expected] of Object.entries(fixture.complete_native_entries)) {
  const response=await page.request.post(url+'/api/entry',{data:{id}});assert.equal(response.status(),200);
  const actual=await response.json();assert.deepEqual(actual.entry,expected);native.push({id,response:actual});
 }
 assert.deepEqual(errors,[]);
 const hash=async p=>createHash('sha256').update(await readFile(p)).digest('hex');
 await writeFile(prefix+'-browser.json',JSON.stringify({schema_version:1,checklist:'COV-022u',cli_sha256:await hash(cli),dictionary_sha256:await hash(db),fixture_sha256:await hash(fixturePath),producer_sha256:await hash(fileURLToPath(import.meta.url)),responses,checks,diagrams,native,browser_errors:errors},null,2)+'\n');
 console.log('Verified 24 sourced -씩 diagrams, whole alternatives, six CLI/export comparisons, 17 exact native endpoints, standalone adverb, Unicode and mobile layout.');
} finally {await browser.close();}
