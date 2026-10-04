import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFile, writeFile } from "node:fs/promises";
const root = process.env.KLEM_ROOT || process.cwd();
import { chromium } from "playwright";
const url = process.env.KLEM_WEB_URL,
  cli = process.env.KLEM_BIN,
  db = root + "/data/dictionaries/krdict/krdict.db";
assert.ok(url && cli, "KLEM_WEB_URL and KLEM_BIN are required");
const fixture = JSON.parse(
  await readFile(root + "/tests/fixtures/rya-copula-regressions.json", "utf8"),
);
const original = JSON.parse(
  await readFile(root + "/tests/fixtures/rya-copula-regressions.json", "utf8"),
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
  await analyze("지위랴 의사랴마는 학생이랴마는 나랴");
  const sentence = page.getByRole("region", {
    name: "Sentence breakdown",
    exact: true,
  });
  for (const [word, forms] of [
    ["지위랴", ["지위", "이", "으랴"]],
    ["의사랴마는", ["의사", "이", "으랴", "마는"]],
    ["학생이랴마는", ["학생", "이", "으랴", "마는"]],
  ]) {
    const part = sentence.locator(".breakdown-word").filter({
      has: page.locator(".breakdown-surface > span", {
        hasText: new RegExp("^" + word + "$"),
      }),
    });
    assert.deepEqual(await part.locator(".part-form").allTextContents(), forms);
    const copula = part
      .locator(".breakdown-component")
      .filter({ has: page.locator(".part-form", { hasText: /^이$/ }) });
    assert.ok(
      (await copula.locator(".part-gloss").textContent()).includes("ida"),
    );
    const ending = part
      .locator(".breakdown-component")
      .filter({ has: page.locator(".part-form", { hasText: /^으랴$/ }) });
    assert.ok(
      (await ending.locator("button").getAttribute("title")).includes("79260"),
    );
    await copula.locator("button").click();
    await page.locator('.entry-content a[href*="ParaWordNo=86232"]').waitFor();
  }
  const ambiguous = sentence.locator(".breakdown-word").filter({
    has: page.locator(".breakdown-surface > span", { hasText: /^나랴$/ }),
  });
  const lexical = ambiguous
    .locator("option")
    .filter({ hasText: /^\d+\. 나 \+ 으랴$/ });
  assert.equal(await lexical.count(), 1);
  await ambiguous
    .locator("select")
    .selectOption(await lexical.getAttribute("value"));
  assert.deepEqual(await ambiguous.locator(".part-form").allTextContents(), [
    "나",
    "으랴",
  ]);
  await page.screenshot({
    path: "/tmp/klem-rya-copula-desktop.png",
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
    path: "/tmp/klem-rya-copula-mobile.png",
    fullPage: true,
  });
  assert.deepEqual(errors, []);
  const report = {
    words: words.length,
    cases: fixture.cases.length,
    checks,
    errors,
    allExportsMatchCli: true,
    omittedCopulaBreakdowns: true,
    lexicalAlternativeSelection: true,
    copulaEntryIds: ["86232"],
    mobileNoHorizontalOverflow: true,
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
