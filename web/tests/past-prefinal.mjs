import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {gunzipSync} from 'node:zlib';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../..',import.meta.url)).replace(/\/$/,''),url=process.env.KLEM_WEB_URL,cli=process.env.KLEM_BIN,prefix=process.env.KLEM_CAPTURE_PREFIX;
assert.ok(url&&cli&&prefix);
const suite=JSON.parse(await readFile(root+'/tests/fixtures/past-prefinal-validity.json'));
const nativeExpected=JSON.parse(gunzipSync(await readFile(root+'/docs/past-prefinal-owner-preparation.json.gz'))).complete_native_entries;
const before=JSON.parse(gunzipSync(await readFile(root+'/docs/past-prefinal-before-api.json.gz')));
const source=JSON.parse(gunzipSync(await readFile(root+'/docs/past-prefinal-source-discovery.json.gz')));
const catalog=JSON.parse(await readFile(root+'/web/src/grammar-labels.json'));
const {chromium}=createRequire(root+'/web/package.json')('playwright');
const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH,args:['--no-sandbox']});
const errors=[],responses=[],exports=[],diagrams=[],native=[],opened=[];
const hash=async path=>createHash('sha256').update(await readFile(path)).digest('hex');
const match=(a,j)=>a.lemmas.map(l=>l.text).join('|')===j.lemmas.join('|')
 && a.lemmas.map(l=>l.kind).join('|')===j.lemma_kinds.join('|')
 && a.morphemes.map(m=>m.form).join('|')===j.morphemes.join('|')
 && a.morphemes.map(m=>m.kind).join('|')===j.morpheme_kinds.join('|')
 &&(!j.required_rules||j.required_rules.every(r=>a.rules.includes(r)));
