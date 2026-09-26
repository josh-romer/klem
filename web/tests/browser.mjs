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
  const negativeAuxiliaries = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-negative-auxiliaries.json"), "utf8"),
  );
  const grammarLabelSources = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-grammar-labels.json"), "utf8"),
  );
  const adverbRoots = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-adverb-roots.json"), "utf8"),
  );
  const hadaKi = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-hada-ki.json"), "utf8"),
  );
  const reporting = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-reporting.json"), "utf8"),
  );
  const copulaYo = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-copula-yo.json"), "utf8"),
  );
  const causal = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-causal.json"), "utf8"),
  );
  const quotedAlternatives = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-quoted-alternatives.json"), "utf8"),
  );
  const enumerativeParticles = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-enumerative-particles.json"), "utf8"),
  );
  const colloquialCopulas = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-colloquial-copulas.json"), "utf8"),
  );
  const emphaticParticles = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-emphatic-particles.json"), "utf8"),
  );
  const adverbExpansion = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-adverb-expansion.json"), "utf8"),
  );
  const negativeContractions = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-negative-contractions.json"), "utf8"),
  );
  fixture.LexicalResource.Lexicon.LexicalEntry.push(
    ...negativeContractions.LexicalResource.Lexicon.LexicalEntry,
  );
  const nominalCopulas = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-nominal-copulas.json"), "utf8"),
  );
  fixture.LexicalResource.Lexicon.LexicalEntry.push(
    ...nominalCopulas.LexicalResource.Lexicon.LexicalEntry,
  );
  const auxiliaryInventory = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-auxiliary-inventory.json"), "utf8"),
  );
  const particleChains = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-particle-chains.json"), "utf8"),
  );
  fixture.LexicalResource.Lexicon.LexicalEntry.push(
    ...particleChains.LexicalResource.Lexicon.LexicalEntry,
  );
  const postEndingParticles = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-post-ending-particles.json"), "utf8"),
  );
  fixture.LexicalResource.Lexicon.LexicalEntry.push(
    ...postEndingParticles.LexicalResource.Lexicon.LexicalEntry,
  );
  const quotedQuestions = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-quoted-questions.json"), "utf8"),
  );
  fixture.LexicalResource.Lexicon.LexicalEntry.push(
    ...quotedQuestions.LexicalResource.Lexicon.LexicalEntry,
  );
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
  // Keep existing, richer fixtures when supplemental inventories overlap.
  // Idioms and proverbs can share a source ID with their primary entry.
  const primaryIds = new Set(
    fixture.LexicalResource.Lexicon.LexicalEntry.filter((entry) => {
      const features = Array.isArray(entry.feat) ? entry.feat : [entry.feat];
      const unit = features.find((f) => f?.att === "lexicalUnit")?.val;
      return unit !== "관용구" && unit !== "속담";
    }).map((entry) => entry.val),
  );
  fixture.LexicalResource.Lexicon.LexicalEntry.push(
    ...[
      ...auxiliaryInventory.LexicalResource.Lexicon.LexicalEntry,
      ...adverbExpansion.LexicalResource.Lexicon.LexicalEntry,
      ...negativeAuxiliaries.LexicalResource.Lexicon.LexicalEntry,
      ...grammarLabelSources.LexicalResource.Lexicon.LexicalEntry,
      ...emphaticParticles.LexicalResource.Lexicon.LexicalEntry,
      ...colloquialCopulas.LexicalResource.Lexicon.LexicalEntry,
      ...adverbRoots.LexicalResource.Lexicon.LexicalEntry,
      ...hadaKi.LexicalResource.Lexicon.LexicalEntry,
      ...reporting.LexicalResource.Lexicon.LexicalEntry,
      ...copulaYo.LexicalResource.Lexicon.LexicalEntry,
      ...causal.LexicalResource.Lexicon.LexicalEntry,
      ...quotedAlternatives.LexicalResource.Lexicon.LexicalEntry,
      ...enumerativeParticles.LexicalResource.Lexicon.LexicalEntry,
    ].filter((entry) => {
      if (primaryIds.has(entry.val)) return false;
      primaryIds.add(entry.val);
      return true;
    }),
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
    ["강구키", ["강구하", "기"]],
    ["생각기", ["생각하", "기"]],
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
    if (word === "강구키") {
      await breakdown.getByRole("button", { name: "기 Nominalizer", exact: true }).click();
      await page.waitForFunction(() => document.querySelector('a[href*="ParaWordNo="]')?.getAttribute("href")?.includes("ParaWordNo=72222"));
    }
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
    ["조성키로", ["조성하", "기", "로"]],
    ["생각기에", ["생각하", "기", "에"]],
    ["돌변키도했다", ["돌변하", "기", "도", "하", "였", "다"]],
  ]) {
    await submit(page, word);
    await waitHeading(page, word);
    const choice = await breakdown.getByRole("combobox").locator("option").evaluateAll(
      (options, text) => options.find(o => o.textContent.replace(/^\d+\. /, "") === text)?.value,
      expected.join(" + "),
    );
    assert.ok(choice, word);
    await breakdown.getByRole("combobox").selectOption(choice);
    assert.deepEqual(await breakdown.locator(".part-form").allTextContents(), expected);
  }
  for (const [word, expected, form, label, id, kind = "ending"] of [
    ["학생이라든가", ["학생", "이라든가"], "이라든가", "Enumerative examples", 85861, "particle"],
    ["학교라든가", ["학교", "라든가"], "라든가", "Enumerative examples", 85861, "particle"],
    ["밥이라든지", ["밥", "이라든지"], "이라든지", "Enumerative examples", 86046, "particle"],
    ["학교에서라든지", ["학교", "에서", "라든지"], "라든지", "Enumerative examples", 86518, "particle"],
    ["학생이든가", ["학생", "이든가"], "이든가", "Any choice", 70330, "particle"],
    ["학교든가", ["학교", "든가"], "든가", "Any choice", 70330, "particle"],
    ["먹든가", ["먹", "든가"], "든가", "Choice / alternative", 82342],
    ["학생이든가", ["학생", "이", "든가"], "든가", "Choice / alternative", 82342],
    ["먹는다든가", ["먹", "는다", "든가"], "든가", "Any choice", 70330, "particle"],
    ["된다거나", ["되", "는다거나"], "는다거나", "Reported alternatives / examples", 86053],
    ["먹었다거나", ["먹", "었", "다거나"], "다거나", "Reported alternatives / examples", 86056],
    ["학생이라거나", ["학생", "이", "라거나"], "라거나", "Reported alternatives / examples", 86057],
    ["먹으라거나", ["먹", "으라거나"], "으라거나", "Reported alternatives / examples", 86332],
    ["먹자거나", ["먹", "자거나"], "자거나", "Reported alternatives / examples", 83892],
    ["경시한다든가", ["경시하", "는다든가"], "는다든가", "Reported alternatives / examples", 82119],
    ["세련되었다든가", ["세련되", "었", "다든가"], "다든가", "Reported alternatives / examples", 82121],
    ["학생이라든가", ["학생", "이", "라든가"], "라든가", "Reported alternatives / examples", 82122],
    ["추천하길래", ["추천하", "길래"], "길래", "Reason / basis", 73011],
    ["뽑길래", ["뽑", "길래"], "길래", "Reason / basis", 73011],
    ["먹기에", ["먹", "기에"], "기에", "Reason / basis", 84811],
    ["학생이기에", ["학생", "이", "기에"], "기에", "Reason / basis", 84811],
    ["넘었답니다", ["넘", "었", "답니다"], "답니다", "Polite information / report", 81393],
    ["산답니다", ["살", "는답니다"], "는답니다", "Polite information / report", 81389],
    ["먹는답니다", ["먹", "는답니다"], "는답니다", "Polite information / report", 81389],
    ["학생이랍니다", ["학생", "이", "랍니다"], "랍니다", "Polite information / report", 76427],
    ["의사랍니다", ["의사", "이", "랍니다"], "랍니다", "Polite information / report", 76427],
    ["먹었더랍니다", ["먹", "었", "더", "랍니다"], "랍니다", "Polite information / report", 76427],
    ["먹으랍니다", ["먹", "으랍니다"], "으랍니다", "Reported command / request", 81412],
    ["먹으시랍니다", ["먹", "시", "으랍니다"], "으랍니다", "Reported command / request", 81412],
    ["먹으시랍니다", ["먹", "시", "랍니다"], "랍니다", "Polite information / report", 76427],
  ]) {
    await submit(page, word);
    await waitHeading(page, word);
    const data = await (await post("analyze", {text: word})).json();
    const eligible = data.records[0].analysis.analyses.flatMap((a, index) =>
      a.morphemes.at(-1)?.kind === kind && a.morphemes.at(-1)?.form === form
        ? [String(index)] : []);
    const choice = await breakdown.getByRole("combobox").locator("option").evaluateAll(
      (options, {text, eligible}) => options.find(o =>
        o.textContent.replace(/^\d+\. /, "") === text && eligible.includes(o.value))?.value,
      {text: expected.join(" + "), eligible},
    );
    assert.ok(choice, word);
    await breakdown.getByRole("combobox").selectOption(choice);
    assert.deepEqual(await breakdown.locator(".part-form").allTextContents(), expected);
    await breakdown.getByRole("button", {name: `${form} ${label}`, exact: true}).click();
    await page.waitForFunction(id => document.querySelector('a[href*="ParaWordNo="]')?.getAttribute("href")?.includes(`ParaWordNo=${id}`), id);
    assert.ok(data.grammar[kind === "particle" ? form : `-${form}`].some(e => e.id === `krdict:${id}`));
    if (form === "기에") {
      const nominal = expected.slice(0, -1).concat(["기", "에"]);
      const alternate = await breakdown.getByRole("combobox").locator("option").evaluateAll(
        (options, text) => options.find(o => o.textContent.replace(/^\d+\. /, "") === text)?.value,
        nominal.join(" + "),
      );
      assert.ok(alternate, word);
      await breakdown.getByRole("combobox").selectOption(alternate);
      assert.deepEqual(await breakdown.locator(".part-form").allTextContents(), nominal);
    }
    if (form === "는답니다") {
      assert.ok(data.grammar["-는답니다"].some(e => e.id === "krdict:81377"));
      assert.ok(data.grammar["-는답니다"].some(e => e.id === "krdict:86633"));
    }
  }
  for (const [word, expected] of [
    ["연장이요", ["연장", "이", "요"]],
    ["자화상이요", ["자화상", "이", "요"]],
    ["아비요", ["아비", "이", "요"]],
    ["아니요", ["아니", "요"]],
  ]) {
    await submit(page, word);
    await waitHeading(page, word);
    const data = await (await post("analyze", {text: word})).json();
    const choices = await breakdown.getByRole("combobox").locator("option").evaluateAll(
      options => options.map(o => ({value:o.value, text:o.textContent.replace(/^\d+\. /, "")})),
    );
    const choice = choices.find(o => o.text === expected.join(" + ") &&
      data.records[0].analysis.analyses[Number(o.value)].morphemes.some(m => m.form === "요" && m.kind === "ending"))?.value;
    assert.ok(choice, word);
    await breakdown.getByRole("combobox").selectOption(choice);
    assert.deepEqual(await breakdown.locator(".part-form").allTextContents(), expected);
    await breakdown.getByRole("button", {name:"요 And / in contrast (copula)", exact:true}).click();
    await page.waitForFunction(() => document.querySelector('a[href*="ParaWordNo="]')?.getAttribute("href")?.includes("ParaWordNo=86117"));
    assert.ok(data.grammar["-요"].some(e => e.id === "krdict:86117" && e.pos === "어미"));
    assert.ok(!data.grammar["요"].some(e => e.id === "krdict:86117"));
    if (word === "아비요") {
      const polite = choices.find(o => o.text === "아비 + 요" && data.records[0].analysis.analyses[Number(o.value)].morphemes[0].kind === "particle");
      assert.ok(polite);await breakdown.getByRole("combobox").selectOption(polite.value);
      assert.deepEqual(await breakdown.locator(".part-form").allTextContents(), ["아비", "요"]);
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
    ["아니냐는", ["아니", "냐는"], "냐는", "Quoted question", 86030],
    ["했느냐는", ["하", "였", "느냐는"], "느냐는", "Quoted question", 86031],
    ["먹으시겠냐는", ["먹", "시", "겠", "냐는"], "냐는", "Quoted question", 86030],
    ["먹어봤느냐는", ["먹", "어", "보", "었", "느냐는"], "느냐는", "Quoted question", 86031],
    ["좋으냐는", ["좋", "으냐는"], "으냐는", "Quoted question", 86032],
    ["추우냐는", ["춥", "으냐는"], "으냐는", "Quoted question", 86032],
    ["파라냐는", ["파랗", "으냐는"], "으냐는", "Quoted question", 86032],
    ["먹더냐는", ["먹", "더", "냐는"], "냐는", "Quoted question", 86030],
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
  for (const [word, expected, form, label, id] of [
    ["있습니다만", ["있", "습니다", "만"], "만", "But / although", 86555],
    ["먹는다마는", ["먹", "는다", "마는"], "마는", "But / although", 86552],
    ["하면서도", ["하", "으면서", "도"], "도", "Also / even", 86258],
    ["먹고는", ["먹", "고", "는"], "는", "Topic / contrast", 85851],
    ["학생만", ["학생", "만"], "만", "Only / emphasis", 86554],
    ["어디까지나", ["어디", "까지", "나"], "나", "Choice / emphasis", 89218],
    ["이제부터라도", ["이제", "부터", "라도"], "라도", "At least / even", 78508],
    ["학생만이라도", ["학생", "만", "이라도"], "이라도", "At least / even", 78504],
    ["학교에서든지", ["학교", "에서", "든지"], "든지", "Any choice", 70334],
    ["사회주의라고", ["사회주의", "라고"], "라고", "Quotation / emphasis", 70074],
    ["학생이라고", ["학생", "이라고"], "이라고", "Quotation / emphasis", 70075],
  ]) {
    await submit(page, word);
    await waitHeading(page, word);
    assert.deepEqual(await breakdown.locator(".part-form").allTextContents(), expected);
    await breakdown.getByRole("button", { name: `${form} ${label}`, exact: true }).click();
    await page.waitForFunction(id => document.querySelector('a[href*="ParaWordNo="]')?.getAttribute('href')?.includes(`ParaWordNo=${id}`), id);
    assert.match(await page.getByRole("link", { name: "Open original dictionary entry" }).getAttribute("href"), new RegExp(`ParaWordNo=${id}`));
  }
  for (const [word, expected] of [
    ["먹을만하다", ["먹", "을", "만하", "다"]],
    ["먹는듯하다", ["먹", "는", "듯하", "다"]],
    ["먹고계셨다", ["먹", "고", "계시", "었", "다"]],
    ["먹어들봐요", ["먹", "어", "들", "보", "어요"]],
    ["먹고야말았다", ["먹", "고", "야", "말", "었", "다"]],
    ["먹곤했다", ["먹", "고", "는", "하", "였", "다"]],
  ]) {
    await submit(page, word);
    await waitHeading(page, word);
    assert.deepEqual(await breakdown.locator(".part-form").allTextContents(), expected);
    if (word === "먹어들봐요") {
      await breakdown.getByRole("button", { name: "들 Plural subjects", exact: true }).click();
      await page.waitForFunction(() => document.querySelector('a[href*="ParaWordNo="]')?.getAttribute('href')?.includes('ParaWordNo=86264'));
    }
    if (word === "먹을만하다") {
      await breakdown.getByRole("button", { name: "을 Prospective noun modifier", exact: true }).click();
      await page.waitForFunction(() => document.querySelector('a[href*="ParaWordNo="]')?.getAttribute('href')?.includes('ParaWordNo=69058'));
    }
  }
  for (const [word, expected] of [
    ["먹지마라", ["먹", "지", "말", "어라"]],
    ["먹지마요", ["먹", "지", "말", "어요"]],
    ["먹지는않았다", ["먹", "지", "는", "않", "었", "다"]],
    ["먹진않았다", ["먹", "지", "는", "않", "었", "다"]],
    ["먹어보진마요", ["먹", "어", "보", "지", "는", "말", "어요"]],
  ]) {
    await submit(page, word);
    await waitHeading(page, word);
    const choice = await breakdown.getByRole("combobox").locator("option").evaluateAll(
      (options, text) => options.find(o => o.textContent.replace(/^\d+\. /, "") === text)?.value,
      expected.join(" + "),
    );
    assert.ok(choice, word);
    await breakdown.getByRole("combobox").selectOption(choice);
    assert.deepEqual(await breakdown.locator(".part-form").allTextContents(), expected);
    if (word === "먹지마라") {
      await breakdown.getByRole("button", {name: "어라 Command / exclamation", exact: true}).click();
      await page.waitForFunction(() => document.querySelector('a[href*="ParaWordNo="]')?.getAttribute('href')?.includes("ParaWordNo=80682"));
    }
    if (word === "먹진않았다") {
      await breakdown.getByRole("button", {name: "는 Topic / contrast", exact: true}).click();
      await page.waitForFunction(() => document.querySelector('a[href*="ParaWordNo="]')?.getAttribute('href')?.includes("ParaWordNo=85851"));
    }
  }
  // Unknown pronunciation is visible on a selected reading and survives export.
  await page.getByLabel("Dictionary matches only").uncheck();
  for (const [word, expected, condition] of [
    ["ABC는", ["ABC", "는"], "vowel"],
    ["3은", ["3", "은"], "consonant"],
    ["3으로는", ["3", "으로", "는"], "non_rieul_consonant"],
    ["1로", ["1", "로"], "vowel_or_rieul"],
    ["café는", ["café", "는"], "vowel"],
    ["ABC예요", ["ABC", "이", "에요"], "vowel"],
    ["ABC였다", ["ABC", "이", "었", "다"], "vowel"],
    ["ABC이었다", ["ABC", "이", "었", "다"], null],
    ["김민수는", ["김민수", "는"], null],
    ["ABC에는", ["ABC", "에", "는"], null],
  ]) {
    await submit(page, word);
    await waitHeading(page, word);
    const selector = breakdown.getByRole("combobox");
    const choice = await selector.locator("option").evaluateAll(
      (options, text) => options.find(o => o.textContent.replace(/^\d+\. /, "") === text)?.value,
      expected.join(" + "),
    );
    assert.ok(choice, word);
    await selector.selectOption(choice);
    assert.deepEqual(await breakdown.locator(".part-form").allTextContents(), expected);
    const data = await (await post("analyze", {text: word})).json();
    const a = data.records[0].analysis.analyses[Number(choice)];
    const rules = a.rules.filter(r => r.startsWith("pronunciation.assumed_"));
    assert.deepEqual(rules, condition ? [`pronunciation.assumed_${condition}`] : []);
    assert.deepEqual(await breakdown.locator(".reading-condition").allTextContents(), rules.map(r => data.rules[r]));
  }
  await submit(page, "ABC는");
  await waitHeading(page, "ABC는");
  const foreignDownload = page.waitForEvent("download");
  await page.getByRole("button", {name: "Export JSON", exact: true}).click();
  const foreignExport = JSON.parse(await readFile(await (await foreignDownload).path(), "utf8"));
  assert.ok(foreignExport.records[0].analysis.analyses.some(a => a.rules.includes("pronunciation.assumed_vowel")));
  assert.match(foreignExport.rules["pronunciation.assumed_vowel"], /pronunciation is not inferred/);
  await page.getByLabel("Dictionary matches only").check();
  assert.match(await breakdown.innerText(), /No matching reading/);
  assert.match(await breakdown.innerText(), /ABC는/);
  assert.equal(await breakdown.locator(".reading-condition").count(), 0);

  // Missing labels, expression POS, component links, and normalized spellings.
  for (const [word, expected, form, label, id, key] of [
    ["먹습니다", ["먹", "습니다"], "습니다", "Formal polite statement", 79398, "-습니다"],
    ["먹네요", ["먹", "네요"], "네요", "Realization / seeking agreement (polite)", 85934, "-네요"],
    ["먹는가요", ["먹", "는가요"], "는가요", "Question / wondering (polite)", 89045, "-는가요"],
    ["먹기가", ["먹", "기가"], "기가", "Nominalizer + subject marker", 72222, "-기가"],
    ["먹는데다가", ["먹", "는데다가"], "는데다가", "In addition", 72714, "-는데다가"],
    ["먹어야죠", ["먹", "어야죠"], "어야죠", "Determination / obligation (polite)", 86245, "-어야죠"],
    ["학교까지", ["학교", "까지"], "까지", "Until / as far as / even", 69698, "까지"],
    ["먹읍시다", ["먹", "읍시다"], "읍시다", "Let's (polite)", 68880, "-읍시다"],
    ["갑시다", ["가", "읍시다"], "읍시다", "Let's (polite)", 68880, "-읍시다"],
    ["먹더냐는", ["먹", "더", "냐는"], "더", "Recalled experience", 85794, "-더-"],
    ["먹으리라고", ["먹", "으리라고"], "으리라고", "Reported intention / expectation", 85920, "-으리라고"],
    ["먹었으리라고", ["먹", "었", "으리라고"], "으리라고", "Reported intention / expectation", 85920, "-으리라고"],
    ["먹을지라도", ["먹", "을지라도"], "을지라도", "Even if / although", 77049, "-을지라도"],
    ["먹어볼지라도", ["먹", "어", "보", "을지라도"], "을지라도", "Even if / although", 77049, "-을지라도"],
    ["먹자면", ["먹", "자면"], "자면", "If intending / if proposing", 80338, "-자면"],
    ["먹어보자면", ["먹", "어", "보", "자면"], "자면", "If intending / if proposing", 80338, "-자면"],
    ["학교야말로", ["학교", "야말로"], "야말로", "Indeed / precisely", 86102, "야말로"],
    ["학생이야말로", ["학생", "이야말로"], "이야말로", "Indeed / precisely", 86103, "이야말로"],
    ["잠시나마", ["잠시", "나마"], "나마", "At least / even if limited", 70309, "나마"],
    ["조금이나마", ["조금", "이나마"], "이나마", "At least / even if limited", 70312, "이나마"],
    ["학교에서나마", ["학교", "에서", "나마"], "나마", "At least / even if limited", 70309, "나마"],
    ["사과는커녕", ["사과", "는커녕"], "는커녕", "Far from / let alone", 70316, "는커녕"],
    ["먹긴커녕", ["먹", "기", "는커녕"], "는커녕", "Far from / let alone", 70316, "는커녕"],
    ["학생은커녕", ["학생", "은커녕"], "은커녕", "Far from / let alone", 70317, "은커녕"],
    ["밥커녕", ["밥", "커녕"], "커녕", "Far from / let alone", 86168, "커녕"],
    ["서울서", ["서울", "서"], "서", "Action location / from / subject emphasis", 86712, "서"],
    ["작으나마", ["작", "으나마"], "으나마", "Although limited", 80164, "-으나마"],
    ["조금이나마", ["조금", "이", "으나마"], "으나마", "Although limited", 80164, "-으나마"],
    ["학교란", ["학교", "란"], "란", "As for / defining", 85858, "란"],
    ["학생이란", ["학생", "이란"], "이란", "As for / defining", 85859, "이란"],
    ["학교란", ["학교", "이", "란"], "란", "Quoted fact (noun-modifying)", 86297, "-란"],
    ["학생이란", ["학생", "이", "란"], "란", "Quoted fact (noun-modifying)", 86297, "-란"],
    ["먹으란", ["먹", "으란"], "으란", "Quoted command (noun-modifying)", 89676, "-으란"],
    ["먹어보란", ["먹", "어", "보", "으란"], "으란", "Quoted command (noun-modifying)", 89676, "-으란"],
    ["먹었더란", ["먹", "었", "더", "란"], "란", "Quoted fact (noun-modifying)", 86297, "-란"],
    ["작으리란", ["작", "으리", "란"], "으리", "Conjecture / intention", 86606, "-으리-"],
    ["겁니다", ["거", "이", "습니다"], "습니다", "Formal polite statement", 79398, "-습니다"],
    ["겁니다", ["것", "이", "습니다"], "습니다", "Formal polite statement", 79398, "-습니다"],
    ["건데", ["것", "이", "은데"], "은데", "Background / contrast / response", 85633, "-은데"],
    ["거죠", ["것", "이", "죠"], "죠", "Confirmation / question / suggestion", 85771, "-죠"],
    ["그건데", ["그것", "이", "은데"], "은데", "Background / contrast / response", 85633, "-은데"],
    ["의삽니다", ["의사", "이", "습니다"], "습니다", "Formal polite statement", 79398, "-습니다"],
    ["먹더라는", ["먹", "더라는"], "더라는", "Quoted experience (noun-modifying)", 86347, "-더라는"],
    ["먹어봤더라는", ["먹", "어", "보", "었", "더라는"], "더라는", "Quoted experience (noun-modifying)", 86347, "-더라는"],
    ["학생답더라는", ["학생", "답", "더라는"], "더라는", "Quoted experience (noun-modifying)", 86347, "-더라는"],
    ["먹었더라", ["먹", "었", "더", "라"], "더", "Recalled experience", 85794, "-더-"],
    ["먹었더라", ["먹", "었", "더라"], "더라", "Recalled experience", 81524, "-더라"],
    ["먹으리라", ["먹", "으리", "라"], "으리", "Conjecture / intention", 86606, "-으리-"],
    ["먹어야겠네요", ["먹", "어야겠", "네요"], "어야겠", "Intention / necessity", 86239, "-어야겠-"],
    ["피해야겠다", ["피하", "여야겠", "다"], "여야겠", "Intention / necessity", 86239, "-어야겠-"],
    ["먹어봐야겠다", ["먹", "어", "보", "어야겠", "다"], "어야겠", "Intention / necessity", 86239, "-어야겠-"],
    ["학생이어야겠다", ["학생", "이", "어야겠", "다"], "어야겠", "Intention / necessity", 86239, "-어야겠-"],
    ["학교여야겠다", ["학교", "이", "어야겠", "다"], "어야겠", "Intention / necessity", 86239, "-어야겠-"],
    ["학생다워야겠다", ["학생", "답", "어야겠", "다"], "어야겠", "Intention / necessity", 86239, "-어야겠-"],
    ["먹으셔야겠다", ["먹", "시", "어야겠", "다"], "어야겠", "Intention / necessity", 86239, "-어야겠-"],
    ["먹었어야겠다", ["먹", "었", "어야겠", "다"], "어야겠", "Intention / necessity", 86239, "-어야겠-"],
    ["작아야겠다", ["작", "어야겠", "다"], "어야겠", "Intention / necessity", 86239, "-어야겠-"],
  ]) {
    await submit(page, word);
    await waitHeading(page, word);
    const selector = breakdown.getByRole("combobox");
    if (await selector.count()) {
      const choice = await selector.locator("option").evaluateAll(
        (options, text) => options.find(o => o.textContent.replace(/^\d+\. /, "") === text)?.value,
        expected.join(" + "),
      );
      assert.ok(choice, word);
      await selector.selectOption(choice);
    }
    assert.deepEqual(await breakdown.locator(".part-form").allTextContents(), expected);
    await breakdown.getByRole("button", { name: `${form} ${label}`, exact: true }).click();
    await page.waitForFunction(id => document.querySelector('a[href*="ParaWordNo="]')?.getAttribute('href')?.includes(`ParaWordNo=${id}`), id);
    const result = await (await post("analyze", {text: word})).json();
    assert.ok(result.grammar[key].some(e => e.id === `krdict:${id}`), key);
    // Grammar lookup enriches the response without replacing rule candidates.
    const cli = JSON.parse(execFileSync(cliBin, ["word", word], {encoding: "utf8"}));
    assert.deepEqual(result.records[0].analysis.analyses, cli.analyses);
  }
  for (const [word, lemmas, forbidden] of [
    ["먹었더라", ["먹다"], ["었", "더", "어라"]],
    ["먹었더라", ["먹다"], ["었", "더", "으라"]],
    ["먹더라는", ["먹다"], ["더", "으라는"]],
    ["학생이라고", ["학생", "이다"], ["으라고"]],
    ["먹었으세요", ["먹다"], ["었", "으세요"]],
  ]) {
    const data = await (await post("analyze", {text: word})).json();
    assert.ok(!data.records[0].analysis.analyses.some(a =>
      JSON.stringify(a.lemmas.map(l => l.text)) === JSON.stringify(lemmas) &&
      JSON.stringify(a.morphemes.map(m => m.form)) === JSON.stringify(forbidden)), word);
  }
  for (const word of ["이라는", "라는"]) {
    await submit(page, word);
    await waitHeading(page, word);
    const data = await (await post("analyze", {text: word})).json();
    const index = data.records[0].analysis.analyses.findIndex(a =>
      a.lemmas.length === 1 && a.lemmas[0].text === "이다" && a.lemmas[0].kind === "copula" &&
      a.morphemes.length === 1 && a.morphemes[0].form === "라는");
    assert.ok(index >= 0, word);
    await breakdown.getByRole("combobox").selectOption(String(index));
    assert.deepEqual(await breakdown.locator(".part-form").allTextContents(), ["이", "라는"]);
    const notes = await breakdown.locator(".reading-condition").allTextContents();
    assert.deepEqual(notes, word === "라는" ? [data.rules["copula.omitted_fragment"]] : []);
    if (word === "라는") {
      assert.match(await breakdown.innerText(), /Expanded \/ normalized/);
      assert.match(notes[0], /preceding quoted material/);
    }
    await breakdown.getByRole("button", {name: "라는 Quoted noun modifier", exact: true}).click();
    await page.waitForFunction(() => document.querySelector('a[href*="ParaWordNo="]')?.getAttribute("href")?.includes("ParaWordNo=82217"));
    const cli = JSON.parse(execFileSync(cliBin, ["word", word], {encoding: "utf8"}));
    assert.deepEqual(data.records[0].analysis.analyses, cli.analyses);
  }
  const fragmentDownload = page.waitForEvent("download");
  await page.getByRole("button", {name: "Export JSON", exact: true}).click();
  const fragmentExport = JSON.parse(await readFile(await (await fragmentDownload).path(), "utf8"));
  assert.ok(fragmentExport.records[0].analysis.analyses.some(a => a.rules.includes("copula.omitted_fragment")));
  assert.match(fragmentExport.rules["copula.omitted_fragment"], /preceding quoted material/);
  const limitedReadings = await (await post("analyze", {text: "조금이나마"})).json();
  assert.ok(!limitedReadings.records[0].analysis.analyses.some(a =>
    a.lemmas.length === 1 && a.lemmas[0].text === "조금" &&
    JSON.stringify(a.morphemes.map(m => m.form)) === JSON.stringify(["이", "나마"])),
    "나마 does not attach to a subject-marked phrase");
  for (const [word, expected] of [
    ["먹고싶은", ["먹", "고", "싶", "은"]],
    ["먹을만한", ["먹", "을", "만하", "은"]],
    ["먹고싶지는않은", ["먹", "고", "싶", "지", "는", "않", "은"]],
    ["먹고싶어하는", ["먹", "고", "싶", "어", "하", "는"]],
    ["먹고싶어해요", ["먹", "고", "싶", "어", "하", "여요"]],
    ["학생다워해요", ["학생", "답", "어", "하", "여요"]],
  ]) {
    await submit(page, word);
    await waitHeading(page, word);
    const selector = breakdown.getByRole("combobox");
    if (await selector.count()) {
      const choice = await selector.locator("option").evaluateAll(
        (options, text) => options.find(o => o.textContent.replace(/^\d+\. /, "") === text)?.value,
        expected.join(" + "),
      );
      assert.ok(choice, word);
      await selector.selectOption(choice);
    }
    assert.deepEqual(await breakdown.locator(".part-form").allTextContents(), expected);
  }
  for (const [word, forbidden] of [
    ["먹어없다", ["먹다", "없다"]],
    ["먹고싶는다", ["먹다", "싶다"]],
    ["먹을만하는", ["먹다", "만하다"]],
    ["먹고싶지않는", ["먹다", "싶다", "않다"]],
    ["먹고싶잖는", ["먹다", "싶다", "않다"]],
    ["학생인듯하는", ["학생", "이다", "듯하다"]],
    ["먹어봐해요", ["먹다", "보다", "하다"]],
    ["먹고있어해요", ["먹다", "있다", "하다"]],
    ["학생이어해요", ["학생", "이다", "하다"]],
    ["먹기이어해요", ["먹다", "이다", "하다"]],
    ["먹어보지않아해요", ["먹다", "보다", "않다", "하다"]],
    ["먹고싶으신다거나", ["먹다", "싶다"]],
    ["학생이신다든가", ["학생", "이다"]],
    ["먹고싶자면", ["먹다", "싶다"]],
    ["학생이자면", ["학생", "이다"]],
  ]) {
    const data = await (await post("analyze", {text: word})).json();
    const candidates = data.records[0].analysis.analyses;
    assert.ok(!candidates.some(a => JSON.stringify(a.lemmas.map(l => l.text)) === JSON.stringify(forbidden)), word);
    assert.ok(candidates.some(a => a.unchanged), `${word}: preserve the original word`);
  }
  for (const [word, expected, form, id] of [
    ["더욱이", ["더욱", "이"], "이", 88927],
    ["곰곰이", ["곰곰", "이"], "이", 88927],
    ["낱낱이", ["낱낱", "이"], "이", 88927],
    ["집집이", ["집집", "이"], "이", 88927],
    ["가만히", ["가만", "히"], "히", 88504],
    ["특히", ["특별", "히"], "히", 88504],
    ["익히", ["익숙", "히"], "히", 88504],
    ["가까이", ["가깝", "이"], "이", 88927],
    ["적잖이", ["적잖", "이"], "이", 88927],
    ["깨끗이", ["깨끗", "이"], "이", 88927],
    ["조용히", ["조용", "히"], "히", 88504],
    ["다분히", ["다분", "히"], "히", 88504],
  ]) {
    await submit(page, word);
    await waitHeading(page, word);
    // A dictionary adverb remains the compact initial reading.
    assert.deepEqual(await breakdown.locator(".part-form").allTextContents(), [word]);
    const api = await (await post("analyze", {text: word})).json();
    // Nominal + subject 이 and nominal + adverbial suffix 이 can have
    // identical component text. Select the suffix role by its API index.
    const choices = await breakdown.getByRole("combobox").locator("option").evaluateAll(
      options => options.map(o => ({value:o.value, text:o.textContent.replace(/^\d+\. /, "")})),
    );
    const choice = choices.find(o => o.text === expected.join(" + ") &&
      api.records[0].analysis.analyses[Number(o.value)].morphemes.some(m => m.kind === "suffix" && m.form === form))?.value;
    assert.ok(choice, word);
    await breakdown.getByRole("combobox").selectOption(choice);
    assert.deepEqual(await breakdown.locator(".part-form").allTextContents(), expected);
    await breakdown.getByRole("button", {name: `${form} Adverb-forming suffix`, exact: true}).click();
    await page.waitForFunction(id => document.querySelector('a[href*="ParaWordNo="]')?.getAttribute('href')?.includes(`ParaWordNo=${id}`), id);
    const response = await (await post("analyze", {text: word})).json();
    const key = `-${form}`;
    assert.ok(response.grammar[key].some(e => e.id === `krdict:${id}`));
  }
  for (const [word, expected] of [
    ["적잖은", ["적", "지", "않", "은"]],
    ["만만찮았다", ["만만하", "지", "않", "었", "다"]],
    ["먹고싶잖다", ["먹", "고", "싶", "지", "않", "다"]],
    ["먹잖아요", ["먹", "지", "않", "어요"]],
  ]) {
    await submit(page, word);
    await waitHeading(page, word);
    const choice = await breakdown.getByRole("combobox").locator("option").evaluateAll(
      (options, text) => options.find(o => o.textContent.replace(/^\d+\. /, "") === text)?.value,
      expected.join(" + "),
    );
    assert.ok(choice, word);
    await breakdown.getByRole("combobox").selectOption(choice);
    assert.deepEqual(await breakdown.locator(".part-form").allTextContents(), expected);
    assert.match(await breakdown.innerText(), /Expanded \/ normalized/);
  }
  for (const [word, expected, form, label, id] of [
    ["먹잖아", ["먹", "잖아"], "잖아", "Confirming / correcting", 86756],
    ["먹잖아요", ["먹", "잖아요"], "잖아요", "Confirming / correcting (polite)", 86757],
    ["학생이잖아요", ["학생", "이", "잖아요"], "잖아요", "Confirming / correcting (polite)", 86757],
  ]) {
    await submit(page, word);
    await waitHeading(page, word);
    assert.deepEqual(await breakdown.locator(".part-form").allTextContents(), expected);
    await breakdown.getByRole("button", {name: `${form} ${label}`, exact: true}).click();
    await page.waitForFunction(id => document.querySelector('a[href*="ParaWordNo="]')?.getAttribute('href')?.includes(`ParaWordNo=${id}`), id);
  }
  for (const [word, expected] of [
    ["학생다움이다", ["학생", "답", "음", "이", "다"]],
    ["학생다움이에요", ["학생", "답", "음", "이", "에요"]],
    ["먹기다", ["먹", "기", "이", "다"]],
    ["먹기예요", ["먹", "기", "이", "에요"]],
    ["먹어보기였다", ["먹", "어", "보", "기", "이", "었", "다"]],
  ]) {
    await submit(page, word);
    await waitHeading(page, word);
    const choice = await breakdown.getByRole("combobox").locator("option").evaluateAll(
      (options, text) => options.find(o => o.textContent.replace(/^\d+\. /, "") === text)?.value,
      expected.join(" + "),
    );
    assert.ok(choice, word);
    await breakdown.getByRole("combobox").selectOption(choice);
    assert.deepEqual(await breakdown.locator(".part-form").allTextContents(), expected);
    const form = word.startsWith("학생") ? "음" : "기";
    const id = form === "음" ? 78528 : 72222;
    await breakdown.getByRole("button", { name: `${form} Nominalizer`, exact: true }).click();
    await page.waitForFunction(id => document.querySelector('a[href*="ParaWordNo="]')?.getAttribute('href')?.includes(`ParaWordNo=${id}`), id);
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
