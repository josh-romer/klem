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
  const particles = JSON.parse(
    await readFile(
      resolve(root, "tests/fixtures/krdict-particles.json"),
      "utf8",
    ),
  );
  fixture.LexicalResource.Lexicon.LexicalEntry.push(
    ...particles.LexicalResource.Lexicon.LexicalEntry,
  );
  const derivation = JSON.parse(
    await readFile(
      resolve(root, "tests/fixtures/krdict-derivation.json"),
      "utf8",
    ),
  );
  fixture.LexicalResource.Lexicon.LexicalEntry.push(
    ...derivation.LexicalResource.Lexicon.LexicalEntry,
  );
  const hada = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-hada.json"), "utf8"),
  );
  fixture.LexicalResource.Lexicon.LexicalEntry.push(
    ...hada.LexicalResource.Lexicon.LexicalEntry,
  );
  const adverbs = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-adverbs.json"), "utf8"),
  );
  fixture.LexicalResource.Lexicon.LexicalEntry.push(
    ...adverbs.LexicalResource.Lexicon.LexicalEntry,
  );
  const input = resolve(scratch, "combined.json");
  const daga = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-daga.json"), "utf8"),
  );
  fixture.LexicalResource.Lexicon.LexicalEntry.push(
    ...daga.LexicalResource.Lexicon.LexicalEntry,
  );
  const adnominal = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-adnominal.json"), "utf8"),
  );
  fixture.LexicalResource.Lexicon.LexicalEntry.push(
    ...adnominal.LexicalResource.Lexicon.LexicalEntry,
  );
  const conditional = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-conditional.json"), "utf8"),
  );
  fixture.LexicalResource.Lexicon.LexicalEntry.push(
    ...conditional.LexicalResource.Lexicon.LexicalEntry,
  );
  const comparative = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-comparative.json"), "utf8"),
  );
  fixture.LexicalResource.Lexicon.LexicalEntry.push(
    ...comparative.LexicalResource.Lexicon.LexicalEntry,
  );
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
  assert.equal(await breakdown.locator(".combination-list li").count(), 4);
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
  for (const [word, expected] of [
    ["학교에선", ["학교", "에서", "는"]],
    ["선생님께선", ["선생님", "께서", "는"]],
    ["저도요", ["저", "도", "요"]],
    ["친구는요", ["친구", "는", "요"]],
    ["이건요", ["이거", "는", "요"]],
    ["빨리들", ["빨리", "들"]],
    ["먹어들", ["먹", "어", "들"]],
  ]) {
    await submit(page, word);
    await waitHeading(page, word);
    assert.deepEqual(
      await breakdown.locator(".part-form").allTextContents(),
      expected,
      word,
    );
    assert.equal(await breakdown.locator(".breakdown-unavailable").count(), 0);
    if (word === "빨리들") {
      assert.match(await breakdown.innerText(), /Plural subjects/);
      await breakdown
        .getByRole("button", { name: "들 Plural subjects", exact: true })
        .click();
      await page.waitForFunction(
        () =>
          document
            .querySelector(".entry-heading h2")
            ?.textContent?.startsWith("들") &&
          document.querySelector(".entry-meta")?.textContent?.includes("조사"),
      );
    }
    if (word === "이건요") {
      const full = await breakdown
        .getByRole("combobox")
        .locator("option")
        .evaluateAll(
          (options) =>
            options.find((o) => o.textContent.includes("이것 + 은 + 요"))
              ?.value,
        );
      assert.ok(full);
      await breakdown.getByRole("combobox").selectOption(full);
      assert.deepEqual(
        await breakdown.locator(".part-form").allTextContents(),
        ["이것", "은", "요"],
      );
    }
  }
  for (const [word, expanded, displayed, suffix, label] of [
    ["선생님께", "선생 + 님 + 께", ["선생", "님", "께"], "님", "Honorific"],
    [
      "과학적이다",
      "과학 + 적 + 이 + 다",
      ["과학", "적", "이", "다"],
      "적",
      "Relating to / having a quality",
    ],
    [
      "학생다워요",
      "학생 + 답 + 어요",
      ["학생", "답", "어요"],
      "답다",
      "Characteristic of",
    ],
  ]) {
    await submit(page, word);
    await waitHeading(page, word);
    if (word === "선생님께") {
      assert.deepEqual(
        await breakdown.locator(".part-form").allTextContents(),
        ["선생님", "께"],
      );
    }
    if (word === "과학적이다") {
      assert.deepEqual(
        await breakdown.locator(".part-form").allTextContents(),
        ["과학적", "이", "다"],
      );
    }
    const choice = await breakdown
      .getByRole("combobox")
      .locator("option")
      .evaluateAll(
        (options, expanded) =>
          options.find((o) => o.textContent.includes(expanded))?.value,
        expanded,
      );
    assert.ok(choice, `${word}: missing ${expanded}`);
    await breakdown.getByRole("combobox").selectOption(choice);
    assert.deepEqual(
      await breakdown.locator(".part-form").allTextContents(),
      displayed,
    );
    await breakdown
      .getByRole("button", {
        name: `${suffix === "답다" ? "답" : suffix} ${label}`,
        exact: true,
      })
      .click();
    await page.waitForFunction(
      (suffix) =>
        document
          .querySelector(".entry-heading h2")
          ?.textContent?.startsWith(`-${suffix}`) &&
        document.querySelector(".entry-meta")?.textContent?.includes("접사"),
      suffix,
    );
    const response = await post("analyze", { text: word });
    const result = await response.json();
    assert.ok(result.grammar[`-${suffix}`].some((e) => e.pos === "접사"));
    assert.ok(
      result.records[0].analysis.analyses.some(
        (a) =>
          a.lemmas[0].kind === "nominal" &&
          a.morphemes.some((m) => m.kind === "suffix" && m.form === suffix),
      ),
    );
  }
  for (const [word, expected] of [
    ["생각지", ["생각하", "지"]],
    ["생각건대", ["생각하", "건대"]],
    ["비유컨대", ["비유하", "건대"]],
    ["피케", ["피하", "게"]],
    ["깨끗지", ["깨끗하", "지"]],
  ]) {
    await submit(page, word);
    await waitHeading(page, word);
    assert.deepEqual(
      await breakdown.locator(".part-form").allTextContents(),
      expected,
    );
    assert.match(await breakdown.innerText(), /Expanded \/ normalized/);
    if (word === "비유컨대") {
      await breakdown
        .getByRole("button", {
          name: "건대 Introducing a thought / wish",
          exact: true,
        })
        .click();
      await page.waitForFunction(
        () =>
          document
            .querySelector(".entry-heading h2")
            ?.textContent?.startsWith("-건대") &&
          document.querySelector(".entry-meta")?.textContent?.includes("어미"),
      );
    }
  }
  for (const [word, expected] of [
    ["같이", ["같", "이"]],
    ["없이", ["없", "이"]],
    ["달리", ["다르", "이"]],
    ["빨리", ["빠르", "이"]],
  ]) {
    await submit(page, word);
    await waitHeading(page, word);
    assert.deepEqual(await breakdown.locator(".part-form").allTextContents(), [
      word,
    ]);
    const choice = await breakdown
      .getByRole("combobox")
      .locator("option")
      .evaluateAll(
        (options, title) =>
          options.find((o) => o.textContent.includes(title))?.value,
        expected.join(" + "),
      );
    assert.ok(choice, word);
    await breakdown.getByRole("combobox").selectOption(choice);
    assert.deepEqual(
      await breakdown.locator(".part-form").allTextContents(),
      expected,
    );
    if (word === "달리")
      assert.match(await breakdown.innerText(), /Expanded \/ normalized/);
    await breakdown
      .getByRole("button", { name: "이 Adverb-forming suffix", exact: true })
      .click();
    await page.waitForFunction(
      () =>
        document
          .querySelector(".entry-heading h2")
          ?.textContent?.startsWith("-이") &&
        document.querySelector(".entry-meta")?.textContent?.includes("접사"),
    );
    const link = page.getByRole("link", {
      name: "Open original dictionary entry",
    });
    assert.match(await link.getAttribute("href"), /ParaWordNo=88927/);
    const result = await (await post("analyze", { text: word })).json();
    assert.ok(result.grammar["-이"].some((e) => e.id === "krdict:88927"));
    assert.ok(result.grammar["-이"].some((e) => e.id === "krdict:88924"));
    assert.ok(result.grammar["-이"].every((e) => e.pos === "접사"));
  }
  for (const [word, ending, id] of [
    ["보듯", "듯", 80280],
    ["보듯이", "듯이", 80282],
  ]) {
    await submit(page, word);
    await waitHeading(page, word);
    assert.deepEqual(await breakdown.locator(".part-form").allTextContents(), ["보", ending]);
    await breakdown.getByRole("button", { name: `${ending} As / like`, exact: true }).click();
    await page.waitForFunction(
      (headword) => document.querySelector(".entry-heading h2")?.textContent?.startsWith(headword)
        && document.querySelector(".entry-meta")?.textContent?.includes("어미"),
      `-${ending}`,
    );
    assert.match(
      await page.getByRole("link", { name: "Open original dictionary entry" }).getAttribute("href"),
      new RegExp(`ParaWordNo=${id}`),
    );
  }
  for (const [word, expected] of [
    ["한다면", ["하", "는다면"]],
    ["먹는다면", ["먹", "는다면"]],
    ["먹으신다면", ["먹", "시", "는다면"]],
  ]) {
    await submit(page, word);
    await waitHeading(page, word);
    assert.deepEqual(await breakdown.locator(".part-form").allTextContents(), expected);
    if (word === "한다면") assert.match(await breakdown.innerText(), /Expanded \/ normalized/);
    await breakdown.getByRole("button", { name: "는다면 If / supposing", exact: true }).click();
    await page.waitForFunction(() =>
      document.querySelector(".entry-heading h2")?.textContent?.startsWith("-는다면")
      && document.querySelector(".entry-meta")?.textContent?.includes("어미"),
    );
    assert.match(
      await page.getByRole("link", { name: "Open original dictionary entry" }).getAttribute("href"),
      /ParaWordNo=68738/,
    );
    const result = await (await post("analyze", { text: word })).json();
    assert.ok(result.grammar["-는다면"].some((e) => e.id === "krdict:68738"));
    assert.ok(result.grammar["-는다면"].every((e) => e.pos === "어미"));
  }
  for (const [word, expected, form, label, id] of [
    ["먹으려는", ["먹", "으려는"], "으려는", "Intending / about to", 86717],
    ["살려는", ["살", "으려는"], "으려는", "Intending / about to", 86717],
    ["먹으시려는", ["먹", "시", "으려는"], "으려는", "Intending / about to", 86717],
    ["먹자는", ["먹", "자는"], "자는", "Quoted suggestion", 83896],
    ["먹어보자는", ["먹", "어", "보", "자는"], "자는", "Quoted suggestion", 83896],
  ]) {
    await submit(page, word);
    await waitHeading(page, word);
    assert.deepEqual(await breakdown.locator(".part-form").allTextContents(), expected);
    if (word === "살려는") assert.match(await breakdown.innerText(), /Expanded \/ normalized/);
    await breakdown.getByRole("button", { name: `${form} ${label}`, exact: true }).click();
    await page.waitForFunction((headword) =>
      document.querySelector(".entry-heading h2")?.textContent?.startsWith(headword)
      && document.querySelector(".entry-meta")?.textContent?.includes("품사 없음"),
      `-${form}`,
    );
    assert.match(
      await page.getByRole("link", { name: "Open original dictionary entry" }).getAttribute("href"),
      new RegExp(`ParaWordNo=${id}`),
    );
    const result = await (await post("analyze", { text: word })).json();
    assert.deepEqual(result.grammar[`-${form}`].map((e) => e.id), [`krdict:${id}`]);
  }
  for (const [word, expected] of [
    ["먹다가", ["먹", "다가"]],
    ["갔다가", ["가", "었", "다가"]],
    ["먹으셨다가", ["먹", "시", "었", "다가"]],
  ]) {
    await submit(page, word);
    await waitHeading(page, word);
    assert.deepEqual(await breakdown.locator(".part-form").allTextContents(), expected);
    await breakdown.getByRole("button", { name: "다가 While / then", exact: true }).click();
    await page.waitForFunction(() =>
      document.querySelector(".entry-heading h2")?.textContent?.startsWith("-다가")
      && document.querySelector(".entry-meta")?.textContent?.includes("어미"),
    );
    assert.match(await page.getByRole("link", { name: "Open original dictionary entry" }).getAttribute("href"), /ParaWordNo=85740/);
  }
  await submit(page, "가다가");
  await waitHeading(page, "가다가");
  for (const [form, label, id] of [
    ["다가", "While / then", 85740],
    ["어다가", "Then / using the result", 86099],
  ]) {
    const choice = await breakdown.getByRole("combobox").locator("option").evaluateAll(
      (options, title) => options.find((o) => o.textContent.includes(title))?.value,
      `가 + ${form}`,
    );
    assert.ok(choice, form);
    await breakdown.getByRole("combobox").selectOption(choice);
    assert.deepEqual(await breakdown.locator(".part-form").allTextContents(), ["가", form]);
    await breakdown.getByRole("button", { name: `${form} ${label}`, exact: true }).click();
    await page.waitForFunction((headword) => document.querySelector(".entry-heading h2")?.textContent?.startsWith(headword), `-${form}`);
    assert.match(await page.getByRole("link", { name: "Open original dictionary entry" }).getAttribute("href"), new RegExp(`ParaWordNo=${id}`));
  }
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
