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
const fixture = JSON.parse(await readFile(root + "/tests/fixtures/doeda-complement-sources.json", "utf8"));
const corrections = JSON.parse(await readFile(root + "/tests/fixtures/doeda-complement-corrections.json", "utf8"));
for (const c of corrections.corrections) {
  const index = fixture.cases.findIndex(x => JSON.stringify(x) === JSON.stringify(c.original));
  assert.ok(index >= 0);
  fixture.cases[index] = c.replacement_control;
  fixture.cases.push(c.replacement_positive);
}
fixture.cases.push(...JSON.parse(await readFile(root + "/tests/fixtures/doeda-complement-bridge-boundaries.json", "utf8")).cases);
const words = [...new Set(fixture.cases.map(c => c.surface))].sort();
function batches(encoding) {
  const chunks = [];
  let words = [];
  for (const word of [...new Set(fixture.cases.map(c => c.surface))].sort()) {
    const candidate = [...words, word].join(" ").normalize(encoding);
    if (Buffer.byteLength(candidate) > 7500 && words.length) {
      chunks.push(words.join(" ").normalize(encoding));
      words = [];
    }
    words.push(word);
  }
  if (words.length) chunks.push(words.join(" ").normalize(encoding));
  return chunks;
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
    for (const [batch, text] of batches(encoding).entries()) {
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
      for (const c of fixture.cases.filter(c => found.has(c.surface))) {
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
              JSON.stringify(c.morpheme_kinds) &&
            c.required_rules.every((r) => a.rules.includes(r)),
        );
        const auxiliaryDoeda = c.lemmas.some((head, i) => head === "되다" && c.lemma_kinds[i] === "auxiliary");
        assert.equal(matches.length > 0, c.verdict === "required" && (mode !== "compatible" || !auxiliaryDoeda), c.id);
        for (const a of matches)
          assert.ok(
            c.required_rules.every((r) => a.rules.includes(r)),
            c.id,
          );
      }
      assert.equal(await page.locator(".sentence").textContent(), text);
      checks.push({ encoding, batch, mode, input: text, records: expected.length });
      console.log(
        encoding,
        mode,
        "source cohort and CLI export parity verified",
      );
    }
  }
  }
  await page.getByLabel("Dictionary matches only").uncheck();
  const diagramWords = [
    "출발하기로되었다",
    "행복해야된다",
    "학생이면된다",
    "먹어도된다",
    "먹어서는안된다",
    "표시하도록되어있다",
  ];
  const cases = diagramWords.map((word) =>
    fixture.cases.find((c) => c.surface === word && c.verdict === "required" && c.lemma_kinds[c.lemmas.indexOf("되다")] === "predicate"),
  );
  assert.ok(cases.every(Boolean));
  await analyze(diagramWords.join(" "));
  const response = await page.request.post(url + "/api/analyze", {
    data: { text: diagramWords.join(" "), suggest_spacing: true },
  });
  assert.equal(response.status(), 200);
  const actual = await response.json();
  const sentence = page.getByRole("region", {
    name: "Sentence breakdown",
    exact: true,
  });
  const rendered = [],
    endingEntryIds = [],
    roleChecks = [];
  for (const c of cases) {
    const recordIndex = actual.records.findIndex(
      (r) => r.surface === c.surface,
    );
    const record = actual.records[recordIndex];
    const choices = record.analysis.analyses;
    const selectedIndex = choices.findIndex(
      (a) =>
        JSON.stringify(a.lemmas.map((l) => l.text)) ===
          JSON.stringify(c.lemmas) &&
        JSON.stringify(a.lemmas.map((l) => l.kind)) ===
          JSON.stringify(c.lemma_kinds) &&
        JSON.stringify(a.morphemes.map((m) => m.form)) ===
          JSON.stringify(c.morphemes) &&
        JSON.stringify(a.morphemes.map((m) => m.kind)) ===
          JSON.stringify(c.morpheme_kinds) &&
        c.required_rules.every((r) => a.rules.includes(r)),
    );
    assert.ok(selectedIndex >= 0, c.id);
    const part = sentence.locator(".breakdown-word").filter({
      has: page.locator(".breakdown-surface > span", {
        hasText: new RegExp("^" + c.surface + "$"),
      }),
    });
    const analysis = choices[selectedIndex];
    const forms = {
      "출발하기로되었다": ["출발하", "기", "로", "되", "었", "다"],
      // The reader displays the native 하 + 여 form; canonical CLI lookup
      // and component identities continue to use 어야.
      "행복해야된다": ["행복하", "여야", "되", "는다"],
      "학생이면된다": ["학생", "이", "으면", "되", "는다"],
      "먹어도된다": ["먹", "어도", "되", "는다"],
      "먹어서는안된다": ["먹", "어서", "는", "안", "되", "는다"],
      "표시하도록되어있다": ["표시하", "도록", "되", "어", "있", "다"],
    }[c.surface];
    await part.locator("select").selectOption(String(selectedIndex));
    assert.deepEqual(await part.locator(".part-form").allTextContents(), forms);
    const doeda = part.locator('.breakdown-part[title^="되다 · predicate"]');
    assert.equal(await doeda.count(), 1, c.surface);
    await doeda.click();
    await page.locator('.entry-content a[href*="ParaWordNo=89858"]').waitFor();
    roleChecks.push({
      word: c.surface,
      lexicalEntryId: "89858",
      kind: "predicate",
      passed: true,
    });
    if (c.surface === "먹어서는안된다") {
      await part.locator('.breakdown-part[title^="안 · adverbial"]').click();
      await page.locator('.entry-content a[href*="ParaWordNo=71372"]').waitFor();
      endingEntryIds.push("71372");
    }
    if (c.surface === "먹어도된다") {
      const auxiliaryIndex = choices.findIndex(
        (a) =>
          JSON.stringify(a.morphemes) === JSON.stringify(analysis.morphemes) &&
          JSON.stringify(a.lemmas) ===
            JSON.stringify(
              analysis.lemmas.map((l, i) =>
                i === 1 ? { ...l, kind: "auxiliary" } : l,
              ),
            ),
      );
      assert.ok(auxiliaryIndex >= 0);
      await part.locator("select").selectOption(String(auxiliaryIndex));
      assert.deepEqual(
        await part.locator(".part-form").allTextContents(),
        forms,
      );
      assert.equal(
        await part
          .locator('.breakdown-part[title^="되다 · auxiliary"]')
          .count(),
        1,
      );
      await page.getByLabel("Dictionary matches only").check();
      await page.getByLabel("Exclude known grammar conflicts").check();
      assert.equal(
        await part.locator('option[value="' + auxiliaryIndex + '"]').count(),
        0,
      );
      assert.equal(
        await part.locator('option[value="' + selectedIndex + '"]').count(),
        1,
      );
      await part.locator("select").selectOption(String(selectedIndex));
      await page.getByLabel("Dictionary matches only").uncheck();
      roleChecks.push({
        word: c.surface,
        historicalAuxiliaryRetained: true,
        compatibleLexicalRetained: true,
        passed: true,
      });
    }
    rendered.push(c.surface);
  }
  await sentence.screenshot({
    path: "/tmp/klem-doeda-complement-diagrams-desktop.png",
  });
  await page.screenshot({
    path: "/tmp/klem-doeda-complement-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
    true,
  );
  await sentence.screenshot({
    path: "/tmp/klem-doeda-complement-diagrams-mobile.png",
  });
  await page.screenshot({
    path: "/tmp/klem-doeda-complement-mobile.png",
    fullPage: true,
  });
  assert.deepEqual(errors, []);
  const report = {
    schema_version: 1,
    checklist: "COV-019ah",
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
    roleChecks,
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
