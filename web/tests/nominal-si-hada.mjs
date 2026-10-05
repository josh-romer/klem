import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {readFile,writeFile} from 'node:fs/promises';

const root=process.env.KLEM_ROOT||fileURLToPath(new URL('../..',import.meta.url));
const url=process.env.KLEM_WEB_URL,cli=process.env.KLEM_BIN;
const db=process.env.KLEM_DICTIONARY||root+'/data/dictionaries/krdict/krdict.db';
const prefix=process.env.KLEM_BROWSER_OUTPUT_PREFIX||'/tmp/klem-nominal-si-hada';
assert.ok(url&&cli,'Set KLEM_WEB_URL and KLEM_BIN to the running server and matching CLI.');
const fixturePath=root+'/tests/fixtures/nominal-si-hada-sources.json';
const selected=[
 {word:'중요시하시다',base:'중요',id:'krdict:91872',nested:true},
 {word:'문제시하지도',base:'문제시',noEntry:true},
 {word:'등한시했어요',base:'등한시',id:'krdict:52824'},
 {word:'야만시한',base:'야만',id:'krdict:17409',nested:true},
 {word:'의문시한다',base:'의문',id:'krdict:24075',nested:true},
];
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
   const record=api.records.find(r=>r.analysis?.normalized===c.word);
   const index=record.analysis.analyses.findIndex(a=>a.rules.includes('suffix.verb.hada')&&a.lemmas[0]?.text===c.base);
   const head=c.nested?c.base+'시':c.base;
   const wholeIndex=record.analysis.analyses.findIndex(a=>a.lemmas[0]?.text===head+'하다'&&a.lemmas[0]?.kind==='predicate');
   assert.ok(index>=0&&wholeIndex>=0,'Keep the original whole-head alternative');
   const owner=record.dictionary.readings[index].lemmas[0];
   if(c.noEntry) {assert.equal(owner.status,'unknown');assert.deepEqual(owner.entries,[]);}
   else {
    assert.equal(owner.status,'compatible');
    const identity=owner.entries.find(e=>e.id===c.id).derivational_identity;
    assert.equal(identity.morpheme_index,c.nested?1:0);assert.equal(identity.relation,'recorded_match');
   }
   const nounId=c.id;
   const part=sentence.locator('.breakdown-word').filter({has:page.locator('.breakdown-surface > span',{hasText:new RegExp('^'+c.word.normalize(encoding)+'$')})});
   await part.locator('select').selectOption(String(wholeIndex));
   const wholeForm=await part.locator('.breakdown-part').first().locator('.part-form').textContent();
   await part.locator('select').selectOption(String(index));
   const stem=part.locator('.breakdown-part').first();
   const form=await stem.locator('.part-form').textContent(),label=await stem.locator('.part-gloss').textContent();
   assert.equal(form,c.base);
   const title=await stem.getAttribute('title');
   if(c.noEntry) {assert.equal(label,'No dictionary gloss');assert.match(title,/No dictionary entry/);assert.doesNotMatch(title,/click for all senses/);assert.notEqual(label,api.glosses['krdict:56920']);assert.notEqual(label,api.glosses['krdict:66246']);}
   else {
    assert.equal(label,api.glosses[nounId]||'No English gloss');assert.match(title,/Dictionary hint only/);
    await stem.click();await page.locator('.entry-content a[href*="ParaWordNo='+nounId.split(':')[1]+'"]').waitFor();
   }
   const parts=await part.locator('.breakdown-part .part-form').allTextContents();assert.deepEqual(parts.slice(0,c.nested?3:2),c.nested?[c.base,'시','하']:[c.base,'하']);
   if(c.word==='등한시했어요')assert.equal(parts[2],'였');
   const suffix=part.locator('.breakdown-part').nth(c.nested?2:1);
   assert.equal(await suffix.locator('.part-gloss').textContent(),'Action / verb formation');
   assert.match(await suffix.getAttribute('title'),/Other -하다 senses/);
   assert.ok(api.grammar['-하다'].some(e=>e.id==='krdict:88475'));
   await suffix.click();await page.locator('.entry-content a[href*="ParaWordNo=88475"]').waitFor();
   if(c.word==='중요시하시다'){
    const honorific=part.locator('.breakdown-part').nth(3);
    assert.equal(await honorific.locator('.part-form').textContent(),'시');
    assert.notEqual(await honorific.locator('.part-gloss').textContent(),'Action / verb formation');
    assert.ok(api.grammar['-시-'].every(e=>e.id!=='krdict:88475'));
   }
   diagrams.push({encoding,word:c.word,base:c.base,nested:!!c.nested,label,entry:nounId||null,no_entry:!!c.noEntry,title,parts,selected:index,whole_selected:wholeIndex,whole_form:wholeForm,owner});
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
 await writeFile(prefix+'-browser.json',JSON.stringify({schema_version:1,checklist:'COV-022r',cli_sha256:await hash(cli),dictionary_sha256:await hash(db),fixture_sha256:await hash(fixturePath),responses,checks,diagrams,browser_errors:errors},null,2)+'\n');
 console.log('Verified ten direct/nested -시하다 diagrams, source-owned origins, missing-entry raw paths and unresolved deep-base boundaries, contracted 하 + 였, whole alternatives, source clicks, exports, Unicode and mobile layout.');
} finally {await browser.close();}