function displayed(a,order){return order.map((c,i)=>{
 if('lemma' in c){const l=a.lemmas[c.lemma];return ['predicate','auxiliary','copula'].includes(l.kind)?l.text.replace(/다$/,''):l.text;}
 const m=a.morphemes[c.morpheme],p=order[i-1];
 const afterHa=p&&(('lemma' in p&&a.lemmas[p.lemma].text.endsWith('하다'))||('morpheme' in p&&a.morphemes[p.morpheme].kind==='suffix'&&a.morphemes[p.morpheme].form==='하다'));
 return afterHa?m.form.replace(/^어/,'여').replace(/^었/,'였'):m.form;
});}
async function analyze(page,text){
 await page.getByLabel('Your sentence',{exact:true}).fill(text);
 const wait=page.waitForResponse(r=>r.url().endsWith('/api/analyze'));
 await page.getByRole('button',{name:'Analyze sentence',exact:true}).click();
 const response=await wait;assert.equal(response.status(),200);
 const api=await response.json();await page.waitForFunction(t=>document.querySelector('.sentence')?.textContent===t,text);return api;
}
try{
 const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});
 page.on('pageerror',e=>errors.push(String(e)));await page.goto(url);
 for(const encoding of ['NFC','NFD']){
  const original=before.runs.find(r=>r.encoding===encoding);
  const response=await page.request.post(url+'/api/analyze',{data:original.request});assert.equal(response.status(),200);
  const full=await response.json();
  for(const key of ['records','rules','breakdowns','glosses'])assert.deepEqual(full[key],original.response[key],key);
  const other={...full.grammar};delete other['-었-'];const oldOther={...original.response.grammar};delete oldOther['-었-'];assert.deepEqual(other,oldOther);
  assert.deepEqual(full.grammar['-었-'][0],original.response.grammar['-었-'][0]);
  assert.deepEqual(full.grammar['-었-'].map(e=>e.id),['krdict:68719','krdict:66954','krdict:68723']);
  responses.push({encoding,request:original.request,response:full});
  const text=[...new Set(suite.cases.map(c=>c.surface))].join(' ').normalize(encoding);
  const api=await analyze(page,text);
  for(const [mode,flag] of [['raw',null],['headword','--dict-only'],['compatible','--dict-compatible']]){
   if(flag){await page.getByLabel('Dictionary matches only').check();if(mode==='compatible')await page.getByLabel('Exclude known grammar conflicts').check();else await page.getByLabel('Exclude known grammar conflicts').uncheck();}
   else await page.getByLabel('Dictionary matches only').uncheck();
   const expected=execFileSync(cli,['text','-','--dictionary',root+'/data/dictionaries/krdict/krdict.db',...(flag?[flag]:[])],{input:text,encoding:'utf8',maxBuffer:64*1024*1024}).trim().split('\n').map(JSON.parse);
   const wait=page.waitForEvent('download');await page.getByRole('button',{name:'Export JSON',exact:true}).click();const download=await wait;
   const actual=JSON.parse(await readFile(await download.path(),'utf8'));assert.deepEqual(actual.records,expected);
   exports.push({encoding,mode,request:{text},records:actual.records});
  }
  await page.getByLabel('Dictionary matches only').uncheck();
  const sentence=page.getByRole('region',{name:'Sentence breakdown',exact:true});
  for(const c of suite.cases){
   const record=api.records.find(r=>r.analysis?.normalized===c.surface);assert.ok(record,c.surface);
   for(const j of c.judgments){
    const index=record.analysis.analyses.findIndex(a=>match(a,j));
    if(j.verdict==='forbidden'){assert.equal(index,-1,c.id);continue;}
    assert.ok(index>=0,c.id);
    const card=sentence.locator('.breakdown-word').filter({has:page.locator('.breakdown-surface > span',{hasText:new RegExp('^'+c.surface.normalize(encoding)+'$')})});
    await card.locator('select').selectOption(String(index));
    const a=record.analysis.analyses[index],order=api.breakdowns[api.records.indexOf(record)][index];assert.ok(order);
    assert.deepEqual(await card.locator('.part-form').allTextContents(),displayed(a,order));
    const piece=order.findIndex(p=>'morpheme' in p&&a.morphemes[p.morpheme].kind==='prefinal'&&a.morphemes[p.morpheme].form==='었');assert.ok(piece>=0);
    const past=card.locator('.breakdown-part').nth(piece);assert.equal(await past.locator('.part-gloss').textContent(),catalog['-었-'].label);
    const title=await past.getAttribute('title');for(const id of [68719,66954,68723])assert.ok(title.includes(String(id)),c.id+' source '+id);
    diagrams.push({case_id:c.id,judgment_id:j.id,surface:c.surface,encoding,index,analysis:a,order,title});
   }
  }
  if(encoding==='NFC'){
   const card=sentence.locator('.breakdown-word').filter({has:page.locator('.breakdown-surface > span',{hasText:/^갔다$/})});
   const past=card.locator('.breakdown-part').filter({has:page.locator('.part-gloss',{hasText:catalog['-었-'].label})});await past.click();
   for(const [id,head] of [['krdict:66954','-았-'],['krdict:68719','-었-'],['krdict:68723','-였-']]){
    const button=page.locator('.entry-choices button').filter({has:page.locator('span',{hasText:new RegExp('^'+head+'$')})});
    const wait=page.waitForResponse(r=>r.url().endsWith('/api/entry')&&r.request().postDataJSON()?.id===id);
    await button.click();const response=await wait;assert.equal(response.status(),200);assert.deepEqual((await response.json()).entry,nativeExpected[id]);
    await page.waitForFunction(head=>document.querySelector('.entry-heading h2')?.textContent?.includes(head),head);
    opened.push({id,head});
   }
   await card.scrollIntoViewIfNeeded();await page.screenshot({path:prefix+'-desktop.png'});
   await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await card.scrollIntoViewIfNeeded();await page.screenshot({path:prefix+'-mobile.png'});await page.setViewportSize({width:1440,height:1000});
  }
 }
 for(const [id,expected] of Object.entries(nativeExpected)){
  const response=await page.request.post(url+'/api/entry',{data:{id}});assert.equal(response.status(),200);const actual=await response.json();assert.deepEqual(actual.entry,expected,id);native.push({id,response:actual});
 }
 assert.deepEqual(errors,[]);assert.equal(diagrams.length,90);assert.equal(exports.length,6);assert.equal(native.length,99);assert.equal(opened.length,3);
 await writeFile(prefix+'-browser.json',JSON.stringify({schema_version:1,scope:'Main debug binaries and built assets; packaged release verification remains separate.',cli_sha256:await hash(cli),suite_sha256:await hash(root+'/tests/fixtures/past-prefinal-validity.json'),producer_sha256:await hash(fileURLToPath(import.meta.url)),responses,exports,diagrams,native,opened,errors},null,2)+'\n');
 console.log('Verified90 NFC/NFD diagrams,6 exact CLI exports,99 complete Native endpoints,3 opened past sources and exact source-frame preservation.');
}finally{await browser.close();}
