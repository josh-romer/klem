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
  await readFile(root + "/tests/fixtures/emphatic-ending-sources.json", "utf8"),
);
const original = JSON.parse(
  await readFile(root + "/tests/fixtures/emphatic-ending-sources.json", "utf8"),
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
      const found = new Map(
        result.records
          .filter((r) => r.kind === "word")
          .map((r) => [r.analysis.normalized, r]),
      );
      for (const c of fixture.cases) {
        const paths = found.get(c.surface).analysis.analyses;
        const matches = paths.filter(
          (a) =>
            JSON.stringify(a.lemmas.map((l) => l.text)) ===
              JSON.stringify(c.lemmas) &&
            JSON.stringify(a.lemmas.map((l) => l.kind)) ===
              JSON.stringify(c.lemma_kinds) &&
            JSON.stringify(a.morphemes.map((m) => m.form)) ===
              JSON.stringify(c.morphemes) &&
            JSON.stringify(a.morphemes.map((m) => m.kind)) ===
              JSON.stringify(c.morpheme_kinds),
        );
        const roleConflict =
          mode === "compatible" &&
          c.lemmas.includes("되다") &&
          c.lemma_kinds.includes("auxiliary");
        assert.equal(
          matches.length > 0,
          c.verdict === "required" && !roleConflict,
          c.id,
        );
        for (const a of matches)
          assert.ok(
            c.required_rules.every((r) => a.rules.includes(r)),
            c.id,
          );
      }
      assert.equal(await page.locator(".sentence").textContent(), text);
      checks.push({ encoding, mode, records: expected.length });
      console.log(
        encoding,
        mode,
        "source cohort and CLI export parity verified",
      );
    }
  }
  await page.getByLabel("Dictionary matches only").uncheck();
  const diagrams = [
    ["먹게끔", ["먹", "게끔"]],
    ["슬프게끔한다", ["슬프", "게끔", "하", "는다"]],
    ["편리하게끔해줍니다", ["편리하", "게끔", "하", "여", "주", "습니다"]],
    ["먹으시게끔했습니다", ["먹", "시", "게끔", "하", "였", "습니다"]],
    ["먹고싶게끔", ["먹", "고", "싶", "게끔"]],
    ["학생이고말고", ["학생", "이", "고말고"]],
    ["먹었고말고", ["먹", "었", "고말고"]],
    ["그렇고말고요", ["그렇", "고말고", "요"]],
    ["아이다우시다마다", ["아이", "답", "시", "다마다"]],
  ];
  await analyze(diagrams.map(([word]) => word).join(" "));
  const sentence = page.getByRole("region", {
    name: "Sentence breakdown",
    exact: true,
  });
  const rendered = [],
    endingEntryIds = [];
  const sources = { 게끔: "88382", 고말고: "66991", 다마다: "75968" };
  for (const [word, forms] of diagrams) {
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
      has: page.locator(".part-form", { hasText: /^(게끔|고말고|다마다)$/ }),
    });
    const form = await ending.locator(".part-form").textContent();
    const gloss = (
      await ending.locator(".part-gloss").textContent()
    ).toLowerCase();
    assert.ok(gloss.includes(form === "게끔" ? "emphatic" : "affirmation"));
    if (!endingEntryIds.includes(sources[form])) {
      await ending.locator("button").click();
      await page
        .locator('.entry-content a[href*="ParaWordNo=' + sources[form] + '"]')
        .waitFor();
      endingEntryIds.push(sources[form]);
    }
    rendered.push(word);
  }
  await page.screenshot({
    path: "/tmp/klem-emphatic-ending-desktop.png",
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
    path: "/tmp/klem-emphatic-ending-mobile.png",
    fullPage: true,
  });
  assert.deepEqual(errors, []);
  const report = {
    schema_version: 1,
    checklist: "COV-017bw",
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
    endingEntryIds,
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
