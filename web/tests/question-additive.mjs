// Finite question/additive cohort; CLI/API evidence supplies actual raw indices.
import assert from "node:assert/strict";
import { isDeepStrictEqual } from "node:util";
import { execFileSync } from "node:child_process";
import { readFile, mkdtemp } from "node:fs/promises";
import { gunzipSync } from "node:zlib";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const root = process.env.KLEM_ROOT || fileURLToPath(new URL("../../", import.meta.url));
const fixture = JSON.parse(await readFile(resolve(root, "tests/fixtures/question-additive-sources.json"), "utf8"));
const evidence = JSON.parse(gunzipSync(await readFile(process.env.KLEM_ADDITIVE_EVIDENCE)));
const url = process.env.KLEM_WEB_URL;
const cli = process.env.KLEM_BIN;
assert.ok(url && cli);
const scratch = await mkdtemp(resolve(tmpdir(), "klem-question-additive-browser-"));
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH, args: ["--no-sandbox"] });
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 }, acceptDownloads: true });
  const errors = [];
  page.on("pageerror", error => errors.push(String(error)));
  await page.goto(url);
  const words = Object.keys(fixture.before_words);
  const text = words.join(" ");
  let submissions = 0;
  for (const nfd of [false, true]) {
    const input = nfd ? text.normalize("NFD") : text;
    for (const [mode, flag] of [["all", null], ["headword", "--dict-only"], ["compatible", "--dict-compatible"]]) {
      if (flag) {
        await page.getByLabel("Dictionary matches only").check();
        if (mode === "compatible") await page.getByLabel("Exclude known grammar conflicts").check();
        else await page.getByLabel("Exclude known grammar conflicts").uncheck();
      } else await page.getByLabel("Dictionary matches only").uncheck();
      await page.getByLabel("Your sentence", { exact: true }).fill(input);
      await page.getByRole("button", { name: "Analyze sentence", exact: true }).click();
      await page.waitForFunction(surface => document.querySelector(".panel-heading h2")?.textContent === surface, input.split(" ")[0]);
      assert.equal(await page.locator(".sentence").textContent(), input);
      assert.equal(await page.locator(".breakdown-word").count(), words.length);
      for (const [index, surface] of words.entries()) {
        const result = evidence.words[surface];
        const expected = result.all.analyses.flatMap((a, i) => result[mode].analyses.some(b => isDeepStrictEqual(a, b)) ? [String(i)] : []);
        const actual = await page.locator(".breakdown-word").nth(index).locator("option").evaluateAll(options => options.map(o => o.value).filter(Boolean));
        assert.deepEqual(actual, expected, `${mode} ${surface}: raw indices`);
        const c = fixture.cases.find(c => c.surface === surface && c.judgments[0].verdict === "required");
        if (c) {
          const j = c.judgments[0];
          const rawIndex = result.all.analyses.findIndex(a => isDeepStrictEqual(a.lemmas.map(l => l.text), j.lemmas) && isDeepStrictEqual(a.lemmas.map(l => l.kind), j.lemma_kinds) && isDeepStrictEqual(a.morphemes.map(m => m.form), j.morphemes) && isDeepStrictEqual(a.morphemes.map(m => m.kind), j.morpheme_kinds));
          assert.ok(rawIndex >= 0 && expected.includes(String(rawIndex)));
          const word = page.locator(".breakdown-word").nth(index);
          await word.locator("select").selectOption(String(rawIndex));
          const forms = await word.locator(".part-form").allTextContents();
          const components = result.api.breakdowns[0][rawIndex];
          assert.equal(forms.length, components.length);
          const displayedMorphemes = components.flatMap((component, position) =>
            Object.hasOwn(component, "morpheme") ? [forms[position]] : []);
          assert.deepEqual(displayedMorphemes, j.morphemes, `${surface}: ordered ending/additive components around their owning predicates`);
        }
      }
      const download = page.waitForEvent("download");
      await page.getByRole("button", { name: "Export JSON", exact: true }).click();
      const exported = JSON.parse(await readFile(await (await download).path(), "utf8"));
      const expectedRecords = execFileSync(cli, ["text", "--dictionary", resolve(root, "data/dictionaries/krdict/krdict.db"), ...(flag ? [flag] : [])], { input, encoding: "utf8", maxBuffer: 64 * 1024 * 1024 }).trim().split("\n").map(JSON.parse);
      assert.deepEqual(exported.records, expectedRecords);
      submissions++;
    }
  }
  await page.getByLabel("Dictionary matches only").uncheck();
  await page.getByLabel("Your sentence", { exact: true }).fill("내느냐도 먹느냐도");
  await page.getByRole("button", { name: "Analyze sentence", exact: true }).click();
  await page.waitForFunction(() => document.querySelector(".panel-heading h2")?.textContent === "내느냐도");
  const result = evidence.words["내느냐도"].all;
  const additive = result.analyses.findIndex(a => a.lemmas.length === 1 && a.lemmas[0].text === "내다" && a.morphemes.map(m => m.form).join("+") === "느냐+도");
  const nominal = result.analyses.findIndex(a => a.lemmas.length === 1 && a.lemmas[0].text === "내느냐" && a.lemmas[0].kind === "nominal" && a.morphemes.length === 1 && a.morphemes[0].form === "도");
  assert.ok(additive >= 0 && nominal >= 0);
  await page.locator(".breakdown-word").first().locator("select").selectOption(String(nominal));
  assert.equal(await page.locator(".breakdown-word").first().locator(".part-form").last().textContent(), "도");
  await page.locator(".breakdown-word").first().locator("select").selectOption(String(additive));
  await page.locator(".breakdown-word").first().locator(".breakdown-part").last().click();
  const particle = fixture.complete_native_entries["krdict:86258"];
  const heading = particle.headword + (particle.homonym === "0" ? "" : particle.homonym);
  await page.waitForFunction(expected => document.querySelector(".entry-heading h2")?.textContent === expected, heading);
  assert.ok(await page.locator(".entry-content a[href*='ParaWordNo=86258']").count());
  const desktop = resolve(scratch, "desktop.png");
  await page.screenshot({ path: desktop, fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  const mobile = resolve(scratch, "mobile.png");
  await page.screenshot({ path: mobile, fullPage: true });
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ submissions, words: words.length, additiveAndNominalSelectable: true, allRawIndicesAndExportsMatchCli: true, desktop, mobile }));
} finally {
  await browser.close();
}
