import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {gunzipSync} from 'node:zlib';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../..',import.meta.url)).replace(/\/$/,''),url=process.env.KLEM_WEB_URL,cli=process.env.KLEM_BIN,prefix=process.env.KLEM_CAPTURE_PREFIX;
assert.ok(url&&cli&&prefix);
const names=['reported-deoni-validity.json','deoniman-emphatic-validity.json','reported-command-deoni-validity.json','reported-dana-validity.json'];
const suites=await Promise.all(names.map(async n=>JSON.parse(await readFile(root+'/tests/fixtures/'+n))));
const cases=suites.flatMap(s=>s.cases);assert.equal(cases.length,130);
const catalog=JSON.parse(await readFile(root+'/web/src/grammar-labels.json'));
const closure=JSON.parse(gunzipSync(await readFile(root+'/docs/reported-dana-browser-native.json.gz')));
const {chromium}=createRequire(root+'/web/package.json')('playwright');
const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH,args:['--no-sandbox']});
const records=[],diagrams=[],responses=[],errors=[],native=[];
const hash=async p=>createHash('sha256').update(await readFile(p)).digest('hex');
const match=(a,j)=>a.lemmas.map(l=>l.text).join('|')===j.lemmas.join('|')
 &&(!j.lemma_kinds||a.lemmas.map(l=>l.kind).join('|')===j.lemma_kinds.join('|'))
 &&(!j.morphemes||a.morphemes.map(m=>m.form).join('|')===j.morphemes.join('|'))
 &&(!j.morpheme_kinds||a.morphemes.map(m=>m.kind).join('|')===j.morpheme_kinds.join('|'))
 &&(!j.required_rules||j.required_rules.every(r=>a.rules.includes(r)));
