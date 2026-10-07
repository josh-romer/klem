import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {gunzipSync} from 'node:zlib';
const root=process.env.KLEM_ROOT || new URL('../..',import.meta.url).pathname.replace(/\/$/,''),proto=root,review=root;
const url=process.env.KLEM_WEB_URL,cli=process.env.KLEM_BIN,prefix=process.env.KLEM_CAPTURE_PREFIX;
assert.ok(url&&cli&&prefix);
const json=async path=>JSON.parse(await readFile(path));
const gz=async path=>JSON.parse(gunzipSync(await readFile(path)));
const suite=await json(review+'/tests/fixtures/literary-ri-prefinal-validity.json');
const policy=await json(review+'/tests/fixtures/literary-ri-prefinal-policy-validity.json');
const owners=(await gz(root+'/docs/literary-ri-prefinal-broad-owner-preparation.json.gz')).complete_native_entries;
const source=await gz(root+'/docs/literary-ri-prefinal-source-discovery.json.gz');
const cliProof=await gz(root+'/docs/literary-ri-prefinal-prototype-cli.json.gz');
const catalog=await json(proto+'/web/src/grammar-labels.json');
const archivedBefore=await json(root+'/docs/literary-ri-prefinal-prototype-browser-final-browser.json');
const hash=async path=>createHash('sha256').update(await readFile(path)).digest('hex');
const match=(a,j)=>a.lemmas.map(l=>l.text).join('|')===j.lemmas.join('|')&&a.lemmas.map(l=>l.kind).join('|')===j.lemma_kinds.join('|')&&a.morphemes.map(m=>m.form).join('|')===j.morphemes.join('|')&&a.morphemes.map(m=>m.kind).join('|')===j.morpheme_kinds.join('|');
const displayed=(a,order)=>order.map((c,i)=>{
 if('lemma' in c){const l=a.lemmas[c.lemma];return ['predicate','auxiliary','copula'].includes(l.kind)?l.text.replace(/다$/,''):l.text;}
 const m=a.morphemes[c.morpheme],p=order[i-1];
 const afterHa=p&&(('lemma' in p&&a.lemmas[p.lemma].text.endsWith('하다'))||('morpheme' in p&&a.morphemes[p.morpheme].kind==='suffix'&&a.morphemes[p.morpheme].form==='하다'));
 return afterHa?m.form.replace(/^어/,'여').replace(/^었/,'였'):m.form;
});
const {chromium}=createRequire(root+'/web/package.json')('playwright');
const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH,args:['--no-sandbox']});
const errors=[],responses=[],exports=[],diagrams=[],native=[],opened=[],modeJudgments=[];
try{
 const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});page.on('pageerror',e=>errors.push(String(e)));await page.goto(url);
 const apiRequest=async (base,text)=>{const r=await page.request.post(base+'/api/analyze',{data:{text}});assert.equal(r.status(),200);return r.json();};
 const analyze=async text=>{await page.getByLabel('Your sentence',{exact:true}).fill(text);const wait=page.waitForResponse(r=>r.url().endsWith('/api/analyze'));await page.getByRole('button',{name:'Analyze sentence',exact:true}).click();const r=await wait;assert.equal(r.status(),200);const api=await r.json();await page.waitForFunction(t=>document.querySelector('.sentence')?.textContent===t,text);return api;};
 const select=async (api,c,j,encoding)=>{
  const record=api.records.find(r=>r.analysis?.normalized===c.surface);assert.ok(record,c.surface);const index=record.analysis.analyses.findIndex(a=>match(a,j));assert.ok(index>=0,c.id);
  const card=page.getByRole('region',{name:'Sentence breakdown',exact:true}).locator('.breakdown-word').filter({has:page.locator('.breakdown-surface > span',{hasText:new RegExp('^'+c.surface.normalize(encoding)+'$')})});await card.locator('select').selectOption(String(index));
  const a=record.analysis.analyses[index],order=api.breakdowns[api.records.indexOf(record)][index];assert.ok(order);assert.deepEqual(await card.locator('.part-form').allTextContents(),displayed(a,order));
  const pieces=[];
  for(const [i,component] of order.entries()){
   if(!('morpheme' in component))continue;const m=a.morphemes[component.morpheme];if(m.form!=='으리'&&m.form!=='으니라'&&m.form!=='으리다')continue;
   const key=m.form==='으리'?'-으리-':m.form==='으리다'?'-으리다':'-으리니라';const atom=card.locator('.breakdown-part').nth(i);const label=await atom.locator('.part-gloss').textContent();assert.equal(label,catalog[key].label,c.id);const title=await atom.getAttribute('title');for(const s of catalog[key].sources)assert.ok(title.includes(String(s.id)),c.id+' source '+s.id);pieces.push({morpheme:component.morpheme,key,label,title});
  }
  assert.ok(pieces.length);return {card,diagram:{case_id:c.id,judgment_id:j.id,encoding,index,analysis:a,order,pieces}};
 };
 for(const encoding of ['NFC','NFD']){
  const text=source.input.normalize(encoding),before=archivedBefore.responses.find(r=>r.encoding===encoding).before,after=await apiRequest(url,text);
  const oldRun=source.runs.find(r=>r.encoding===encoding&&r.mode==='raw'),newRun=cliProof.streams.find(r=>r.encoding===encoding&&r.mode==='raw');
  assert.deepEqual(before.records,oldRun.jsonl.trim().split('\n').map(JSON.parse));assert.deepEqual(after.records,newRun.jsonl.trim().split('\n').map(JSON.parse));assert.equal(after.records.length,275);
  for(let ri=0;ri<before.records.length;ri++){
   const old=before.records[ri],next=after.records[ri];if(!old.analysis)continue;let last=-1;
   for(const [i,a] of old.analysis.analyses.entries()){
    const at=next.analysis.analyses.findIndex(n=>JSON.stringify(n)===JSON.stringify(a));assert.ok(at>last);last=at;assert.deepEqual(after.breakdowns[ri][at],before.breakdowns[ri][i]);
   }
  }
  responses.push({encoding,request:{text},before,after});
  const words=[...new Set(policy.cases.map(c=>c.surface))].join(' ').normalize(encoding),api=await analyze(words);
  for(const [mode,flag] of [['raw',null],['headword','--dict-only'],['compatible','--dict-compatible']]){
   if(flag){await page.getByLabel('Dictionary matches only').check();if(mode==='compatible')await page.getByLabel('Exclude known grammar conflicts').check();else await page.getByLabel('Exclude known grammar conflicts').uncheck();}else await page.getByLabel('Dictionary matches only').uncheck();
   const records=execFileSync(cli,['text','-','--dictionary',root+'/data/dictionaries/krdict/krdict.db',...(flag?[flag]:[])],{input:words,encoding:'utf8',maxBuffer:64*1024*1024}).trim().split('\n').map(JSON.parse);
   const wait=page.waitForEvent('download');await page.getByRole('button',{name:'Export JSON',exact:true}).click();const d=await wait,actual=JSON.parse(await readFile(await d.path(),'utf8'));assert.deepEqual(actual.records,records);
   exports.push({encoding,mode,request:{text:words},records});
   const applicable=mode==='compatible'?policy:suite;
   for(const c of applicable.cases){const record=records.find(r=>r.analysis?.normalized===c.surface);for(const j of c.judgments){const present=record?.analysis.analyses.some(a=>match(a,j))??false;assert.equal(present,j.verdict==='required',c.id+' '+mode);modeJudgments.push({encoding,mode,case_id:c.id,judgment_id:j.id,present,verdict:j.verdict});}}
  }
  await page.getByLabel('Dictionary matches only').uncheck();
  for(const c of suite.cases)for(const j of c.judgments)if(j.verdict==='required')diagrams.push((await select(api,c,j,encoding)).diagram);
  if(encoding==='NFC'){
   const c=suite.cases.find(c=>c.surface==='행복하리니'),j=c.judgments[0],selected=await select(api,c,j,encoding);const ri=selected.card.locator('.breakdown-part').filter({has:page.locator('.part-gloss',{hasText:catalog['-으리-'].label})});await ri.click();
   for(const [id,head] of [['krdict:52612','-리-'],['krdict:86606','-으리-']]){
    const button=page.locator('.entry-choices button').filter({has:page.locator('span',{hasText:new RegExp('^'+head+'(?:[0-9]+)?$')})});await button.click();await page.waitForFunction(head=>document.querySelector('.entry-heading h2')?.textContent?.includes(head),head);const response=await page.request.post(url+'/api/entry',{data:{id}});assert.equal(response.status(),200);assert.deepEqual((await response.json()).entry,owners[id]);for(const sense of owners[id].senses)assert.ok((await page.locator('.entry-content').textContent()).includes(sense.definition));opened.push({id,head});
   }
   const smallApi=await analyze('행복하리니 가리니라');for(const word of ['행복하리니','가리니라']){const c=suite.cases.find(c=>c.surface===word);await select(smallApi,c,c.judgments[0],encoding);}
   const card=page.locator('.breakdown-word').filter({has:page.locator('.breakdown-surface > span',{hasText:/^가리니라$/})});await card.scrollIntoViewIfNeeded();await page.screenshot({path:prefix+'-desktop.png'});await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.evaluate(async()=>{await document.fonts.ready;});await card.evaluate(el=>el.scrollIntoView({behavior:'instant',block:'center'}));await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));await page.screenshot({path:prefix+'-mobile.png'});await page.setViewportSize({width:1440,height:1000});
  }
 }
 for(const [id,expected] of Object.entries(owners)){const r=await page.request.post(url+'/api/entry',{data:{id}});assert.equal(r.status(),200);const response=await r.json();assert.deepEqual(response.entry,expected,id);native.push({id,response});}
 assert.equal(diagrams.length,60);assert.equal(exports.length,6);assert.equal(native.length,182);assert.deepEqual(errors,[]);
 await writeFile(prefix+'-browser.json',JSON.stringify({schema_version:1,scope:'Actual main/library UI and CLI, complete original frames and named mode-specific structures including two positive B counterparts. Packaged release checks remain separate. Contextual and broader candidate precision remain unjudged.',cli_sha256:await hash(cli),producer_sha256:await hash(new URL(import.meta.url)),suite_sha256:await hash(review+'/tests/fixtures/literary-ri-prefinal-validity.json'),catalog_sha256:await hash(proto+'/web/src/grammar-labels.json'),responses,exports,diagrams,native,opened,modeJudgments,errors},null,2)+'\n');console.log('Passed60 ordered NFC/NFD diagrams,6 exact exports,182 Native entries,2 source clicks;2x275 original frames and candidate orders preserved.');
}finally{await browser.close();}
