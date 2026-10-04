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
  await readFile(root + "/tests/fixtures/lexical-nada-spacing.json", "utf8"),
);
const dependency = JSON.parse(
  await readFile(
    root + "/tests/fixtures/lexical-nada-dependencies.json",
    "utf8",
  ),
);
const words = [
  ...new Set([
    ...Object.keys(fixture.before_raw_words),
    ...fixture.cases.map((c) => c.surface),
    ...Object.keys(dependency.before_words),
    ...Object.keys(fixture.before_legacy_words),
  ]),
].sort();

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
  await analyze("사고났다 짜증나버렸어요 연기나랴 생각났다 냄새나는");
  const sections = page.getByRole("region", {
    name: "Missing-space suggestions",
    exact: true,
  });
  const accident = sections.locator(".spacing-hypothesis").filter({
    has: page.getByRole("heading", { name: "사고 났다", exact: true }),
  });
  await accident.waitFor();
  assert.deepEqual(await accident.locator(".part-form").allTextContents(), [
    "사고",
    "나",
    "었",
    "다",
  ]);
  await accident.locator(".breakdown-part.lexical").nth(1).click();
  await page.locator('.entry-content a[href*="ParaWordNo=62210"]').waitFor();
  assert.ok(
    (await page.locator(".entry-heading").textContent()).includes("동사"),
  );
  assert.ok(
    !(await page.locator(".entry-heading").textContent()).includes("보조 동사"),
  );
  const smoke = sections.locator(".spacing-hypothesis").filter({
    has: page.getByRole("heading", { name: "연기 나랴", exact: true }),
  });
  assert.deepEqual(await smoke.locator(".part-form").allTextContents(), [
    "연기",
    "나",
    "으랴",
  ]);
  const ending = smoke
    .locator(".breakdown-component")
    .filter({ has: page.locator(".part-form", { hasText: /^으랴$/ }) });
  assert.equal(
    await ending.locator(".part-gloss").textContent(),
    "Rhetorical question / offer / enumeration",
  );
  const sourceHint = await ending.locator("button").getAttribute("title");
  for (const id of ["79260", "79261", "80306", "80308"])
    assert.ok(sourceHint.includes(id));
  await ending.locator("button").click();
  await page.locator('.entry-content a[href*="ParaWordNo=79260"]').waitFor();
  assert.ok(
    (await page.locator(".entry-heading").textContent()).includes("-랴"),
  );
  assert.ok(
    (await page.locator(".entry-heading").textContent()).includes("어미"),
  );
  await page.screenshot({
    path: "/tmp/klem-lexical-nada-desktop.png",
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
    path: "/tmp/klem-lexical-nada-mobile.png",
    fullPage: true,
  });
  assert.deepEqual(errors, []);
  const report = {
    submissions,
    words: words.length,
    errors,
    allExportsMatchCli: true,
    nativeMainEntry: "62210",
    endingSourceIds: ["79260", "79261", "80306", "80308"],
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
