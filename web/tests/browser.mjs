import { chromium } from "playwright";
import assert from "node:assert/strict";
import { spawn, execFileSync } from "node:child_process";
import { mkdtemp, readFile, writeFile, rm, mkdir } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { request as httpRequest } from "node:http";

const root = fileURLToPath(new URL("../../", import.meta.url));
const serverBin =
  process.env.KLEM_WEB_BIN || resolve(root, "target/debug/klem-web");
const cliBin = process.env.KLEM_BIN || resolve(root, "target/debug/klem");
const scratch = await mkdtemp(resolve(tmpdir(), "klem-browser-"));
const assets = resolve(root, "web/dist");
const database = resolve(scratch, "test.db");
const processes = [];
let browser;
async function start(dictionary) {
  const process = spawn(
    serverBin,
    [
      "--port",
      "0",
      "--assets",
      assets,
      ...(dictionary ? ["--dictionary", database] : []),
    ],
    { cwd: root, stdio: ["ignore", "ignore", "pipe"] },
  );
  processes.push(process);
  return await new Promise((resolve, reject) => {
    let output = "";
    const timer = setTimeout(
      () => reject(new Error(`Server startup timed out: ${output}`)),
      15000,
    );
    process.once("error", (e) => {
      clearTimeout(timer);
      reject(e);
    });
    process.once("exit", (code) => {
      clearTimeout(timer);
      reject(new Error(`Server exited ${code}: ${output}`));
    });
    process.stderr.on("data", (chunk) => {
      output += chunk;
      const match = output.match(/http:\/\/127\.0\.0\.1:\d+/);
      if (match) {
        clearTimeout(timer);
        resolve(match[0]);
      }
    });
  });
}
async function waitHeading(page, text) {
  await page.waitForFunction(
    (text) => document.querySelector(".panel-heading h2")?.textContent === text,
    text,
  );
}
async function submit(page, text) {
  await page.getByLabel("Your sentence", { exact: true }).fill(text);
  await page
    .getByRole("button", { name: "Analyze sentence", exact: true })
    .click();
}
try {
  const fixture = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict.json"), "utf8"),
  );
  const extra = JSON.parse(
    await readFile(
      resolve(root, "tests/fixtures/krdict-breakdown.json"),
      "utf8",
    ),
  );
  fixture.LexicalResource.Lexicon.LexicalEntry.push(
    ...extra.LexicalResource.Lexicon.LexicalEntry,
  );
  const input = resolve(scratch, "combined.json");
  await writeFile(input, JSON.stringify(fixture));
  execFileSync(cliBin, [
    "dict",
    "import-krdict",
    input,
    database,
    "--snapshot",
    "browser-tests",
  ]);
  const url = await start(true);
  const post = (path, body) =>
    fetch(`${url}/api/${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  const sample = "가까워 가가 xyz.\n";
  const apiResponse = await post("analyze", { text: sample });
  assert.equal(apiResponse.status, 200);
  const data = await apiResponse.json();
  const cli = execFileSync(cliBin, ["text", "-", "--dictionary", database], {
    input: sample,
    encoding: "utf8",
  })
    .trim()
    .split("\n")
    .map(JSON.parse);
  assert.deepEqual(
    data.records,
    cli,
    "HTTP results must equal the CLI including annotations and offsets",
  );
  assert.equal((await post("analyze", { text: "가".repeat(65) })).status, 422);
  assert.equal((await post("analyze", { text: "" })).status, 422);
  assert.equal(
    (await post("analyze", { text: "가 ".repeat(3000) })).status,
    422,
  );
  assert.equal(
    (await post("analyze", { text: "a".repeat(40000) })).status,
    413,
  );
  assert.equal(
    (await fetch(`${url}/api/analyze`, { method: "POST", body: "{}" })).status,
    415,
  );
  assert.equal(
    (
      await fetch(`${url}/api/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{",
      })
    ).status,
    400,
  );
  assert.equal((await post("entry", { id: "' OR 1=1 --" })).status, 404);
  const hostStatus = await new Promise((resolve, reject) => {
    const req = httpRequest(
      `${url}/api/status`,
      { headers: { Host: "malicious.example" } },
      (response) => {
        response.resume();
        resolve(response.statusCode);
      },
    );
    req.on("error", reject);
    req.end();
  });
  assert.equal(hostStatus, 403);
  assert.equal(
    (
      await fetch(`${url}/api/status`, {
        headers: { Origin: "https://malicious.example" },
      })
    ).status,
    403,
  );
  assert.equal((await fetch(`${url}/%2e%2e/Cargo.toml`)).status, 404);
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROMIUM_PATH,
    args: ["--no-sandbox"],
  });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1100 },
  });
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto(url);
  await page.waitForSelector(".reading");
  await submit(page, "저는 한국어를 공부해요.");
  await waitHeading(page, "저는");
  await page.getByLabel("Dictionary matches only").check();
  const breakdown = page.getByRole("region", {
    name: "Sentence breakdown",
    exact: true,
  });
  assert.deepEqual(await breakdown.locator(".part-form").allTextContents(), [
    "저",
    "는",
    "한국어",
    "를",
    "공부하",
    "여요",
  ]);
  assert.deepEqual(await breakdown.locator(".part-gloss").allTextContents(), [
    "I; me",
    "Topic / contrast",
    "Korean; Korean language",
    "Object marker",
    "study",
    "Polite informal",
  ]);
  assert.match(await breakdown.innerText(), /Expanded \/ normalized/);
  const selector = breakdown.getByRole("combobox").first();
  assert.equal(await selector.locator("option").count(), 2);
  await breakdown
    .getByRole("button", { name: "Show all combinations", exact: true })
    .click();
  assert.equal(await breakdown.locator(".combination-list li").count(), 2);
  await selector.selectOption({ label: "2. 절 + 는" });
  assert.deepEqual(
    await breakdown
      .locator(".breakdown-word")
      .first()
      .locator(".part-form")
      .allTextContents(),
    ["절", "는"],
  );
  assert.match(
    await breakdown.locator(".breakdown-word").first().innerText(),
    /Noun modifier/,
  );
  await breakdown
    .getByRole("button", { name: "Use this combination", exact: true })
    .first()
    .click();
  await breakdown.locator(".grammatical").first().click();
  await page.waitForFunction(() =>
    document.querySelector(".entry-meta")?.textContent?.includes("조사"),
  );
  await page.getByLabel("Dictionary matches only").uncheck();
  assert.match(await breakdown.innerText(), /More than 20/);
  assert.equal(await breakdown.locator(".combination-list li").count(), 0);
  const identity = await selector
    .locator("option")
    .evaluateAll(
      (options) => options.find((o) => o.textContent.endsWith(". 저는"))?.value,
    );
  assert.ok(identity);
  await selector.selectOption(identity);
  await page.getByLabel("Dictionary matches only").check();
  assert.equal(
    await selector.inputValue(),
    await selector.locator("option").first().getAttribute("value"),
    "Removed selections must fall back to a retained reading",
  );
  // Stable original indices survive filtering and align with the exported analyses.
  const exportedBreakdown = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export JSON" }).click();
  const exportedData = JSON.parse(
    await readFile(await (await exportedBreakdown).path(), "utf8"),
  );
  exportedData.records.forEach((token, i) => {
    assert.equal(
      exportedData.breakdowns[i]?.length ?? 0,
      token.analysis?.analyses.length ?? 0,
    );
    for (const [j, order] of (exportedData.breakdowns[i] ?? []).entries()) {
      const a = token.analysis.analyses[j];
      assert.equal(order.length, a.lemmas.length + a.morphemes.length);
      for (const part of order)
        assert.ok(
          "lemma" in part ? a.lemmas[part.lemma] : a.morphemes[part.morpheme],
        );
    }
  });
  await submit(page, "지식인들을");
  await waitHeading(page, "지식인들을");
  assert.deepEqual(await breakdown.locator(".part-form").allTextContents(), [
    "지식인",
    "들",
    "을",
  ]);
  assert.deepEqual(await breakdown.locator(".part-gloss").allTextContents(), [
    "intellectual",
    "Plural",
    "Object marker",
  ]);
  assert.equal(await page.locator(".candidate").count(), 1);
  await breakdown
    .getByRole("button", { name: "들 Plural", exact: true })
    .click();
  await page.waitForFunction(
    () =>
      document
        .querySelector(".entry-heading h2")
        ?.textContent?.startsWith("-들") &&
      document.querySelector(".entry-meta")?.textContent?.includes("접사"),
  );
  await page.getByLabel("Dictionary matches only").uncheck();
  await submit(page, sample);
  await waitHeading(page, "가까워");
  await page.waitForSelector(".entry-heading h2");
  assert.match(await page.locator(".entry-heading h2").innerText(), /가깝다/);
  const before = await page.locator(".candidate").count();
  await page.getByLabel("Dictionary matches only").check();
  assert.ok((await page.locator(".candidate").count()) < before);
  await page.getByRole("button", { name: "xyz", exact: true }).click();
  await waitHeading(page, "xyz");
  assert.equal(await page.locator(".candidate").count(), 0);
  assert.match(
    await page.locator(".no-matches").innerText(),
    /No matching readings/,
  );
  await page.getByLabel("Dictionary matches only").uncheck();
  assert.equal(await page.locator(".candidate").count(), 1);
  await page.getByRole("button", { name: "가가", exact: true }).click();
  await waitHeading(page, "가가");
  await page.getByLabel("Dictionary matches only").check();
  assert.ok(
    (await page
      .locator(".lemma-chain")
      .filter({ hasText: "Auxiliary" })
      .count()) > 0,
  );
  await page
    .locator(".entry-choices button")
    .filter({ hasText: "보조 동사" })
    .first()
    .click();
  await page.waitForFunction(() =>
    document.querySelector(".entry-meta")?.textContent?.includes("보조 동사"),
  );
  await page.locator(".trace summary").first().click();
  assert.ok((await page.locator(".trace[open] li").count()) > 0);
  const downloaded = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export JSON" }).click();
  const download = await downloaded;
  const exported = JSON.parse(await readFile(await download.path(), "utf8"));
  assert.equal(exported.records.map((r) => r.surface).join(""), sample);
  assert.deepEqual(
    exported.records.find((r) => r.surface === "xyz").analysis.analyses,
    [],
  );
  await submit(page, "가".repeat(65));
  await page.getByRole("alert").waitFor();
  assert.match(await page.getByRole("alert").innerText(), /word is too long/);
  await page.route(
    "**/api/analyze",
    (route) =>
      route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ error: "Test server failure" }),
      }),
    { times: 1 },
  );
  await submit(page, "가까워");
  await page.getByRole("alert").waitFor();
  assert.match(
    await page.getByRole("alert").innerText(),
    /Test server failure/,
  );
  await page
    .getByRole("button", { name: "Analyze sentence", exact: true })
    .click();
  await waitHeading(page, "가까워");
  await page.route(
    "**/api/analyze",
    async (route) => {
      await new Promise((r) => setTimeout(r, 300));
      await route.continue().catch(() => {});
    },
    { times: 1 },
  );
  await submit(page, "가다");
  await page.getByLabel("Your sentence", { exact: true }).fill("A new draft");
  await page.waitForTimeout(450);
  assert.equal(
    await page.locator(".reading").count(),
    0,
    "A stale response must not replace the current draft",
  );
  await submit(page, "가까워 가가 xyz.");
  await waitHeading(page, "가까워");
  await page.getByLabel("Dictionary matches only").check();
  await mkdir(resolve(root, "web/test-results"), { recursive: true });
  await page.screenshot({
    path: resolve(root, "web/test-results/desktop.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  assert.ok(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
    "Mobile must not overflow horizontally",
  );
  await page.screenshot({
    path: resolve(root, "web/test-results/mobile.png"),
    fullPage: true,
  });
  assert.deepEqual(errors, [], "Browser must not report runtime errors");
  const without = await start(false);
  await page.goto(without);
  await page.waitForSelector(".reading");
  assert.equal(
    await page.getByLabel("Dictionary matches only").isDisabled(),
    true,
  );
  assert.match(
    await page.locator(".notice").innerText(),
    /Dictionary not connected/,
  );
  await page.getByLabel("Your sentence", { exact: true }).fill("");
  assert.equal(
    await page
      .getByRole("button", { name: "Analyze sentence", exact: true })
      .isDisabled(),
    true,
  );
  console.log(
    "Browser and HTTP checks passed: candidate parity, filtering/grouping, definitions, export, errors, stale requests, mobile, and dictionary-free mode.",
  );
} finally {
  await browser?.close();
  await Promise.all(
    processes.map(
      (p) =>
        new Promise((resolve) => {
          if (p.exitCode !== null) return resolve();
          p.once("exit", resolve);
          p.kill();
        }),
    ),
  );
  await rm(scratch, { recursive: true, force: true });
}
