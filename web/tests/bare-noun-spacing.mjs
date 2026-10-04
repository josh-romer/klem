import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {readFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';
const root=process.env.KLEM_ROOT || fileURLToPath(new URL('../../',import.meta.url)),url=process.env.KLEM_WEB_URL,cli=process.env.KLEM_BIN,db=root+'/data/dictionaries/krdict/krdict.db';
const source=JSON.parse(await readFile(root+'/tests/fixtures/bare-noun-spacing-sources.json','utf8')),extra=JSON.parse(await readFile(root+'/tests/fixtures/bare-noun-spacing-additional-pairs.json','utf8'));
assert.ok(url && cli, 'KLEM_WEB_URL and KLEM_BIN are required');
const words=[...new Set([...Object.keys(source.before_words),...Object.keys(extra.before_words)])].sort();
const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH,args:['--no-sandbox']});
let submissions=0;const errors=[];
try{
 const page=await browser.newPage({viewport:{width:1440,height:1100},acceptDownloads:true});page.on('pageerror',e=>errors.push(String(e)));await page.goto(url);
 for(const encoding of ['NFC','NFD'])for(const [mode,flag]of[['all',null],['headword','--dict-only'],['compatible','--dict-compatible']]){
  if(flag){await page.getByLabel('Dictionary matches only').check();if(mode==='compatible')await page.getByLabel('Exclude known grammar conflicts').check();else await page.getByLabel('Exclude known grammar conflicts').uncheck();}else await page.getByLabel('Dictionary matches only').uncheck();
  const input=words.join(' ').normalize(encoding);await page.getByLabel('Your sentence',{exact:true}).fill(input);await page.getByRole('button',{name:'Analyze sentence',exact:true}).click();await page.waitForFunction(first=>document.querySelector('.panel-heading h2')?.textContent===first,input.split(' ')[0]);await page.getByLabel('Suggest missing spaces').check();
  const sections=page.getByRole('region',{name:'Missing-space suggestions',exact:true});await sections.getByRole('heading',{name:'짜증 낼'.normalize(encoding),exact:true}).waitFor();assert.equal(await page.locator('.sentence').textContent(),input);
  for(const [surface,forms,head,id]of[['짜증 낼',['짜증','내','을'],'내다','89906'],['기분 내키는',['기분','내키','는'],'내키다','41145']]){
   const card=sections.locator('.spacing-hypothesis').filter({has:page.getByRole('heading',{name:surface.normalize(encoding),exact:true})});assert.deepEqual(await card.locator('.part-form').allTextContents(),forms);await card.locator('.breakdown-part.lexical').nth(1).click();await page.waitForFunction(head=>document.querySelector('.entry-heading h2')?.textContent?.replace(/[0-9]/g,'').trim()===head,head);assert.ok(await page.locator(`.entry-content a[href*='ParaWordNo=${id}']`).count());assert.ok((await page.locator('.entry-heading').textContent()).includes('동사'));assert.ok(!(await page.locator('.entry-heading').textContent()).includes('보조 동사'));
  }
  const download=page.waitForEvent('download');await page.getByRole('button',{name:'Export JSON',exact:true}).click();const exported=JSON.parse(await readFile(await(await download).path(),'utf8'));const expected=execFileSync(cli,['text','-','--dictionary',db,...(flag?[flag]:[]),'--suggest-spacing'],{input,encoding:'utf8',maxBuffer:128*1024*1024}).trim().split('\n').map(JSON.parse);assert.deepEqual(exported.records,expected);submissions++;console.log(encoding,mode,`${words.length}-word native cohort, cards, entry clicks and exports verified`);
 }
 const preview='짜증낼 용기내서 신경질내며 기분내키는';await page.getByLabel('Your sentence',{exact:true}).fill(preview);await page.getByRole('button',{name:'Analyze sentence',exact:true}).click();await page.waitForFunction(()=>document.querySelector('.panel-heading h2')?.textContent==='짜증낼');await page.getByRole('heading',{name:'짜증 낼',exact:true}).waitFor();
 await page.screenshot({path:'/tmp/klem-bare-noun-native-desktop.png',fullPage:true});await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);await page.screenshot({path:'/tmp/klem-bare-noun-native-mobile.png',fullPage:true});assert.deepEqual(errors,[]);console.log(JSON.stringify({submissions,words:words.length,errors,allExportsMatchCli:true,nativeEntryClicks:['89906','41145'],desktop:'/tmp/klem-bare-noun-native-desktop.png',mobile:'/tmp/klem-bare-noun-native-mobile.png'}));
}finally{await browser.close();}
