import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {dirname} from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {gunzipSync} from 'node:zlib';
const root=fileURLToPath(new URL('../..',import.meta.url)).replace(/\/$/,''),url=process.env.KLEM_WEB_URL,cli=process.env.KLEM_BIN;
const prefix=process.env.KLEM_CAPTURE_PREFIX || root+'/web/test-results/copula-expectation';
await mkdir(dirname(prefix),{recursive:true});
assert.ok(url && cli);
const suitePath=root+'/tests/copula-expectation-validity.json';
const suite=JSON.parse(await readFile(suitePath));
const nativeExpected=JSON.parse(gunzipSync(await readFile(root+'/docs/copula-expectation-source-preparation.json.gz'))).complete_native_entries;
const {chromium}=createRequire(root+'/web/package.json')('playwright');
const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH,args:['--no-sandbox']});
const records=[],diagrams=[],responses=[],errors=[],native=[];
const hash=async p=>createHash('sha256').update(await readFile(p)).digest('hex');
try {
 const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});
 page.on('pageerror',e=>errors.push(String(e)));await page.goto(url);
 for(const encoding of ['NFC','NFD']) {
  const text=suite.cases.map(c=>c.surface).join(' ').normalize(encoding);
  await page.getByLabel('Your sentence',{exact:true}).fill(text);
  const wait=page.waitForResponse(r=>r.url().endsWith('/api/analyze'));
  await page.getByRole('button',{name:'Analyze sentence',exact:true}).click();
  const response=await wait;assert.equal(response.status(),200);const api=await response.json();responses.push({encoding,request:{text},response:api});
  await page.waitForFunction(t=>document.querySelector('.sentence')?.textContent===t,text);
  for(const [mode,flag] of [['raw',null],['headword','--dict-only'],['compatible','--dict-compatible']]) {
   if(flag) {
    await page.getByLabel('Dictionary matches only').check();
    if(mode==='compatible')await page.getByLabel('Exclude known grammar conflicts').check();
    else await page.getByLabel('Exclude known grammar conflicts').uncheck();
   } else await page.getByLabel('Dictionary matches only').uncheck();
   const expected=execFileSync(cli,['text','-','--dictionary',root+'/data/dictionaries/krdict/krdict.db',...(flag?[flag]:[])],{input:text,encoding:'utf8'}).trim().split('\n').map(JSON.parse);
   const download=page.waitForEvent('download');await page.getByRole('button',{name:'Export JSON',exact:true}).click();
   const actual=JSON.parse(await readFile(await(await download).path(),'utf8'));assert.deepEqual(actual.records,expected);
   records.push({encoding,mode,records:actual.records});
   if(mode==='raw')assert.deepEqual(api.records,expected);
  }
  await page.getByLabel('Dictionary matches only').uncheck();
  const sentence=page.getByRole('region',{name:'Sentence breakdown',exact:true});
  for(const c of suite.cases) {
   const record=api.records.find(r=>r.analysis?.normalized===c.surface);assert.ok(record,c.surface);
   const j=c.judgments[0];
   const index=record.analysis.analyses.findIndex(a=>a.lemmas.map(l=>l.text).join('|')===j.lemmas.join('|') && a.lemmas.map(l=>l.kind).join('|')===j.lemma_kinds.join('|') && a.morphemes.map(m=>m.form).join('|')===j.morphemes.join('|') && j.required_rules.every(r=>a.rules.includes(r)));
   if(j.verdict==='forbidden'){assert.equal(index,-1,c.surface);continue;}
   assert.ok(index>=0,c.surface);
   const card=sentence.locator('.breakdown-word').filter({has:page.locator('.breakdown-surface > span',{hasText:new RegExp('^'+c.surface.normalize(encoding)+'$')})});
   await card.locator('select').selectOption(String(index));
   const order=api.breakdowns[api.records.indexOf(record)][index];assert.ok(order);
   const parts=card.locator('.breakdown-part');assert.equal(await parts.count(),order.length);
   assert.deepEqual(order.slice(0,2),[{lemma:0},{lemma:1}]);
   assert.equal(await parts.nth(0).locator('.part-form').textContent(),j.lemmas[0]);
   assert.equal(await parts.nth(1).locator('.part-form').textContent(),'이');
   assert.ok((await parts.nth(1).getAttribute('title')).startsWith('이다 · copula.'));
   const ending=parts.nth(order.length-1);const form=j.morphemes.at(-1);assert.equal(await ending.locator('.part-form').textContent(),form);
   const label=form==='으리만큼'?'To such a degree':'Counterfactual expectation';assert.equal(await ending.locator('.part-gloss').textContent(),label);
   const ids=form==='으리만큼'?[87692,86608]:form==='으련마는'?[86545,86602]:[86546,86603];
   const title=await ending.getAttribute('title');for(const id of ids)assert.ok(title.includes(String(id)));
   diagrams.push({case_id:c.id,surface:c.surface,encoding,index,analysis:record.analysis.analyses[index],order,label,title});
  }
  if(encoding==='NFC') {
   await sentence.scrollIntoViewIfNeeded();await page.screenshot({path:prefix+'-desktop.png'});
   await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   await sentence.scrollIntoViewIfNeeded();await page.screenshot({path:prefix+'-mobile.png'});
   await page.setViewportSize({width:1440,height:1000});
  }
 }
 for(const id of ['krdict:86118','krdict:86232','krdict:92457','krdict:87692','krdict:86608','krdict:86545','krdict:86602','krdict:86546','krdict:86603']) {
  const response=await page.request.post(url+'/api/entry',{data:{id}});assert.equal(response.status(),200);const actual=await response.json();assert.deepEqual(actual.entry,nativeExpected[id]);native.push({id,response:actual});
 }
 assert.deepEqual(errors,[]);assert.equal(diagrams.length,42);assert.equal(records.length,6);
 await writeFile(prefix+'-browser.json',JSON.stringify({schema_version:1,production:true,cli_sha256:await hash(cli),suite_sha256:await hash(suitePath),producer_sha256:await hash(fileURLToPath(import.meta.url)),records,responses,diagrams,native,errors},null,2)+'\n');
 console.log('Verified42 production diagrams,6 CLI/export comparisons,9 Native endpoints,original NFC/NFD byte spans and mobile fit.');
} finally {await browser.close();}
