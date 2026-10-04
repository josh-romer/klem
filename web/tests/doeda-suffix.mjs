import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { readFile, writeFile } from "node:fs/promises";
import { chromium } from "playwright";

const root = process.env.KLEM_ROOT || process.cwd();
const url = process.env.KLEM_WEB_URL;
const cli = process.env.KLEM_BIN;
const db = `${root}/data/dictionaries/krdict/krdict.db`;
assert.ok(url && cli, "KLEM_WEB_URL and KLEM_BIN are required");
const bytes = await readFile(`${root}/tests/fixtures/doeda-suffix-sources.json`);
const fixture = JSON.parse(bytes);
const corrections = JSON.parse(await readFile(`${root}/tests/fixtures/doeda-suffix-corrections.json`, "utf8"));
assert.equal(createHash("sha256").update(bytes).digest("hex"), corrections.source_fixture_sha256);
for (const c of corrections.corrections) {
  const index = fixture.cases.findIndex(x => JSON.stringify(x) === JSON.stringify(c.original));
  assert.ok(index >= 0);
  fixture.cases[index] = c.replacement_control;
  fixture.cases.push(c.replacement_positive);
}
assert.equal(fixture.cases.length, 1600);
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
function matched(a, c) {
  return same(a.lemmas.map(l => l.text), c.lemmas) &&
    same(a.lemmas.map(l => l.kind), c.lemma_kinds) &&
    same(a.morphemes.map(m => m.form), c.morphemes) &&
    same(a.morphemes.map(m => m.kind), c.morpheme_kinds) &&
    c.required_rules.every(r => a.rules.includes(r));
}
function batches(encoding) {
  const chunks = [];
  let chunk = [];
  for (const word of [...new Set(fixture.cases.map(c => c.surface))].sort()) {
    if (Buffer.byteLength([...chunk, word].join(" ").normalize(encoding)) > 7500 && chunk.length) {
      chunks.push(chunk.join(" ").normalize(encoding));
      chunk = [];
    }
    chunk.push(word);
  }
  if (chunk.length) chunks.push(chunk.join(" ").normalize(encoding));
  return chunks;
}
const missing = new Set(["앳", "외람", "편벽", "허황", "헛", "이룩"]);
const browser = await chromium.launch({executablePath: process.env.CHROMIUM_PATH, args: ["--no-sandbox"]});
const errors = [], checks = [], diagrams = [];
try {
  const page = await browser.newPage({viewport: {width: 1440, height: 1100}, acceptDownloads: true});
  page.on("pageerror", e => errors.push(String(e)));
  await page.goto(url);
  async function analyze(text) {
    await page.getByLabel("Your sentence", {exact: true}).fill(text);
    const response = page.waitForResponse(r => r.url().endsWith("/api/analyze") && r.request().method() === "POST");
    await page.getByRole("button", {name: "Analyze sentence", exact: true}).click();
    assert.equal((await response).status(), 200);
    await page.waitForFunction(t => document.querySelector(".sentence")?.textContent === t, text);
    await page.getByLabel("Suggest missing spaces").check();
  }
  for (const encoding of ["NFC", "NFD"]) {
    for (const [batch, text] of batches(encoding).entries()) {
      await analyze(text);
      for (const [mode, flag] of [["all", null], ["headword", "--dict-only"], ["compatible", "--dict-compatible"]]) {
        if (flag) {
          await page.getByLabel("Dictionary matches only").check();
          if (mode === "compatible") await page.getByLabel("Exclude known grammar conflicts").check();
          else await page.getByLabel("Exclude known grammar conflicts").uncheck();
        } else await page.getByLabel("Dictionary matches only").uncheck();
        const expected = execFileSync(cli, ["text", "-", "--dictionary", db, "--suggest-spacing", ...(flag ? [flag] : [])], {input: text, encoding: "utf8", maxBuffer: 128 * 1024 * 1024}).trim().split("\n").map(JSON.parse);
        const download = page.waitForEvent("download");
        await page.getByRole("button", {name: "Export JSON", exact: true}).click();
        const result = JSON.parse(await readFile(await (await download).path(), "utf8"));
        assert.deepEqual(result.records, expected);
        const found = new Map(result.records.filter(r => r.kind === "word").map(r => [r.analysis.normalized, r]));
        const cases = fixture.cases.filter(c => found.has(c.surface));
        for (const c of cases) {
          const exists = found.get(c.surface).analysis.analyses.some(a => matched(a, c));
          const required = c.verdict === "required" && (mode === "all" || !missing.has(c.lemmas[0])) && (mode !== "compatible" || c.lemmas[0] !== "속");
          assert.equal(exists, required, `${encoding}/${mode}/${c.id}`);
        }
        checks.push({encoding, batch, mode, cases: cases.map(c => c.id), records: expected.length});
        console.log(`${encoding}/${mode}/${batch}: ${cases.length} cases and exact CLI export parity`);
      }
    }
  }
  await page.getByLabel("Dictionary matches only").uncheck();
  const words = ["타도되었다", "고돼요", "못돼요", "속된", "가결됨이다", "한갓된"];
  const forms = {
    "타도되었다": ["타도", "되", "었", "다"],
    "고돼요": ["고", "되", "어요"],
    "못돼요": ["못", "되", "어요"],
    "속된": ["속", "되", "은"],
    "가결됨이다": ["가결", "되", "음", "이", "다"],
    "한갓된": ["한갓", "되", "은"],
  };
  await analyze(words.join(" "));
  const response = await page.request.post(url + "/api/analyze", {data: {text: words.join(" "), suggest_spacing: true}});
  assert.equal(response.status(), 200);
  const actual = await response.json();
  const sentence = page.getByRole("region", {name: "Sentence breakdown", exact: true});
  for (const word of words) {
    const c = fixture.cases.find(c => c.surface === word && c.verdict === "required");
    const record = actual.records.find(r => r.surface === word);
    const index = record.analysis.analyses.findIndex(a => matched(a, c));
    assert.ok(index >= 0, word);
    const part = sentence.locator(".breakdown-word").filter({has: page.locator(".breakdown-surface > span", {hasText: new RegExp(`^${word}$`)})});
    await part.locator("select").selectOption(String(index));
    assert.deepEqual(await part.locator(".part-form").allTextContents(), forms[word]);
    const suffix = part.locator('.breakdown-part[title^="-되다 ·"]');
    assert.equal(await suffix.count(), 1, word);
    await suffix.click();
    await page.locator('.entry-content a[href*="ParaWordNo=74902"]').waitFor();
    if (word === "속된") {
      assert.match(await part.locator(".breakdown-part").first().textContent(), /Root/);
      assert.doesNotMatch(await part.locator(".breakdown-part").first().textContent(), /inside|interior/i);
    }
    diagrams.push({word, case_id: c.id, forms: forms[word], suffix_entry_id: "krdict:74902", passed: true});
  }
  if (process.env.KLEM_SCREENSHOT_PREFIX) {
    await page.screenshot({path: `${process.env.KLEM_SCREENSHOT_PREFIX}-desktop.png`, fullPage: true});
    await page.setViewportSize({width: 390, height: 844});
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({path: `${process.env.KLEM_SCREENSHOT_PREFIX}-mobile.png`, fullPage: true});
  }
  assert.deepEqual(errors, []);
  const report = {schema_version: 1, checklist: "COV-022m", fixture_sha256: corrections.source_fixture_sha256, cli_sha256: createHash("sha256").update(await readFile(cli)).digest("hex"), dictionary_sha256: createHash("sha256").update(await readFile(db)).digest("hex"), case_count: fixture.cases.length, checks, diagrams, browser_errors: errors, contextual_verdict: "unjudged", independent_review: "pending"};
  if (process.env.KLEM_BROWSER_REPORT) await writeFile(process.env.KLEM_BROWSER_REPORT, JSON.stringify(report, null, 2) + "\n");
  console.log("Verified all suffix cases/controls, NFC/NFD/filter exports, six diagrams and source clicks.");
} finally {
  await browser.close();
}
