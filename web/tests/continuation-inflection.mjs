import assert from "node:assert/strict";
import { isDeepStrictEqual } from "node:util";
import { spawn, execFileSync } from "node:child_process";
import { readFile, realpath, stat, mkdtemp } from "node:fs/promises";
import { once } from "node:events";
import { gunzipSync } from "node:zlib";
import { resolve } from "node:path";
import { tmpdir } from "node:os";
import { chromium } from "playwright";
const root = process.cwd();
const cli = process.env.KLEM_BIN || resolve(root, "target/release/klem");
const serverBin =
  process.env.KLEM_WEB_BIN || resolve(root, "target/release/klem-web");
const evidence = JSON.parse(
  gunzipSync(
    await readFile(
      process.env.KLEM_INFLECTION_EVIDENCE ||
        resolve(root, "docs/continuation-inflection-runtime.json.gz"),
    ),
  ),
);
const cases = JSON.parse(
  await readFile(
    resolve(root, "tests/fixtures/continuation-inflection-judgments.json"),
    "utf8",
  ),
).cases;
const words = [...new Set(cases.map((c) => c.surface))];
const scratch = await mkdtemp(
  resolve(tmpdir(), "klem-continuation-inflection-browser-"),
);
async function identity(pid) {
  const p = "/proc/" + pid;
  return {
    uid: (await stat(p)).uid,
    start: (await readFile(p + "/stat", "utf8"))
      .split(")")
      .slice(1)
      .join(")")
      .trim()
      .split(/\s+/)[19],
    exe: await realpath(p + "/exe"),
    cwd: await realpath(p + "/cwd"),
    args: await readFile(p + "/cmdline", "utf8"),
  };
}
const server = spawn(
  serverBin,
  [
    "--port",
    "0",
    "--assets",
    process.env.KLEM_WEB_ASSETS || resolve(root, "web/dist"),
    "--dictionary",
    resolve(root, "data/dictionaries/krdict/krdict.db"),
  ],
  { cwd: root, stdio: ["ignore", "ignore", "pipe"] },
);
let browser, stamp;
try {
  const url = await new Promise((resolve, reject) => {
    let text = "";
    const timer = setTimeout(
      () => reject(new Error("server startup timed out")),
      15000,
    );
    server.once("error", reject);
    server.once("exit", () => reject(new Error("server exited")));
    server.stderr.on("data", (s) => {
      text += s;
      const m = text.match(/http:\/\/127\.0\.0\.1:\d+/);
      if (m) {
        clearTimeout(timer);
        resolve(m[0]);
      }
    });
  });
  stamp = await identity(server.pid);
  assert.equal(stamp.uid, process.getuid());
  assert.equal(stamp.exe, await realpath(serverBin));
  browser = await chromium.launch({
    executablePath: process.env.CHROMIUM_PATH,
    args: ["--no-sandbox"],
  });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1100 },
    acceptDownloads: true,
  });
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto(url);
  let submissions = 0,
    selections = 0;
  for (const nfd of [false, true]) {
    const input = nfd ? words.join(" ").normalize("NFD") : words.join(" ");
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
      await page.getByLabel("Your sentence", { exact: true }).fill(input);
      await page
        .getByRole("button", { name: "Analyze sentence", exact: true })
        .click();
      await page.waitForFunction(
        (s) => document.querySelector(".panel-heading h2")?.textContent === s,
        input.split(" ")[0],
      );
      assert.equal(await page.locator(".sentence").textContent(), input);
      assert.equal(await page.locator(".breakdown-word").count(), words.length);
      for (const [index, surface] of words.entries()) {
        const result = evidence.words[surface];
        const expected = result.all.analyses.flatMap((a, i) =>
          result[mode].analyses.some((b) => isDeepStrictEqual(a, b))
            ? [String(i)]
            : [],
        );
        const word = page.locator(".breakdown-word").nth(index);
        const actual = await word
          .locator("option")
          .evaluateAll((options) =>
            options.map((o) => o.value).filter(Boolean),
          );
        assert.deepEqual(
          actual,
          expected,
          mode + " " + surface + " raw indices",
        );
        for (const c of cases.filter((c) => c.surface === surface)) {
          const rawIndex = result.all.analyses.findIndex(
            (a) =>
              isDeepStrictEqual(a.lemmas, c.lemmas) &&
              isDeepStrictEqual(a.morphemes, c.morphemes),
          );
          assert.ok(rawIndex >= 0, c.id);
          assert.equal(
            expected.includes(String(rawIndex)),
            mode !== "compatible" || c.filter_retained,
            c.id,
          );
          if (expected.includes(String(rawIndex))) {
            await word.locator("select").selectOption(String(rawIndex));
            const components = result.api.breakdowns[0][rawIndex];
            assert.equal(
              await word.locator(".part-form").count(),
              components.length,
            );
            selections++;
          }
        }
      }
      const pending = page.waitForEvent("download");
      await page
        .getByRole("button", { name: "Export JSON", exact: true })
        .click();
      const output = JSON.parse(
        await readFile(await (await pending).path(), "utf8"),
      );
      const expected = execFileSync(
        cli,
        [
          "text",
          "--dictionary",
          resolve(root, "data/dictionaries/krdict/krdict.db"),
          ...(flag ? [flag] : []),
        ],
        { input, encoding: "utf8", maxBuffer: 128 * 1024 * 1024 },
      )
        .trim()
        .split("\n")
        .map(JSON.parse);
      assert.deepEqual(output.records, expected);
      submissions++;
    }
  }
  await page.getByLabel("Dictionary matches only").uncheck();
  await page
    .getByLabel("Your sentence", { exact: true })
    .fill("먹고나셔서 아프고난 먹고났더니");
  await page
    .getByRole("button", { name: "Analyze sentence", exact: true })
    .click();
  await page.waitForFunction(
    () =>
      document.querySelector(".panel-heading h2")?.textContent === "먹고나셔서",
  );
  const c = cases.find(
    (c) => c.id === "continuation-inflection-nada-right-honorific",
  );
  const result = evidence.words[c.surface];
  const raw = result.all.analyses.findIndex(
    (a) =>
      isDeepStrictEqual(a.lemmas, c.lemmas) &&
      isDeepStrictEqual(a.morphemes, c.morphemes),
  );
  const word = page.locator(".breakdown-word").first();
  await word.locator("select").selectOption(String(raw));
  assert.ok(
    await page
      .getByText("Known dictionary class conflict.", { exact: false })
      .count(),
  );
  const part = result.api.breakdowns[0][raw].findIndex((c) => c.lemma === 1);
  assert.ok(part >= 0);
  await word.locator(".breakdown-part").nth(part).click();
  await page.waitForFunction(
    () => document.querySelector(".entry-heading h2")?.textContent === "나다2",
  );
  assert.ok(
    await page.locator('.entry-content a[href*="ParaWordNo=62134"]').count(),
  );
  const desktop = resolve(scratch, "desktop.png");
  await page.screenshot({ path: desktop, fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
    true,
  );
  const mobile = resolve(scratch, "mobile.png");
  await page.screenshot({ path: mobile, fullPage: true });
  assert.deepEqual(errors, []);
  console.log(
    JSON.stringify({
      submissions,
      words: words.length,
      policyCases: cases.length,
      selections,
      rawIndicesAndExportsMatchCli: true,
      nativeConflictEntryVisible: true,
      mobileFits: true,
      errors,
      desktop,
      mobile,
    }),
  );
} finally {
  if (browser) await browser.close();
  if (server.exitCode === null) {
    if (stamp) assert.deepEqual(await identity(server.pid), stamp);
    server.kill("SIGTERM");
    await once(server, "exit");
  }
}
