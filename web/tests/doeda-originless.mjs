import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {readFile,writeFile} from 'node:fs/promises';

const root=process.env.KLEM_ROOT||fileURLToPath(new URL('../..',import.meta.url));
const url=process.env.KLEM_WEB_URL,cli=process.env.KLEM_BIN;
const db=process.env.KLEM_DICTIONARY||root+'/data/dictionaries/krdict/krdict.db';
const prefix=process.env.KLEM_BROWSER_OUTPUT_PREFIX||'/tmp/klem-doeda-originless';
assert.ok(url&&cli,'Set KLEM_WEB_URL and KLEM_BIN to the running server and matching CLI.');
const supplemental=process.env.KLEM_BROWSER_SCOPE==='partial-origin';
const fixturePath=root+'/tests/fixtures/'+(supplemental?'doeda-partial-origin-sources.json':'doeda-originless-formations.json');
const fixture=JSON.parse(await readFile(fixturePath,'utf8'));
const selected=supplemental?[{word:'첨삭됐어요',base:'첨삭'},{word:'대칭돼요',base:'대칭'},{word:'첨삭되는',base:'첨삭'}]:[{word:'되풀이됐어요',base:'되풀이'},{word:'마무리돼요',base:'마무리'},{word:'풀이되는',base:'풀이'}];
const {chromium}=createRequire(root+'/web/package.json')('playwright');
const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH,args:['--no-sandbox']});
const checks=[],diagrams=[],responses=[],errors=[];
try {
 const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});
 page.on('pageerror',error=>errors.push(String(error)));await page.goto(url);
 for(const encoding of ['NFC','NFD']) {
  const text=selected.map(c=>c.word).join(' ').normalize(encoding);
  await page.getByLabel('Your sentence',{exact:true}).fill(text);
  const wait=page.waitForResponse(r=>r.url().endsWith('/api/analyze'));
  await page.getByRole('button',{name:'Analyze sentence',exact:true}).click();
  const response=await wait;assert.equal(response.status(),200);
  const api=await response.json();responses.push({encoding,request:{text},response:api});
  await page.waitForFunction(t=>document.querySelector('.sentence')?.textContent===t,text);
  for(const [mode,flag] of [['raw',null],['headword','--dict-only'],['compatible','--dict-compatible']]) {
   if(flag){await page.getByLabel('Dictionary matches only').check();if(mode==='compatible')await page.getByLabel('Exclude known grammar conflicts').check();else await page.getByLabel('Exclude known grammar conflicts').uncheck();}
   else await page.getByLabel('Dictionary matches only').uncheck();
   const expected=execFileSync(cli,['text','-','--dictionary',db,...(flag?[flag]:[])],{input:text,encoding:'utf8'}).trim().split('\n').map(JSON.parse);
   const download=page.waitForEvent('download');await page.getByRole('button',{name:'Export JSON',exact:true}).click();
   const exported=JSON.parse(await readFile(await(await download).path(),'utf8'));
   assert.deepEqual(exported.records,expected);checks.push({encoding,mode,records:expected.length,exported_records:exported.records,cli_records:expected});
  }
  await page.getByLabel('Dictionary matches only').uncheck();
  const sentence=page.getByRole('region',{name:'Sentence breakdown',exact:true});
  for(const c of selected) {
   const formation=fixture.formations.find(f=>f.base===c.base);assert.ok(formation);
   const record=api.records.find(r=>r.analysis?.normalized===c.word);
   const index=record.analysis.analyses.findIndex(a=>a.lemmas[0]?.text===c.base&&a.rules.includes('suffix.verb.doeda'));
   const wholeIndex=record.analysis.analyses.findIndex(a=>a.lemmas[0]?.text===formation.head&&a.lemmas[0]?.kind==='predicate');
   assert.ok(index>=0&&wholeIndex>=0,'Keep the original whole-head alternative');
   const nounId=formation.noun_entries[0];
   const assessed=record.dictionary.readings[index].lemmas[0].entries.find(e=>e.id===nounId);
   assert.deepEqual(assessed.derivational_identity,{relation:'unknown',morpheme_index:0,expected_origins:formation.expected_origins||[],whole_entries:formation.whole_entries,whole_origins_complete:formation.whole_origins_complete||false});
   const part=sentence.locator('.breakdown-word').filter({has:page.locator('.breakdown-surface > span',{hasText:new RegExp('^'+c.word.normalize(encoding)+'$')})});
   await part.locator('select').selectOption(String(wholeIndex));
   const wholeForm=await part.locator('.breakdown-part').first().locator('.part-form').textContent();
   await part.locator('select').selectOption(String(index));
   const stem=part.locator('.breakdown-part').first();
   const form=await stem.locator('.part-form').textContent(),label=await stem.locator('.part-gloss').textContent();
   assert.equal(form,c.base);assert.equal(label,api.glosses[nounId]||'No English gloss');
   const title=await stem.getAttribute('title');assert.match(title,/Dictionary hint only/);
   await stem.click();await page.locator('.entry-content a[href*="ParaWordNo='+nounId.split(':')[1]+'"]').waitFor();
   const parts=await part.locator('.breakdown-part .part-form').allTextContents();assert.ok(parts.includes('되'));
   diagrams.push({encoding,word:c.word,base:c.base,label,entry:nounId,title,parts,selected:index,whole_selected:wholeIndex,whole_form:wholeForm,identity:assessed.derivational_identity});
  }
  if(encoding==='NFC') {
   await page.screenshot({path:prefix+'-desktop.png',fullPage:true});
   await page.setViewportSize({width:390,height:844});
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   await page.screenshot({path:prefix+'-mobile.png',fullPage:true});
   await page.setViewportSize({width:1440,height:1000});
  }
 }
 assert.deepEqual(errors,[]);
 const hash=async path=>createHash('sha256').update(await readFile(path)).digest('hex');
 await writeFile(prefix+'-browser.json',JSON.stringify({schema_version:1,checklist:'COV-022m',cli_sha256:await hash(cli),dictionary_sha256:await hash(db),fixture_sha256:await hash(fixturePath),responses,checks,diagrams,browser_errors:errors},null,2)+'\n');
 console.log('Verified six source-owned diagrams, unknown identity, whole alternatives, source clicks, exports, Unicode and mobile layout.');
} finally {await browser.close();}
