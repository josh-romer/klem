import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {gunzipSync} from 'node:zlib';
const root=process.env.KLEM_ROOT,proto=root;
assert.ok(root);
const url=process.env.KLEM_WEB_URL,cli=process.env.KLEM_BIN,prefix=process.env.KLEM_CAPTURE_PREFIX;
assert.ok(url&&cli&&prefix);
const json=async p=>JSON.parse(await readFile(p));
const gz=async p=>JSON.parse(gunzipSync(await readFile(p)));
const hash=async p=>createHash('sha256').update(await readFile(p)).digest('hex');
const cases=await json(proto+'/tests/fixtures/literary-future-kko-original-cases.json');
const boundaries=(await json(proto+'/tests/fixtures/literary-future-kko-authored-boundaries.json')).cases;
const finite=await json(root+'/tests/fixtures/literary-future-kko-validity.json');
for(const c of finite.cases.filter(c=>c.id.startsWith('literary-future-kko-owner-extension-'))){const j=c.judgments[0];boundaries.push({...c,...j,expected_presence:{raw:j.verdict==='required',headword:j.verdict==='required',compatible:j.verdict==='required'}});}
const source=await gz(root+'/docs/literary-future-kko-source-discovery.json.gz');
const replay=await gz(root+'/docs/literary-future-kko-prototype-source-replay.json.gz');
const owners=(await gz(root+'/docs/literary-future-kko-spacing-owner-preparation.json.gz')).complete_native_entries;
const catalog=await json(proto+'/web/src/grammar-labels.json');
const match=(a,c)=>JSON.stringify(a.lemmas.map(l=>l.text))===JSON.stringify(c.lemmas)
 &&JSON.stringify(a.lemmas.map(l=>l.kind))===JSON.stringify(c.lemma_kinds)
 &&JSON.stringify(a.morphemes.map(m=>m.form))===JSON.stringify(c.morphemes)
 &&JSON.stringify(a.morphemes.map(m=>m.kind))===JSON.stringify(c.morpheme_kinds)
 &&c.required_rules.every(r=>a.rules.includes(r));
