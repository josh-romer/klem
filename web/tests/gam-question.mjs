import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { readFile, writeFile } from "node:fs/promises";
const root = process.env.KLEM_ROOT || process.cwd();
import { chromium } from "playwright";
const url = process.env.KLEM_WEB_URL,
  cli = process.env.KLEM_BIN,
  db = root + "/data/dictionaries/krdict/krdict.db";
assert.ok(url && cli, "KLEM_WEB_URL and KLEM_BIN are required");
const fixture = JSON.parse(
  await readFile(root + "/tests/fixtures/gam-question-sources.json", "utf8"),
);
const original = JSON.parse(
  await readFile(root + "/tests/fixtures/gam-question-sources.json", "utf8"),
);
const words = Object.keys(original.before_words).sort();
const browser = await chromium.launch({
  executablePath: process.env.CHROMIUM_PATH,
  args: ["--no-sandbox"],
});
const errors = [],
  checks = [];
try {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1100 },
    acceptDownloads: true,
  });
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto(url);
  async function analyze(text) {
    await page.getByLabel("Your sentence", { exact: true }).fill(text);
    const response = page.waitForResponse(
      (r) =>
        r.url().endsWith("/api/analyze") && r.request().method() === "POST",
    );
    await page
      .getByRole("button", { name: "Analyze sentence", exact: true })
      .click();
    assert.equal((await response).status(), 200);
    await page.waitForFunction(
      (t) => document.querySelector(".sentence")?.textContent === t,
      text,
    );
    await page.getByLabel("Suggest missing spaces").check();
  }
  for (const encoding of ["NFC", "NFD"]) {
    const text = words.join(" ").normalize(encoding);
    await analyze(text);
    for (const [mode, flag] of [
      ["all", null],
      ["headword", "--dict-only"],
      ["compatible", "--dict-compatible"],
    ]) {
      if (flag) {
        await page.getByLabel("Dictionary matches only").check();
        if (mode === "compatible")
          await page.getByLabel("Exclude known grammar conflicts").check();
        else await page.getByLabel("Exclude known grammar conflicts").uncheck();
      } else await page.getByLabel("Dictionary matches only").uncheck();
      const expected = execFileSync(
        cli,
        [
          "text",
          "-",
          "--dictionary",
          db,
          ...(flag ? [flag] : []),
          "--suggest-spacing",
        ],
        { input: text, encoding: "utf8", maxBuffer: 128 * 1024 * 1024 },
      )
        .trim()
        .split("\n")
        .map(JSON.parse);
      const download = page.waitForEvent("download");
      await page
        .getByRole("button", { name: "Export JSON", exact: true })
        .click();
      const result = JSON.parse(
        await readFile(await (await download).path(), "utf8"),
      );
      assert.deepEqual(result.records, expected);
      assert.equal(await page.locator(".sentence").textContent(), text);
      checks.push({ encoding, mode, records: expected.length });
      console.log(
        encoding,
        mode,
        "source cohort and CLI export parity verified",
      );
    }
  }
  await analyze(
    "더운감 좋은감 하는감 멀었는감 하던감 학생인감 먹으신감 먹고있는감 아이다운감",
  );
  const sentence = page.getByRole("region", {
    name: "Sentence breakdown",
    exact: true,
  });
  const rendered = [];
  for (const [word, forms] of [
    ["더운감", ["덥", "은감"]],
    ["좋은감", ["좋", "은감"]],
    ["하는감", ["하", "는감"]],
    ["멀었는감", ["멀", "었", "는감"]],
    ["하던감", ["하", "던감"]],
    ["학생인감", ["학생", "이", "은감"]],
    ["먹으신감", ["먹", "시", "은감"]],
    ["먹고있는감", ["먹", "고", "있", "는감"]],
    ["아이다운감", ["아이", "답", "은감"]],
  ]) {
    const part = sentence.locator(".breakdown-word").filter({
      has: page.locator(".breakdown-surface > span", {
        hasText: new RegExp("^" + word + "$"),
      }),
    });
    const choice = part
      .locator("option")
      .filter({ hasText: new RegExp("^\\d+\\. " + forms.join(" \\+ ") + "$") });
    assert.equal(await choice.count(), 1, word);
    await part
      .locator("select")
      .selectOption(await choice.getAttribute("value"));
    assert.deepEqual(await part.locator(".part-form").allTextContents(), forms);
    const ending = part.locator(".breakdown-component").filter({
      has: page.locator(".part-form", { hasText: /^(은감|는감|던감)$/ }),
    });
    assert.ok(
      (await ending.locator(".part-gloss").textContent())
        .toLowerCase()
        .includes("refuting"),
    );
    if (word === "더운감") {
      await ending.locator("button").click();
      for (const [head, id] of [
        ["-ㄴ감", "73878"],
        ["-은감", "73888"],
      ]) {
        await page
          .locator(".entry-choices button")
          .filter({ hasText: head })
          .click();
        await page
          .locator('.entry-content a[href*="ParaWordNo=' + id + '"]')
          .waitFor();
      }
    }
    rendered.push(word);
  }
  for (const [word, form, id] of [
    ["하는감", "는감", "73879"],
    ["하던감", "던감", "73880"],
  ]) {
    const part = sentence.locator(".breakdown-word").filter({
      has: page.locator(".breakdown-surface > span", {
        hasText: new RegExp("^" + word + "$"),
      }),
    });
    const ending = part.locator(".breakdown-component").filter({
      has: page.locator(".part-form", {
        hasText: new RegExp("^" + form + "$"),
      }),
    });
    await ending.locator("button").click();
    await page
      .locator('.entry-content a[href*="ParaWordNo=' + id + '"]')
      .waitFor();
  }
  await page.screenshot({
    path: "/tmp/klem-gam-question-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
    true,
  );
  await page.screenshot({
    path: "/tmp/klem-gam-question-mobile.png",
    fullPage: true,
  });
  assert.deepEqual(errors, []);
  const report = {
    schema_version: 1,
    checklist: "COV-017bv",
    cli_sha256: createHash("sha256")
      .update(await readFile(cli))
      .digest("hex"),
    engine_sha256: createHash("sha256")
      .update(await readFile(root + "/src/engine.rs"))
      .digest("hex"),
    catalog_sha256: createHash("sha256")
      .update(await readFile(root + "/web/src/grammar-labels.json"))
      .digest("hex"),
    browser_tool_sha256: createHash("sha256")
      .update(await readFile(new URL(import.meta.url)))
      .digest("hex"),
    words: words.length,
    cases: fixture.cases.length,
    checks,
    errors,
    allExportsMatchCli: true,
    rendered,
    endingEntryIds: ["73878", "73888", "73879", "73880"],
    mobileNoHorizontalOverflow: true,
    contextual_verdict: "unjudged",
    independent_review: "pending",
  };
  if (process.env.KLEM_REPORT)
    await writeFile(
      process.env.KLEM_REPORT,
      JSON.stringify(report, null, 2) + "\n",
    );
  console.log(JSON.stringify(report));
} finally {
  await browser.close();
}
