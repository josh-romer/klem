import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile,writeFile} from 'node:fs/promises';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
const root=process.env.KLEM_ROOT || '/home/josh/projects/klem';
const url=process.env.KLEM_WEB_URL, cli=process.env.KLEM_BIN;
assert.ok(url && cli);
const prefix=process.env.KLEM_BROWSER_OUTPUT_PREFIX || '/tmp/klem-degree-expectation-main';
const sourcePaths=['docs/degree-rimankeum-source-preparation.json.gz','docs/counterfactual-ryeon-source-preparation.json.gz'];
const sources=await Promise.all(sourcePaths.map(async p=>JSON.parse(gunzipSync(await readFile(root+'/'+p)))));
const sourceHash={};
const hash=async p=>createHash('sha256').update(await readFile(p)).digest('hex');
for(const p of sourcePaths)sourceHash[p]=await hash(root+'/'+p);
const {chromium}=createRequire(root+'/web/package.json')('playwright');
const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH,args:['--no-sandbox']});
const records=[],diagrams=[],errors=[],native=[],responses=[];
try {
 const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});
 page.on('pageerror',e=>errors.push(String(e)));await page.goto(url);
 for(const [family,source] of sources.entries()) {
 for(const encoding of ['NFC','NFD']) {
  const text=Object.keys(source.expected_single_predicate_heads).sort().join(' ').normalize(encoding);
  await page.getByLabel('Your sentence',{exact:true}).fill(text);
  const wait=page.waitForResponse(r=>r.url().endsWith('/api/analyze'));
  await page.getByRole('button',{name:'Analyze sentence',exact:true}).click();
  const response=await wait;assert.equal(response.status(),200);const api=await response.json();responses.push({family,encoding,request:{text},response:api});
  await page.waitForFunction(t=>document.querySelector('.sentence')?.textContent===t,text);
  for(const [mode,flag] of [['raw',null],['headword','--dict-only'],['compatible','--dict-compatible']]) {
   if(flag) {
    await page.getByLabel('Dictionary matches only').check();
    if(mode==='compatible')await page.getByLabel('Exclude known grammar conflicts').check();
    else await page.getByLabel('Exclude known grammar conflicts').uncheck();
   } else await page.getByLabel('Dictionary matches only').uncheck();
   const expected=execFileSync(cli,['text','-','--dictionary',root+'/data/dictionaries/krdict/krdict.db',...(flag?[flag]:[])],{input:text,encoding:'utf8'}).trim().split('\n').map(JSON.parse);
   const download=page.waitForEvent('download');await page.getByRole('button',{name:'Export JSON',exact:true}).click();
   const actual=JSON.parse(await readFile(await(await download).path(),'utf8'));
   assert.deepEqual(actual.records,expected);records.push({family,encoding,mode,records:actual.records});
  }
  await page.getByLabel('Dictionary matches only').uncheck();
  const sentence=page.getByRole('region',{name:'Sentence breakdown',exact:true});
  for(const [word,head] of Object.entries(source.expected_single_predicate_heads)) {
   const form=family===0?'으리만큼':word.endsWith('마는')?'으련마는':'으련만';
   const shortId=family===0?87692:form==='으련마는'?86545:86546, fullId=family===0?86608:form==='으련마는'?86602:86603;
   const rule=family===0?'ending.degree_rimankeum':'ending.counterfactual_ryeon', label=family===0?'To such a degree':'Counterfactual expectation';
   const record=api.records.find(r=>r.analysis?.normalized===word);
   const index=record.analysis.analyses.findIndex(a=>a.lemmas.length===1 && a.lemmas[0].text===head && a.rules.includes(rule) && a.morphemes.at(-1)?.form===form);
   assert.ok(index>=0,word);
   const card=sentence.locator('.breakdown-word').filter({has:page.locator('.breakdown-surface > span',{hasText:new RegExp('^'+word.normalize(encoding)+'$')})});
   await card.locator('select').selectOption(String(index));
   const order=api.breakdowns[api.records.indexOf(record)][index];
   const ending=record.analysis.analyses[index].morphemes.findIndex(m=>m.kind==='ending' && m.form===form);
   const part=card.locator('.breakdown-part').nth(order.findIndex(c=>c.morpheme===ending));
   assert.equal(await part.locator('.part-form').textContent(),form);
   assert.equal(await part.locator('.part-gloss').textContent(),label);
   const title=await part.getAttribute('title');assert.ok(title.includes(String(shortId)) && title.includes(String(fullId)));
   await part.click();await page.locator(`.entry-content a[href*="ParaWordNo=${shortId}"]`).waitFor();
   await page.locator('.entry-choices button').filter({hasText:'-'+form}).click();
   await page.locator(`.entry-content a[href*="ParaWordNo=${fullId}"]`).waitFor();
   diagrams.push({family,encoding,word,head,index,analysis:record.analysis.analyses[index],order,label:await part.locator('.part-gloss').textContent(),title});
  }
  if(encoding==='NFC') {
   await sentence.scrollIntoViewIfNeeded();await page.screenshot({path:prefix+'-'+family+'-desktop.png'});
   await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   await sentence.scrollIntoViewIfNeeded();await page.screenshot({path:prefix+'-'+family+'-mobile.png'});
   await page.setViewportSize({width:1440,height:1000});
  }
 }
 }
 const allNative={};
 for(const source of sources)for(const [id,entry] of Object.entries(source.complete_native_entries)){if(allNative[id])assert.deepEqual(allNative[id],entry);allNative[id]=entry;}
 for(const id of Object.keys(allNative)) {
  const response=await page.request.post(url+'/api/entry',{data:{id}});assert.equal(response.status(),200);
  const actual=await response.json();const expected=structuredClone(allNative[id]);
  assert.deepEqual(actual.entry,expected);native.push({id,response:actual});
 }
 assert.deepEqual(errors,[]);
 await writeFile(prefix+'-browser.json',JSON.stringify({schema_version:1,production_worktree:true,cli_sha256:await hash(cli),source_sha256:sourceHash,producer_sha256:await hash(root+'/web/tests/degree-expectation.mjs'),records,responses,diagrams,native,errors},null,2)+'\n');
 console.log('Verified',diagrams.length,'production diagrams,',records.length,'CLI/export comparisons and',native.length,'complete native entries.');
} finally {await browser.close();}
