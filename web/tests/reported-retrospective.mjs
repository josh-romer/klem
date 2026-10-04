import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFile, writeFile } from "node:fs/promises";
const root = process.env.KLEM_ROOT || process.cwd();
import { chromium } from "playwright";
const url = process.env.KLEM_WEB_URL,
  cli = process.env.KLEM_BIN,
  db = root + "/data/dictionaries/krdict/krdict.db";
assert.ok(url && cli, "KLEM_WEB_URL and KLEM_BIN are required");
const load = async (name) =>
  JSON.parse(await readFile(root + "/tests/fixtures/" + name, "utf8"));
const core = await load("reported-retrospective-sources.json");
const followers = await load("reported-retrospective-followers.json");
const corrections = await load("reported-retrospective-corrections.json");
const boundaries = await load("reported-retrospective-boundaries.json");
const fixture = {
  cases: [...core.cases, ...followers.cases]
    .map(
      (c) =>
        corrections.superseded.find((x) => x.original.id === c.id)
          ?.replacement || c,
    )
    .concat(corrections.cases, boundaries.cases),
};
const words = [
  ...new Set([
    ...Object.keys(core.before_words),
    ...Object.keys(corrections.before_words),
    ...fixture.cases.map((c) => c.surface),
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
    for (const text of batches(encoding)) {
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
  }
  await analyze(
    "났다던데 간다던 학생이라던데 먹으라던데 먹자던데 좋으냐던데 먹어본다던데 이기리라던 도와달라던데요",
  );
  const sentence = page.getByRole("region", {
    name: "Sentence breakdown",
    exact: true,
  });
  const rendered = [];
  for (const [word, forms] of [
    ["났다던데", ["나", "었", "다던데"]],
    ["간다던", ["가", "는다던"]],
    ["학생이라던데", ["학생", "이", "라던데"]],
    ["먹으라던데", ["먹", "으라던데"]],
    ["먹자던데", ["먹", "자던데"]],
    ["좋으냐던데", ["좋", "으냐던데"]],
    ["먹어본다던데", ["먹", "어", "보", "는다던데"]],
    ["이기리라던", ["이기", "으리", "라던"]],
    ["도와달라던데요", ["돕", "어", "달", "으라던데", "요"]],
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
      has: page.locator(".part-form", {
        hasText: new RegExp(
          "^" +
            forms.find((f) =>
              [
                "다던데",
                "는다던",
                "라던데",
                "으라던데",
                "자던데",
                "으냐던데",
                "는다던데",
                "라던",
              ].includes(f),
            ) +
            "$",
        ),
      }),
    });
    assert.ok(
      (await ending.locator(".part-gloss").textContent()).includes("recalled"),
    );
    if (word === "간다던") {
      await ending.locator("button").click();
      for (const [head, id] of [
        ["-ㄴ다던", "82037"],
        ["-는다던", "82038"],
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
    path: "/tmp/klem-reported-retrospective-desktop.png",
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
    path: "/tmp/klem-reported-retrospective-mobile.png",
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
    endingEntryIds: ["82037", "82038"],
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
