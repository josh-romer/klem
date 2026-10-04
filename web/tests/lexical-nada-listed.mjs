import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const root =
  process.env.KLEM_ROOT || fileURLToPath(new URL("../../", import.meta.url));
const url = process.env.KLEM_WEB_URL;
const cli = process.env.KLEM_BIN;
const db = root + "/data/dictionaries/krdict/krdict.db";
assert.ok(url && cli, "KLEM_WEB_URL and KLEM_BIN are required");
const fixture = JSON.parse(
  await readFile(root + "/tests/fixtures/lexical-nada-listed.json", "utf8"),
);
const words = Object.keys(fixture.before_raw_words).sort();

function batches(encoding) {
  const output = [];
  let current = [];
  for (const original of words) {
    const word = original.normalize(encoding);
    if (Buffer.byteLength(current.concat(word).join(" ")) > 7000) {
      output.push(current.join(" "));
      current = [];
    }
    current.push(word);
  }
  if (current.length) output.push(current.join(" "));
  return output;
}

const browser = await chromium.launch({
  executablePath: process.env.CHROMIUM_PATH,
  args: ["--no-sandbox"],
});
const errors = [];
const submissions = [];
try {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1100 },
    acceptDownloads: true,
  });
  page.on("pageerror", (error) => errors.push(String(error)));
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
      (expected) =>
        document.querySelector(".sentence")?.textContent === expected,
      text,
    );
    await page.getByLabel("Suggest missing spaces").check();
  }
  async function exportedRecords() {
    const download = page.waitForEvent("download");
    await page
      .getByRole("button", { name: "Export JSON", exact: true })
      .click();
    return JSON.parse(await readFile(await (await download).path(), "utf8"))
      .records;
  }
  for (const encoding of ["NFC", "NFD"]) {
    for (const [batch, input] of batches(encoding).entries()) {
      await analyze(input);
      for (const [mode, flag] of [
        ["all", null],
        ["headword", "--dict-only"],
        ["compatible", "--dict-compatible"],
      ]) {
        if (flag) {
          await page.getByLabel("Dictionary matches only").check();
          if (mode === "compatible")
            await page.getByLabel("Exclude known grammar conflicts").check();
          else
            await page.getByLabel("Exclude known grammar conflicts").uncheck();
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
          {
            input,
            encoding: "utf8",
            maxBuffer: 128 * 1024 * 1024,
          },
        )
          .trim()
          .split("\n")
          .map(JSON.parse);
        assert.deepEqual(await exportedRecords(), expected);
        const sections = page.getByRole("region", {
          name: "Missing-space suggestions",
          exact: true,
        });
        for (const record of expected) {
          for (const hypothesis of record.spacing?.alternatives ?? []) {
            if (hypothesis.rule === "spacing.bare_noun_main_nada") {
              assert.ok(
                await sections
                  .getByRole("heading", {
                    name: hypothesis.spaced,
                    exact: true,
                  })
                  .count(),
              );
            }
          }
        }
        assert.equal(await page.locator(".sentence").textContent(), input);
        submissions.push({ encoding, batch, mode, records: expected.length });
        console.log(
          encoding,
          batch,
          mode,
          "native cohort, cards and CLI export verified",
        );
      }
    }
  }
  await analyze("집난 사람나고 돈났지 피나는지 피나는");
  const sections = page.getByRole("region", {
    name: "Missing-space suggestions", exact: true,
  });
  const rendered = [];
  for (const [spaced, nounId, forms] of [
    ["집 난", "71358", ["집", "나", "은"]],
    ["사람 나고", "58161", ["사람", "나", "고"]],
    ["돈 났지", "17204", ["돈", "나", "었", "지"]],
    ["피 나는지", "73269", ["피", "나", "는지"]],
    ["피 나는", "73269", ["피", "나", "는"]],
  ]) {
    const card = sections.locator(".spacing-hypothesis").filter({
      has: page.getByRole("heading", { name: spaced, exact: true }),
    });
    await card.waitFor();
    const word = card.locator(".breakdown-word").last();
    const choice = word.locator("option").filter({
      hasText: new RegExp("^\\d+\\. " + forms.slice(1).join(" \\+ ") + "$"),
    });
    if (await choice.count()) {
      await word.locator("select").selectOption(await choice.getAttribute("value"));
    }
    assert.deepEqual(await card.locator(".part-form").allTextContents(), forms);
    await card.locator(".breakdown-part.lexical").first().click();
    await page.locator('.entry-content a[href*="ParaWordNo=' + nounId + '"]').waitFor();
    await card.locator(".breakdown-part.lexical").nth(1).click();
    await page.locator('.entry-content a[href*="ParaWordNo=62210"]').waitFor();
    rendered.push({ spaced, nounId, forms });
  }
  const whole = page.getByRole("region", { name: "Sentence breakdown", exact: true })
    .locator(".breakdown-word").filter({
      has: page.locator(".breakdown-surface > span", { hasText: /^피나는$/ }),
    });
  const option = whole.locator("option").filter({ hasText: /^\d+\. 피나 \+ 는$/ });
  assert.equal(await option.count(), 1);
  await whole.locator("select").selectOption(await option.getAttribute("value"));
  await whole.locator(".breakdown-part.lexical").first().click();
  await page.locator('.entry-content a[href*="ParaWordNo=83815"]').waitFor();
  await page.screenshot({
    path: "/tmp/klem-lexical-nada-listed-desktop.png",
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
    path: "/tmp/klem-lexical-nada-listed-mobile.png",
    fullPage: true,
  });
  assert.deepEqual(errors, []);
  const report = {
    submissions,
    words: words.length,
    errors,
    allExportsMatchCli: true,
    rendered,
    wholePiVerbPreserved: true,
    nativeMainEntry: "62210",
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
