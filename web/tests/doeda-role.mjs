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
  await readFile(root + "/tests/fixtures/doeda-role-sources.json", "utf8"),
);
const original = JSON.parse(
  await readFile(root + "/tests/fixtures/doeda-role-sources.json", "utf8"),
);
const words = Object.keys(original.before_case_words).sort();
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
              JSON.stringify(c.morpheme_kinds) &&
            c.required_rules.every((r) => a.rules.includes(r)),
        );
        assert.equal(matches.length > 0, c.verdict === "required", c.id);
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
  const diagramWords = [
    "먹게되었다",
    "좋게됩니다",
    "살게끔되어있다",
    "먹으시게끔되었습니다",
  ];
  const cases = diagramWords.map((word) =>
    fixture.cases.find((c) => c.surface === word && c.verdict === "required"),
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
    const forms = actual.breakdowns[recordIndex][selectedIndex].map(
      (component) =>
        "lemma" in component
          ? analysis.lemmas[component.lemma].text.replace(/다$/, "")
          : analysis.morphemes[component.morpheme].form,
    );
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
    const ending = part.locator(".breakdown-component").filter({
      has: page.locator(".part-form", { hasText: /^게끔$/ }),
    });
    if (await ending.count()) {
      await ending.locator("button").click();
      await page
        .locator('.entry-content a[href*="ParaWordNo=88382"]')
        .waitFor();
      endingEntryIds.push("88382");
    }
    if (c.surface === "먹게되었다") {
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
    path: "/tmp/klem-doeda-role-diagrams-desktop.png",
  });
  await page.screenshot({
    path: "/tmp/klem-doeda-role-desktop.png",
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
    path: "/tmp/klem-doeda-role-diagrams-mobile.png",
  });
  await page.screenshot({
    path: "/tmp/klem-doeda-role-mobile.png",
    fullPage: true,
  });
  assert.deepEqual(errors, []);
  const report = {
    schema_version: 1,
    checklist: "COV-019ag",
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
