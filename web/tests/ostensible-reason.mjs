import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {gunzipSync} from 'node:zlib';
const root=process.env.KLEM_ROOT || new URL('../..',import.meta.url).pathname.replace(/\/$/,''),proto=process.env.KLEM_PROTOTYPE||root,web=process.env.KLEM_FRONTEND||root+'/web';
const url=process.env.KLEM_WEB_URL,cli=process.env.KLEM_BIN,prefix=process.env.KLEM_CAPTURE_PREFIX;
assert.ok(url&&cli&&prefix);
const json=async p=>JSON.parse(await readFile(p));
const gz=async p=>JSON.parse(gunzipSync(await readFile(p)));
const hash=async p=>createHash('sha256').update(await readFile(p)).digest('hex');
const cases=await json(proto+'/tests/fixtures/ostensible-reason-original-cases.json');
const suite=await json(proto+'/tests/fixtures/ostensible-reason-validity.json');
const source=await gz(root+'/docs/ostensible-reason-source-discovery.json.gz');
const replay=await gz(root+'/docs/ostensible-reason-prototype-source-replay.json.gz');
const owners=(await gz(root+'/docs/ostensible-reason-boundary-owner-preparation.json.gz')).complete_native_entries;
const catalog=await json(web+'/src/grammar-labels.json');
const conditional=(await json(proto+'/tests/fixtures/ostensible-reason-mode-scope.json')).cases;
const {chromium}=createRequire(root+'/web/package.json')('playwright');
const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH,args:['--no-sandbox']});
const errors=[],responses=[],exports=[],diagrams=[],particleDiagrams=[],native=[],opened=[],modeJudgments=[],conditionalExports=[],conditionalDiagrams=[],conditionalModeJudgments=[];
const match=(a,j)=>a.lemmas.map(l=>l.text).join('|')===j.lemmas.join('|')&&a.lemmas.map(l=>l.kind).join('|')===j.lemma_kinds.join('|')&&a.morphemes.map(m=>m.form).join('|')===j.morphemes.join('|')&&a.morphemes.map(m=>m.kind).join('|')===j.morpheme_kinds.join('|')&&j.required_rules.every(r=>a.rules.includes(r));
const displayed=(a,order)=>order.map((c,i)=>{
 if('lemma' in c){const l=a.lemmas[c.lemma];return ['predicate','auxiliary','copula'].includes(l.kind)?l.text.replace(/다$/,''):l.text;}
 const m=a.morphemes[c.morpheme],p=order[i-1];
 const afterHa=p&&(('lemma' in p&&a.lemmas[p.lemma].text.endsWith('하다'))||('morpheme' in p&&a.morphemes[p.morpheme].kind==='suffix'&&a.morphemes[p.morpheme].form==='하다'));
 return afterHa?m.form.replace(/^어/,'여').replace(/^었/,'였'):m.form;
});
try{
 const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});page.on('pageerror',e=>errors.push(String(e)));await page.goto(url);
 const analyze=async text=>{
  await page.getByLabel('Your sentence',{exact:true}).fill(text);
  const wait=page.waitForResponse(r=>r.url().endsWith('/api/analyze'));
  await page.getByRole('button',{name:'Analyze sentence',exact:true}).click();const response=await wait;assert.equal(response.status(),200);
  const api=await response.json();await page.waitForFunction(t=>document.querySelector('.sentence')?.textContent===t,text);return api;
 };
 const cardFor=(surface,encoding)=>page.getByRole('region',{name:'Sentence breakdown',exact:true}).locator('.breakdown-word').filter({has:page.locator('.breakdown-surface > span',{hasText:new RegExp('^'+surface.normalize(encoding)+'$')})});
 const select=async(api,c,j,encoding)=>{
  const record=api.records.find(r=>r.analysis?.normalized===c.surface);assert.ok(record,c.surface);
  const index=record.analysis.analyses.findIndex(a=>match(a,j));assert.ok(index>=0,c.id);
  const card=cardFor(c.surface,encoding);await card.locator('select').selectOption(String(index));
  const a=record.analysis.analyses[index],order=api.breakdowns[api.records.indexOf(record)][index];assert.ok(order);
  assert.deepEqual(await card.locator('.part-form').allTextContents(),displayed(a,order));
  const pieces=[];
  for(const [i,component] of order.entries()){
   if(!('morpheme' in component))continue;const m=a.morphemes[component.morpheme];if(!['답시고','는답시고'].includes(m.form))continue;
   const key='-'+m.form,atom=card.locator('.breakdown-part').nth(i),label=await atom.locator('.part-gloss').textContent(),title=await atom.getAttribute('title');
   assert.equal(label,catalog[key].label,c.id);for(const s of catalog[key].sources)assert.ok(title.includes(String(s.id)),c.id+' source '+s.id);
   pieces.push({morpheme:component.morpheme,key,label,title});
  }
  assert.equal(pieces.length,1);return {card,diagram:{case_id:c.id,judgment_id:j.id,encoding,index,analysis:a,order,pieces}};
 };
 for(const encoding of ['NFC','NFD']){
  const text=source.input.normalize(encoding),response=await page.request.post(url+'/api/analyze',{data:{text}});assert.equal(response.status(),200);const apiSource=await response.json();
  const before=source.runs.find(r=>r.encoding===encoding&&r.mode==='raw').jsonl.trim().split('\n').map(JSON.parse);
  const after=replay.runs.find(r=>r.encoding===encoding&&r.mode==='raw').jsonl.trim().split('\n').map(JSON.parse);
  assert.deepEqual(apiSource.records,after);assert.equal(after.length,233);
  for(let i=0;i<before.length;i++)if(before[i].analysis){let last=-1;for(const a of before[i].analysis.analyses){const at=after[i].analysis.analyses.findIndex(n=>JSON.stringify(n)===JSON.stringify(a));assert.ok(at>last);last=at;assert.ok(apiSource.breakdowns[i][at]);}}
  responses.push({encoding,request:{text},before:{records:before},after:apiSource});
  const words=[...new Set(suite.cases.map(c=>c.surface))].join(' ').normalize(encoding),api=await analyze(words);
  for(const [mode,flag] of [['raw',null],['headword','--dict-only'],['compatible','--dict-compatible']]){
   if(flag){await page.getByLabel('Dictionary matches only').check();if(mode==='compatible')await page.getByLabel('Exclude known grammar conflicts').check();else await page.getByLabel('Exclude known grammar conflicts').uncheck();}else await page.getByLabel('Dictionary matches only').uncheck();
   const records=execFileSync(cli,['text','-','--dictionary',root+'/data/dictionaries/krdict/krdict.db',...(flag?[flag]:[])],{input:words,encoding:'utf8',maxBuffer:64*1024*1024}).trim().split('\n').map(JSON.parse);
   const wait=page.waitForEvent('download');await page.getByRole('button',{name:'Export JSON',exact:true}).click();const d=await wait,actual=JSON.parse(await readFile(await d.path(),'utf8'));assert.deepEqual(actual.records,records);
   exports.push({encoding,mode,request:{text:words},records});
   for(const c of suite.cases){const record=records.find(r=>r.analysis?.normalized===c.surface);for(const j of c.judgments){const present=record?.analysis.analyses.some(a=>match(a,j))??false;assert.equal(present,j.verdict==='required',c.id+' '+mode);modeJudgments.push({encoding,mode,case_id:c.id,judgment_id:j.id,present,verdict:j.verdict});}}
  }
  await page.getByLabel('Dictionary matches only').uncheck();
  for(const c of suite.cases)for(const j of c.judgments)if(j.verdict==='required')diagrams.push((await select(api,c,j,encoding)).diagram);
  if(encoding==='NFC'){
   for(const id of ['krdict:80316','krdict:80317','krdict:80318']){
    const c=cases.find(c=>c.source_occurrence.source===id);const selected=await select(api,c,{id:'source-whole-connective',...c.expected},encoding);const atom=selected.card.locator('.breakdown-part').filter({has:page.locator('.part-gloss',{hasText:catalog['-'+c.expected.morphemes.at(-1)].label})});await atom.click();
    const head=owners[id].headword;const button=page.locator('.entry-choices button').filter({has:page.locator('span',{hasText:new RegExp('^'+head+'(?:[0-9]+)?$')})});await button.click();await page.waitForFunction(h=>document.querySelector('.entry-heading h2')?.textContent?.includes(h),head);
    for(const sense of owners[id].senses)assert.ok((await page.locator('.entry-content').textContent()).includes(sense.definition));opened.push({id,head});
   }
   const small=await analyze('간답시고 먹는답시고 좋답시고');for(const word of ['간답시고','먹는답시고','좋답시고']){const c=suite.cases.find(c=>c.surface===word&&c.judgments[0].verdict==='required');await select(small,c,c.judgments[0],encoding);}
   await page.screenshot({path:prefix+'-desktop.png'});await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.evaluate(async()=>{await document.fonts.ready;});await cardFor('좋답시고',encoding).evaluate(el=>el.scrollIntoView({behavior:'instant',block:'center'}));await page.screenshot({path:prefix+'-mobile.png'});await page.setViewportSize({width:1440,height:1000});
  }
  const modeWords=conditional.map(c=>c.surface).join(' ').normalize(encoding),modeApi=await analyze(modeWords);
  for(const [mode,flag] of [['raw',null],['headword','--dict-only'],['compatible','--dict-compatible']]){
   if(flag){await page.getByLabel('Dictionary matches only').check();if(mode==='compatible')await page.getByLabel('Exclude known grammar conflicts').check();else await page.getByLabel('Exclude known grammar conflicts').uncheck();}else await page.getByLabel('Dictionary matches only').uncheck();
   const records=execFileSync(cli,['text','-','--dictionary',root+'/data/dictionaries/krdict/krdict.db',...(flag?[flag]:[])],{input:modeWords,encoding:'utf8',maxBuffer:64*1024*1024}).trim().split('\n').map(JSON.parse);
   const wait=page.waitForEvent('download');await page.getByRole('button',{name:'Export JSON',exact:true}).click();const download=await wait,actual=JSON.parse(await readFile(await download.path(),'utf8'));assert.deepEqual(actual.records,records);
   conditionalExports.push({encoding,mode,request:{text:modeWords},records});
   for(const c of conditional){
    const record=records.find(r=>r.analysis?.normalized===c.surface);assert.ok(record,c.id);
    const targets=record.analysis.analyses.flatMap((a,index)=>match(a,c.expected)?[index]:[]);
    assert.equal(targets.length>0,c.expected_presence[mode],c.id+' '+mode);
    for(const index of targets)for(const expected of c.expected_entry_statuses){const entry=record.dictionary.readings[index].lemmas[expected.lemma].entries.find(e=>e.id===expected.id);assert.ok(entry,c.id+' '+expected.id);assert.equal(entry.status,expected.status);}
    conditionalModeJudgments.push({encoding,mode,case_id:c.id,judgment_id:c.judgment_id,present:targets.length>0,expected_presence:c.expected_presence[mode],contextual_verdict:'unjudged'});
   }
  }
  await page.getByLabel('Dictionary matches only').uncheck();
  for(const c of conditional)if(c.expected_presence.raw)conditionalDiagrams.push((await select(modeApi,c,{id:c.judgment_id,...c.expected},encoding)).diagram);
 }
 for(const [id,expected] of Object.entries(owners)){const r=await page.request.post(url+'/api/entry',{data:{id}});assert.equal(r.status(),200);const response=await r.json();assert.deepEqual(response.entry,expected,id);native.push({id,response});}
 assert.equal(diagrams.length,42);assert.equal(particleDiagrams.length,0);assert.equal(exports.length,6);assert.equal(native.length,91);assert.equal(opened.length,3);assert.equal(modeJudgments.length,156);assert.equal(conditionalExports.length,6);assert.equal(conditionalDiagrams.length,22);assert.equal(conditionalModeJudgments.length,72);assert.deepEqual(errors,[]);
 await writeFile(prefix+'-browser.json',JSON.stringify({schema_version:1,scope:'Actual configured current runtime and SolidJS assets; all complete original-source streams, 26 individual structural cases and full91-entry finite Native closure. Twelve own-POS/negative/copular cases have separate mode-specific presence and Native status assertions, without promoting Unknown attachments or raw hypotheses to structural correctness. Browser results do not certify contextual sense/register or candidate precision; captures are bound to the configured CLI; each main/package build requires its own actual run.',cli_sha256:await hash(cli),producer_sha256:await hash(new URL(import.meta.url)),catalog_sha256:await hash(web+'/src/grammar-labels.json'),responses,exports,diagrams,particleDiagrams,native,opened,modeJudgments,conditionalExports,conditionalDiagrams,conditionalModeJudgments,errors},null,2)+'\n');
 console.log('Passed42 ordered ostensible-reason diagrams,6 exact exports,91 complete Native entries,3 primary-source clicks,156 mode judgments and2x233 original API frames;22 conditional diagrams,6 further exact exports and72 owner/mode observations.');
}finally{await browser.close();}
