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
  const grammarLabels = JSON.parse(await readFile(resolve(root, "web/src/grammar-labels.json"), "utf8"));
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
  const ryeona = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-ryeona.json"), "utf8"));
  const attachmentConnectives = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-attachment-connectives.json"), "utf8"));
  const resultConnectives = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-result-connectives.json"), "utf8"));
  const intentionConnectives = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-intention-connectives.json"), "utf8"));
  const uncertainty = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-uncertainty.json"), "utf8"));
  const adjectivalQuestion = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-adjectival-question.json"), "utf8"));
  const continuativeTopic = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-continuative-topic.json"), "utf8"));
  const adverbFocus = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-adverb-focus.json"), "utf8"));
  const attachments = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-attachments.json"), "utf8"));
  const shortClauses = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-short-clauses.json"), "utf8"));
  const reportNi = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-report-ni.json"), "utf8"));
  const presentLicenses = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-present-licenses.json"), "utf8"));
  const stativeReport = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-stative-report.json"), "utf8"));
  const reportMyeo = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-report-myeo.json"), "utf8"));
  const approximation = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-approximation.json"), "utf8"));
  const extent = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-extent.json"), "utf8"));
  const rangeCase = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-range-case.json"), "utf8"));
  const chigo = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-chigo.json"), "utf8"));
  const doe = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-doe.json"), "utf8"));
  const reportNe = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-report-ne.json"), "utf8"),
  );
  const nohContraction = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-noh-contraction.json"), "utf8"),
  );
  const questionCopulas = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-question-copulas.json"), "utf8"),
  );
  const prefinalCopulas = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-prefinal-copulas.json"), "utf8"),
  );
  const seoConnectives = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-seo-connectives.json"), "utf8"),
  );
  const honorificCopulas = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-honorific-copulas.json"), "utf8"),
  );
  const omittedConnectives = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-omitted-connectives.json"), "utf8"),
  );
  const enumerativeDa = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-enumerative-da.json"), "utf8"),
  );
  const destinationParticles = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-destination-particles.json"), "utf8"),
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
  const auxiliaryClasses = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-auxiliary-dictionary.json"), "utf8"),
  );
  const shortRecipient = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-short-recipient.json"), "utf8"),
  );
  const expressiveHada = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-expressive-hada.json"), "utf8"));
  const additiveParticles = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-additive-particles.json"), "utf8"));
  const quotedBakke = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-quoted-bakke.json"), "utf8"));
  const necessity = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-necessity.json"), "utf8"));
  const llachimyeon = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-llachimyeon.json"), "utf8"));
  const comparisonCase = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-comparison-case.json"), "utf8"));
  const comparisonParticles = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-comparison-particles.json"), "utf8"));
  const hadaComplex = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-hada-complex.json"), "utf8"));
  const adverbCopulas = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-adverb-copulas.json"), "utf8"));
  const connectiveCopulas = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-connective-copulas.json"), "utf8"));
  const concessiveEndings = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-concessive-endings.json"), "utf8"));
  const concessiveDesignation = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-concessive-designation.json"), "utf8"));
  const sourceParticles = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-source-particles.json"), "utf8"));
  const coreCase = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-core-case.json"), "utf8"));
  const kkaena = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-kkaena.json"), "utf8"));
  const raConditions = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-ra-conditions.json"), "utf8"));
  const eya = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-eya.json"), "utf8"));
  const vocative = JSON.parse(await readFile(resolve(root, "tests/fixtures/krdict-vocative.json"), "utf8"));
  const nira = JSON.parse(
    await readFile(resolve(root, "tests/fixtures/krdict-nira.json"), "utf8"),
  );
  fixture.LexicalResource.Lexicon.LexicalEntry.push(
    ...[
      ...expressiveHada.LexicalResource.Lexicon.LexicalEntry,
      ...hadaComplex.LexicalResource.Lexicon.LexicalEntry,
      ...quotedBakke.LexicalResource.Lexicon.LexicalEntry,
      ...necessity.LexicalResource.Lexicon.LexicalEntry,
      ...llachimyeon.LexicalResource.Lexicon.LexicalEntry,
      ...comparisonCase.LexicalResource.Lexicon.LexicalEntry,
      ...comparisonParticles.LexicalResource.Lexicon.LexicalEntry,
      ...additiveParticles.LexicalResource.Lexicon.LexicalEntry,
      ...adverbCopulas.LexicalResource.Lexicon.LexicalEntry,
      ...connectiveCopulas.LexicalResource.Lexicon.LexicalEntry,
      ...concessiveEndings.LexicalResource.Lexicon.LexicalEntry,
      ...concessiveDesignation.LexicalResource.Lexicon.LexicalEntry,
      ...sourceParticles.LexicalResource.Lexicon.LexicalEntry,
      ...coreCase.LexicalResource.Lexicon.LexicalEntry,
      ...kkaena.LexicalResource.Lexicon.LexicalEntry,
      ...raConditions.LexicalResource.Lexicon.LexicalEntry,
      ...eya.LexicalResource.Lexicon.LexicalEntry,
      ...vocative.LexicalResource.Lexicon.LexicalEntry,
      ...nira.LexicalResource.Lexicon.LexicalEntry,
      ...shortRecipient.LexicalResource.Lexicon.LexicalEntry,
      ...auxiliaryClasses.LexicalResource.Lexicon.LexicalEntry,
      ...ryeona.LexicalResource.Lexicon.LexicalEntry,
      ...attachmentConnectives.LexicalResource.Lexicon.LexicalEntry,
      ...resultConnectives.LexicalResource.Lexicon.LexicalEntry,
      ...intentionConnectives.LexicalResource.Lexicon.LexicalEntry,
      ...uncertainty.LexicalResource.Lexicon.LexicalEntry,
      ...adjectivalQuestion.LexicalResource.Lexicon.LexicalEntry,
      ...continuativeTopic.LexicalResource.Lexicon.LexicalEntry,
      ...adverbFocus.LexicalResource.Lexicon.LexicalEntry,
      ...attachments.LexicalResource.Lexicon.LexicalEntry,
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
      ...destinationParticles.LexicalResource.Lexicon.LexicalEntry,
      ...enumerativeDa.LexicalResource.Lexicon.LexicalEntry,
      ...omittedConnectives.LexicalResource.Lexicon.LexicalEntry,
      ...honorificCopulas.LexicalResource.Lexicon.LexicalEntry,
      ...seoConnectives.LexicalResource.Lexicon.LexicalEntry,
      ...prefinalCopulas.LexicalResource.Lexicon.LexicalEntry,
      ...questionCopulas.LexicalResource.Lexicon.LexicalEntry,
      ...nohContraction.LexicalResource.Lexicon.LexicalEntry,
      ...reportNe.LexicalResource.Lexicon.LexicalEntry,
      ...doe.LexicalResource.Lexicon.LexicalEntry,
      ...chigo.LexicalResource.Lexicon.LexicalEntry,
      ...rangeCase.LexicalResource.Lexicon.LexicalEntry,
      ...extent.LexicalResource.Lexicon.LexicalEntry,
      ...approximation.LexicalResource.Lexicon.LexicalEntry,
      ...presentLicenses.LexicalResource.Lexicon.LexicalEntry,
      ...reportNi.LexicalResource.Lexicon.LexicalEntry,
      ...shortClauses.LexicalResource.Lexicon.LexicalEntry,
      ...stativeReport.LexicalResource.Lexicon.LexicalEntry,
      ...reportMyeo.LexicalResource.Lexicon.LexicalEntry,
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
  // Keep the homonymous noun suffix in the database so the later -단 ending
  // source exclusion actually exercises POS filtering.
  const danEntries = JSON.parse(execFileSync(cliBin, ["dict", "lookup", database, "-단"], {encoding: "utf8"})).entries;
  assert.ok(danEntries.some(e => e.id === "krdict:73350" && e.pos === "접사"));
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
  assert.equal(await page.getByLabel("Exclude known grammar conflicts").isDisabled(), true);
  const attachmentText = "가늘다니 가는다니 길으냐니 아니라니 늦으냐니 큰다니 가늘어한다니 싶었다 xyz.\n";
  await submit(page, attachmentText);
  await waitHeading(page, "가늘다니");
  await page.getByLabel("Dictionary matches only").check();
  const attachmentRaw = await (await post("analyze", { text: attachmentText })).json();
  await page.getByLabel("Exclude known grammar conflicts").check();
  const expectedAttachment = execFileSync(cliBin, ["text", "-", "--dictionary", database, "--dict-compatible"], {
    input: attachmentText, encoding: "utf8",
  }).trim().split("\n").map(JSON.parse);
  const attachmentKey = (a) => JSON.stringify([a.lemmas.map((l) => [l.text, l.kind]), a.morphemes.map((m) => [m.form, m.kind]), a.rules, a.unchanged]);
  const words = expectedAttachment.filter((r) => r.kind === "word");
  for (const [i, word] of words.entries()) {
    const block = page.locator(".breakdown-word").nth(i);
    const options = block.locator("select option");
    if (!word.analysis.analyses.length) {
      assert.equal(await block.locator("select").isDisabled(), true);
    } else {
      assert.equal(await options.count(), word.analysis.analyses.length);
      const raw = attachmentRaw.records.find((r) => r.surface === word.surface);
      const expected = raw.analysis.analyses.flatMap((a, j) =>
        word.analysis.analyses.some((b) => attachmentKey(a) === attachmentKey(b)) ? [String(j)] : []);
      assert.deepEqual(await options.evaluateAll((items) => items.map((o) => o.value)), expected);
    }
  }
  // This question must use the adjective 늦다 entry, not its verb homonym.
  const late = page.locator(".breakdown-word").nth(4);
  assert.equal(await late.locator(".part-gloss").first().innerText(), attachmentRaw.glosses["krdict:64526"]);
  assert.ok(attachmentRaw.glosses["krdict:62657"]);
  assert.equal(await page.locator(".breakdown-word").nth(7).locator(".part-gloss").first().innerText(), attachmentRaw.glosses["krdict:62657"]);
  await late.locator(".breakdown-part").first().click();
  await page.waitForFunction(() => document.querySelector('a[href*="ParaWordNo=64526"]'));
  assert.match(await page.getByRole("link", { name: "Open original dictionary entry" }).getAttribute("href"), /ParaWordNo=64526/);
  const attachmentDownload = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export JSON" }).click();
  const attachmentExport = JSON.parse(await readFile(await (await attachmentDownload).path(), "utf8"));
  assert.deepEqual(attachmentExport.records, expectedAttachment);
  for (const [i, record] of attachmentExport.records.entries()) {
    if (!record.analysis) continue;
    assert.equal(attachmentExport.breakdowns[i].length, record.analysis.analyses.length);
    record.analysis.analyses.forEach((a, j) => {
      const originalIndex = attachmentRaw.records[i].analysis.analyses.findIndex((b) => attachmentKey(a) === attachmentKey(b));
      assert.deepEqual(attachmentExport.breakdowns[i][j], attachmentRaw.breakdowns[i][originalIndex]);
    });
  }
  await page.screenshot({ path: resolve(tmpdir(), "klem-attachments-desktop.png"), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  await page.screenshot({ path: resolve(tmpdir(), "klem-attachments-mobile.png"), fullPage: true });
  await page.setViewportSize({ width: 1440, height: 1100 });
  await page.getByLabel("Dictionary matches only").uncheck();
  assert.equal(await page.getByLabel("Exclude known grammar conflicts").isChecked(), false);
  assert.equal(await page.getByLabel("Exclude known grammar conflicts").isDisabled(), true);
  // The finite lexical check shares the reviewed intention/result families.
  const connectiveLedger = JSON.parse(await readFile(resolve(root, "tests/fixtures/dictionary-attachments.json"), "utf8"));
  const connectiveCases = connectiveLedger.cases.filter(c => c.id.startsWith("attachment-connectives-"));
  assert.equal(connectiveCases.length, 122);
  for (const c of connectiveCases) {
    const data = await (await post("analyze", {text: c.surface})).json();
    const token = data.records[0];
    for (const j of c.judgments) {
      const matches = a => JSON.stringify(a.lemmas.map(l => l.text)) === JSON.stringify(j.lemmas)
        && JSON.stringify(a.lemmas.map(l => l.kind)) === JSON.stringify(j.lemma_kinds)
        && JSON.stringify(a.morphemes.map(m => m.form)) === JSON.stringify(j.morphemes)
        && JSON.stringify(a.morphemes.map(m => m.kind)) === JSON.stringify(j.morpheme_kinds);
      const index = token.analysis.analyses.findIndex(matches);
      assert(index >= 0, `${c.id}: retain raw hypothesis`);
      assert.equal(token.dictionary.readings[index].status === "incompatible", j.verdict === "forbidden", c.id);
    }
  }
  const connectiveText = "크려는 좋으려다가 커다 좋아해다주었다";
  await submit(page, connectiveText);
  await waitHeading(page, "크려는");
  await page.getByLabel("Dictionary matches only").check();
  assert(await page.locator(".breakdown-word").nth(1).locator("option").count() > 0);
  await page.getByLabel("Exclude known grammar conflicts").check();
  assert(await page.locator(".breakdown-word").nth(1).locator("select").isDisabled());
  const connectiveData = await (await post("analyze", {text: connectiveText})).json();
  const connectiveExpected = execFileSync(cliBin, ["text", "-", "--dictionary", database, "--dict-compatible"], {input: connectiveText, encoding: "utf8"}).trim().split("\n").map(JSON.parse);
  for (const [i, expected] of [[0, ["크", "으려는"]], [2, ["크", "어다"]], [3, ["좋", "어", "하", "여다", "주", "었", "다"]]]) {
    const word = page.locator(".breakdown-word").nth(i), select = word.locator("select");
    const choice = await select.locator("option").evaluateAll((options, parts) => options.find(o => o.textContent.replace(/^\d+\. /, "") === parts.join(" + "))?.value, expected);
    assert.ok(choice, expected.join(" + "));
    await select.selectOption(choice);
    assert.deepEqual(await word.locator(".part-form").allTextContents(), expected);
    if (i !== 3) assert.equal(await word.locator(".part-gloss").first().innerText(), connectiveData.glosses["krdict:66584"]);
  }
  const connectiveDownload = page.waitForEvent("download");
  await page.getByRole("button", {name: "Export JSON", exact: true}).click();
  const connectiveExport = JSON.parse(await readFile(await (await connectiveDownload).path(), "utf8"));
  assert.deepEqual(connectiveExport.records, connectiveExpected);
  await page.locator(".breakdown-word").first().locator(".breakdown-part").nth(1).click();
  await page.locator(".entry-choices button").filter({hasText: "-려는"}).click();
  await page.waitForFunction(() => document.querySelector('a[href*="ParaWordNo=86688"]'));
  await page.getByLabel("Dictionary matches only").uncheck();
  // A connector's known auxiliary class selects its supported homonym hint.
  // The same headword can have different evidence in two slots of one reading.
  const auxiliaryLedger = JSON.parse(await readFile(resolve(root, "tests/fixtures/auxiliary-dictionary.json"), "utf8"));
  const auxiliaryPath = (a, c) => JSON.stringify(a.lemmas.map(l => [l.text, l.kind])) === JSON.stringify(c.lemmas.map(l => [l.text, l.kind]))
    && JSON.stringify(a.morphemes.map(m => [m.form, m.kind])) === JSON.stringify(c.morphemes.map(m => [m.form, m.kind]));
  for (const c of auxiliaryLedger.cases) {
    const data = await (await post("analyze", {text: c.surface})).json();
    const token = data.records[0];
    const index = token.analysis.analyses.findIndex(a => auxiliaryPath(a, c));
    assert(index >= 0, c.id);
    for (const j of c.judgments) {
      const e = token.dictionary.readings[index].lemmas[j.lemma_index].entries.find(e => e.id === j.entry_id);
      assert.equal(e.status, j.status, `${c.id}: ${j.entry_id}`);
      assert.deepEqual(e.conflicts, j.conflicts, c.id);
    }
  }
  const auxiliaryText = "오려나봐 먹어봐 먹어보나보다 먹고싶지않다";
  await submit(page, auxiliaryText);
  await waitHeading(page, "오려나봐");
  await page.getByLabel("Dictionary matches only").check();
  await page.getByLabel("Exclude known grammar conflicts").check();
  const auxiliaryData = await (await post("analyze", {text: auxiliaryText})).json();
  const auxiliaryWordIndices = auxiliaryData.records.flatMap((r, i) => r.analysis ? [i] : []);
  for (const [i, caseId, slot, entryId] of [
    [0, "aux-class-inference", 1, "krdict:62249"],
    [1, "aux-class-trial", 1, "krdict:62171"],
    [2, "aux-class-same-lemma-trial", 1, "krdict:62171"],
    [2, "aux-class-same-lemma-inference", 2, "krdict:62249"],
    [3, "aux-class-negative-adjective-71583", 2, "krdict:71583"],
  ]) {
    const c = auxiliaryLedger.cases.find(c => c.id === caseId);
    const recordIndex = auxiliaryWordIndices[i];
    const index = auxiliaryData.records[recordIndex].analysis.analyses.findIndex(a => auxiliaryPath(a, c));
    const word = page.locator(".breakdown-word").nth(i);
    await word.locator("select").selectOption(String(index));
    const position = auxiliaryData.breakdowns[recordIndex][index].findIndex(p => p.lemma === slot);
    assert.equal(await word.locator(".part-gloss").nth(position).innerText(), auxiliaryData.glosses[entryId]);
    await word.locator(".breakdown-part").nth(position).click();
    await page.waitForFunction(id => document.querySelector(`a[href*="ParaWordNo=${id}"]`), entryId.split(":")[1]);
  }
  const auxiliaryDownload = page.waitForEvent("download");
  await page.getByRole("button", {name: "Export JSON", exact: true}).click();
  const auxiliaryExport = JSON.parse(await readFile(await (await auxiliaryDownload).path(), "utf8"));
  const auxiliaryExpected = execFileSync(cliBin, ["text", "-", "--dictionary", database, "--dict-compatible"], {input: auxiliaryText, encoding: "utf8"}).trim().split("\n").map(JSON.parse);
  assert.deepEqual(auxiliaryExport.records, auxiliaryExpected);
  await page.screenshot({path: resolve(tmpdir(), "klem-auxiliary-classes-desktop.png"), fullPage: true});
  await page.setViewportSize({width: 390, height: 844});
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  await page.screenshot({path: resolve(tmpdir(), "klem-auxiliary-classes-mobile.png"), fullPage: true});
  await page.setViewportSize({width: 1440, height: 1100});
  await page.getByLabel("Dictionary matches only").uncheck();
  // Independent 게/게서 particles preserve 내/네/제 and their grammar homonyms.
  const recipientLedger = JSON.parse(await readFile(resolve(root, "tests/fixtures/validity.json"), "utf8"));
  const recipientCases = recipientLedger.cases.filter(c => c.id.startsWith("short-recipient-"));
  assert.equal(recipientCases.length, 93);
  for (const c of recipientCases) {
    const data = await (await post("analyze", {text: c.surface})).json(), token = data.records[0];
    for (const j of c.judgments) {
      const match = a => JSON.stringify(a.lemmas.map(l => l.text)) === JSON.stringify(j.lemmas)
        && JSON.stringify(a.lemmas.map(l => l.kind)) === JSON.stringify(j.lemma_kinds)
        && JSON.stringify(a.morphemes.map(m => m.form)) === JSON.stringify(j.morphemes)
        && JSON.stringify(a.morphemes.map(m => m.kind)) === JSON.stringify(j.morpheme_kinds);
      const index = token.analysis.analyses.findIndex(match);
      assert.equal(index >= 0, j.verdict === "required", c.id);
      if (index >= 0) assert.notEqual(token.dictionary.readings[index].status, "incompatible", c.id);
    }
  }
  const recipientText = "내겐 네게서도 제게다가 먹게";
  await submit(page, recipientText);
  await waitHeading(page, "내겐");
  await page.getByLabel("Dictionary matches only").check();
  await page.getByLabel("Exclude known grammar conflicts").check();
  for (const [i, expected, sourceId] of [[0, ["내", "게", "는"], 66937], [1, ["네", "게서", "도"], 66974], [2, ["제", "게", "다가"], 66937]]) {
    const word = page.locator(".breakdown-word").nth(i), select = word.locator("select");
    const value = await select.locator("option").evaluateAll((os, forms) => os.find(o => o.textContent.replace(/^\d+\. /, "") === forms.join(" + "))?.value, expected);
    assert.ok(value, expected.join(" + ")); await select.selectOption(value);
    assert.deepEqual(await word.locator(".part-form").allTextContents(), expected);
    await word.locator(".breakdown-part").nth(1).click();
    await page.waitForFunction(id => document.querySelector(`a[href*="ParaWordNo=${id}"]`), sourceId);
  }
  const recipientDownload = page.waitForEvent("download");
  await page.getByRole("button", {name: "Export JSON", exact: true}).click();
  const recipientExport = JSON.parse(await readFile(await (await recipientDownload).path(), "utf8"));
  const recipientExpected = execFileSync(cliBin, ["text", "-", "--dictionary", database, "--dict-compatible"], {input: recipientText, encoding: "utf8"}).trim().split("\n").map(JSON.parse);
  assert.deepEqual(recipientExport.records, recipientExpected);
  await page.screenshot({path: resolve(tmpdir(), "klem-short-recipient-desktop.png"), fullPage: true});
  await page.setViewportSize({width: 390, height: 844});
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  await page.screenshot({path: resolve(tmpdir(), "klem-short-recipient-mobile.png"), fullPage: true});
  await page.setViewportSize({width: 1440, height: 1100});
  await page.getByLabel("Dictionary matches only").uncheck();
  const adverbCopulaCases = recipientLedger.cases.filter(c => c.id.startsWith("adverb-copula-"));
  assert.equal(adverbCopulaCases.length, 72);
  for (const c of adverbCopulaCases) {
    const token = (await (await post("analyze", {text:c.surface})).json()).records[0];
    for (const j of c.judgments) {
      const index = token.analysis.analyses.findIndex(a => JSON.stringify(a.lemmas.map(l => l.text)) === JSON.stringify(j.lemmas)
        && JSON.stringify(a.lemmas.map(l => l.kind)) === JSON.stringify(j.lemma_kinds)
        && JSON.stringify(a.morphemes.map(m => m.form)) === JSON.stringify(j.morphemes)
        && JSON.stringify(a.morphemes.map(m => m.kind)) === JSON.stringify(j.morpheme_kinds));
      assert.equal(index >= 0, j.verdict === "required", c.id);
      if (index >= 0) assert.notEqual(token.dictionary.readings[index].status, "incompatible", c.id);
    }
  }
  const adverbCopulaText = "제법이다 들쑥날쑥이다 별로였어요 딱입니다 왜냐고 먼저니 그럭저럭이다";
  const adverbCopulaTokens = (await (await post("analyze", {text:adverbCopulaText})).json()).records.filter(r => r.kind === "word");
  await submit(page, adverbCopulaText); await waitHeading(page, "제법이다");
  await page.getByLabel("Dictionary matches only").check();
  await page.getByLabel("Exclude known grammar conflicts").check();
  for (const [i, forms] of [[0,["제법","이","다"]],[1,["들쑥날쑥","이","다"]],[2,["별로","이","었","어요"]],[3,["딱","이","습니다"]],[4,["왜","이","냐고"]],[5,["먼저","이","니"]],[6,["그럭저럭","이","다"]]]) {
    const word = page.locator(".breakdown-word").nth(i), select = word.locator("select");
    const adverbIndices = adverbCopulaTokens[i].analysis.analyses.flatMap((a, index) => a.lemmas[0].kind === "adverbial" ? [index] : []);
    const value = await select.locator("option").evaluateAll((os, {forms, adverbIndices}) => os.find(o => adverbIndices.includes(Number(o.value)) && o.textContent.replace(/^\d+\. /, "") === forms.join(" + "))?.value, {forms, adverbIndices});
    assert.ok(value, JSON.stringify({i,forms,options:await select.locator("option").allTextContents()}));
    await select.selectOption(value); assert.deepEqual(await word.locator(".part-form").allTextContents(), forms);
  }
  await page.locator(".breakdown-word").first().locator(".breakdown-part").first().click();
  await page.waitForFunction(() => document.querySelector('a[href*="ParaWordNo=31789"]'));
  const adverbCopulaDownload = page.waitForEvent("download");
  await page.getByRole("button", {name:"Export JSON",exact:true}).click();
  const adverbCopulaExport = JSON.parse(await readFile(await (await adverbCopulaDownload).path(), "utf8"));
  const adverbCopulaExpected = execFileSync(cliBin, ["text","-","--dictionary",database,"--dict-compatible"], {input:adverbCopulaText,encoding:"utf8"}).trim().split("\n").map(JSON.parse);
  assert.deepEqual(adverbCopulaExport.records, adverbCopulaExpected);
  assert.ok(adverbCopulaExport.records[0].analysis.analyses.some(a => a.rules.includes("copula.adverbial_base")));
  await page.screenshot({path:resolve(tmpdir(),"klem-adverb-copulas-desktop.png"),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  await page.screenshot({path:resolve(tmpdir(),"klem-adverb-copulas-mobile.png"),fullPage:true});
  await page.setViewportSize({width:1440,height:1100});
  await page.getByLabel("Dictionary matches only").uncheck();
  const additiveParticleCases = recipientLedger.cases.filter(c => c.id.startsWith("additive-"));
  assert.equal(additiveParticleCases.length, 50);
  for (const c of additiveParticleCases) {
    const token = (await (await post("analyze", {text:c.surface})).json()).records[0];
    for (const j of c.judgments) {
      const index = token.analysis.analyses.findIndex(a => JSON.stringify(a.lemmas.map(l => l.text)) === JSON.stringify(j.lemmas)
        && JSON.stringify(a.lemmas.map(l => l.kind)) === JSON.stringify(j.lemma_kinds)
        && JSON.stringify(a.morphemes.map(m => m.form)) === JSON.stringify(j.morphemes)
        && JSON.stringify(a.morphemes.map(m => m.kind)) === JSON.stringify(j.morpheme_kinds));
      assert.equal(index >= 0, j.verdict === "required", c.id);
      if (index >= 0) assert.notEqual(token.dictionary.readings[index].status, "incompatible", c.id);
    }
  }
  const additiveParticleText = "대해서조차 거룩하게조차 대해서마저 천천히조차 생사조차를 통신마저가 어린이까지마저";
  await submit(page, additiveParticleText); await waitHeading(page, "대해서조차");
  await page.getByLabel("Dictionary matches only").check();
  await page.getByLabel("Exclude known grammar conflicts").check();
  for (const [i, forms] of [[0,["대하","여서","조차"]],[1,["거룩하","게","조차"]],[2,["대하","여서","마저"]],[3,["천천히","조차"]],[4,["생사","조차","를"]],[5,["통신","마저","가"]],[6,["어린이","까지","마저"]]]) {
    const word = page.locator(".breakdown-word").nth(i), select = word.locator("select");
    const value = await select.locator("option").evaluateAll((os, forms) => os.find(o => o.textContent.replace(/^\d+\. /, "") === forms.join(" + "))?.value, forms);
    assert.ok(value, JSON.stringify({i,forms,options:await select.locator("option").allTextContents()}));
    await select.selectOption(value); assert.deepEqual(await word.locator(".part-form").allTextContents(), forms);
    await word.locator(".breakdown-part").nth(forms.findIndex(f => f === "조차" || f === "마저")).click();
    await page.waitForFunction(id => document.querySelector(`a[href*="ParaWordNo=${id}"]`), [70345,70345,70332,70345,70345,70332,70332][i]);
  }
  const additiveParticleDownload = page.waitForEvent("download");
  await page.getByRole("button", {name:"Export JSON",exact:true}).click();
  const additiveParticleExport = JSON.parse(await readFile(await (await additiveParticleDownload).path(), "utf8"));
  const additiveParticleExpected = execFileSync(cliBin, ["text","-","--dictionary",database,"--dict-compatible"], {input:additiveParticleText,encoding:"utf8"}).trim().split("\n").map(JSON.parse);
  assert.deepEqual(additiveParticleExport.records, additiveParticleExpected);
  await page.screenshot({path:resolve(tmpdir(),"klem-additive-desktop.png"),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  await page.screenshot({path:resolve(tmpdir(),"klem-additive-mobile.png"),fullPage:true});
  await page.setViewportSize({width:1440,height:1100});
  await page.getByLabel("Dictionary matches only").uncheck();
  const llachimyeonDictionaryCases = connectiveLedger.cases.filter(c => c.id.startsWith("llachimyeon-"));
  assert.equal(llachimyeonDictionaryCases.length, 10);
  for (const c of llachimyeonDictionaryCases) {
    const token = (await (await post("analyze", {text:c.surface})).json()).records[0];
    for (const j of c.judgments) {
      const i = token.analysis.analyses.findIndex(a => JSON.stringify(a.lemmas.map(l=>l.text)) === JSON.stringify(j.lemmas) && JSON.stringify(a.lemmas.map(l=>l.kind)) === JSON.stringify(j.lemma_kinds) && JSON.stringify(a.morphemes.map(m=>m.form)) === JSON.stringify(j.morphemes));
      assert.ok(i >= 0, c.id);
      assert.equal(token.dictionary.readings[i].status === "incompatible", j.verdict === "forbidden", c.id);
      if (j.verdict === "forbidden") assert.ok(token.dictionary.readings[i].lemmas[0].entries.some(e=>e.conflicts.some(c=>c.rule === "habitual_condition_verb" && c.morpheme_index === j.morphemes.length - 1)));
    }
  }
  const quotedBakkePolicy = connectiveLedger.cases.filter(c => c.id.startsWith("quoted-bakke-"));
  assert.equal(quotedBakkePolicy.length, 4);
  for (const c of quotedBakkePolicy) {
    const token = (await (await post("analyze", {text:c.surface})).json()).records[0];
    for (const j of c.judgments) {
      const index = token.analysis.analyses.findIndex(a => JSON.stringify(a.lemmas.map(l=>l.text)) === JSON.stringify(j.lemmas) && JSON.stringify(a.morphemes.map(m=>m.form)) === JSON.stringify(j.morphemes));
      assert.ok(index >= 0, c.id);
      assert.equal(token.dictionary.readings[index].status === "incompatible", j.verdict === "forbidden", c.id);
    }
  }
  const quotedBakkeCases = recipientLedger.cases.filter(c => c.id.startsWith("quoted-bakke-"));
  assert.equal(quotedBakkeCases.length, 56);
  for (const c of quotedBakkeCases) {
    const token = (await (await post("analyze", {text:c.surface})).json()).records[0];
    for (const j of c.judgments) {
      const index = token.analysis.analyses.findIndex(a => JSON.stringify(a.lemmas.map(l => l.text)) === JSON.stringify(j.lemmas)
        && JSON.stringify(a.lemmas.map(l => l.kind)) === JSON.stringify(j.lemma_kinds)
        && JSON.stringify(a.morphemes.map(m => m.form)) === JSON.stringify(j.morphemes)
        && JSON.stringify(a.morphemes.map(m => m.kind)) === JSON.stringify(j.morpheme_kinds));
      assert.equal(index >= 0, j.verdict === "required", c.id);
      if (index >= 0) assert.notEqual(token.dictionary.readings[index].status, "incompatible", c.id);
    }
  }
  const quotedBakkeText = "못하다고밖에 명궁이라고밖에 초능력이라고밖에는 보고있다고밖에 먹느냐고밖에 좋으냐고밖에";
  await submit(page, quotedBakkeText); await waitHeading(page, "못하다고밖에");
  await page.getByLabel("Dictionary matches only").check();
  await page.getByLabel("Exclude known grammar conflicts").check();
  for (const [i, forms] of [[0,["못하","다고","밖에"]],[1,["명궁","이","라고","밖에"]],[2,["초능력","이","라고","밖에","는"]],[3,["보","고","있","다고","밖에"]],[4,["먹","느냐고","밖에"]],[5,["좋","으냐고","밖에"]]]) {
    const word = page.locator(".breakdown-word").nth(i), select = word.locator("select");
    const value = await select.locator("option").evaluateAll((os, forms) => os.find(o => o.textContent.replace(/^\d+\. /, "") === forms.join(" + "))?.value, forms);
    assert.ok(value, JSON.stringify({i,forms,options:await select.locator("option").allTextContents()}));
    await select.selectOption(value); assert.deepEqual(await word.locator(".part-form").allTextContents(), forms);
    await word.locator(".breakdown-part").nth(forms.indexOf("밖에")).click();
    await page.waitForFunction(() => document.querySelector('a[href*="ParaWordNo=70070"]'));
    if (i >= 4) {
      await word.locator(".breakdown-part").nth(1).click();
      await page.waitForFunction(id => document.querySelector(`a[href*="ParaWordNo=${id}"]`), i === 4 ? 87443 : 87444);
    }

  }
  assert.equal(await page.locator(".breakdown-word").count(), 6);
  const quotedBakkeDownload = page.waitForEvent("download");
  await page.getByRole("button", {name:"Export JSON",exact:true}).click();
  const quotedBakkeExport = JSON.parse(await readFile(await (await quotedBakkeDownload).path(), "utf8"));
  const quotedBakkeExpected = execFileSync(cliBin, ["text","-","--dictionary",database,"--dict-compatible"], {input:quotedBakkeText,encoding:"utf8"}).trim().split("\n").map(JSON.parse);
  assert.deepEqual(quotedBakkeExport.records, quotedBakkeExpected);
  await page.screenshot({path:resolve(tmpdir(),"klem-quoted-bakke-desktop.png"),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  await page.screenshot({path:resolve(tmpdir(),"klem-quoted-bakke-mobile.png"),fullPage:true});
  await page.setViewportSize({width:1440,height:1100});
  await page.getByLabel("Dictionary matches only").uncheck();
  const necessityCases = recipientLedger.cases.filter(c => c.id.startsWith("necessity-"));
  assert.equal(necessityCases.length, 66);
  for (const c of necessityCases) {
    const token = (await (await post("analyze", {text:c.surface})).json()).records[0];
    for (const j of c.judgments) {
      const index = token.analysis.analyses.findIndex(a => JSON.stringify(a.lemmas.map(l => l.text)) === JSON.stringify(j.lemmas)
        && JSON.stringify(a.lemmas.map(l => l.kind)) === JSON.stringify(j.lemma_kinds)
        && JSON.stringify(a.morphemes.map(m => m.form)) === JSON.stringify(j.morphemes)
        && JSON.stringify(a.morphemes.map(m => m.kind)) === JSON.stringify(j.morpheme_kinds));
      assert.equal(index >= 0, j.verdict === "required", c.id);
      if (index >= 0) assert.notEqual(token.dictionary.readings[index].status, "incompatible", c.id);
    }
  }
  const necessityText = "먹을밖에 아팠을밖에 고수일밖에 학생다울밖에 먹고싶을밖에 너밖에";
  await submit(page, necessityText); await waitHeading(page, "먹을밖에");
  await page.getByLabel("Dictionary matches only").check();
  await page.getByLabel("Exclude known grammar conflicts").check();
  for (const [i, forms] of [[0,["먹","을밖에"]],[1,["아프","었","을밖에"]],[2,["고수","이","을밖에"]],[3,["학생","답","을밖에"]],[4,["먹","고","싶","을밖에"]],[5,["너","밖에"]]]) {
    const word = page.locator(".breakdown-word").nth(i), select = word.locator("select");
    const value = await select.locator("option").evaluateAll((os, forms) => os.find(o => o.textContent.replace(/^\d+\. /, "") === forms.join(" + "))?.value, forms);
    assert.ok(value, JSON.stringify({i,forms,options:await select.locator("option").allTextContents()}));
    await select.selectOption(value); assert.deepEqual(await word.locator(".part-form").allTextContents(), forms);
    await word.locator(".breakdown-part").last().click();
    if (i < 5) {
      await page.waitForFunction(() => document.querySelector('a[href*="ParaWordNo=85762"]'));
      await page.locator(".entry-choices button").filter({hasText:"-을밖에"}).click();
      await page.waitForFunction(() => document.querySelector('a[href*="ParaWordNo=85772"]'));
    } else {
      await page.waitForFunction(() => document.querySelector('a[href*="ParaWordNo=70070"]'));
    }

  }
  assert.equal(await page.locator(".breakdown-word").count(), 6);
  const necessityDownload = page.waitForEvent("download");
  await page.getByRole("button", {name:"Export JSON",exact:true}).click();
  const necessityExport = JSON.parse(await readFile(await (await necessityDownload).path(), "utf8"));
  const necessityExpected = execFileSync(cliBin, ["text","-","--dictionary",database,"--dict-compatible"], {input:necessityText,encoding:"utf8"}).trim().split("\n").map(JSON.parse);
  assert.deepEqual(necessityExport.records, necessityExpected);
  await page.screenshot({path:resolve(tmpdir(),"klem-necessity-desktop.png"),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  await page.screenshot({path:resolve(tmpdir(),"klem-necessity-mobile.png"),fullPage:true});
  await page.setViewportSize({width:1440,height:1100});
  await page.getByLabel("Dictionary matches only").uncheck();
  const llachimyeonCases = recipientLedger.cases.filter(c => c.id.startsWith("llachimyeon-"));
  assert.equal(llachimyeonCases.length, 42);
  for (const c of llachimyeonCases) {
    const token = (await (await post("analyze", {text:c.surface})).json()).records[0];
    for (const j of c.judgments) {
      const index = token.analysis.analyses.findIndex(a => JSON.stringify(a.lemmas.map(l => l.text)) === JSON.stringify(j.lemmas)
        && JSON.stringify(a.lemmas.map(l => l.kind)) === JSON.stringify(j.lemma_kinds)
        && JSON.stringify(a.morphemes.map(m => m.form)) === JSON.stringify(j.morphemes)
        && JSON.stringify(a.morphemes.map(m => m.kind)) === JSON.stringify(j.morpheme_kinds));
      assert.equal(index >= 0, j.verdict === "required", c.id);
      if (index >= 0) assert.notEqual(token.dictionary.readings[index].status, "incompatible", c.id);
    }
  }
  const llachimyeonText = "먹을라치면 있을라치면 갈라치면 먹으실라치면 보고있을라치면 먹지않을라치면";
  await submit(page, llachimyeonText); await waitHeading(page, "먹을라치면");
  await page.getByLabel("Dictionary matches only").check();
  await page.getByLabel("Exclude known grammar conflicts").check();
  for (const [i, forms] of [[0,["먹","을라치면"]],[1,["있","을라치면"]],[2,["가","을라치면"]],[3,["먹","시","을라치면"]],[4,["보","고","있","을라치면"]],[5,["먹","지","않","을라치면"]]]) {
    const word = page.locator(".breakdown-word").nth(i), select = word.locator("select");
    const value = await select.locator("option").evaluateAll((os, forms) => os.find(o => o.textContent.replace(/^\d+\. /, "") === forms.join(" + "))?.value, forms);
    assert.ok(value, JSON.stringify({i,forms,options:await select.locator("option").allTextContents()}));
    await select.selectOption(value); assert.deepEqual(await word.locator(".part-form").allTextContents(), forms);
    await word.locator(".breakdown-part").last().click();
    await page.waitForFunction(id => document.querySelector(`a[href*="ParaWordNo=${id}"]`), 86489);
    await page.locator(".entry-choices button").filter({hasText:"-을라치면"}).click();
    await page.waitForFunction(() => document.querySelector('a[href*="ParaWordNo=86616"]'));

  }
  assert.equal(await page.locator(".breakdown-word").count(), 6);
  const llachimyeonDownload = page.waitForEvent("download");
  await page.getByRole("button", {name:"Export JSON",exact:true}).click();
  const llachimyeonExport = JSON.parse(await readFile(await (await llachimyeonDownload).path(), "utf8"));
  const llachimyeonExpected = execFileSync(cliBin, ["text","-","--dictionary",database,"--dict-compatible"], {input:llachimyeonText,encoding:"utf8"}).trim().split("\n").map(JSON.parse);
  assert.deepEqual(llachimyeonExport.records, llachimyeonExpected);
  await page.screenshot({path:resolve(tmpdir(),"klem-llachimyeon-desktop.png"),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  await page.screenshot({path:resolve(tmpdir(),"klem-llachimyeon-mobile.png"),fullPage:true});
  await page.setViewportSize({width:1440,height:1100});
  await page.getByLabel("Dictionary matches only").uncheck();
  const comparisonCaseCases = recipientLedger.cases.filter(c => c.id.startsWith("comparison-case-"));
  assert.equal(comparisonCaseCases.length, 22);
  for (const c of comparisonCaseCases) {
    const token = (await (await post("analyze", {text:c.surface})).json()).records[0];
    for (const j of c.judgments) {
      const index = token.analysis.analyses.findIndex(a => JSON.stringify(a.lemmas.map(l => l.text)) === JSON.stringify(j.lemmas)
        && JSON.stringify(a.lemmas.map(l => l.kind)) === JSON.stringify(j.lemma_kinds)
        && JSON.stringify(a.morphemes.map(m => m.form)) === JSON.stringify(j.morphemes)
        && JSON.stringify(a.morphemes.map(m => m.kind)) === JSON.stringify(j.morpheme_kinds));
      assert.equal(index >= 0, j.verdict === "required", c.id);
      if (index >= 0) assert.notEqual(token.dictionary.readings[index].status, "incompatible", c.id);
    }
  }
  const comparisonCaseText = "학교에서처럼만 전에처럼 학교서처럼 회사들에서처럼 친구같이 친구와 같이";
  await submit(page, comparisonCaseText); await waitHeading(page, "학교에서처럼만");
  await page.getByLabel("Dictionary matches only").check();
  await page.getByLabel("Exclude known grammar conflicts").check();
  for (const [i, forms] of [[0,["학교","에서","처럼","만"]],[1,["전","에","처럼"]],[2,["학교","서","처럼"]],[3,["회사","들","에서","처럼"]],[4,["친구","같이"]]]) {
    const word = page.locator(".breakdown-word").nth(i), select = word.locator("select");
    const value = await select.locator("option").evaluateAll((os, forms) => os.find(o => o.textContent.replace(/^\d+\. /, "") === forms.join(" + "))?.value, forms);
    assert.ok(value, JSON.stringify({i,forms,options:await select.locator("option").allTextContents()}));
    await select.selectOption(value); assert.deepEqual(await word.locator(".part-form").allTextContents(), forms);
    await word.locator(".breakdown-part").nth(forms.indexOf(i === 4 ? "같이" : "처럼")).click();
    await page.waitForFunction(id => document.querySelector(`a[href*="ParaWordNo=${id}"]`), [68275,68275,68275,68275,22776][i]);
  }
  assert.equal(await page.locator(".breakdown-word").count(), 7);
  const comparisonCaseDownload = page.waitForEvent("download");
  await page.getByRole("button", {name:"Export JSON",exact:true}).click();
  const comparisonCaseExport = JSON.parse(await readFile(await (await comparisonCaseDownload).path(), "utf8"));
  const comparisonCaseExpected = execFileSync(cliBin, ["text","-","--dictionary",database,"--dict-compatible"], {input:comparisonCaseText,encoding:"utf8"}).trim().split("\n").map(JSON.parse);
  assert.deepEqual(comparisonCaseExport.records, comparisonCaseExpected);
  await page.screenshot({path:resolve(tmpdir(),"klem-comparison-case-desktop.png"),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  await page.screenshot({path:resolve(tmpdir(),"klem-comparison-case-mobile.png"),fullPage:true});
  await page.setViewportSize({width:1440,height:1100});
  await page.getByLabel("Dictionary matches only").uncheck();
  const comparisonParticleCases = recipientLedger.cases.filter(c => c.id.startsWith("comparison-particle-"));
  assert.equal(comparisonParticleCases.length, 33);
  for (const c of comparisonParticleCases) {
    const token = (await (await post("analyze", {text:c.surface})).json()).records[0];
    for (const j of c.judgments) {
      const index = token.analysis.analyses.findIndex(a => JSON.stringify(a.lemmas.map(l => l.text)) === JSON.stringify(j.lemmas)
        && JSON.stringify(a.lemmas.map(l => l.kind)) === JSON.stringify(j.lemma_kinds)
        && JSON.stringify(a.morphemes.map(m => m.form)) === JSON.stringify(j.morphemes)
        && JSON.stringify(a.morphemes.map(m => m.kind)) === JSON.stringify(j.morpheme_kinds));
      assert.equal(index >= 0, j.verdict === "required", c.id);
      if (index >= 0) assert.notEqual(token.dictionary.readings[index].status, "incompatible", c.id);
    }
  }
  const comparisonParticleText = "친구같이 새벽같이 계획대로 공부대로 새처럼";
  await submit(page, comparisonParticleText); await waitHeading(page, "친구같이");
  await page.getByLabel("Dictionary matches only").check();
  await page.getByLabel("Exclude known grammar conflicts").check();
  for (const [i, forms] of [[0,["친구","같이"]],[1,["새벽","같이"]],[2,["계획","대로"]],[3,["공부","대로"]],[4,["새","처럼"]]]) {
    const word = page.locator(".breakdown-word").nth(i), select = word.locator("select");
    const value = await select.locator("option").evaluateAll((os, forms) => os.find(o => o.textContent.replace(/^\d+\. /, "") === forms.join(" + "))?.value, forms);
    assert.ok(value, JSON.stringify({i,forms,options:await select.locator("option").allTextContents()}));
    await select.selectOption(value); assert.deepEqual(await word.locator(".part-form").allTextContents(), forms);
    await word.locator(".breakdown-part").last().click();
    await page.waitForFunction(id => document.querySelector(`a[href*="ParaWordNo=${id}"]`), [22776,22776,48410,48410,68275][i]);
  }
  const comparisonParticleDownload = page.waitForEvent("download");
  await page.getByRole("button", {name:"Export JSON",exact:true}).click();
  const comparisonParticleExport = JSON.parse(await readFile(await (await comparisonParticleDownload).path(), "utf8"));
  const comparisonParticleExpected = execFileSync(cliBin, ["text","-","--dictionary",database,"--dict-compatible"], {input:comparisonParticleText,encoding:"utf8"}).trim().split("\n").map(JSON.parse);
  assert.deepEqual(comparisonParticleExport.records, comparisonParticleExpected);
  await page.screenshot({path:resolve(tmpdir(),"klem-comparison-particle-desktop.png"),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  await page.screenshot({path:resolve(tmpdir(),"klem-comparison-particle-mobile.png"),fullPage:true});
  await page.setViewportSize({width:1440,height:1100});
  await page.getByLabel("Dictionary matches only").uncheck();
  const hadaComplexCases = recipientLedger.cases.filter(c => c.id.startsWith("hada-complex-"));
  assert.equal(hadaComplexCases.length, 52);
  for (const c of hadaComplexCases) {
    const token = (await (await post("analyze", {text:c.surface})).json()).records[0];
    for (const j of c.judgments) {
      const index = token.analysis.analyses.findIndex(a => JSON.stringify(a.lemmas.map(l => l.text)) === JSON.stringify(j.lemmas)
        && JSON.stringify(a.lemmas.map(l => l.kind)) === JSON.stringify(j.lemma_kinds)
        && JSON.stringify(a.morphemes.map(m => m.form)) === JSON.stringify(j.morphemes)
        && JSON.stringify(a.morphemes.map(m => m.kind)) === JSON.stringify(j.morpheme_kinds));
      assert.equal(index >= 0, j.verdict === "required", c.id);
      if (index >= 0) assert.notEqual(token.dictionary.readings[index].status, "incompatible", c.id);
    }
  }
  const hadaComplexText = "한몫지 값기로 꼴값지않았다 값진 귀찮은 귀찮게";
  await submit(page, hadaComplexText); await waitHeading(page, "한몫지");
  await page.getByLabel("Dictionary matches only").check();
  await page.getByLabel("Exclude known grammar conflicts").check();
  for (const [i, forms] of [[0,["한몫하","지"]],[1,["값하","기로"]],[2,["꼴값하","지","않","었","다"]],[3,["값지","은"]],[4,["귀찮","은"]],[5,["귀찮","게"]]]) {
    const word = page.locator(".breakdown-word").nth(i), select = word.locator("select");
    const value = await select.locator("option").evaluateAll((os, forms) => os.find(o => o.textContent.replace(/^\d+\. /, "") === forms.join(" + "))?.value, forms);
    assert.ok(value, JSON.stringify({i,forms,options:await select.locator("option").allTextContents()}));
    await select.selectOption(value); assert.deepEqual(await word.locator(".part-form").allTextContents(), forms);
  }
  await page.locator(".breakdown-word").first().locator(".breakdown-part").first().click();
  await page.waitForFunction(() => document.querySelector('a[href*="ParaWordNo=84890"]'));
  const hadaComplexDownload = page.waitForEvent("download");
  await page.getByRole("button", {name:"Export JSON",exact:true}).click();
  const hadaComplexExport = JSON.parse(await readFile(await (await hadaComplexDownload).path(), "utf8"));
  const hadaComplexExpected = execFileSync(cliBin, ["text","-","--dictionary",database,"--dict-compatible"], {input:hadaComplexText,encoding:"utf8"}).trim().split("\n").map(JSON.parse);
  assert.deepEqual(hadaComplexExport.records, hadaComplexExpected);
  assert.ok(hadaComplexExport.records[0].analysis.analyses.some(a => a.rules.includes("deletion.ha")));
  await page.screenshot({path:resolve(tmpdir(),"klem-hada-complex-desktop.png"),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  await page.screenshot({path:resolve(tmpdir(),"klem-hada-complex-mobile.png"),fullPage:true});
  await page.setViewportSize({width:1440,height:1100});
  await page.getByLabel("Dictionary matches only").uncheck();
  const connectiveCopulaCases = recipientLedger.cases.filter(c => c.id.startsWith("connective-copula-"));
  assert.equal(connectiveCopulaCases.length, 53);
  for (const c of connectiveCopulaCases) {
    const token = (await (await post("analyze", {text:c.surface})).json()).records[0];
    for (const j of c.judgments) {
      const index = token.analysis.analyses.findIndex(a => JSON.stringify(a.lemmas.map(l => l.text)) === JSON.stringify(j.lemmas)
        && JSON.stringify(a.lemmas.map(l => l.kind)) === JSON.stringify(j.lemma_kinds)
        && JSON.stringify(a.morphemes.map(m => m.form)) === JSON.stringify(j.morphemes)
        && JSON.stringify(a.morphemes.map(m => m.kind)) === JSON.stringify(j.morpheme_kinds));
      assert.equal(index >= 0, j.verdict === "required", c.id);
      if (index >= 0) assert.notEqual(token.dictionary.readings[index].status, "incompatible", c.id);
    }
  }
  const connectiveCopulaText = "넘어서였다 나서이다 추워서인지 먹어봐서다 학생다워서다 딸이었던들";
  await submit(page, connectiveCopulaText); await waitHeading(page, "넘어서였다");
  await page.getByLabel("Dictionary matches only").check();
  await page.getByLabel("Exclude known grammar conflicts").check();
  for (const [i, forms] of [[0,["넘","어서","이","었","다"]],[1,["나","어서","이","다"]],[2,["춥","어서","이","은지"]],[3,["먹","어","보","어서","이","다"]],[4,["학생","답","어서","이","다"]],[5,["딸","이","었","던들"]]]) {
    const word = page.locator(".breakdown-word").nth(i), select = word.locator("select");
    const value = await select.locator("option").evaluateAll((os, forms) => os.find(o => o.textContent.replace(/^\d+\. /, "") === forms.join(" + "))?.value, forms);
    assert.ok(value, JSON.stringify({i,forms,options:await select.locator("option").allTextContents()}));
    await select.selectOption(value); assert.deepEqual(await word.locator(".part-form").allTextContents(), forms);
  }
  const connectiveCopulaDownload = page.waitForEvent("download");
  await page.getByRole("button", {name:"Export JSON",exact:true}).click();
  const connectiveCopulaExport = JSON.parse(await readFile(await (await connectiveCopulaDownload).path(), "utf8"));
  const connectiveCopulaExpected = execFileSync(cliBin, ["text","-","--dictionary",database,"--dict-compatible"], {input:connectiveCopulaText,encoding:"utf8"}).trim().split("\n").map(JSON.parse);
  assert.deepEqual(connectiveCopulaExport.records, connectiveCopulaExpected);
  assert.ok(connectiveCopulaExport.records[0].analysis.analyses.some(a => a.rules.includes("copula.connective_seo")));
  await page.screenshot({path:resolve(tmpdir(),"klem-connective-copulas-desktop.png"),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  await page.screenshot({path:resolve(tmpdir(),"klem-connective-copulas-mobile.png"),fullPage:true});
  await page.setViewportSize({width:1440,height:1100});
  await page.getByLabel("Dictionary matches only").uncheck();
  const concessiveEndingCases = recipientLedger.cases.filter(c => c.id.startsWith("concessive-endings-"));
  assert.equal(concessiveEndingCases.length, 130);
  for (const c of concessiveEndingCases) {
    const token = (await (await post("analyze", {text:c.surface})).json()).records[0];
    for (const j of c.judgments) {
      const index = token.analysis.analyses.findIndex(a => JSON.stringify(a.lemmas.map(l => l.text)) === JSON.stringify(j.lemmas)
        && JSON.stringify(a.lemmas.map(l => l.kind)) === JSON.stringify(j.lemma_kinds)
        && JSON.stringify(a.morphemes.map(m => m.form)) === JSON.stringify(j.morphemes)
        && JSON.stringify(a.morphemes.map(m => m.kind)) === JSON.stringify(j.morpheme_kinds));
      assert.equal(index >= 0, j.verdict === "required", c.id);
      if (index >= 0) assert.notEqual(token.dictionary.readings[index].status, "incompatible", c.id);
    }
  }
  const concessiveEndingText = "한들 있은들 할망정 먹을망정 될지언정 있었을지언정 학생인들 먹고싶은들 확인했던들";
  await submit(page, concessiveEndingText); await waitHeading(page, "한들");
  await page.getByLabel("Dictionary matches only").check();
  await page.getByLabel("Exclude known grammar conflicts").check();
  for (const [i, forms, sourceId] of [[0,["하","은들"],80346],[1,["있","은들"],80345],[2,["하","을망정"],80277],[3,["먹","을망정"],80274],[4,["되","을지언정"],77052],[5,["있","었","을지언정"],77050],[6,["학생","이","은들"],80346],[7,["먹","고","싶","은들"],80345],[8,["확인하","였","던들"],80347]]) {
    const word = page.locator(".breakdown-word").nth(i), select = word.locator("select");
    const choose = async fs => {
      const value = await select.locator("option").evaluateAll((os, forms) => os.find(o => o.textContent.replace(/^\d+\. /, "") === forms.join(" + "))?.value, fs);
      assert.ok(value, JSON.stringify({i,forms:fs,options:await select.locator("option").allTextContents()}));
      await select.selectOption(value); assert.deepEqual(await word.locator(".part-form").allTextContents(), fs);
    };
    if (i === 6) await choose(["학생", "인들"]);
    await choose(forms);
    await word.locator(".breakdown-part").last().click();
    const source = Object.values(grammarLabels).flatMap(v => v.sources).find(s => s.id === sourceId);
    const entryChoice = page.locator(".entry-choices button").filter({hasText:source.headword});
    if (await entryChoice.count()) await entryChoice.click();
    await page.waitForFunction(id => document.querySelector(`a[href*="ParaWordNo=${id}"]`), sourceId);
  }
  const concessiveEndingDownload = page.waitForEvent("download");
  await page.getByRole("button", {name:"Export JSON",exact:true}).click();
  const concessiveEndingExport = JSON.parse(await readFile(await (await concessiveEndingDownload).path(), "utf8"));
  const concessiveEndingExpected = execFileSync(cliBin, ["text","-","--dictionary",database,"--dict-compatible"], {input:concessiveEndingText,encoding:"utf8"}).trim().split("\n").map(JSON.parse);
  assert.deepEqual(concessiveEndingExport.records, concessiveEndingExpected);
  await page.screenshot({path:resolve(tmpdir(),"klem-concessive-endings-desktop.png"),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  await page.screenshot({path:resolve(tmpdir(),"klem-concessive-endings-mobile.png"),fullPage:true});
  await page.setViewportSize({width:1440,height:1100});
  await page.getByLabel("Dictionary matches only").uncheck();
  const designationParticleCases = recipientLedger.cases.filter(c => c.id.startsWith("concessive-designation-"));
  assert.equal(designationParticleCases.length, 98);
  for (const c of designationParticleCases) {
    const token = (await (await post("analyze", {text:c.surface})).json()).records[0];
    for (const j of c.judgments) {
      const index = token.analysis.analyses.findIndex(a => JSON.stringify(a.lemmas.map(l => l.text)) === JSON.stringify(j.lemmas)
        && JSON.stringify(a.lemmas.map(l => l.kind)) === JSON.stringify(j.lemma_kinds)
        && JSON.stringify(a.morphemes.map(m => m.form)) === JSON.stringify(j.morphemes)
        && JSON.stringify(a.morphemes.map(m => m.kind)) === JSON.stringify(j.morpheme_kinds));
      assert.equal(index >= 0, j.verdict === "required", c.id);
      if (index >= 0) assert.notEqual(token.dictionary.readings[index].status, "incompatible", c.id);
    }
  }
  const designationParticleText = "학잔들 힘인들 얘길랑 널랑은 책을랑 말을랑은 미련일랑 술일랑은 먹고설랑 가설랑은 학교에설랑";
  await submit(page, designationParticleText); await waitHeading(page, "학잔들");
  await page.getByLabel("Dictionary matches only").check();
  await page.getByLabel("Exclude known grammar conflicts").check();
  for (const [i, forms, sourceId] of [[0,["학자","ㄴ들"],70267],[1,["힘","인들"],70053],[2,["얘기","ㄹ랑"],86492],[3,["너","ㄹ랑은"],89694],[4,["책","을랑"],86122],[5,["말","을랑은"],86131],[6,["미련","일랑"],86123],[7,["술","일랑은"],86132],[8,["먹","고","설랑"],86087],[9,["가","어","설랑은"],86088],[10,["학교","에설랑"],86576]]) {
    const word = page.locator(".breakdown-word").nth(i), select = word.locator("select");
    const choose = async fs => {
      const value = await select.locator("option").evaluateAll((os, forms) => os.find(o => o.textContent.replace(/^\d+\. /, "") === forms.join(" + "))?.value, fs);
      assert.ok(value, JSON.stringify({i,forms:fs,options:await select.locator("option").allTextContents()}));
      await select.selectOption(value); assert.deepEqual(await word.locator(".part-form").allTextContents(), fs);
    };
    if ([3,5,7,9].includes(i)) await choose([...forms.slice(0,-1), forms.at(-1).slice(0,-1), "은"]);
    if (i === 8) await choose(["먹", "고서", "ㄹ랑"]);
    if (i === 10) await choose(["학교", "에서", "ㄹ랑"]);
    await choose(forms);
    await word.locator(".breakdown-part").last().click();
    await page.waitForFunction(id => document.querySelector(`a[href*="ParaWordNo=${id}"]`), sourceId);
  }
  const designationParticleDownload = page.waitForEvent("download");
  await page.getByRole("button", {name:"Export JSON",exact:true}).click();
  const designationParticleExport = JSON.parse(await readFile(await (await designationParticleDownload).path(), "utf8"));
  const designationParticleExpected = execFileSync(cliBin, ["text","-","--dictionary",database,"--dict-compatible"], {input:designationParticleText,encoding:"utf8"}).trim().split("\n").map(JSON.parse);
  assert.deepEqual(designationParticleExport.records, designationParticleExpected);
  await page.screenshot({path:resolve(tmpdir(),"klem-concessive-designation-desktop.png"),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  await page.screenshot({path:resolve(tmpdir(),"klem-concessive-designation-mobile.png"),fullPage:true});
  await page.setViewportSize({width:1440,height:1100});
  await page.getByLabel("Dictionary matches only").uncheck();
  const sourceParticleCases = recipientLedger.cases.filter(c => c.id.startsWith("source-particles-"));
  assert.equal(sourceParticleCases.length, 99);
  for (const c of sourceParticleCases) {
    const token = (await (await post("analyze", {text:c.surface})).json()).records[0];
    for (const j of c.judgments) {
      const index = token.analysis.analyses.findIndex(a => JSON.stringify(a.lemmas.map(l => l.text)) === JSON.stringify(j.lemmas)
        && JSON.stringify(a.lemmas.map(l => l.kind)) === JSON.stringify(j.lemma_kinds)
        && JSON.stringify(a.morphemes.map(m => m.form)) === JSON.stringify(j.morphemes)
        && JSON.stringify(a.morphemes.map(m => m.kind)) === JSON.stringify(j.morpheme_kinds));
      assert.equal(index >= 0, j.verdict === "required", c.id);
      if (index >= 0) assert.notEqual(token.dictionary.readings[index].status, "incompatible", c.id);
    }
  }
  const sourceParticleText = "부모로부터 객석으로부터 집에서부터 여기서부터 대표로서 자식으로서 철사로써 흙으로써 있음으로써 서울서";
  await submit(page, sourceParticleText); await waitHeading(page, "부모로부터");
  await page.getByLabel("Dictionary matches only").check();
  await page.getByLabel("Exclude known grammar conflicts").check();
  for (const [i, forms, sourceId] of [[0,["부모","로부터"],80332],[1,["객석","으로부터"],80331],[2,["집","에서부터"],70333],[3,["여기","서부터"],86713],[4,["대표","로서"],70301],[5,["자식","으로서"],70300],[6,["철사","로써"],80297],[7,["흙","으로써"],80296],[8,["있","음","으로써"],80296],[9,["서울","서"],86712]]) {
    const word = page.locator(".breakdown-word").nth(i), select = word.locator("select");
    const choose = async fs => {
      const value = await select.locator("option").evaluateAll((os, forms) => os.find(o => o.textContent.replace(/^\d+\. /, "") === forms.join(" + "))?.value, fs);
      assert.ok(value, JSON.stringify({i,forms:fs,options:await select.locator("option").allTextContents()}));
      await select.selectOption(value); assert.deepEqual(await word.locator(".part-form").allTextContents(), fs);
    };
    if (i < 4) await choose([forms[0], forms[1].replace(/부터$/, ""), "부터"]);
    await choose(forms);
    await word.locator(".breakdown-part").last().click();
    await page.waitForFunction(id => document.querySelector(`a[href*="ParaWordNo=${id}"]`), sourceId);
  }
  const sourceParticleDownload = page.waitForEvent("download");
  await page.getByRole("button", {name:"Export JSON",exact:true}).click();
  const sourceParticleExport = JSON.parse(await readFile(await (await sourceParticleDownload).path(), "utf8"));
  const sourceParticleExpected = execFileSync(cliBin, ["text","-","--dictionary",database,"--dict-compatible"], {input:sourceParticleText,encoding:"utf8"}).trim().split("\n").map(JSON.parse);
  assert.deepEqual(sourceParticleExport.records, sourceParticleExpected);
  await page.screenshot({path:resolve(tmpdir(),"klem-source-particles-desktop.png"),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  await page.screenshot({path:resolve(tmpdir(),"klem-source-particles-mobile.png"),fullPage:true});
  await page.setViewportSize({width:1440,height:1100});
  await page.getByLabel("Dictionary matches only").uncheck();
  const coreCaseCases=recipientLedger.cases.filter(c=>c.id.startsWith("core-case-"));
  assert.equal(coreCaseCases.length,105);
  for(const c of coreCaseCases) {
    const token=(await (await post("analyze",{text:c.surface})).json()).records[0];
    for(const j of c.judgments) {
      const index=token.analysis.analyses.findIndex(a=>JSON.stringify(a.lemmas.map(l=>l.text))===JSON.stringify(j.lemmas)
        && JSON.stringify(a.lemmas.map(l=>l.kind))===JSON.stringify(j.lemma_kinds)
        && JSON.stringify(a.morphemes.map(m=>m.form))===JSON.stringify(j.morphemes)
        && JSON.stringify(a.morphemes.map(m=>m.kind))===JSON.stringify(j.morpheme_kinds));
      assert.equal(index>=0,j.verdict==="required",c.id);
      if(index>=0) assert.notEqual(token.dictionary.readings[index].status,"incompatible",c.id);
    }
  }
  const coreCaseText="맘껏을 빨리를 익지가않는다 물얼봐야지 내게로 친구에게로 친구한테로 선생님께서 학생의 책을 집으로 선생님께 친구에게 친구한테 친구에게서 친구한테서 학교에서 학생이 곧이를";
  await submit(page,coreCaseText); await waitHeading(page,"맘껏을");
  await page.getByLabel("Dictionary matches only").check();
  await page.getByLabel("Exclude known grammar conflicts").check();
  for(const [i,forms,partIndex,sourceId] of [[0,["맘껏","을"],1,86355],[1,["빨리","를"],1,85764],[2,["익","지","가","않","는다"],2,66341],[3,["묻","어","를","보","어야지"],2,85764],[4,["내","게로"],1,66970],[5,["친구","에게로"],1,70320],[6,["친구","한테로"],1,83881],[7,["선생님","께서"],1,73012],[8,["학생","의"],1,86290],[9,["책","을"],1,86355],[10,["집","으로"],1,85784],[11,["선생님","께"],1,69701],[12,["친구","에게"],1,69713],[13,["친구","한테"],1,69714],[14,["친구","에게서"],1,70321],[15,["친구","한테서"],1,68864],[16,["학교","에서"],1,68853],[17,["학생","이"],1,86289]]) {
    const word=page.locator(".breakdown-word").nth(i),select=word.locator("select");
    const value=await select.locator("option").evaluateAll((os,fs)=>os.find(o=>o.textContent.replace(/^\d+\. /,"")===fs.join(" + "))?.value,forms);
    assert.ok(value,forms.join(" + ")); await select.selectOption(value);
    assert.deepEqual(await word.locator(".part-form").allTextContents(),forms);
    await word.locator(".breakdown-part").nth(partIndex).click();
    await page.waitForFunction(id=>document.querySelector(`a[href*="ParaWordNo=${id}"]`),sourceId);
  }
  const coreCaseDownload=page.waitForEvent("download");
  await page.getByRole("button",{name:"Export JSON",exact:true}).click();
  const coreCaseExport=JSON.parse(await readFile(await (await coreCaseDownload).path(),"utf8"));
  const coreCaseExpected=execFileSync(cliBin,["text","-","--dictionary",database,"--dict-compatible"],{input:coreCaseText,encoding:"utf8"}).trim().split("\n").map(JSON.parse);
  assert.deepEqual(coreCaseExport.records,coreCaseExpected);
  assert(!coreCaseExport.records.filter(r=>r.kind==="word").at(-1).analysis.analyses.some(a=>a.lemmas.some(l=>l.text==="곧이")));
  await page.screenshot({path:resolve(tmpdir(),"klem-core-case-desktop.png"),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  await page.screenshot({path:resolve(tmpdir(),"klem-core-case-mobile.png"),fullPage:true});
  await page.setViewportSize({width:1440,height:1100});
  await page.getByLabel("Dictionary matches only").uncheck();
  // Degree 깨나 preserves noun/plural structure and existing 깨다/깨/꽤 readings.
  const kkaenaCases = recipientLedger.cases.filter(c=>c.id.startsWith("kkaena-"));
  assert.equal(kkaenaCases.length,27);
  for(const c of kkaenaCases) {
    const token=(await (await post("analyze",{text:c.surface})).json()).records[0];
    for(const j of c.judgments) {
      const index=token.analysis.analyses.findIndex(a=>JSON.stringify(a.lemmas.map(l=>l.text))===JSON.stringify(j.lemmas)
        && JSON.stringify(a.lemmas.map(l=>l.kind))===JSON.stringify(j.lemma_kinds)
        && JSON.stringify(a.morphemes.map(m=>m.form))===JSON.stringify(j.morphemes)
        && JSON.stringify(a.morphemes.map(m=>m.kind))===JSON.stringify(j.morpheme_kinds));
      assert.equal(index>=0,j.verdict==="required",c.id);
      if(index>=0) assert.notEqual(token.dictionary.readings[index].status,"incompatible",c.id);
    }
  }
  const kkaenaText="땀깨나 족보깨나 사람들깨나 아씨들깨나 꽤나 깨나";
  await submit(page,kkaenaText); await waitHeading(page,"땀깨나");
  const unknownWord=page.locator(".breakdown-word").nth(3);
  const unknownValue=await unknownWord.locator("select option").evaluateAll(os=>os.find(o=>o.textContent.replace(/^\d+\. /,"")==="아씨 + 들 + 깨나")?.value);
  assert.ok(unknownValue); await unknownWord.locator("select").selectOption(unknownValue);
  assert.deepEqual(await unknownWord.locator(".part-form").allTextContents(),["아씨","들","깨나"]);
  await page.getByLabel("Dictionary matches only").check();
  await page.getByLabel("Exclude known grammar conflicts").check();
  assert.equal(await unknownWord.locator("select").isDisabled(),true);
  assert.equal(await unknownWord.locator(".breakdown-unavailable").textContent(),"No matching reading");
  for(const [i,forms] of [[0,["땀","깨나"]],[1,["족보","깨나"]],[2,["사람","들","깨나"]]]) {
    const word=page.locator(".breakdown-word").nth(i),select=word.locator("select");
    const value=await select.locator("option").evaluateAll((os,fs)=>os.find(o=>o.textContent.replace(/^\d+\. /,"")===fs.join(" + "))?.value,forms);
    assert.ok(value); await select.selectOption(value);
    assert.deepEqual(await word.locator(".part-form").allTextContents(),forms);
    await word.locator(".breakdown-part").last().click();
    await page.waitForFunction(()=>document.querySelector('a[href*="ParaWordNo=69715"]'));
  }
  const kkaenaDownload=page.waitForEvent("download");
  await page.getByRole("button",{name:"Export JSON",exact:true}).click();
  const kkaenaExport=JSON.parse(await readFile(await (await kkaenaDownload).path(),"utf8"));
  const kkaenaExpected=execFileSync(cliBin,["text","-","--dictionary",database,"--dict-compatible"],{input:kkaenaText,encoding:"utf8"}).trim().split("\n").map(JSON.parse);
  assert.deepEqual(kkaenaExport.records,kkaenaExpected);
  assert.equal(kkaenaExport.records.filter(r=>r.kind==="word")[3].analysis.analyses.length,0);
  await page.screenshot({path:resolve(tmpdir(),"klem-kkaena-desktop.png"),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  await page.screenshot({path:resolve(tmpdir(),"klem-kkaena-mobile.png"),fullPage:true});
  await page.setViewportSize({width:1440,height:1100});
  await page.getByLabel("Dictionary matches only").uncheck();
  // Copular and particle homonyms retain their own source entries and role boundaries.
  const raConditionsCases = recipientLedger.cases.filter(c => c.id.startsWith("ra-conditions-"));
  assert.equal(raConditionsCases.length, 72);
  for (const c of raConditionsCases) {
    const data = await (await post("analyze", {text:c.surface})).json(), token = data.records[0];
    for (const j of c.judgments) {
      const index = token.analysis.analyses.findIndex(a => JSON.stringify(a.lemmas.map(l=>l.text)) === JSON.stringify(j.lemmas)
        && JSON.stringify(a.lemmas.map(l=>l.kind)) === JSON.stringify(j.lemma_kinds)
        && JSON.stringify(a.morphemes.map(m=>m.form)) === JSON.stringify(j.morphemes)
        && JSON.stringify(a.morphemes.map(m=>m.kind)) === JSON.stringify(j.morpheme_kinds));
      assert.equal(index >= 0, j.verdict === "required", c.id);
      if(index >= 0) assert.notEqual(token.dictionary.readings[index].status, "incompatible", c.id);
    }
  }
  const raConditionsText = "교양만이라도 휴가라야만 꽃다발이라야 먹더라도 것이라야만";
  await submit(page, raConditionsText); await waitHeading(page, "교양만이라도");
  await page.getByLabel("Dictionary matches only").check();
  await page.getByLabel("Exclude known grammar conflicts").check();
  const raConditionsData = await (await post("analyze",{text:raConditionsText})).json();
  const raConditionsWords = raConditionsData.records.filter(r=>r.kind==="word");
  for(const [i, expected, sourceId] of [[0,["교양","만","이","라도"],80246],[1,["휴가","라야만"],86066],[1,["휴가","라야","만"],86520],[1,["휴가","이","라야만"],80237],[1,["휴가","이","라야","만"],80230],[2,["꽃다발","이","라야"],80230],[2,["꽃다발","이라야"],86620],[3,["먹","더","라도"],80246],[4,["것","이라야만"],86067]]) {
    const word=page.locator(".breakdown-word").nth(i), select=word.locator("select");
    // A subject particle 이 and copula 이 can print identically; select by
    // both displayed forms and the grammar source's actual morpheme role.
    const [key,label]=Object.entries(grammarLabels).find(([,v])=>v.sources.some(s=>s.id===sourceId));
    const allowed=raConditionsWords[i].analysis.analyses.flatMap((a,j)=>a.morphemes.some(m=>m.form===key.replace(/^-/,'') && m.kind===label.kind)?[String(j)]:[]);
    const value=await select.locator("option").evaluateAll((os,{forms,allowed})=>os.find(o=>allowed.includes(o.value) && o.textContent.replace(/^\d+\. /,"")===forms.join(" + "))?.value,{forms:expected,allowed});
    assert.ok(value,expected.join(" + ")); await select.selectOption(value);
    assert.deepEqual(await word.locator(".part-form").allTextContents(),expected);
    const partIndex=expected.at(-1)==="만"?expected.length-2:expected.length-1;
    await word.locator(".breakdown-part").nth(partIndex).click();
    await page.waitForFunction(id=>document.querySelector(`a[href*="ParaWordNo=${id}"]`),sourceId);
  }
  const raConditionsDownload=page.waitForEvent("download");
  await page.getByRole("button",{name:"Export JSON",exact:true}).click();
  const raConditionsExport=JSON.parse(await readFile(await (await raConditionsDownload).path(),"utf8"));
  const raConditionsExpected=execFileSync(cliBin,["text","-","--dictionary",database,"--dict-compatible"],{input:raConditionsText,encoding:"utf8"}).trim().split("\n").map(JSON.parse);
  assert.deepEqual(raConditionsExport.records,raConditionsExpected);
  await page.screenshot({path:resolve(tmpdir(),"klem-ra-conditions-desktop.png"),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  await page.screenshot({path:resolve(tmpdir(),"klem-ra-conditions-mobile.png"),fullPage:true});
  await page.setViewportSize({width:1440,height:1100});
  await page.getByLabel("Dictionary matches only").uncheck();
  // Emphatic 에야 preserves bundled and split alternatives with outer particles.
  const eyaCases = recipientLedger.cases.filter(c => c.id.startsWith("eya-"));
  assert.equal(eyaCases.length, 34);
  for (const c of eyaCases) {
    const data = await (await post("analyze", {text:c.surface})).json(), token = data.records[0];
    for (const j of c.judgments) {
      const index = token.analysis.analyses.findIndex(a => JSON.stringify(a.lemmas.map(l=>l.text)) === JSON.stringify(j.lemmas)
        && JSON.stringify(a.lemmas.map(l=>l.kind)) === JSON.stringify(j.lemma_kinds)
        && JSON.stringify(a.morphemes.map(m=>m.form)) === JSON.stringify(j.morphemes)
        && JSON.stringify(a.morphemes.map(m=>m.kind)) === JSON.stringify(j.morpheme_kinds));
      assert.equal(index >= 0, j.verdict === "required", c.id);
      if(index >= 0) assert.notEqual(token.dictionary.readings[index].status, "incompatible", c.id);
    }
  }
  const eyaText = "때에야만 전에야 학생임에야 죽음에야";
  await submit(page, eyaText); await waitHeading(page, "때에야만");
  await page.getByLabel("Dictionary matches only").check();
  await page.getByLabel("Exclude known grammar conflicts").check();
  for(const [i, expected, sourceId] of [[0,["때","에야","만"],86578],[1,["전","에야"],86578],[2,["학생","이","음","에야"],86578],[3,["죽","음","에야"],86578]]) {
    const word=page.locator(".breakdown-word").nth(i), select=word.locator("select");
    const value=await select.locator("option").evaluateAll((os,forms)=>os.find(o=>o.textContent.replace(/^\d+\. /,"")===forms.join(" + "))?.value,expected);
    assert.ok(value,expected.join(" + ")); await select.selectOption(value);
    assert.deepEqual(await word.locator(".part-form").allTextContents(),expected);
    const splitForms=expected.flatMap(f=>f==="에야"?["에","야"]:[f]);
    const splitValue=await select.locator("option").evaluateAll((os,forms)=>os.find(o=>o.textContent.replace(/^\d+\. /,"")===forms.join(" + "))?.value,splitForms);
    assert.ok(splitValue,splitForms.join(" + ")); await select.selectOption(splitValue);
    assert.deepEqual(await word.locator(".part-form").allTextContents(),splitForms);
    await select.selectOption(value);
    await word.locator(".breakdown-part").nth(expected.indexOf("에야")).click();
    await page.waitForFunction(id=>document.querySelector(`a[href*="ParaWordNo=${id}"]`),sourceId);
  }
  const eyaDownload=page.waitForEvent("download");
  await page.getByRole("button",{name:"Export JSON",exact:true}).click();
  const eyaExport=JSON.parse(await readFile(await (await eyaDownload).path(),"utf8"));
  const eyaExpected=execFileSync(cliBin,["text","-","--dictionary",database,"--dict-compatible"],{input:eyaText,encoding:"utf8"}).trim().split("\n").map(JSON.parse);
  assert.deepEqual(eyaExport.records,eyaExpected);
  await page.screenshot({path:resolve(tmpdir(),"klem-eya-desktop.png"),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  await page.screenshot({path:resolve(tmpdir(),"klem-eya-mobile.png"),fullPage:true});
  await page.setViewportSize({width:1440,height:1100});
  await page.getByLabel("Dictionary matches only").uncheck();
  // Vocative allomorphs preserve nominal roles and their distinct source entries.
  const vocativeCases = recipientLedger.cases.filter(c => c.id.startsWith("vocative-"));
  assert.equal(vocativeCases.length, 34);
  for (const c of vocativeCases) {
    const data = await (await post("analyze", {text:c.surface})).json(), token = data.records[0];
    for (const j of c.judgments) {
      const index = token.analysis.analyses.findIndex(a => JSON.stringify(a.lemmas.map(l=>l.text)) === JSON.stringify(j.lemmas)
        && JSON.stringify(a.lemmas.map(l=>l.kind)) === JSON.stringify(j.lemma_kinds)
        && JSON.stringify(a.morphemes.map(m=>m.form)) === JSON.stringify(j.morphemes)
        && JSON.stringify(a.morphemes.map(m=>m.kind)) === JSON.stringify(j.morpheme_kinds));
      assert.equal(index >= 0, j.verdict === "required", c.id);
      if(index >= 0) assert.notEqual(token.dictionary.readings[index].status, "incompatible", c.id);
    }
  }
  const vocativeText = "검이여 왕자시여 하나님이시여 젊은이여 국민들이여";
  await submit(page, vocativeText); await waitHeading(page, "검이여");
  await page.getByLabel("Dictionary matches only").check();
  await page.getByLabel("Exclude known grammar conflicts").check();
  for(const [i, expected, sourceId] of [[0,["검","이여"],86621],[1,["왕자","시여"],86091],[2,["하나님","이시여"],86092],[3,["젊은이","여"],86583],[4,["국민","들","이여"],86621]]) {
    const word=page.locator(".breakdown-word").nth(i), select=word.locator("select");
    const value=await select.locator("option").evaluateAll((os,forms)=>os.find(o=>o.textContent.replace(/^\d+\. /,"")===forms.join(" + "))?.value,expected);
    assert.ok(value,expected.join(" + ")); await select.selectOption(value);
    assert.deepEqual(await word.locator(".part-form").allTextContents(),expected);
    await word.locator(".breakdown-part").last().click();
    await page.waitForFunction(id=>document.querySelector(`a[href*="ParaWordNo=${id}"]`),sourceId);
  }
  const vocativeDownload=page.waitForEvent("download");
  await page.getByRole("button",{name:"Export JSON",exact:true}).click();
  const vocativeExport=JSON.parse(await readFile(await (await vocativeDownload).path(),"utf8"));
  const vocativeExpected=execFileSync(cliBin,["text","-","--dictionary",database,"--dict-compatible"],{input:vocativeText,encoding:"utf8"}).trim().split("\n").map(JSON.parse);
  assert.deepEqual(vocativeExport.records,vocativeExpected);
  await page.screenshot({path:resolve(tmpdir(),"klem-vocative-desktop.png"),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  await page.screenshot({path:resolve(tmpdir(),"klem-vocative-mobile.png"),fullPage:true});
  await page.setViewportSize({width:1440,height:1100});
  await page.getByLabel("Dictionary matches only").uncheck();
  const expressivePolicies = connectiveLedger.cases.filter(c => c.id.startsWith("attachment-expressive-"));
  assert.equal(expressivePolicies.length, 22);
  for (const [cases, policy] of [[expressivePolicies, true]]) {
    for (const c of cases) {
      const data = await (await post("analyze", {text: c.surface})).json(), token = data.records[0];
      for (const j of c.judgments) {
        const match = a => JSON.stringify(a.lemmas.map(l => l.text)) === JSON.stringify(j.lemmas)
          && JSON.stringify(a.lemmas.map(l => l.kind)) === JSON.stringify(j.lemma_kinds)
          && JSON.stringify(a.morphemes.map(m => m.form)) === JSON.stringify(j.morphemes)
          && JSON.stringify(a.morphemes.map(m => m.kind)) === JSON.stringify(j.morpheme_kinds);
        const index = token.analysis.analyses.findIndex(match);
        assert.equal(index >= 0, policy || j.verdict === "required", c.id);
        if (index >= 0) assert.equal(token.dictionary.readings[index].status === "incompatible", j.verdict === "forbidden", c.id);
      }
    }
  }
  const expressiveText = "잘해서 커한다 읽지않아한다 좋아를한다";
  await submit(page, expressiveText); await waitHeading(page, "잘해서");
  await page.getByLabel("Dictionary matches only").check();
  await page.getByLabel("Exclude known grammar conflicts").uncheck();
  const expressiveData = await (await post("analyze", {text: expressiveText})).json();
  const badIndex = expressiveData.records[0].analysis.analyses.findIndex(a => a.lemmas[0].text === "자다" && a.lemmas.at(-1).text === "하다");
  assert.ok(badIndex >= 0);
  const firstOptions = page.locator(".breakdown-word").nth(0).locator("select option");
  assert.ok((await firstOptions.evaluateAll(os => os.map(o => o.value))).includes(String(badIndex)));
  await page.getByLabel("Exclude known grammar conflicts").check();
  assert.ok((await firstOptions.evaluateAll(os => os.map(o => o.value))).includes(String(badIndex)));
  assert.equal(expressiveData.records[0].dictionary.readings[badIndex].status, "unknown");
  for (const [i, forms] of [[0, ["잘하", "여서"]], [1, ["크", "어", "하", "는다"]], [3, ["좋", "어", "를", "하", "는다"]]]) {
    const word = page.locator(".breakdown-word").nth(i), select = word.locator("select");
    const value = await select.locator("option").evaluateAll((os, fs) => os.find(o => o.textContent.replace(/^\d+\. /, "") === fs.join(" + "))?.value, forms);
    assert.ok(value, JSON.stringify({i,forms,options:await select.locator("option").allTextContents()})); await select.selectOption(value);
    assert.deepEqual(await word.locator(".part-form").allTextContents(), forms);
    if (i === 1) assert.equal(await word.locator(".part-gloss").first().innerText(), expressiveData.glosses["krdict:66586"]);
  }
  const expressiveDownload = page.waitForEvent("download");
  await page.getByRole("button", {name: "Export JSON", exact: true}).click();
  const expressiveExport = JSON.parse(await readFile(await (await expressiveDownload).path(), "utf8"));
  const expressiveExpected = execFileSync(cliBin, ["text", "-", "--dictionary", database, "--dict-compatible"], {input: expressiveText, encoding: "utf8"}).trim().split("\n").map(JSON.parse);
  assert.deepEqual(expressiveExport.records, expressiveExpected);
  await page.getByLabel("Dictionary matches only").uncheck();
  // Literary assertions retain distinct forms, copulas and lexical homonyms.
  const niraCases = recipientLedger.cases.filter(c => c.id.startsWith("nira-"));
  const niraPolicies = connectiveLedger.cases.filter(c => c.id.startsWith("attachment-nira-"));
  assert.equal(niraCases.length, 54); assert.equal(niraPolicies.length, 15);
  for (const [cases, policy] of [[niraCases, false], [niraPolicies, true]]) {
    for (const c of cases) {
      const data = await (await post("analyze", {text: c.surface})).json(), token = data.records[0];
      for (const j of c.judgments) {
        const match = a => JSON.stringify(a.lemmas.map(l => l.text)) === JSON.stringify(j.lemmas)
          && JSON.stringify(a.lemmas.map(l => l.kind)) === JSON.stringify(j.lemma_kinds)
          && JSON.stringify(a.morphemes.map(m => m.form)) === JSON.stringify(j.morphemes)
          && JSON.stringify(a.morphemes.map(m => m.kind)) === JSON.stringify(j.morpheme_kinds);
        const index = token.analysis.analyses.findIndex(match);
        assert.equal(index >= 0, policy || j.verdict === "required", c.id);
        if (index >= 0) assert.equal(token.dictionary.readings[index].status === "incompatible", j.verdict === "forbidden", c.id);
      }
    }
  }
  const niraText = "사랑하느니라 그림자니라 같으니라 크니라 크느니라";
  await submit(page, niraText); await waitHeading(page, "사랑하느니라");
  await page.getByLabel("Dictionary matches only").check();
  await page.getByLabel("Exclude known grammar conflicts").check();
  const niraData = await (await post("analyze", {text: niraText})).json();
  for (const [i, expected, sourceId] of [[0, ["사랑하", "느니라"], 86128], [1, ["그림자", "이", "으니라"], 86126], [2, ["같", "으니라"], 86126], [3, ["크", "으니라"], 86126], [4, ["크", "느니라"], 86128]]) {
    const word = page.locator(".breakdown-word").nth(i), select = word.locator("select");
    const value = await select.locator("option").evaluateAll((os, forms) => os.find(o => o.textContent.replace(/^\d+\. /, "") === forms.join(" + "))?.value, expected);
    assert.ok(value, expected.join(" + ")); await select.selectOption(value);
    assert.deepEqual(await word.locator(".part-form").allTextContents(), expected);
    if (i >= 3) assert.equal(await word.locator(".part-gloss").first().innerText(), niraData.glosses[i === 3 ? "krdict:66586" : "krdict:66584"]);
    await word.locator(".breakdown-part").last().click();
    if (sourceId === 86126) await page.locator(".entry-choices button").filter({hasText: "-으니라"}).click();
    await page.waitForFunction(id => document.querySelector(`a[href*="ParaWordNo=${id}"]`), sourceId);
  }
  const niraDownload = page.waitForEvent("download");
  await page.getByRole("button", {name: "Export JSON", exact: true}).click();
  const niraExport = JSON.parse(await readFile(await (await niraDownload).path(), "utf8"));
  const niraExpected = execFileSync(cliBin, ["text", "-", "--dictionary", database, "--dict-compatible"], {input: niraText, encoding: "utf8"}).trim().split("\n").map(JSON.parse);
  assert.deepEqual(niraExport.records, niraExpected);
  await page.screenshot({path: resolve(tmpdir(), "klem-nira-desktop.png"), fullPage: true});
  await page.setViewportSize({width: 390, height: 844});
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  await page.screenshot({path: resolve(tmpdir(), "klem-nira-mobile.png"), fullPage: true});
  await page.setViewportSize({width: 1440, height: 1100});
  await page.getByLabel("Dictionary matches only").uncheck();
  // Whole lexical adverbs survive both filters with their own role and gloss.
  const focusText = "아직도 퍽도 너무도 자세히는 일찍부터 아직까지도 오늘은 학교도";
  await submit(page, focusText);
  await waitHeading(page, "아직도");
  await page.getByLabel("Dictionary matches only").check();
  await page.getByLabel("Exclude known grammar conflicts").check();
  const focusData = await (await post("analyze", { text: focusText })).json();
  const focusExpected = execFileSync(cliBin, ["text", "-", "--dictionary", database, "--dict-compatible"], { input: focusText, encoding: "utf8" }).trim().split("\n").map(JSON.parse);
  const focusWords = focusExpected.filter((r) => r.kind === "word");
  for (let i = 0; i < focusWords.length; i++) {
    const block = page.locator(".breakdown-word").nth(i);
    assert.equal(await block.locator("option").count(), focusWords[i].analysis.analyses.length);
  }
  assert.deepEqual(await page.locator(".breakdown-word").first().locator(".part-form").allTextContents(), ["아직", "도"]);
  assert.deepEqual(await page.locator(".breakdown-word").nth(5).locator(".part-form").allTextContents(), ["아직", "까지", "도"]);
  assert.equal(await page.locator(".breakdown-word").first().locator(".part-gloss").first().innerText(), focusData.glosses["krdict:71254"]);
  assert(focusWords[6].analysis.analyses.some((a) => a.lemmas[0].kind === "adverbial"));
  assert(focusWords[6].analysis.analyses.some((a) => a.lemmas[0].kind === "nominal"));
  assert(focusWords[7].analysis.analyses.every((a) => a.lemmas[0].kind !== "adverbial"));
  const focusDownload = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export JSON" }).click();
  const focusExport = JSON.parse(await readFile(await (await focusDownload).path(), "utf8"));
  assert.deepEqual(focusExport.records, focusExpected);
  await page.screenshot({path: resolve(tmpdir(), "klem-adverb-focus-desktop.png"), fullPage: true});
  await page.setViewportSize({width: 390, height: 844});
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  await page.screenshot({path: resolve(tmpdir(), "klem-adverb-focus-mobile.png"), fullPage: true});
  await page.setViewportSize({width: 1440, height: 1100});
  await page.getByLabel("Dictionary matches only").uncheck();
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
    "Object / emphasis",
    "study",
    "Polite informal",
  ]);
  assert.match(await breakdown.innerText(), /Expanded \/ normalized/);
  const selector = breakdown.getByRole("combobox").first();
  assert.equal(await selector.locator("option").count(), 3);
  await breakdown
    .getByRole("button", { name: "Show all combinations", exact: true })
    .click();
  assert.equal(await breakdown.locator(".combination-list li").count(), 6);
  await selector.selectOption({ label: "3. 절 + 는" });
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
    "Object / emphasis",
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
    ["번쯤", "번 + 쯤", ["번", "쯤"], "쯤", "About / approximately"],
    ["내일쯤에", "내일 + 쯤 + 에", ["내일", "쯤", "에"], "쯤", "About / approximately"],
    ["그쯤", "그 + 쯤", ["그", "쯤"], "쯤", "About / approximately"],
    ["교수님들쯤은", "교수 + 님 + 들 + 쯤 + 은", ["교수", "님", "들", "쯤", "은"], "쯤", "About / approximately"],
    ["중간쯤이었다", "중간 + 쯤 + 이 + 었 + 다", ["중간", "쯤", "이", "었", "다"], "쯤", "About / approximately"],
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
      // The compact enumerative particle now ties the copular analysis.
      // Initial ordering is deterministic, not contextual disambiguation.
      assert.deepEqual(
        await breakdown.locator(".part-form").allTextContents(),
        ["과학적", "이다"],
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
    if (suffix === "쯤") {
      assert.deepEqual(result.grammar["-쯤"].map(e => e.id), ["krdict:88691"]);
      assert.ok(result.records[0].analysis.analyses[Number(choice)].rules.includes("suffix.approximation"));
      if (word === "그쯤") {
        const whole = await breakdown.getByRole("combobox").locator("option").evaluateAll(options =>
          options.find(o => o.textContent.replace(/^\d+\. /, "") === "그쯤")?.value);
        assert.ok(whole);
        await breakdown.getByRole("combobox").selectOption(whole);
        assert.deepEqual(await breakdown.locator(".part-form").allTextContents(), ["그쯤"]);
      }
    }

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
    ["학생치고는", ["학생", "치고", "는"], "는", "Topic / contrast", 85851, "particle"],
    ["사람치고서는", ["사람", "치고서", "는"], "는", "Topic / contrast", 85851, "particle"],
    ["간다", ["가", "는다"], "는다", "Present statement / self-question", 85037, "ending"],
    ["간다고", ["가", "는다고"], "는다고", "Assertion / reason / quotation", 74684, "ending"],
    ["간다는", ["가", "는다는"], "는다는", "Quoted noun modifier", 82214, "ending"],
    ["간다면", ["가", "는다면"], "는다면", "If / supposing", 68738, "ending"],
    ["먹으신다", ["먹", "시", "는다"], "는다", "Present statement / self-question", 85037, "ending"],
    ["먹고계신다", ["먹", "고", "계시", "는다"], "는다", "Present statement / self-question", 85037, "ending"],
    ["먹고싶으시다고", ["먹", "고", "싶", "시", "다고"], "다고", "Assertion / reason / quotation", 73900, "ending"],
    ["학생다우시다는", ["학생", "답", "시", "다는"], "다는", "Quoted noun modifier", 82216, "ending"],
    ["학생이시다네", ["학생", "이", "시", "다네"], "다네", "Information / report", 75191, "ending"],
    ["지내고있다네", ["지내", "고", "있", "다네"], "다네", "Information / report", 75191, "ending"],
    ["먹고계시다는데", ["먹", "고", "계시", "다는데"], "다는데", "Report / background", 82257, "ending"],
    ["감염되어있다거나", ["감염되", "어", "있", "다거나"], "다거나", "Reported alternatives / examples", 86056, "ending"],
    ["변해가고있다든가", ["변하", "여", "가", "고", "있", "다든가"], "다든가", "Reported alternatives / examples", 82121, "ending"],
    ["먹고있지않다네", ["먹", "고", "있", "지", "않", "다네"], "다네", "Information / report", 75191, "ending"],
    ["먹고있지못하다는데", ["먹", "고", "있", "지", "못하", "다는데"], "다는데", "Report / background", 82257, "ending"],
    ["먹고계신다네", ["먹", "고", "계시", "는다네"], "는다네", "Information / report", 75175, "ending"],
    ["먹고있지않는다네", ["먹", "고", "있", "지", "않", "는다네"], "는다네", "Information / report", 75175, "ending"],
    ["먹고있어본다네", ["먹", "고", "있", "어", "보", "는다네"], "는다네", "Information / report", 75175, "ending"],
    ["먹고있다며", ["먹", "고", "있", "다며"], "다며", "Report / confirmation", 81466, "ending"],
    ["먹고있지않다면서", ["먹", "고", "있", "지", "않", "다면서"], "다면서", "Report / confirmation", 78806, "ending"],
    ["좋다며", ["좋", "다며"], "다며", "Report / confirmation", 81466, "ending"],
    ["지원한다며", ["지원하", "는다며"], "는다며", "Report / confirmation", 81465, "ending"],
    ["학생이라며", ["학생", "이", "라며"], "라며", "Copular / factual report", 81469, "ending"],
    ["먹으라며", ["먹", "으라며"], "으라며", "Reported command / confirmation", 81479, "ending"],
    ["먹더라며", ["먹", "더라며"], "더라며", "Retrospective report", 81531, "ending"],
    ["먹자며", ["먹", "자며"], "자며", "Reported proposal / confirmation", 81474, "ending"],
    ["먹냐며", ["먹", "냐며"], "냐며", "Reported question", 86914, "ending"],
    ["먹느냐며", ["먹", "느냐며"], "느냐며", "Reported question", 86861, "ending"],
    ["좋으냐며", ["좋", "으냐며"], "으냐며", "Reported question", 86921, "ending"],
    ["좋다면서", ["좋", "다면서"], "다면서", "Report / confirmation", 78806, "ending"],
    ["지원한다면서", ["지원하", "는다면서"], "는다면서", "Report / confirmation", 78804, "ending"],
    ["학생이라면서", ["학생", "이", "라면서"], "라면서", "Copular / factual report", 78807, "ending"],
    ["먹으라면서", ["먹", "으라면서"], "으라면서", "Reported command / confirmation", 78808, "ending"],
    ["먹더라면서", ["먹", "더라면서"], "더라면서", "Retrospective report", 81529, "ending"],
    ["먹자면서", ["먹", "자면서"], "자면서", "Reported proposal / confirmation", 78809, "ending"],
    ["먹냐면서", ["먹", "냐면서"], "냐면서", "Reported question", 86922, "ending"],
    ["먹느냐면서", ["먹", "느냐면서"], "느냐면서", "Reported question", 88031, "ending"],
    ["좋으냐면서", ["좋", "으냐면서"], "으냐면서", "Reported question", 86119, "ending"],
    ["모자란다면서도", ["모자라", "는다면서", "도"], "도", "Also / even", 86258, "particle"],
    ["필요하다면서", ["필요하", "다면서"], "다면서", "Report / confirmation", 78806, "ending"],
    ["극복하겠다며", ["극복하", "겠", "다며"], "다며", "Report / confirmation", 81466, "ending"],
    ["먹는다면서요", ["먹", "는다면서", "요"], "요", "Polite", 86116, "particle"],
    ["된단", ["되", "는단"], "는단", "Quoted modifier", 86207, "ending"],
    ["노력했단", ["노력하", "였", "단"], "단", "Quoted modifier / conditional", 86205, "ending"],
    ["먹는단", ["먹", "는단"], "는단", "Quoted modifier", 86207, "ending"],
    ["하신단", ["하", "시", "는단"], "는단", "Quoted modifier", 86207, "ending"],
    ["먹잔", ["먹", "잔"], "잔", "Quoted proposal", 83897, "ending"],
    ["학생이냔", ["학생", "이", "냔"], "냔", "Quoted question", 85653, "ending"],
    ["누구냔", ["누구", "이", "냔"], "냔", "Quoted question", 85653, "ending"],
    ["먹느냔", ["먹", "느냔"], "느냔", "Quoted question", 85659, "ending"],
    ["좋으냔", ["좋", "으냔"], "으냔", "Quoted question", 85664, "ending"],
    ["먹다간", ["먹", "다간"], "다간", "Change / conditional", 73746, "ending"],
    ["먹다가는", ["먹", "다가는"], "다가는", "Change / conditional", 73730, "ending"],
    ["먹어보단", ["먹", "어", "보", "단"], "단", "Quoted modifier / conditional", 86205, "ending"],
    ["하다니", ["하", "다니"], "다니", "Surprise / repeated question", 74141, "ending"],
    ["하신다니", ["하", "시", "는다니"], "는다니", "Present report / surprise", 75475, "ending"],
    ["먹는다니", ["먹", "는다니"], "는다니", "Present report / surprise", 75475, "ending"],
    ["학생이라니", ["학생", "이", "라니"], "라니", "Copular / factual report", 81584, "ending"],
    ["먹으라니", ["먹", "으라니"], "으라니", "Reported command / surprise", 80893, "ending"],
    ["가라니", ["가", "으라니"], "으라니", "Reported command / surprise", 80893, "ending"],
    ["먹더라니", ["먹", "더라니"], "더라니", "Retrospective report", 75986, "ending"],
    ["먹더라니", ["먹", "더", "라니"], "라니", "Copular / factual report", 81584, "ending"],
    ["먹자니", ["먹", "자니"], "자니", "Reported proposal", 85768, "ending"],
    ["학생이냐니", ["학생", "이", "냐니"], "냐니", "Reported question", 87423, "ending"],
    ["먹느냐니", ["먹", "느냐니"], "느냐니", "Reported question", 87424, "ending"],
    ["좋으냐니", ["좋", "으냐니"], "으냐니", "Reported question", 87425, "ending"],
    ["먹어보다니", ["먹", "어", "보", "다니"], "다니", "Surprise / repeated question", 74141, "ending"],
    ["하신다니요", ["하", "시", "는다니", "요"], "요", "Polite", 86116, "particle"],
    ["먹고있으라니요", ["먹", "고", "있", "으라니", "요"], "요", "Polite", 86116, "particle"],
    ["필생토록", ["필생", "토록"], "토록", "Throughout / to the extent", 86121, "particle"],
    ["그토록", ["그", "토록"], "토록", "Throughout / to the extent", 86121, "particle"],
    ["학생마냥", ["학생", "마냥"], "마냥", "Like / as if", 80341, "particle"],
    ["아이들마냥", ["아이", "들", "마냥"], "마냥", "Like / as if", 80341, "particle"],
    ["오늘만치", ["오늘", "만치"], "만치", "As much as / limited to", 80343, "particle"],
    ["학교에서만치", ["학교", "에서", "만치"], "만치", "As much as / limited to", 80343, "particle"],
    ["있어서만치는", ["있", "어서", "만치", "는"], "는", "Topic / contrast", 85851, "particle"],
    ["있어서만큼은", ["있", "어서", "만큼", "은"], "은", "Topic / contrast", 86111, "particle"],
    ["역사까지를", ["역사", "까지", "를"], "를", "Object / emphasis", 85764, "particle"],
    ["여기까지가", ["여기", "까지", "가"], "가", "Subject / emphasis", 66341, "particle"],
    ["페이지까지로", ["페이지", "까지", "로"], "로", "Direction / means / role", 85761, "particle"],
    ["정착되기까지에는", ["정착되", "기", "까지", "에", "는"], "는", "Topic / contrast", 85851, "particle"],
    ["제목부터가", ["제목", "부터", "가"], "가", "Subject / emphasis", 66341, "particle"],
    ["교수님들까지가", ["교수", "님", "들", "까지", "가"], "가", "Subject / emphasis", 66341, "particle"],
    ["역사까질", ["역사", "까지", "를"], "를", "Object / emphasis", 85764, "particle"],
    ["아파트치고", ["아파트", "치고"], "치고", "Generalization / exception", 73015, "particle"],
    ["학생치고는", ["학생", "치고는"], "치고는", "Against expectations", 83882, "particle"],
    ["음식치고서", ["음식", "치고서"], "치고서", "Emphatic generalization / exception", 73016, "particle"],
    ["아이들치고", ["아이", "들", "치고"], "치고", "Generalization / exception", 73015, "particle"],
    ["교수님들치고서", ["교수", "님", "들", "치고서"], "치고서", "Emphatic generalization / exception", 73016, "particle"],
    ["아이들치고서", ["아이", "들", "치고서"], "치고서", "Emphatic generalization / exception", 73016, "particle"],
    ["치렀으되", ["치르", "었", "으되"], "으되", "Contrast / qualification / quotation", 80291, "ending"],
    ["그리되", ["그리", "으되"], "으되", "Contrast / qualification / quotation", 80291, "ending"],
    ["살되", ["살", "으되"], "으되", "Contrast / qualification / quotation", 80291, "ending"],
    ["있으되", ["있", "으되"], "으되", "Contrast / qualification / quotation", 80291, "ending"],
    ["학생이었으되", ["학생", "이", "었", "으되"], "으되", "Contrast / qualification / quotation", 80291, "ending"],
    ["먹고있으되", ["먹", "고", "있", "으되"], "으되", "Contrast / qualification / quotation", 80291, "ending"],
    ["학생답되", ["학생", "답", "으되"], "으되", "Contrast / qualification / quotation", 80291, "ending"],
    ["좋다는데도", ["좋", "다는데", "도"], "도", "Also / even", 86258, "particle"],
    ["먹는다는데도", ["먹", "는다는데", "도"], "도", "Also / even", 86258, "particle"],
    ["학생이라는데도", ["학생", "이", "라는데", "도"], "도", "Also / even", 86258, "particle"],
    ["먹으라는데도", ["먹", "으라는데", "도"], "도", "Also / even", 86258, "particle"],
    ["풍속이었다네", ["풍속", "이", "었", "다네"], "다네", "Information / report", 75191, "ending"],
    ["먹는다네", ["먹", "는다네"], "는다네", "Information / report", 75175, "ending"],
    ["산다네", ["살", "는다네"], "는다네", "Information / report", 75175, "ending"],
    ["학생이라네", ["학생", "이", "라네"], "라네", "Copular / factual report", 75476, "ending"],
    ["먹으라네", ["먹", "으라네"], "으라네", "Reported command / request", 69096, "ending"],
    ["있다는데", ["있", "다는데"], "다는데", "Report / background", 82257, "ending"],
    ["간다는데", ["가", "는다는데"], "는다는데", "Report / background", 82255, "ending"],
    ["대부분이라는데", ["대부분", "이", "라는데"], "라는데", "Copular / factual background", 82259, "ending"],
    ["먹으라는데", ["먹", "으라는데"], "으라는데", "Reported command / background", 86598, "ending"],
    ["먹더라네", ["먹", "더라네"], "더라네", "Retrospective report", 89635, "ending"],
    ["먹더라네", ["먹", "더", "라네"], "라네", "Copular / factual report", 75476, "ending"],
    ["먹더라는데", ["먹", "더라는데"], "더라는데", "Retrospective report / background", 86356, "ending"],
    ["먹더라는데", ["먹", "더", "라는데"], "라는데", "Copular / factual background", 82259, "ending"],
    ["의사더라는데", ["의사", "이", "더라는데"], "더라는데", "Retrospective report / background", 86356, "ending"],
    ["판매한다네요", ["판매하", "는다네", "요"], "요", "Polite", 86116, "particle"],
    ["놔", ["놓", "어"], "어", "Connective / informal", 86094, "ending"],
    ["놨었지요", ["놓", "었", "었", "지요"], "지요", "Confirmation / question / suggestion", 85770, "ending"],
    ["내놔요", ["내놓", "어요"], "어요", "Polite informal", 86571, "ending"],
    ["먹어놨다", ["먹", "어", "놓", "었", "다"], "다", "Plain / dictionary ending", 85041, "ending"],
    ["놔두었다", ["놓", "어", "두", "었", "다"], "다", "Plain / dictionary ending", 85041, "ending"],
    ["놔두었다", ["놔두", "었", "다"], "다", "Plain / dictionary ending", 85041, "ending"],
    ["좋아놔서", ["좋", "어", "놓", "어서"], "어서", "Sequence / reason / means", 80215, "ending"],
    ["학생이어놔서", ["학생", "이", "어", "놓", "어서"], "어서", "Sequence / reason / means", 80215, "ending"],
    ["뭔지", ["뭐", "이", "은지"], "은지", "Uncertainty / wondering", 87432, "ending"],
    ["뭔가", ["뭐", "이", "은가"], "은가", "Question / wondering", 86125, "ending"],
    ["뭔가요", ["뭐", "이", "은가요"], "은가요", "Question / wondering (polite)", 86125, "ending"],
    ["뭘까", ["뭐", "이", "을까"], "을까", "Question / proposal / conjecture", 86120, "ending"],
    ["뭘까요", ["뭐", "이", "을까요"], "을까요", "Question / proposal / conjecture (polite)", 82348, "ending"],
    ["누굴지", ["누구", "이", "을지"], "을지", "Uncertainty / wondering", 86133, "ending"],
    ["건지", ["것", "이", "은지"], "은지", "Uncertainty / wondering", 87432, "ending"],
    ["먹긴지", ["먹", "기", "이", "은지"], "은지", "Uncertainty / wondering", 87432, "ending"],
    ["뭔가보다", ["뭐", "이", "은가", "보", "다"], "다", "Plain / dictionary ending", 85041, "ending"],
    ["먹던", ["먹", "더", "은"], "은", "Noun modifier", 80344, "ending"],
    ["먹던", ["먹", "던"], "던", "Recalled noun modifier / question", 86038, "ending"],
    ["먹던가", ["먹", "더", "은가"], "은가", "Question / wondering", 86125, "ending"],
    ["먹던가", ["먹", "던가"], "던가", "Recalled question / wondering", 89043, "ending"],
    ["먹던지", ["먹", "더", "은지"], "은지", "Uncertainty / wondering", 87432, "ending"],
    ["먹던지", ["먹", "던지"], "던지", "Recalled reason / wondering", 87431, "ending"],
    ["의사던가", ["의사", "이", "던가"], "던가", "Recalled question / wondering", 89043, "ending"],
    ["먹던가요", ["먹", "던가", "요"], "요", "Polite", 86116, "particle"],
    ["먹던가싶다", ["먹", "던가", "싶", "다"], "다", "Plain / dictionary ending", 85041, "ending"],
    ["갈수록", ["가", "을수록"], "을수록", "The more … the more", 74356, "ending"],
    ["먹나요", ["먹", "나", "요"], "요", "Polite", 86116, "particle"],
    ["먹기", ["먹", "기"], "기", "Nominalizer", 72222, "ending"],
    ["먹음", ["먹", "음"], "음", "Nominalizer", 78528, "ending"],
    ["먹기다", ["먹", "기", "이", "다"], "다", "Plain / dictionary ending", 85041, "ending"],
    ["가며", ["가", "으며"], "으며", "And / while", 80257, "ending"],
    ["가면서", ["가", "으면서"], "으면서", "While / simultaneous contrast", 80267, "ending"],
    ["가므로", ["가", "으므로"], "으므로", "Because", 80270, "ending"],
    ["먹어서야", ["먹", "어서야"], "어서야", "Only after / emphatic reason", 86569, "ending"],
    ["먹더라", ["먹", "더", "라"], "라", "Statement / reason / contrast", 79275, "ending"],
    ["먹더라", ["먹", "더라"], "더라", "Recalled experience", 81524, "ending"],
    ["먹더니", ["먹", "더", "으니"], "으니", "Reason / premise / question", 80142, "ending"],
    ["먹더니까", ["먹", "더", "으니까"], "으니까", "Reason / premise", 80137, "ending"],
    ["먹더군요", ["먹", "더군요"], "더군요", "Recalled realization (polite)", 86281, "ending"],
    ["학생이더군요", ["학생", "이", "더군요"], "더군요", "Recalled realization (polite)", 86281, "ending"],
    ["의사겠지", ["의사", "이", "겠", "지"], "지", "Connective / final", 78636, "ending"],
    ["최고더군요", ["최고", "이", "더군요"], "더군요", "Recalled realization (polite)", 86281, "ending"],
    ["최고더군요", ["최고", "이", "더", "군", "요"], "요", "Polite", 86116, "particle"],
    ["의사겠더라", ["의사", "이", "겠", "더라"], "더라", "Recalled experience", 81524, "ending"],
    ["의사던데요", ["의사", "이", "던데요"], "던데요", "Recalled background (polite)", 85637, "ending"],
    ["먹기겠다", ["먹", "기", "이", "겠", "다"], "다", "Plain / dictionary ending", 85041, "ending"],
    ["가지고서", ["가지", "고서"], "고서", "After / reason / condition", 78584, "ending"],
    ["돌리고서는", ["돌리", "고서", "는"], "는", "Topic / contrast", 85851, "particle"],
    ["되어서야", ["되", "어서야"], "어서야", "Only after / emphatic reason", 86569, "ending"],
    ["되어서야", ["되", "어서", "야"], "야", "Emphasis / address", 70339, "particle"],
    ["공부해서야", ["공부하", "여서야"], "어서야", "Only after / emphatic reason", 86569, "ending"],
    ["나오면서부터", ["나오", "으면서", "부터"], "부터", "From / starting at", 70055, "particle"],
    ["통해서보다는", ["통하", "여서", "보다", "는"], "는", "Topic / contrast", 85851, "particle"],
    ["먹고계시냐", ["먹", "고", "계시", "냐"], "냐", "Question", 76230],
    ["먹고계시냐는", ["먹", "고", "계시", "냐는"], "냐는", "Quoted question", 86030],
    ["먹고싶으냐", ["먹", "고", "싶", "으냐"], "으냐", "Question", 76235],
    ["먹고싶으시냐", ["먹", "고", "싶", "시", "냐"], "냐", "Question", 76230],
    ["먹고싶었냐", ["먹", "고", "싶", "었", "냐"], "냐", "Question", 76230],
    ["먹고는있느냐", ["먹", "고", "는", "있", "느냐"], "느냐", "Question", 76231],
    ["많으냐", ["많", "으냐"], "으냐", "Question", 76235],
    ["먹고는있다네", ["먹", "고", "는", "있", "다네"], "다네", "Information / report", 75191, "ending"],
    ["먹곤있다", ["먹", "고", "는", "있", "다"], "다", "Plain / dictionary ending", 85041],
    ["앉아는있다", ["앉", "어", "는", "있", "다"], "다", "Plain / dictionary ending", 85041],
    ["앉아는계셨다", ["앉", "어", "는", "계시", "었", "다"], "다", "Plain / dictionary ending", 85041],
    ["먹고는계셨다", ["먹", "고", "는", "계시", "었", "다"], "다", "Plain / dictionary ending", 85041],
    ["먹고는싶다", ["먹", "고", "는", "싶", "다"], "다", "Plain / dictionary ending", 85041],
    ["먹곤싶다", ["먹", "고", "는", "싶", "다"], "다", "Plain / dictionary ending", 85041],
    ["학생이고는싶다", ["학생", "이", "고", "는", "싶", "다"], "다", "Plain / dictionary ending", 85041],
    ["의사곤싶다", ["의사", "이", "고", "는", "싶", "다"], "다", "Plain / dictionary ending", 85041],
    ["선수셨다", ["선수", "이", "시", "었", "다"], "다", "Plain / dictionary ending", 85041],
    ["의사시니까", ["의사", "이", "시", "으니까"], "으니까", "Reason / premise", 80137],
    ["의사셨어요", ["의사", "이", "시", "었", "어요"], "어요", "Polite informal", 86571],
    ["의사세요", ["의사", "이", "으세요"], "으세요", "Polite statement / question / request", 86609],
    ["의사십니까", ["의사", "이", "시", "습니까"], "습니까", "Formal polite question", 79402],
    ["배우셨었다", ["배우", "이", "시", "었", "었", "다"], "다", "Plain / dictionary ending", 85041],
    ["노동자니까", ["노동자", "이", "으니까"], "으니까", "Reason / premise", 80137, "ending"],
    ["어디니", ["어디", "이", "니"], "니", "Question / reason / statement", 76426, "ending"],
    ["의사고", ["의사", "이", "고"], "고", "Connective / final", 78583, "ending"],
    ["의사지만", ["의사", "이", "지만"], "지만", "But / although", 78638, "ending"],
    ["의사거든", ["의사", "이", "거든"], "거든", "If / explaining a reason", 66501, "ending"],
    ["의사거든요", ["의사", "이", "거든요"], "거든요", "Explaining a reason (polite)", 66503, "ending"],
    ["의사네", ["의사", "이", "네"], "네", "Statement / realization", 77333, "ending"],
    ["최고네요", ["최고", "이", "네요"], "네요", "Realization / seeking agreement (polite)", 85934, "ending"],
    ["의사지만은", ["의사", "이", "지만", "은"], "은", "Topic / contrast", 86111, "particle"],
    ["구두다", ["구두", "다"], "다", "Enumeration", 85738, "particle"],
    ["옷이다", ["옷", "이다"], "이다", "Enumeration", 86118, "particle"],
    ["먹기다", ["먹", "기", "다"], "다", "Enumeration", 85738, "particle"],
    ["학생들이다", ["학생", "들", "이다"], "이다", "Enumeration", 86118, "particle"],
    ["강에다", ["강", "에다"], "에다", "Location / addition", 73013, "particle"],
    ["강에다", ["강", "에", "다"], "다", "Adverbial emphasis", 41693, "particle"],
    ["학교에다가", ["학교", "에다가"], "에다가", "Location / addition", 73014, "particle"],
    ["학교에다가", ["학교", "에", "다가"], "다가", "Adverbial emphasis", 41695, "particle"],
    ["친구에게다", ["친구", "에게다"], "에게다", "Emphatic recipient", 80293, "particle"],
    ["친구에게다가", ["친구", "에게다가"], "에게다가", "Emphatic recipient", 86573, "particle"],
    ["친구한테다", ["친구", "한테다"], "한테다", "Emphatic recipient", 83879, "particle"],
    ["친구한테다가", ["친구", "한테다가"], "한테다가", "Emphatic recipient", 83880, "particle"],
    ["서울로다가", ["서울", "로다가"], "로다가", "Emphatic direction / means", 86550, "particle"],
    ["손으로다가", ["손", "으로다가"], "으로다가", "Emphatic direction / means", 86577, "particle"],
    ["노동자보고", ["노동자", "보고"], "보고", "Recipient / addressee", 70051, "particle"],
    ["나더러", ["나", "더러"], "더러", "Recipient / addressee", 70037, "particle"],
    ["저기다", ["저기", "다"], "다", "Enumeration / emphasis", 41693, "particle"],
    ["어디다가", ["어디", "다가"], "다가", "Adverbial emphasis", 41695, "particle"],
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
    if (["놔", "놨었지요", "내놔요", "먹어놨다", "좋아놔서", "학생이어놔서"].includes(word) || (word === "놔두었다" && expected[0] === "놓")) {
      assert.ok(data.records[0].analysis.analyses[Number(choice)].rules.includes("contraction.noh"));
      assert.match(await breakdown.innerText(), /Expanded \/ normalized/);
    }
    if (["다네", "는다네", "라네", "으라네", "다는데", "는다는데", "라는데", "으라는데", "더라네", "더라는데"].includes(form) || word === "판매한다네요") {
      assert.ok(data.records[0].analysis.analyses[Number(choice)].rules.includes("ending.reporting_ne"));
      for (const source of grammarLabels["-" + (word === "판매한다네요" ? "는다네" : form)].sources) {
        assert.ok(data.grammar["-" + (word === "판매한다네요" ? "는다네" : form)].some(e => e.id === `krdict:${source.id}`));
      }
    }
    if (form === "으라네") assert.ok(!data.grammar["-으라네"].some(e => e.id === "krdict:75476"));
    if (form === "으되") {
      assert.ok(data.records[0].analysis.analyses[Number(choice)].rules.includes("ending.contrast_doe"));
      assert.ok(data.grammar["-으되"].some(e => e.id === "krdict:80289"));
    }
    if (["치고", "치고는", "치고서"].includes(form)) {
      assert.ok(data.records[0].analysis.analyses[Number(choice)].rules.includes("particle.chigo"));
    }
    if (["역사까지를", "여기까지가", "페이지까지로", "정착되기까지에는", "제목부터가", "교수님들까지가", "역사까질"].includes(word)) {
      assert.ok(data.records[0].analysis.analyses[Number(choice)].rules.includes("particle.range_case"));
    }
    if (["토록", "마냥", "만치"].includes(form)) {
      assert.ok(data.records[0].analysis.analyses[Number(choice)].rules.includes("particle.comparison_extent"));
    }
    if (["있어서만치는", "있어서만큼은"].includes(word)) {
      assert.ok(data.records[0].analysis.analyses[Number(choice)].rules.includes("particle.comparison_seo"));
    }
    if (word === "그토록") {
      const readings = await breakdown.getByRole("combobox").locator("option").allTextContents();
      assert.ok(readings.some(text => text.replace(/^\d+\. /, "") === "그토록"));
    }
    if (form === "만치") assert.ok(!data.grammar["만치"].some(e => e.id === "krdict:53006"));
    if (form === "마냥") assert.ok(!data.grammar["마냥"].some(e => e.id === "krdict:51528"));
    if (data.records[0].analysis.analyses[Number(choice)].morphemes.some(m =>
        Object.hasOwn(grammarLabels, "-" + m.form) && /(?:며|면서)$/.test(m.form) && !["으며", "으면서"].includes(m.form))) {
      assert.ok(data.records[0].analysis.analyses[Number(choice)].rules.includes("ending.reporting_myeo"));
    }
    // Display may use 여 after 하 while lookup retains canonical 어.
    await breakdown.getByRole("button", {name: `${expected.at(-1)} ${label}`, exact: true}).click();
    await page.waitForFunction(id => document.querySelector('a[href*="ParaWordNo="]')?.getAttribute("href")?.includes(`ParaWordNo=${id}`), id);
    assert.ok(data.grammar[kind === "particle" ? form : `-${form}`].some(e => e.id === `krdict:${id}`));
    if (["단", "는단", "잔", "냔", "느냔", "으냔", "다간", "다가는"].includes(form)) {
      assert.ok(data.records[0].analysis.analyses[Number(choice)].rules.includes("ending.short_clause"));
      for (const source of grammarLabels["-" + form].sources) {
        const entry = data.grammar["-" + form].find(e => e.id === `krdict:${source.id}`);
        assert.ok(entry, `${word}: ${source.id}`);
        const index = await page.locator(".entry-choices button").evaluateAll((buttons, e) => buttons.findIndex(b =>
          b.querySelector("span")?.textContent === e.headword + (e.homonym === "0" ? "" : e.homonym) &&
          b.querySelector("small")?.textContent === e.pos), entry);
        assert.ok(index >= 0, `${word}: ${source.id}`);
        await page.locator(".entry-choices button").nth(index).click();
        await page.waitForFunction(id => document.querySelector('a[href*="ParaWordNo="]')?.getAttribute("href")?.includes(`ParaWordNo=${id}`), source.id);
      }
      if (form === "단") assert.ok(!data.grammar["-단"].some(e => e.id === "krdict:73350"));
    }
    if (["다니", "는다니", "라니", "으라니", "더라니", "자니", "냐니", "느냐니", "으냐니"].includes(form)) {
      assert.ok(data.records[0].analysis.analyses[Number(choice)].rules.includes("ending.reporting_ni"));
      for (const source of grammarLabels["-" + form].sources) {
        const entry = data.grammar["-" + form].find(e => e.id === `krdict:${source.id}`);
        assert.ok(entry, `${word}: ${source.id}`);
        const index = await page.locator(".entry-choices button").evaluateAll((buttons, e) => buttons.findIndex(b =>
          b.querySelector("span")?.textContent === e.headword + (e.homonym === "0" ? "" : e.homonym) &&
          b.querySelector("small")?.textContent === e.pos), entry);
        assert.ok(index >= 0, `${word}: ${source.id}`);
        await page.locator(".entry-choices button").nth(index).click();
        await page.waitForFunction(id => document.querySelector('a[href*="ParaWordNo="]')?.getAttribute("href")?.includes(`ParaWordNo=${id}`), source.id);
      }
      if (form === "으라니") assert.ok(!data.grammar["-으라니"].some(e => ["krdict:81584", "krdict:85121"].includes(e.id)));
    }
    if (["먹고는싶다", "먹곤싶다", "학생이고는싶다", "의사곤싶다", "먹고는있다네", "먹곤있다", "앉아는있다", "앉아는계셨다", "먹고는계셨다"].includes(word)) {
      const selected = data.records[0].analysis.analyses[Number(choice)];
      assert.ok(selected.rules.includes("auxiliary.internal_particle"));
      if (word.includes("곤")) {
        assert.ok(selected.rules.includes("particle.contraction.n"));
        assert.match(await breakdown.innerText(), /Expanded \/ normalized/);
      }
      await breakdown.getByRole("button", {name: "는 Topic / contrast", exact: true}).click();
      await page.waitForFunction(() => document.querySelector('a[href*="ParaWordNo="]')?.getAttribute("href")?.includes("ParaWordNo=85851"));
    }
    if (word === "공부해서야") {
      for (const id of [86567, 86569, 86584]) {
        assert.ok(data.grammar["-어서야"].some(e => e.id === `krdict:${id}`));
      }
    }
    if (word === "선수셨다") {
      const selected = data.records[0].analysis.analyses[Number(choice)];
      assert.ok(selected.rules.includes("copula.omitted_honorific"));
      assert.match(await breakdown.innerText(), /Expanded \/ normalized/);
      assert.ok(!data.records[0].analysis.analyses.some(a => a.lemmas.some(l => l.text === "선수이다")));
      await breakdown.getByRole("button", {name: "시 Subject honorific", exact: true}).click();
      await page.waitForFunction(() => document.querySelector('a[href*="ParaWordNo="]')?.getAttribute("href")?.includes("ParaWordNo=80330"));
      assert.ok(data.grammar["-시-"].some(e => e.id === "krdict:80329"));
    }
    if (word === "의사세요") {
      assert.ok(data.grammar["-으세요"].some(e => e.id === "krdict:86558"));
    }
    if (word === "저기다" && kind === "particle") {
      assert.ok(data.grammar["다"].some(e => e.id === "krdict:85738"));
      const selected = data.records[0].analysis.analyses[Number(choice)];
      assert.ok(selected.rules.includes("particle.enumerative_da"));
      assert.ok(selected.rules.includes("particle.emphatic_adverbial"));
      assert.match(await breakdown.getByRole("button", {name: `${form} ${label}`, exact: true}).getAttribute("title"), /85738/);
    }
    if (word === "옷이다" && kind === "particle") {
      const copula = data.records[0].analysis.analyses.findIndex(a =>
        a.lemmas.length === 2 && a.lemmas[0].text === "옷" &&
        a.lemmas[1].kind === "copula" && a.morphemes.length === 1 &&
        a.morphemes[0].form === "다" && a.morphemes[0].kind === "ending");
      assert.ok(copula >= 0);
      await breakdown.getByRole("combobox").selectOption(String(copula));
      assert.deepEqual(await breakdown.locator(".part-form").allTextContents(), ["옷", "이", "다"]);
      await breakdown.locator("button").filter({has: page.locator(".part-form", {hasText: /^이$/})}).click();
      await page.waitForFunction(() => document.querySelector('a[href*="ParaWordNo="]')?.getAttribute("href")?.includes("ParaWordNo=86232"));
    }
    if (form === "을까요") assert.ok(data.grammar["-을까요"].some(e => e.id === "krdict:82350"));
    const shortConnective = {"으며": 80253, "으면서": 80266, "으므로": 80268}[form];
    if (shortConnective) assert.ok(data.grammar[`-${form}`].some(e => e.id === `krdict:${shortConnective}`));
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
    assert.deepEqual(result.grammar["-는다면"].map(e => e.id).sort(),
      grammarLabels["-는다면"].sources.map(s => `krdict:${s.id}`).sort());
  }
  for (const [word, expected, form, label, id] of [
    ["먹으려는", ["먹", "으려는"], "으려는", "Intending / about to", 86717],
    ["살려는", ["살", "으려는"], "으려는", "Intending / about to", 86688],
    ["먹으시려는", ["먹", "시", "으려는"], "으려는", "Intending / about to", 86688],
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
    if (form === "으려는") {
      await page.locator(".entry-choices button").filter({hasText: id === 86688 ? "-려는" : "-으려는"}).click();
    }
    await page.waitForFunction((headword) =>
      document.querySelector(".entry-heading h2")?.textContent?.startsWith(headword)
      && document.querySelector(".entry-meta")?.textContent?.includes("품사 없음"),
      id === 86688 ? "-려는" : `-${form}`,
    );
    assert.match(
      await page.getByRole("link", { name: "Open original dictionary entry" }).getAttribute("href"),
      new RegExp(`ParaWordNo=${id}`),
    );
    const result = await (await post("analyze", { text: word })).json();
    assert.deepEqual(result.grammar[`-${form}`].map((e) => e.id).sort(), grammarLabels[`-${form}`].sources.map(e => `krdict:${e.id}`).sort());
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

  // Intention and uncertainty forms expose allomorphs and expression homonyms.
  for (const [word, expected, form, label, id, key = `-${form}`] of [
    ["좋으려나", ["좋", "으려나"], "으려나", "Wonder / intention question", 79263],
    ["가려나", ["가", "으려나"], "으려나", "Wonder / intention question", 79262],
    ["가려나", ["가", "으려나"], "으려나", "Wonder / intention question", 86503],
    ["먹으려나", ["먹", "으려나"], "으려나", "Wonder / intention question", 86715],
    ["모였으려나", ["모이", "었", "으려나"], "으려나", "Wonder / intention question", 79263],
    ["학생이려나", ["학생", "이", "으려나"], "으려나", "Wonder / intention question", 79262],
    ["오려나봐", ["오", "으려나", "보", "어"], "으려나", "Wonder / intention question", 79262],
    ["좋으려나요", ["좋", "으려나", "요"], "으려나", "Wonder / intention question", 79263],
    ["잡아다", ["잡", "어다"], "어다", "Then / using the result", 86096],
    ["빌려다", ["빌리", "어다"], "어다", "Then / using the result", 86097],
    ["해다", ["하", "여다"], "여다", "Then / using the result", 86144, "-어다"],
    ["잡아다가", ["잡", "어다가"], "어다가", "Then / using the result", 86098],
    ["빌려다가", ["빌리", "어다가"], "어다가", "Then / using the result", 86099],
    ["해다가", ["하", "여다가"], "여다가", "Then / using the result", 86143, "-어다가"],
    ["모셔다드렸어요", ["모시", "어다", "드리", "었", "어요"], "어다", "Then / using the result", 86097],
    ["빌려다놓았다", ["빌리", "어다", "놓", "었", "다"], "어다", "Then / using the result", 86097],
    ["먹으려거든", ["먹", "으려거든"], "으려거든", "Conditional intention", 80336],
    ["살려거든", ["살", "으려거든"], "으려거든", "Conditional intention", 80334],
    ["먹으려기에", ["먹", "으려기에"], "으려기에", "Intention as a reason", 86547],
    ["살려기에", ["살", "으려기에"], "으려기에", "Intention as a reason", 86539],
    ["먹으려는데", ["먹", "으려는데"], "으려는데", "Intention / impending situation", 86720],
    ["살려는데", ["살", "으려는데"], "으려는데", "Intention / impending situation", 86691],
    ["먹으려다", ["먹", "으려다"], "으려다", "Interrupted intention", 86727],
    ["살려다", ["살", "으려다"], "으려다", "Interrupted intention", 86697],
    ["먹으려다가", ["먹", "으려다가"], "으려다가", "Interrupted intention", 86729],
    ["살려다가", ["살", "으려다가"], "으려다가", "Interrupted intention", 86699],
    ["먹으려더니", ["먹", "으려더니"], "으려더니", "Intention followed by a change", 86730],
    ["살려더니", ["살", "으려더니"], "으려더니", "Intention followed by a change", 86700],
    ["먹으려도", ["먹", "으려도"], "으려도", "Despite intending", 86737],
    ["살려도", ["살", "으려도"], "으려도", "Despite intending", 86705],
    ["먹으려야", ["먹", "으려야"], "으려야", "Intention as a condition", 86742],
    ["살려야", ["살", "으려야"], "으려야", "Intention as a condition", 86709],
    ["가려거든", ["가", "으려거든"], "으려거든", "Conditional intention", 80335],
    ["먹으려거든", ["먹", "으려거든"], "으려거든", "Conditional intention", 80337],
    ["먹으려다보니", ["먹", "으려다", "보", "으니"], "으려다", "Interrupted intention", 86727],
    ["같을는지", ["같", "을는지"], "을는지", "Uncertain possibility / question", 86615],
    ["갔을는지", ["가", "었", "을는지"], "을는지", "Uncertain possibility / question", 86615],
    ["살는지", ["살", "을는지"], "을는지", "Uncertain possibility / question", 86488],
    ["먹으려는가", ["먹", "으려는가"], "으려는가", "Intention / impending event question", 86719],
    ["가려는가", ["가", "으려는가"], "으려는가", "Intention / impending event question", 86689],
    ["먹으려는지", ["먹", "으려는지"], "으려는지", "Uncertain intention / impending event", 86721],
    ["먹으시려는지", ["먹", "시", "으려는지"], "으려는지", "Uncertain intention / impending event", 86693],
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
    await breakdown.getByRole("button", {name: `${form} ${label}`, exact: true}).click();
    const result = await (await post("analyze", {text: word})).json();
    const sources = result.grammar[key];
    assert.deepEqual(sources.map(e => e.id).sort(), grammarLabels[key].sources.map(e => `krdict:${e.id}`).sort());
    const entry = sources.find(e => e.id === `krdict:${id}`);
    const index = await page.locator(".entry-choices button").evaluateAll((buttons, e) =>
      buttons.findIndex(b => b.querySelector("span")?.textContent === e.headword + (e.homonym === "0" ? "" : e.homonym)
        && b.querySelector("small")?.textContent === e.pos), entry);
    assert.ok(index >= 0, `${word}: ${id}`);
    await page.locator(".entry-choices button").nth(index).click();
    await page.waitForFunction(id => document.querySelector('a[href*="ParaWordNo="]')?.getAttribute("href")?.includes(`ParaWordNo=${id}`), id);
    const cli = JSON.parse(execFileSync(cliBin, ["word", word], {encoding: "utf8"}));
    assert.deepEqual(result.records[0].analysis.analyses, cli.analyses);
  }

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
    ["먹고싶어하고있다", ["먹", "고", "싶", "어", "하", "고", "있", "다"]],
    ["학생답게하고있다", ["학생", "답", "게", "하", "고", "있", "다"]],
    ["먹어보지않고있다", ["먹", "어", "보", "지", "않", "고", "있", "다"]],
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
  for (const [word, form, sourceIds] of [
    ["간다", "는다", [73909, 85033]],
    ["간다고", "는다고", [74683, 86060, 86061]],
    ["간다는", "는다는", [82213]],
    ["간다면", "는다면", [66956, 68841, 68881]],
  ]) {
    await submit(page, word);
    await waitHeading(page, word);
    const data = await (await post("analyze", {text: word})).json();
    for (const id of sourceIds) {
      const e = data.grammar[`-${form}`].find(e => e.id === `krdict:${id}`);
      assert.ok(e, `${word}: ${id}`);
      const choice = await page.locator(".entry-choices button").evaluateAll((buttons, e) =>
        buttons.findIndex(b => b.querySelector("span")?.textContent === e.headword + (e.homonym === "0" ? "" : e.homonym)
          && b.querySelector("small")?.textContent === e.pos), e);
      assert.ok(choice >= 0, `${word}: ${id} selectable`);
      await page.locator(".entry-choices button").nth(choice).click();
      await page.waitForFunction(id => document.querySelector('a[href*="ParaWordNo="]')?.getAttribute("href")?.includes(`ParaWordNo=${id}`), id);
    }
  }
  const retrospectiveLedger = JSON.parse(await readFile(resolve(root, "tests/fixtures/validity.json"), "utf8"));
  const retrospectiveResults = new Map();
  for (const c of retrospectiveLedger.cases.filter(c => (c.id.startsWith("retrospective-license-") || c.id.startsWith("retrospective-connective-") || c.id.startsWith("retrospective-adnominal-") || c.id.startsWith("question-copula-") || c.id.startsWith("noh-") || c.id.startsWith("report-ne-") || c.id.startsWith("doe-") || c.id.startsWith("chigo-") || c.id.startsWith("range-case-") || c.id.startsWith("extent-") || c.id.startsWith("approximation-") || c.id.startsWith("report-myeo-") || c.id.startsWith("stative-report-") || c.id.startsWith("present-license-") || c.id.startsWith("report-ni-") || c.id.startsWith("short-clause-") || c.id.startsWith("continuative-topic-") || c.id.startsWith("adjectival-question-") || c.id.startsWith("uncertainty-") || c.id.startsWith("intention-connectives-") || c.id.startsWith("result-connectives-") || c.id.startsWith("ryeona-")))) {
    for (const j of c.judgments.filter(j => j.verdict === "forbidden")) {
      if (!retrospectiveResults.has(c.surface)) retrospectiveResults.set(c.surface, await (await post("analyze", {text: c.surface})).json());
      const data = retrospectiveResults.get(c.surface);
      assert.ok(!data.records[0].analysis.analyses.some(a =>
        JSON.stringify(a.lemmas.map(l => l.text)) === JSON.stringify(j.lemmas) &&
        JSON.stringify(a.morphemes.map(m => m.form)) === JSON.stringify(j.morphemes)), `${c.id}: ${j.id}`);
    }
  }
  for (const [word, forbidden] of [
    ["학생겠지", ["학생", "이다"]],
    ["길겠지", ["길", "이다"]],
    ["학생더군요", ["학생", "이다"]],
    ["길더라", ["길", "이다"]],
    ["도우겠지", ["돕", "이다"]],
    ["사겠지", ["살", "이다"]],
    ["의사더겠지", ["의사", "이다"]],
    ["의사겠었다", ["의사", "이다"]],
    ["의사겠시다", ["의사", "이다"]],
    ["의사겠지", ["의사이다"]],
    ["최고더군요", ["최고이다"]],
    ["먹었고서", ["먹다"]],
    ["먹겠고서", ["먹다"]],
    ["먹더고서", ["먹다"]],
    ["도우고서", ["돕다"]],
    ["들고서", ["듣다"]],
    ["학생이고서", ["학생", "이다"]],
    ["먹고싶고서", ["먹다", "싶다"]],
    ["먹고싶지않고서", ["먹다", "싶다", "않다"]],
    ["학생답고서", ["학생"]],
    ["먹고싶어있다", ["먹다", "싶다", "있다"]],
    ["먹고싶고있다", ["먹다", "싶다", "있다"]],
    ["먹고싶어계신다", ["먹다", "싶다", "계시다"]],
    ["학생이고있다", ["학생", "이다", "있다"]],
    ["학생이어있다", ["학생", "이다", "있다"]],
    ["학생이시고계신다", ["학생", "이다", "계시다"]],
    ["의사고있다", ["의사", "이다", "있다"]],
    ["먹고싶지않고있다", ["먹다", "싶다", "않다", "있다"]],
    ["먹고싶잖아계신다", ["먹다", "싶다", "않다", "계시다"]],
    ["먹고는싶어있는다", ["먹다", "싶다", "있다"]],
    ["학생다워있다", ["학생", "있다"]],
    ["먹는가봐있다", ["먹다", "보다", "있다"]],
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
    if (form === "어다가") {
      await page.locator(".entry-choices button").filter({ hasText: "-어다가" }).click();
    }
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
  assert.equal(await page.getByLabel("Exclude known grammar conflicts").isDisabled(), true);
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
