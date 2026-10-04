// Entry-class conflicts must preserve selectable raw paths and exported indices.
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
const fixture = JSON.parse(await readFile(resolve(root, "tests/fixtures/continuation-left-sources.json"), "utf8"));
const overlay = JSON.parse(await readFile(resolve(root, "tests/fixtures/continuation-left-written-vowel-judgments.json"), "utf8"));
const vowelCompat = JSON.parse(await readFile(resolve(root, "tests/fixtures/continuation-left-vowel-compat-judgments.json"), "utf8"));
const cases = [...fixture.cases, ...overlay.cases.map(c => ({
  id: c.id, surface: c.surface, judgments: [{
    lemmas: c.lemmas.map(l => l.text), lemma_kinds: c.lemmas.map(l => l.kind),
    morphemes: c.morphemes.map(m => m.form), morpheme_kinds: c.morphemes.map(m => m.kind), verdict: "forbidden",
  }],
})), ...vowelCompat.cases.map(u => ({
  id: u.original_case.id, surface: u.original_case.surface, judgments: [{
    lemmas: u.original_case.lemmas.map(l => l.text), lemma_kinds: u.original_case.lemmas.map(l => l.kind),
    morphemes: u.original_case.morphemes.map(m => m.form), morpheme_kinds: u.original_case.morphemes.map(m => m.kind),
    verdict: u.compatible_retained ? "required" : "forbidden",
  }],
}))];
const evidence = JSON.parse(gunzipSync(await readFile(process.env.KLEM_CONTINUATION_EVIDENCE)));
const url = process.env.KLEM_WEB_URL;
const cli = process.env.KLEM_BIN;
assert.ok(url && cli);
const scratch = await mkdtemp(resolve(tmpdir(), "klem-continuation-left-browser-"));
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH, args: ["--no-sandbox"] });
const match = (a, j) => isDeepStrictEqual(a.lemmas.map(l => l.text), j.lemmas)
  && isDeepStrictEqual(a.lemmas.map(l => l.kind), j.lemma_kinds)
  && isDeepStrictEqual(a.morphemes.map(m => m.form), j.morphemes)
  && isDeepStrictEqual(a.morphemes.map(m => m.kind), j.morpheme_kinds);
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 }, acceptDownloads: true });
  const errors = [];
  page.on("pageerror", error => errors.push(String(error)));
  await page.goto(url);
  const words = [...new Set([...Object.keys(fixture.before_words), ...overlay.cases.map(c => c.surface), ...vowelCompat.cases.map(u => u.original_case.surface)])];
  let submissions = 0;
  let reviewedSelections = 0;
  for (const nfd of [false, true]) {
    const input = nfd ? words.join(" ").normalize("NFD") : words.join(" ");
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
        const word = page.locator(".breakdown-word").nth(index);
        const actual = await word.locator("option").evaluateAll(options => options.map(o => o.value).filter(Boolean));
        assert.deepEqual(actual, expected, `${mode} ${surface}: raw indices`);
        const c = cases.find(c => c.surface === surface);
        if (c) {
          const j = c.judgments[0];
          const rawIndex = result.all.analyses.findIndex(a => match(a, j));
          assert.ok(rawIndex >= 0);
          assert.equal(expected.includes(String(rawIndex)), mode !== "compatible" || j.verdict === "required", c.id);
          if (expected.includes(String(rawIndex))) {
            await word.locator("select").selectOption(String(rawIndex));
            const forms = await word.locator(".part-form").allTextContents();
            const components = result.api.breakdowns[0][rawIndex];
            assert.equal(forms.length, components.length);
            const display = j.morphemes.map(form => form === "답다" ? "답" : form);
            // This named 하다 adjective uses the established 하 + 여 display;
            // canonical 어 and source indices remain unchanged in the export.
            if (c.id === "continuation-left-independent-pos-adjective") display[0] = "여";
            assert.deepEqual(components.flatMap((component, position) => Object.hasOwn(component, "morpheme") ? [forms[position]] : []), display, c.id);
            reviewedSelections++;
          }
        }
      }
      const download = page.waitForEvent("download");
      await page.getByRole("button", { name: "Export JSON", exact: true }).click();
      const exported = JSON.parse(await readFile(await (await download).path(), "utf8"));
      const expectedRecords = execFileSync(cli, ["text", "--dictionary", resolve(root, "data/dictionaries/krdict/krdict.db"), ...(flag ? [flag] : [])], { input, encoding: "utf8", maxBuffer: 128 * 1024 * 1024 }).trim().split("\n").map(JSON.parse);
      assert.deepEqual(exported.records, expectedRecords);
      submissions++;
    }
  }
  await page.getByLabel("Dictionary matches only").uncheck();
  await page.getByLabel("Your sentence", { exact: true }).fill("좋아내다 커내다 먹어내다 좋아내느냐도");
  await page.getByRole("button", { name: "Analyze sentence", exact: true }).click();
  await page.waitForFunction(() => document.querySelector(".panel-heading h2")?.textContent === "좋아내다");
  const j = fixture.cases.find(c => c.id === "continuation-left-내다-어-adjective").judgments[0];
  const result = evidence.words["좋아내다"];
  const rawIndex = result.all.analyses.findIndex(a => match(a, j));
  await page.locator(".breakdown-word").first().locator("select").selectOption(String(rawIndex));
  assert.ok(await page.getByText("Known dictionary class conflict.", { exact: false }).count());
  const component = result.api.breakdowns[0][rawIndex].findIndex(c => c.lemma === 1);
  assert.ok(component >= 0);
  await page.locator(".breakdown-word").first().locator(".breakdown-part").nth(component).click();
  await page.waitForFunction(() => document.querySelector(".entry-heading h2")?.textContent === "내다2");
  assert.ok(await page.locator(".entry-content a[href*='ParaWordNo=60625']").count());
  const desktop = resolve(scratch, "desktop.png");
  await page.screenshot({ path: desktop, fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  const mobile = resolve(scratch, "mobile.png");
  await page.screenshot({ path: mobile, fullPage: true });
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ submissions, words: words.length, reviewedSelections, allRawIndicesAndExportsMatchCli: true, conflictAndNativeEntryVisible: true, desktop, mobile }));
} finally {
  await browser.close();
}
