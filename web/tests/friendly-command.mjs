import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {readFile,writeFile} from 'node:fs/promises';
const root=process.env.KLEM_ROOT || fileURLToPath(new URL('../..',import.meta.url));
const url=process.env.KLEM_WEB_URL, cli=process.env.KLEM_BIN;
assert.ok(url && cli,'Set matching KLEM_WEB_URL and KLEM_BIN.');
const db=process.env.KLEM_DICTIONARY || root+'/data/dictionaries/krdict/krdict.db';
const prefix=process.env.KLEM_BROWSER_OUTPUT_PREFIX || '/tmp/klem-friendly-command';
const fixturePath=root+'/tests/fixtures/friendly-command-sources.json';
const fixture=JSON.parse(await readFile(fixturePath,'utf8'));
const {chromium}=createRequire(root+'/web/package.json')('playwright');
const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH,args:['--no-sandbox']});
const responses=[],checks=[],diagrams=[],native=[],errors=[];
try {
 const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});
 page.on('pageerror',e=>errors.push(String(e))); await page.goto(url);
 for(const encoding of ['NFC','NFD']) {
  const words=['온','날아온','내려온','돌아온','못난이','흰둥이'];
  const text=words.join(' ').normalize(encoding);
  await page.getByLabel('Your sentence',{exact:true}).fill(text);
  const wait=page.waitForResponse(r=>r.url().endsWith('/api/analyze'));
  await page.getByRole('button',{name:'Analyze sentence',exact:true}).click();
  const response=await wait;assert.equal(response.status(),200);const api=await response.json();
  responses.push({encoding,request:{text},response:api});
  await page.waitForFunction(t=>document.querySelector('.sentence')?.textContent===t,text);
  for(const [mode,flag] of [['raw',null],['headword','--dict-only'],['compatible','--dict-compatible']]) {
   if(flag) {
    await page.getByLabel('Dictionary matches only').check();
    if(mode==='compatible')await page.getByLabel('Exclude known grammar conflicts').check();
    else await page.getByLabel('Exclude known grammar conflicts').uncheck();
   } else await page.getByLabel('Dictionary matches only').uncheck();
   const records=execFileSync(cli,['text','-','--dictionary',db,...(flag?[flag]:[])],{input:text,encoding:'utf8'}).trim().split('\n').map(JSON.parse);
   const download=page.waitForEvent('download');await page.getByRole('button',{name:'Export JSON',exact:true}).click();
   const exported=JSON.parse(await readFile(await(await download).path(),'utf8'));
   assert.deepEqual(exported.records,records); checks.push({encoding,mode,cli_records:records,exported_records:exported.records});
  }
  await page.getByLabel('Dictionary matches only').uncheck();
  const sentence=page.getByRole('region',{name:'Sentence breakdown',exact:true});
  for(const word of words) {
   const record=api.records.find(r=>r.analysis?.normalized===word);
   const friendly=!['못난이','흰둥이'].includes(word);
   const index=record.analysis.analyses.findIndex(a=>friendly
    ? a.rules.includes('ending.friendly_command.n') && a.lemmas.length===1
    : a.rules.includes('derivation.nominal.adnominal'));
   assert.ok(index>=0,word);
   const card=sentence.locator('.breakdown-word').filter({has:page.locator('.breakdown-surface > span',{hasText:new RegExp('^'+word.normalize(encoding)+'$')})});
   const selector=card.locator('select');
   const whole=record.analysis.analyses.findIndex(a=>a.unchanged);assert.ok(whole>=0);
   await selector.selectOption(String(whole));
   if(friendly) {
    const old=record.analysis.analyses.findIndex(a=>a.lemmas.length===1 && a.lemmas[0].text===record.analysis.analyses[index].lemmas[0].text && a.morphemes.length===1 && a.morphemes[0].form==='은');
    assert.ok(old>=0);await selector.selectOption(String(old));
    assert.equal(await card.locator('.part-gloss').last().textContent(),'Noun modifier');
   }
   await selector.selectOption(String(index));
   assert.equal((await selector.locator('option:checked').textContent()).includes('friendly command'),friendly);
   const a=record.analysis.analyses[index];
   const mi=a.morphemes.findIndex(m=>m.kind==='ending' && m.form==='ㄴ');
   const order=api.breakdowns[api.records.indexOf(record)][index];
   const position=order.findIndex(c=>c.morpheme===mi);assert.ok(position>=0);
   const part=card.locator('.breakdown-part').nth(position);
   assert.equal(await part.locator('.part-form').textContent(),'ㄴ');
   const label=friendly?'Friendly command (come)':'Noun modifier';
   assert.equal(await part.locator('.part-gloss').textContent(),label);
   const source=friendly?73877:78634;
   const hint=await part.getAttribute('title');assert.ok(hint.includes(String(source)));
   assert.ok(!hint.includes(String(friendly?78634:73877)));
   await part.click();await page.locator(`.entry-content a[href*="ParaWordNo=${source}"]`).waitFor();
   diagrams.push({encoding,word,selected:index,whole_selected:whole,analysis:a,order,parts:await card.locator('.part-form').allTextContents(),label,title:hint,source});
  }
  if(encoding==='NFC') {
   await sentence.scrollIntoViewIfNeeded();await page.screenshot({path:prefix+'-desktop.png'});
   await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   await sentence.scrollIntoViewIfNeeded();await page.screenshot({path:prefix+'-mobile.png'});
   await page.setViewportSize({width:1440,height:1000});
  }
 }
 for(const [id,expected] of Object.entries(fixture.complete_native_entries)) {
  const response=await page.request.post(url+'/api/entry',{data:{id}});assert.equal(response.status(),200);
  const actual=await response.json();assert.deepEqual(actual.entry,expected);native.push({id,response:actual});
 }
 assert.deepEqual(errors,[]);
 const hash=async p=>createHash('sha256').update(await readFile(p)).digest('hex');
 await writeFile(prefix+'-browser.json',JSON.stringify({schema_version:1,checklist:'COV-017bx',cli_sha256:await hash(cli),dictionary_sha256:await hash(db),fixture_sha256:await hash(fixturePath),producer_sha256:await hash(fileURLToPath(import.meta.url)),responses,checks,diagrams,native,browser_errors:errors},null,2)+'\n');
 console.log('Verified twelve command/adnominal source diagrams, retained alternatives, six CLI/export comparisons, sixty complete native endpoints, Unicode and mobile layout.');
} finally {await browser.close();}
