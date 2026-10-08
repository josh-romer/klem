import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {gunzipSync} from 'node:zlib';
const root=process.env.KLEM_ROOT,url=process.env.KLEM_WEB_URL,cli=process.env.KLEM_BIN,prefix=process.env.KLEM_CAPTURE_PREFIX;
assert.ok(root&&url&&cli&&prefix);
const baseCases=JSON.parse(await readFile(root+'/tests/fixtures/predicate-auxiliary-spacing-cases.json','utf8')).cases;
const ownerCases=JSON.parse(await readFile(root+'/tests/fixtures/predicate-auxiliary-spacing-owner-cases.json','utf8')).cases
 .filter(c=>c.id!=='auxiliary-nominalization-topic').map(c=>({...c,required_spaces:[c.required_space]}));
const cases=[...baseCases,...ownerCases];
const owners=JSON.parse(gunzipSync(await readFile(process.env.KLEM_PPUN_OWNERS))).complete_native_entries;
const {chromium}=createRequire(process.env.KLEM_DEPENDENCY_ROOT+'/web/package.json')('playwright');
const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH,args:['--no-sandbox']});
const errors=[],exports=[],responses=[],diagrams=[],native=[];
try {
 const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});
 page.on('pageerror',error=>errors.push(String(error)));await page.goto(url);
 async function analyze(text) {
  await page.getByLabel('Your sentence',{exact:true}).fill(text);
  const wait=page.waitForResponse(r=>r.url().endsWith('/api/analyze')&&r.request().method()==='POST'&&r.request().postDataJSON().text===text);
  await page.getByRole('button',{name:'Analyze sentence',exact:true}).click();
  const response=await wait;assert.equal(response.status(),200);
  const api=await response.json();await page.waitForFunction(t=>document.querySelector('.sentence')?.textContent===t,text);return api;
 }
 for(const encoding of ['NFC','NFD']) {
  const text=cases.map(c=>c.surface.normalize(encoding)).join(' ');
  let api=await analyze(text);
  if(!await page.getByLabel('Suggest missing spaces').isChecked()) {
   const wait=page.waitForResponse(r=>r.url().endsWith('/api/analyze')&&r.request().postDataJSON()?.suggest_spacing===true);
   await page.getByLabel('Suggest missing spaces').check();const response=await wait;assert.equal(response.status(),200);api=await response.json();
   await page.getByRole('button',{name:'Export JSON',exact:true}).waitFor();
  }
  responses.push({encoding,response:api});
  for(const [mode,flag] of [['raw',null],['headword','--dict-only'],['compatible','--dict-compatible']]) {
   if(flag) {await page.getByLabel('Dictionary matches only').check();if(mode==='compatible')await page.getByLabel('Exclude known grammar conflicts').check();else await page.getByLabel('Exclude known grammar conflicts').uncheck();}
   else await page.getByLabel('Dictionary matches only').uncheck();
   const expected=execFileSync(cli,['text','-','--dictionary',process.env.KLEM_DICTIONARY,'--suggest-spacing',...(flag?[flag]:[])],{input:text,encoding:'utf8',maxBuffer:32*1024*1024}).trim().split('\n').map(JSON.parse);
   const wait=page.waitForEvent('download');await page.getByRole('button',{name:'Export JSON',exact:true}).click();
   const exported=JSON.parse(await readFile(await (await wait).path(),'utf8'));assert.deepEqual(exported.records,expected);exports.push({encoding,mode,records:expected});
   for(const c of cases) for(const spaced of c.required_spaces) {
    const escaped=spaced.normalize(encoding).replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
    const allArticles=page.locator('.spacing-hypothesis').filter({has:page.locator('h3',{hasText:new RegExp('^'+escaped+'$')})});
    if(c.id==='lexical-return')assert.ok(await allArticles.count()>=2,'Preserve the prior nominal/vocative alternative beside the auxiliary option');
    const article=allArticles.filter({has:page.locator('.auxiliary-spacing-context')});assert.equal(await article.count(),1,c.id);
    const details=article.locator('.auxiliary-spacing-context');assert.ok(await details.count()>=1,c.id);
    if(!await details.first().evaluate(el=>el.open))await details.first().locator('summary').click();
    const region=article.getByRole('region',{name:'Auxiliary relationship for '+spaced.normalize(encoding),exact:true}).first();
    await region.waitFor({state:'visible'});
    const source=expected.find(r=>r.analysis?.normalized===c.surface);
    const hypothesis=source.spacing.alternatives.find(h=>h.rule==='spacing.predicate_auxiliary'&&h.spaced===spaced.normalize(encoding));assert.ok(hypothesis?.joined_contexts?.length);
    assert.ok(await region.locator('.breakdown-part').count()>0);
    diagrams.push({case_id:c.id,encoding,mode,spaced:spaced.normalize(encoding),contexts:hypothesis.joined_contexts});
   }
  }
 }
 // A nominal prefix has no whole-token auxiliary reading. Its joined witness
 // still needs complete rule/gloss metadata, independent of another sentence.
 await page.getByLabel('Dictionary matches only').uncheck();
 const single=await analyze('밥을먹어줄뿐더러');assert.ok(single.rules.auxiliary);
 const scene=await analyze('먹어줄뿐더러 학생인가싶어요 학생답게해줄뿐더러');
 assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 await page.locator('.spacing-suggestions').scrollIntoViewIfNeeded();await page.screenshot({path:prefix+'-desktop.png'});
 await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 await page.locator('.spacing-suggestions').scrollIntoViewIfNeeded();await page.screenshot({path:prefix+'-mobile.png'});
 for(const [id,expected] of Object.entries(owners)) {
  const response=await page.request.post(url+'/api/entry',{data:{id}});assert.equal(response.status(),200);const body=await response.json();assert.deepEqual(body.entry,expected);native.push({id,response:body});
 }
 assert.equal(exports.length,6);assert.equal(native.length,105);assert.equal(diagrams.length,156);assert.deepEqual(errors,[]);
 await writeFile(prefix+'-browser.json',JSON.stringify({state:'passed',producer_sha256:createHash('sha256').update(await readFile(new URL(import.meta.url))).digest('hex'),responses,exports,diagrams,native,single,scene,errors,scope:'Actual isolated SolidJS: every declared split and joined context across Unicode/filter modes, six exact CLI exports,105complete Native endpoints, nominal-prefix metadata and desktop/mobile geometry. Contextual intended spacing and main/Nix/performance remain open.'},null,2)+'\n');
 console.log('Passed156 joined-context diagrams,6 exact exports,105complete Native endpoints and nominal-prefix metadata.');
} finally {await browser.close();}