const {chromium}=createRequire(root+'/web/package.json')('playwright');
const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH,args:['--no-sandbox']});
const errors=[],responses=[],exports=[],diagrams=[],native=[],opened=[],modeJudgments=[];
try{
 const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});
 page.on('pageerror',e=>errors.push(String(e)));await page.goto(url);
 const analyze=async text=>{
  await page.getByLabel('Your sentence',{exact:true}).fill(text);
  const wait=page.waitForResponse(r=>r.url().endsWith('/api/analyze'));
  await page.getByRole('button',{name:'Analyze sentence',exact:true}).click();
  const response=await wait;assert.equal(response.status(),200);
  const api=await response.json();await page.waitForFunction(t=>document.querySelector('.sentence')?.textContent===t,text);return api;
 };
 for(const encoding of ['NFC','NFD']){
  const response=await page.request.post(url+'/api/analyze',{data:{text:source.input.normalize(encoding)}});
  assert.equal(response.status(),200);const apiSource=await response.json();
  const expected=replay.runs.find(r=>r.encoding===encoding&&r.mode==='raw').jsonl.trim().split('\n').map(JSON.parse);
  assert.deepEqual(apiSource.records,expected);assert.equal(expected.length,253);
  responses.push({encoding,response:apiSource});
  const words=[...new Set([...cases,...boundaries].map(c=>c.surface))].join(' ').normalize(encoding);
  const api=await analyze(words);
  for(const [mode,flag] of [['raw',null],['headword','--dict-only'],['compatible','--dict-compatible']]){
   if(flag){await page.getByLabel('Dictionary matches only').check();if(mode==='compatible')await page.getByLabel('Exclude known grammar conflicts').check();else await page.getByLabel('Exclude known grammar conflicts').uncheck();}else await page.getByLabel('Dictionary matches only').uncheck();
   const records=execFileSync(cli,['text','-','--dictionary',root+'/data/dictionaries/krdict/krdict.db',...(flag?[flag]:[])],{input:words,encoding:'utf8',maxBuffer:64*1024*1024}).trim().split('\n').map(JSON.parse);
   const wait=page.waitForEvent('download');await page.getByRole('button',{name:'Export JSON',exact:true}).click();const download=await wait;
   const exported=JSON.parse(await readFile(await download.path(),'utf8'));assert.deepEqual(exported.records,records);
   exports.push({encoding,mode,request:{text:words},records});
   for(const c of [...cases.map(c=>({...c,...c.expected,expected_presence:{raw:true,headword:true,compatible:true}})),...boundaries]){
    const record=records.find(r=>r.analysis?.normalized===c.surface);assert.ok(record,c.id);
    const present=record.analysis.analyses.some(a=>match(a,c));assert.equal(present,c.expected_presence[mode],c.id+' '+mode);
    modeJudgments.push({encoding,mode,case_id:c.id,present,expected_present:c.expected_presence[mode]});
   }
  }
  await page.getByLabel('Dictionary matches only').uncheck();
  for(const c of cases){
   const record=api.records.find(r=>r.analysis?.normalized===c.surface),index=record.analysis.analyses.findIndex(a=>match(a,c.expected));assert.ok(index>=0,c.id);
   const card=page.getByRole('region',{name:'Sentence breakdown',exact:true}).locator('.breakdown-word').filter({has:page.locator('.breakdown-surface > span',{hasText:new RegExp('^'+c.surface.normalize(encoding)+'$')})});
   await card.locator('select').selectOption(String(index));
   const a=record.analysis.analyses[index],order=api.breakdowns[api.records.indexOf(record)][index];assert.ok(order);
   const position=order.findIndex(v=>'morpheme' in v&&a.morphemes[v.morpheme].form==='을꼬');assert.ok(position>=0);
   const atom=card.locator('.breakdown-part').nth(position),label=await atom.locator('.part-gloss').textContent(),title=await atom.getAttribute('title');
   assert.equal(label,'Literary future question');for(const entry of catalog['-을꼬'].sources)assert.ok(title.includes(String(entry.id)));
   diagrams.push({case_id:c.id,encoding,index,analysis:a,order,label,title});
  }
  if(encoding==='NFC'){
   const last=cases.at(-1),card=page.getByRole('region',{name:'Sentence breakdown',exact:true}).locator('.breakdown-word').filter({has:page.locator('.breakdown-surface > span',{hasText:new RegExp('^'+last.surface+'$')})});
   const atom=card.locator('.breakdown-part').filter({has:page.locator('.part-gloss',{hasText:'Literary future question'})});
   for(const id of ['krdict:81026','krdict:81032']){
    await atom.click();const head=owners[id].headword;
    await page.locator('.entry-choices button').filter({has:page.locator('span',{hasText:new RegExp('^'+head+'(?:[0-9]+)?$')})}).click();
    await page.waitForFunction(h=>document.querySelector('.entry-heading h2')?.textContent?.includes(h),head);
    for(const sense of owners[id].senses)assert.ok((await page.locator('.entry-content').textContent()).includes(sense.definition));opened.push({id,head});
   }
   const scene=['누구일꼬','뜰꼬','먹을꼬','갔을꼬'],visual=await analyze(scene.join(' '));
   for(const word of scene){
    const c=cases.find(c=>c.surface===word),r=visual.records.find(r=>r.analysis?.normalized===word),at=r.analysis.analyses.findIndex(a=>match(a,c.expected));assert.ok(at>=0);
    const card=page.getByRole('region',{name:'Sentence breakdown',exact:true}).locator('.breakdown-word').filter({has:page.locator('.breakdown-surface > span',{hasText:new RegExp('^'+word+'$')})});await card.locator('select').selectOption(String(at));
    assert.ok((await card.locator('.part-gloss').allTextContents()).includes('Literary future question'));
   }
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.evaluate(async()=>{await document.fonts.ready;});
   await page.getByRole('region',{name:'Sentence breakdown',exact:true}).evaluate(el=>el.scrollIntoView({behavior:'instant',block:'start'}));await page.screenshot({path:prefix+'-desktop.png'});
   await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   await page.getByRole('region',{name:'Sentence breakdown',exact:true}).evaluate(el=>el.scrollIntoView({behavior:'instant',block:'start'}));await page.screenshot({path:prefix+'-mobile.png'});await page.setViewportSize({width:1440,height:1000});
  }
 }
 for(const [id,expected] of Object.entries(owners)){
  const r=await page.request.post(url+'/api/entry',{data:{id}});assert.equal(r.status(),200);const response=await r.json();assert.deepEqual(response.entry,expected,id);native.push({id,response});
 }
 assert.equal(diagrams.length,38);assert.equal(exports.length,6);assert.equal(native.length,153);assert.equal(modeJudgments.length,504);assert.equal(opened.length,2);assert.deepEqual(errors,[]);
 await writeFile(prefix+'-browser.json',JSON.stringify({schema_version:1,scope:'Actual configured browser: two complete source APIs, nineteen original diagrams in both encodings, six exact CLI exports, all47 original boundary cases and18 finite owner-extension structures, with153 complete Native endpoints. All947main inputs and built assets are frozen by the runtime producer. Performance/combined inventory gates and contextual/sense/independent review remain separate.',cli_sha256:await hash(cli),producer_sha256:await hash(new URL(import.meta.url)),catalog_sha256:await hash(proto+'/web/src/grammar-labels.json'),responses,exports,diagrams,native,opened,modeJudgments,errors},null,2)+'\n');
 console.log('Passed38 original diagrams,6 exact exports,153 complete Native endpoints,504 finite mode checks and2x253 source API frames.');
}finally{await browser.close();}
