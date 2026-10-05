import assert from 'node:assert/strict';
import {isDeepStrictEqual} from 'node:util';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const root=fileURLToPath(new URL('../..',import.meta.url));
const {chromium}=createRequire(root+'/web/package.json')('playwright');
const url=process.env.KLEM_WEB_URL,cli=process.env.KLEM_BIN,db=root+'/data/dictionaries/krdict/krdict.db';
assert.ok(url&&cli);
const fixture=JSON.parse(await readFile(root+'/tests/fixtures/doeda-native-formations.json','utf8'));
const variants=['past-final','contracted-polite','nominal-topic','nominal-copula','present-adnominal','formal-polite'];
const selected=variants.map((name,i)=>{const f=fixture.formations[Math.floor(i*fixture.formations.length/6)],v=fixture.variants.find(v=>v.id===name);return {id:f.id+'-'+v.id,word:f.base+v.tail,base:f.base,lemmas:[{text:f.base,kind:'nominal'},...(v.later_lemmas||[])],morphemes:[{form:'되다',kind:'suffix'},...v.morphemes.map((form,j)=>({form,kind:v.morpheme_kinds[j]}))],forms:[f.base,'되',...(name==='nominal-copula'?['음','이','다']:v.morphemes)]};});
function matched(a,c){return isDeepStrictEqual(a.lemmas,c.lemmas)&&isDeepStrictEqual(a.morphemes,c.morphemes)&&a.rules.includes('suffix.verb.doeda');}
const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH,args:['--no-sandbox']});
const errors=[],checks=[],diagrams=[];
try{
 const page=await browser.newPage({viewport:{width:1440,height:1100},acceptDownloads:true});page.on('pageerror',e=>errors.push(String(e)));await page.goto(url);await page.getByLabel('Your sentence',{exact:true}).fill(selected.map(c=>c.word).join(' '));const initial=page.waitForResponse(r=>r.url().endsWith('/api/analyze'));await page.getByRole('button',{name:'Analyze sentence',exact:true}).click();await initial;const spaced=page.waitForResponse(r=>r.url().endsWith('/api/analyze'));await page.getByLabel('Suggest missing spaces').check();await spaced;
 for(const encoding of ['NFC','NFD']){
  const text=selected.map(c=>c.word).join(' ').normalize(encoding);
  await page.getByLabel('Your sentence',{exact:true}).fill(text);
  const wait=page.waitForResponse(r=>r.url().endsWith('/api/analyze')&&r.request().method()==='POST');await page.getByRole('button',{name:'Analyze sentence',exact:true}).click();assert.equal((await wait).status(),200);await page.waitForFunction(t=>document.querySelector('.sentence')?.textContent===t,text);
  for(const [mode,flag] of [['raw',null],['headword','--dict-only'],['compatible','--dict-compatible']]){
   if(flag){await page.getByLabel('Dictionary matches only').check();if(mode==='compatible')await page.getByLabel('Exclude known grammar conflicts').check();else await page.getByLabel('Exclude known grammar conflicts').uncheck();}else await page.getByLabel('Dictionary matches only').uncheck();
   const expected=execFileSync(cli,['text','-','--dictionary',db,'--suggest-spacing',...(flag?[flag]:[])],{input:text,encoding:'utf8'}).trim().split('\n').map(JSON.parse);
   const download=page.waitForEvent('download');await page.getByRole('button',{name:'Export JSON',exact:true}).click();const exported=JSON.parse(await readFile(await(await download).path(),'utf8'));assert.deepEqual(exported.records,expected);
   for(const c of selected){const r=exported.records.find(r=>r.analysis?.normalized===c.word);assert.ok(r?.analysis.analyses.some(a=>matched(a,c)),c.id);}
   checks.push({encoding,mode,cases:selected.map(c=>c.id),records:expected.length});
  }
  if(encoding==='NFC'){
   await page.getByLabel('Dictionary matches only').uncheck();const res=await page.request.post(url+'/api/analyze',{data:{text,suggest_spacing:true}});assert.equal(res.status(),200);const actual=await res.json();const sentence=page.getByRole('region',{name:'Sentence breakdown',exact:true});
   for(const c of selected){const r=actual.records.find(r=>r.surface===c.word);const index=r.analysis.analyses.findIndex(a=>matched(a,c));assert.ok(index>=0);const part=sentence.locator('.breakdown-word').filter({has:page.locator('.breakdown-surface > span',{hasText:new RegExp('^'+c.word+'$')})});await part.locator('select').selectOption(String(index));assert.deepEqual(await part.locator('.part-form').allTextContents(),c.forms);const suffix=part.locator('.breakdown-part[title^="-되다 ·"]');assert.equal(await suffix.count(),1);await suffix.click();await page.locator('.entry-content a[href*="ParaWordNo=74902"]').waitFor();diagrams.push({word:c.word,case_id:c.id,forms:c.forms,suffix_entry_id:'krdict:74902'});}
   await page.screenshot({path:'/tmp/klem-doeda-native-desktop.png',fullPage:true});await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:'/tmp/klem-doeda-native-mobile.png',fullPage:true});await page.setViewportSize({width:1440,height:1100});
  }
 }
 assert.deepEqual(errors,[]);
 const report={schema_version:1,checklist:'COV-022m',fixture_sha256:createHash('sha256').update(await readFile(root+'/tests/fixtures/doeda-native-formations.json')).digest('hex'),cli_sha256:createHash('sha256').update(await readFile(cli)).digest('hex'),dictionary_sha256:createHash('sha256').update(await readFile(db)).digest('hex'),checks,diagrams,browser_errors:errors};await writeFile('/tmp/klem-doeda-native-browser.json',JSON.stringify(report,null,2)+'\n');console.log('Verified six diagrams, six Unicode/filter exports, source clicks and mobile layout.');
}finally{await browser.close();}
