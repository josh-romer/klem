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
  await readFile(root + "/tests/fixtures/caution-ending-sources.json", "utf8"),
);
const original = JSON.parse(
  await readFile(root + "/tests/fixtures/caution-ending-sources.json", "utf8"),
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
    "날라 들을라 가짜일라 깨실라 먹었을라 학생다울라 먹어볼라 먹어보겠을라",
  );
  const sentence = page.getByRole("region", {
    name: "Sentence breakdown",
    exact: true,
  });
  const rendered = [];
  for (const [word, forms] of [
    ["날라", ["나", "을라"]],
    ["들을라", ["듣", "을라"]],
    ["가짜일라", ["가짜", "이", "을라"]],
    ["깨실라", ["깨", "시", "을라"]],
    ["먹었을라", ["먹", "었", "을라"]],
    ["학생다울라", ["학생", "답", "을라"]],
    ["먹어볼라", ["먹", "어", "보", "을라"]],
    ["먹어보겠을라", ["먹", "어", "보", "겠", "을라"]],
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
    const ending = part
      .locator(".breakdown-component")
      .filter({ has: page.locator(".part-form", { hasText: /^을라$/ }) });
    assert.ok(
      (await ending.locator(".part-gloss").textContent()).includes("Caution"),
    );
    if (word === "날라") {
      await ending.locator("button").click();
      for (const [head, id] of [
        ["-ㄹ라", "77345"],
        ["-을라", "77346"],
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
  await page.screenshot({
    path: "/tmp/klem-caution-ending-desktop.png",
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
    path: "/tmp/klem-caution-ending-mobile.png",
    fullPage: true,
  });
  assert.deepEqual(errors, []);
  const report = {
    words: words.length,
    cases: fixture.cases.length,
    checks,
    errors,
    allExportsMatchCli: true,
    rendered,
    endingEntryIds: ["77345", "77346"],
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