function displayed(a,order) {
 return order.map((c,i)=>{
  if('lemma' in c){const l=a.lemmas[c.lemma];return ['predicate','auxiliary','copula'].includes(l.kind)?l.text.replace(/다$/,''):l.text;}
  const m=a.morphemes[c.morpheme],p=order[i-1];
  const afterHa=p&&(('lemma' in p&&a.lemmas[p.lemma].text.endsWith('하다'))||('morpheme' in p&&a.morphemes[p.morpheme].kind==='suffix'&&a.morphemes[p.morpheme].form==='하다'));
  return afterHa?m.form.replace(/^어/,'여').replace(/^었/,'였'):m.kind==='suffix'&&['답다','되다','하다'].includes(m.form)?m.form.replace(/다$/,''):m.form;
 });
}
try {
 const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});
 page.on('pageerror',e=>errors.push(String(e)));await page.goto(url);
 for(const encoding of ['NFC','NFD']) {
  const text=[...new Set(cases.map(c=>c.surface))].join(' ').normalize(encoding);
  await page.getByLabel('Your sentence',{exact:true}).fill(text);
  const wait=page.waitForResponse(r=>r.url().endsWith('/api/analyze'));
  await page.getByRole('button',{name:'Analyze sentence',exact:true}).click();
  const response=await wait;assert.equal(response.status(),200);const api=await response.json();responses.push({encoding,request:{text},response:api});
  await page.waitForFunction(t=>document.querySelector('.sentence')?.textContent===t,text);
  for(const [mode,flag] of [['raw',null],['headword','--dict-only'],['compatible','--dict-compatible']]) {
   if(flag){await page.getByLabel('Dictionary matches only').check();if(mode==='compatible')await page.getByLabel('Exclude known grammar conflicts').check();else await page.getByLabel('Exclude known grammar conflicts').uncheck();}
   else await page.getByLabel('Dictionary matches only').uncheck();
   const expected=execFileSync(cli,['text','-','--dictionary',root+'/data/dictionaries/krdict/krdict.db',...(flag?[flag]:[])],{input:text,encoding:'utf8',maxBuffer:64*1024*1024}).trim().split('\n').map(JSON.parse);
   const download=page.waitForEvent('download');await page.getByRole('button',{name:'Export JSON',exact:true}).click();
   const actual=JSON.parse(await readFile(await(await download).path(),'utf8'));assert.deepEqual(actual.records,expected);records.push({encoding,mode,records:actual.records});
   if(mode==='raw')assert.deepEqual(api.records,expected);
  }
  await page.getByLabel('Dictionary matches only').uncheck();
  const sentence=page.getByRole('region',{name:'Sentence breakdown',exact:true});
  for(const c of cases) {
   const record=api.records.find(r=>r.analysis?.normalized===c.surface);assert.ok(record,c.surface);
   const j=c.judgments[0],index=record.analysis.analyses.findIndex(a=>match(a,j));
   if(j.verdict==='forbidden'){assert.equal(index,-1,c.id);continue;}
   assert.ok(index>=0,c.id);
   const card=sentence.locator('.breakdown-word').filter({has:page.locator('.breakdown-surface > span',{hasText:new RegExp('^'+c.surface.normalize(encoding)+'$')})});
   await card.locator('select').selectOption(String(index));
   const analysis=record.analysis.analyses[index],order=api.breakdowns[api.records.indexOf(record)][index];assert.ok(order);
   assert.deepEqual(await card.locator('.part-form').allTextContents(),displayed(analysis,order));
   const ending=card.locator('.breakdown-part').last(),form=analysis.morphemes.at(-1).form,label=catalog['-'+form];assert.ok(label,form);
   assert.equal(await ending.locator('.part-gloss').textContent(),label.label);
   const title=await ending.getAttribute('title');for(const source of label.sources)assert.ok(title.includes(String(source.id)),c.id+' source '+source.id);
   diagrams.push({case_id:c.id,surface:c.surface,encoding,index,analysis,order,label:label.label,title});
  }
  if(encoding==='NFC'){
   const focus=suites.at(-1).cases.find(c=>c.judgments[0].verdict==='required');
   const focusCard=sentence.locator('.breakdown-word').filter({has:page.locator('.breakdown-surface > span',{hasText:new RegExp('^'+focus.surface+'$')})});
   await focusCard.scrollIntoViewIfNeeded();await page.screenshot({path:prefix+'-desktop.png'});
   await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await focusCard.scrollIntoViewIfNeeded();await page.screenshot({path:prefix+'-mobile.png'});await page.setViewportSize({width:1440,height:1000});
  }
 }
 for(const [id,expected] of Object.entries(closure.complete_native_entries)){
  const response=await page.request.post(url+'/api/entry',{data:{id}});assert.equal(response.status(),200);const actual=await response.json();assert.deepEqual(actual.entry,expected,id);native.push({id,response:actual});
 }
 const prior=JSON.parse(gunzipSync(await readFile(root+'/docs/reported-deoni-main-browser.json.gz'))).browser;
 const current=new Map(diagrams.map(d=>[d.case_id+'|'+d.encoding,d]));
 assert.equal(prior.diagrams.length,148);
 for(const diagram of prior.diagrams)assert.deepEqual(current.get(diagram.case_id+'|'+diagram.encoding),diagram);
 assert.deepEqual(errors,[]);assert.equal(diagrams.length,220);assert.equal(records.length,6);assert.equal(native.length,208);
 await writeFile(prefix+'-browser.json',JSON.stringify({schema_version:1,prototype:true,cli_sha256:await hash(cli),suite_sha256:Object.fromEntries(await Promise.all(names.map(async n=>[n,await hash(root+'/tests/fixtures/'+n)]))),producer_sha256:await hash(fileURLToPath(import.meta.url)),records,responses,diagrams,native,errors},null,2)+'\n');
 console.log('Verified220 prototype diagrams,6 exact CLI/export streams,208 complete Native endpoints and original NFC/NFD byte spans.');
}finally{await browser.close();}
