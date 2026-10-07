import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {gunzipSync} from 'node:zlib';
const root=process.env.KLEM_ROOT || new URL('../..',import.meta.url).pathname.replace(/\/$/,''),proto=root,web=root+'/web';
const url=process.env.KLEM_WEB_URL,cli=process.env.KLEM_BIN,prefix=process.env.KLEM_CAPTURE_PREFIX;
assert.ok(url&&cli&&prefix);
const json=async p=>JSON.parse(await readFile(p));
const gz=async p=>JSON.parse(gunzipSync(await readFile(p)));
const hash=async p=>createHash('sha256').update(await readFile(p)).digest('hex');
const cases=await json(proto+'/tests/fixtures/declarative-contrast-original-cases.json');
const suite=await json(proto+'/tests/fixtures/declarative-contrast-validity.json');
const source=await gz(root+'/docs/declarative-contrast-source-discovery.json.gz');
const replay=await gz(root+'/docs/declarative-contrast-prototype-source-replay.json.gz');
const owners=(await gz(root+'/docs/declarative-contrast-broad-owner-preparation.json.gz')).complete_native_entries;
const catalog=await json(web+'/src/grammar-labels.json');
const {chromium}=createRequire(root+'/web/package.json')('playwright');
const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH,args:['--no-sandbox']});
const errors=[],responses=[],exports=[],diagrams=[],particleDiagrams=[],native=[],opened=[],modeJudgments=[];
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
   if(!('morpheme' in component))continue;const m=a.morphemes[component.morpheme];if(!['다마는','다만','는다마는','는다만'].includes(m.form))continue;
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
  assert.deepEqual(apiSource.records,after);assert.equal(after.length,506);
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
  for(const c of cases){const record=api.records.find(r=>r.analysis?.normalized===c.surface);const at=record.analysis.analyses.findIndex(a=>a.lemmas.map(l=>l.text).join('|')===c.expected.lemmas.join('|')&&a.rules.includes('particle.concessive'));assert.ok(at>=0,c.id+' older particle');
   const card=cardFor(c.surface,encoding);await card.locator('select').selectOption(String(at));const a=record.analysis.analyses[at],order=api.breakdowns[api.records.indexOf(record)][at];assert.deepEqual(await card.locator('.part-form').allTextContents(),displayed(a,order));
   for(const [i,component] of order.entries())if('morpheme' in component){const m=a.morphemes[component.morpheme];if(m.kind==='particle'&&['만','마는'].includes(m.form)){const title=await card.locator('.breakdown-part').nth(i).getAttribute('title');assert.ok(title.includes(m.form==='만'?'86555':'86552'));}}
   particleDiagrams.push({case_id:c.id,encoding,index:at,analysis:a,order});
  }
  if(encoding==='NFC'){
   for(const id of ['krdict:80321','krdict:80322','krdict:80323','krdict:80324','krdict:80325','krdict:80326']){
    const c=cases.find(c=>c.source_occurrence.source===id);const selected=await select(api,c,{id:'source-whole-connective',...c.expected},encoding);const atom=selected.card.locator('.breakdown-part').filter({has:page.locator('.part-gloss',{hasText:catalog['-'+c.expected.morphemes.at(-1)].label})});await atom.click();
    const head=owners[id].headword;const button=page.locator('.entry-choices button').filter({has:page.locator('span',{hasText:new RegExp('^'+head+'(?:[0-9]+)?$')})});await button.click();await page.waitForFunction(h=>document.querySelector('.entry-heading h2')?.textContent?.includes(h),head);
    for(const sense of owners[id].senses)assert.ok((await page.locator('.entry-content').textContent()).includes(sense.definition));opened.push({id,head});
   }
   const small=await analyze('없다마는 간다마는 안다만');for(const word of ['없다마는','간다마는','안다만']){const c=suite.cases.find(c=>c.surface===word&&c.judgments[0].verdict==='required');await select(small,c,c.judgments[0],encoding);}
   await page.screenshot({path:prefix+'-desktop.png'});await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.evaluate(async()=>{await document.fonts.ready;});await cardFor('안다만',encoding).evaluate(el=>el.scrollIntoView({behavior:'instant',block:'center'}));await page.screenshot({path:prefix+'-mobile.png'});await page.setViewportSize({width:1440,height:1000});
  }
 }
 for(const [id,expected] of Object.entries(owners)){const r=await page.request.post(url+'/api/entry',{data:{id}});assert.equal(r.status(),200);const response=await r.json();assert.deepEqual(response.entry,expected,id);native.push({id,response});}
 assert.equal(diagrams.length,64);assert.equal(particleDiagrams.length,48);assert.equal(exports.length,6);assert.equal(native.length,115);assert.equal(opened.length,6);assert.equal(modeJudgments.length,252);assert.deepEqual(errors,[]);
 await writeFile(prefix+'-browser.json',JSON.stringify({schema_version:1,scope:'Actual configured current runtime and SolidJS assets; all complete original-source streams, separately retained ending/particle interpretations, 42 individual structural cases and full 115-entry Native closure. Browser results do not certify contextual sense/register or candidate precision; captures are bound to the configured CLI; each main/package build requires its own actual run.',cli_sha256:await hash(cli),producer_sha256:await hash(new URL(import.meta.url)),catalog_sha256:await hash(web+'/src/grammar-labels.json'),responses,exports,diagrams,particleDiagrams,native,opened,modeJudgments,errors},null,2)+'\n');
 console.log('Passed64 whole-connective and48 split-particle ordered diagrams,6 exact exports,115 complete Native entries,6 primary-source clicks,252 mode judgments and2x506 original API frames.');
}finally{await browser.close();}
