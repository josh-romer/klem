// Full excluded-field cohort against a running immutable package and native DB.
// KLEM_WEB_URL=http://127.0.0.1:8081 KLEM_BIN=... CHROMIUM_PATH=... node web/tests/excluded-paradigms.mjs
import assert from "node:assert/strict";
import { isDeepStrictEqual } from "node:util";
import { execFileSync } from "node:child_process";
import { readFile, mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const root = fileURLToPath(new URL("../../", import.meta.url));
const fixture = JSON.parse(await readFile(resolve(root, "tests/fixtures/excluded-paradigm-sources.json"), "utf8"));
const url = process.env.KLEM_WEB_URL;
const cli = process.env.KLEM_BIN;
assert.ok(url && cli, "Set KLEM_WEB_URL and KLEM_BIN to the verified immutable native-dictionary runtime.");
const scratch = await mkdtemp(resolve(tmpdir(), "klem-excluded-browser-"));
const browser = await chromium.launch({executablePath: process.env.CHROMIUM_PATH, args: ["--no-sandbox"]});
try {
  const page = await browser.newPage({ viewport: {width: 1440, height: 1100}, acceptDownloads: true });
  const errors = [];
  page.on("pageerror", error => errors.push(String(error)));
  await page.goto(url);
  const padded = fixture.reviews.filter(r => r.diagnostic_surface);
  const text = padded.map(r => r.original_observation.written).join("\n") + "\n졸아들어";
  assert.equal(padded.length, 57);
  let submissions = 0;
  for (const decomposed of [false, true]) {
    const input = decomposed ? text.normalize("NFD") : text;
    for (const [mode, flag] of [["all", null], ["headword", "--dict-only"], ["compatible", "--dict-compatible"]]) {
      if (flag) {
        await page.getByLabel("Dictionary matches only").check();
        if (mode === "compatible") await page.getByLabel("Exclude known grammar conflicts").check();
        else await page.getByLabel("Exclude known grammar conflicts").uncheck();
      } else await page.getByLabel("Dictionary matches only").uncheck();
      await page.getByLabel("Your sentence", { exact: true }).fill(input);
      await page.getByRole("button", { name: "Analyze sentence", exact: true }).click();
      await page.waitForFunction(surface => document.querySelector(".panel-heading h2")?.textContent === surface, input.trim().split(/\s+/)[0]);
      assert.equal(await page.locator(".sentence").textContent(), input);
      const words = [...padded.map(r => r.diagnostic_surface), "졸아들어"];
      assert.equal(await page.locator(".breakdown-word").count(), words.length);
      for (const [index, surface] of words.entries()) {
        const frozen = fixture.before_words[surface];
        const kept = frozen[mode].analyses;
        const expected = frozen.all.analyses.flatMap((analysis, rawIndex) => kept.some(a => isDeepStrictEqual(a, analysis)) ? [String(rawIndex)] : []);
        const actual = await page.locator(".breakdown-word").nth(index).locator("option").evaluateAll(options => options.map(o => o.value).filter(Boolean));
        assert.deepEqual(actual, expected, `${decomposed ? "NFD" : "NFC"} ${mode} ${surface}: raw reading indices`);
      }
      const downloaded = page.waitForEvent("download");
      await page.getByRole("button", {name: "Export JSON", exact: true}).click();
      const exported = JSON.parse(await readFile(await (await downloaded).path(), "utf8"));
      const expectedRecords = execFileSync(cli, ["text", "--dictionary", resolve(root, "data/dictionaries/krdict/krdict.db"), ...(flag ? [flag] : [])], { input, encoding: "utf8", maxBuffer: 64 * 1024 * 1024 }).trim().split("\n").map(JSON.parse);
      assert.deepEqual(exported.records, expectedRecords);
      assert.equal(exported.records.map(r => r.surface).join(""), input);
      submissions++;
    }
  }
  await page.getByLabel("Dictionary matches only").uncheck();
  await page.getByLabel("Your sentence", {exact: true}).fill("  졸아들어 조라들어 기꺼우니 휩쓰니  ");
  await page.getByRole("button", {name: "Analyze sentence", exact: true}).click();
  await page.waitForFunction(() => document.querySelector(".panel-heading h2")?.textContent === "졸아들어");
  await page.locator(".entry-choices button").filter({hasText: "졸아들다"}).click();
  await page.waitForFunction(() => document.querySelector(".entry-heading h2")?.textContent === "졸아들다");
  await page.locator(".senses > li").first().locator("details summary").first().click();
  assert.ok((await page.locator(".entry-content").innerText()).includes("졸아들어"));
  await page.locator(".forms summary").click();
  const nativeForms = fixture.complete_native_entries["krdict:90327"].forms.filter(f => f.written).map(f => f.written).join(" · ");
  assert.equal(await page.locator(".forms p").textContent(), nativeForms);
  const desktop = resolve(scratch, "desktop.png");
  await page.screenshot({path: desktop, fullPage: true});
  await page.setViewportSize({width: 390, height: 844});
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  const mobile = resolve(scratch, "mobile.png");
  await page.screenshot({path: mobile, fullPage: true});
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({submissions, cohortWords: 58, filters: 3, unicodeForms: 2, originalWhitespaceAndOffsetsRetained: true, allRawIndicesAndExportsMatchCli: true, nativeConflictExamplesRetained: true, desktop, mobile}));
} finally {
  await browser.close();
}
