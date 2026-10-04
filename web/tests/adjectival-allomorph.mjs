import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFile, writeFile } from "node:fs/promises";
import { chromium } from "playwright";

const root = process.env.KLEM_ROOT || process.cwd();
const url = process.env.KLEM_WEB_URL;
const cli = process.env.KLEM_BIN;
assert.ok(url && cli, "KLEM_WEB_URL and KLEM_BIN are required");
const runtime = JSON.parse(
  await readFile(
    root + "/docs/adjectival-allomorph-packaged-runtime.json",
    "utf8",
  ),
);
const words = runtime.words;
const db = root + "/data/dictionaries/krdict/krdict.db";
const browser = await chromium.launch({
  executablePath: process.env.CHROMIUM_PATH,
  args: ["--no-sandbox"],
});
const errors = [],
  checks = [],
  rendered = [];
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
      (t) => document.querySelector(".sentence")?.textContent === t,
      text,
    );
    if (!(await page.getByLabel("Suggest missing spaces").isChecked())) {
      const spacing = page.waitForResponse(
        (r) =>
          r.url().endsWith("/api/analyze") && r.request().method() === "POST",
      );
      await page.getByLabel("Suggest missing spaces").check();
      assert.equal((await spacing).status(), 200);
      await page.waitForFunction(
        (t) => document.querySelector(".sentence")?.textContent === t,
        text,
      );
    }
  }
  for (const encoding of ["NFC", "NFD"]) {
    for (let start = 0; start < words.length;) {
      const batch = [];
      while (start + batch.length < words.length && batch.length < 250) {
        const word = words[start + batch.length].normalize(encoding);
        if (Buffer.byteLength([...batch, word].join(" ")) > 7000) break;
        batch.push(word);
      }
      assert.ok(batch.length);
      const text = batch.join(" ");
      assert.ok(Buffer.byteLength(text) <= 7000);
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
        const exported = JSON.parse(
          await readFile(await (await download).path(), "utf8"),
        );
        assert.deepEqual(exported.records, expected);
        assert.equal(await page.locator(".sentence").textContent(), text);
        checks.push({
          encoding,
          mode,
          start,
          words: batch.length,
          records: expected.length,
          passed: true,
        });
        console.log(
          encoding,
          mode,
          start,
          "browser/CLI export parity verified",
        );
      }
      start += batch.length;
    }
  }
  await page.getByLabel("Dictionary matches only").uncheck();
  const diagrams = [
    ["예쁘냐고", ["예쁘", "냐고"], "냐고", ["76243", "87442"]],
    ["기냐고", ["길", "냐고"], "냐고", ["76243", "87442"]],
    ["좋으냐고", ["좋", "으냐고"], "으냐고", ["79258", "87444"]],
    ["어떠냐", ["어떻", "으냐"], "으냐", ["76235"]],
    ["아이다우냐", ["아이", "답", "으냐"], "으냐", ["76235"]],
    ["학생이냐", ["학생", "이", "냐"], "냐", ["76230"]],
    ["먹고계시냐면", ["먹", "고", "계시", "냐면"], "냐면", ["80177"]],
    ["기냐는구나", ["길", "냐는구나"], "냐는구나", ["88945"]],
    ["좋으냐는구나", ["좋", "으냐는구나"], "으냐는구나", ["88947"]],
  ];
  await analyze(diagrams.map(([word]) => word).join(" "));
  const sentence = page.getByRole("region", {
    name: "Sentence breakdown",
    exact: true,
  });
  for (const [word, forms, form, ids] of diagrams) {
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
        hasText: new RegExp("^" + form + "$"),
      }),
    });
    await ending.locator("button").click();
    const links = page.locator(
      ids
        .map((id) => '.entry-content a[href*="ParaWordNo=' + id + '"]')
        .join(","),
    );
    await links.first().waitFor();
    const href = await links.first().getAttribute("href");
    const entry = new URL(href).searchParams.get("ParaWordNo");
    assert.ok(ids.includes(entry));
    rendered.push({ word, forms, ending: form, entry, passed: true });
  }
  await page.screenshot({
    path: "/tmp/klem-adjectival-allomorph-desktop.png",
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
    path: "/tmp/klem-adjectival-allomorph-mobile.png",
    fullPage: true,
  });
  assert.deepEqual(errors, []);
  const report = {
    schema_version: 1,
    words: words.length,
    checks,
    errors,
    allExportsMatchCli: true,
    rendered,
    mobileNoHorizontalOverflow: true,
  };
  assert.ok(process.env.KLEM_REPORT);
  await writeFile(
    process.env.KLEM_REPORT,
    JSON.stringify(report, null, 2) + "\n",
  );
  console.log(
    "Verified",
    checks.length,
    "browser exports and",
    rendered.length,
    "selected source-linked diagrams.",
  );
} finally {
  await browser.close();
}
