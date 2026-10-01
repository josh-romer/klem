import {
  For,
  Show,
  createMemo,
  createResource,
  createSignal,
  onCleanup,
  onMount,
} from "solid-js";
import {
  analyses,
  api,
  filteredResult,
  grammarHeadword,
  matches,
  readingConditions,
  readingMatches,
  type Entry,
  type Lemma,
  type Result,
  type Status,
  type Token,
} from "./model";
import SentenceBreakdown from "./SentenceBreakdown";
import SpacingSuggestions from "./SpacingSuggestions";

const initial = "어제 친구와 맛있는 음식을 먹어봤어요.";
const examples = [
  "저는 한국어를 공부해요.",
  "먹어봤어요.",
  "학교에서는 책을 읽었어요.",
  "날씨가 추워서 집에 있었어요.",
];
const label = (kind: string) =>
  ({
    predicate: "Predicate",
    nominal: "Nominal",
    auxiliary: "Auxiliary",
    copula: "Copula",
    unclassified: "Unclassified",
    adverbial: "Adverb",
    root: "Root",
  })[kind] ?? kind;

function Arrow() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="1.7"
      aria-hidden="true"
    >
      <path d="M4 12h15m-6-6 6 6-6 6" />
    </svg>
  );
}
function Book() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="1.5"
      aria-hidden="true"
    >
      <path d="M12 6c-3-2-6-2-9-1v14c3-1 6-1 9 1 3-2 6-2 9-1V5c-3-1-6-1-9 1Zm0 0v14" />
    </svg>
  );
}

export default function App() {
  const [text, setText] = createSignal(initial);
  const [status, setStatus] = createSignal<Status>();
  const [connectionError, setConnectionError] = createSignal("");
  const [result, setResult] = createSignal<Result>();
  const [busy, setBusy] = createSignal(false);
  const [error, setError] = createSignal("");
  const [only, setOnly] = createSignal(false);
  const [compatible, setCompatible] = createSignal(false);
  const [suggestSpacing, setSuggestSpacing] = createSignal(false);
  const [selected, setSelected] = createSignal(0);
  const [visible, setVisible] = createSignal(20);
  const [entryId, setEntryId] = createSignal<string>();
  const [entry, { refetch: retryEntry }] = createResource(
    entryId,
    async (id) => (await api<{ entry: Entry }>("entry", { id })).entry,
  );
  let request: AbortController | undefined;
  let generation = 0;
  const token = createMemo(() => result()?.records[selected()]);
  const candidates = createMemo(() =>
    token() ? analyses(token()!, only(), compatible()) : [],
  );
  const entryChoices = createMemo(() => {
    const current = token();
    if (!current) return [];
    const entries = candidates().flatMap((a) => [
      ...a.lemmas.flatMap((l) => matches(current, l)),
      ...a.morphemes.flatMap(
        (m) => result()?.grammar[grammarHeadword(m)] ?? [],
      ),
    ]);
    return [...new Map(entries.map((e) => [e.id, e])).values()];
  });
  const words = createMemo(
    () => result()?.records.filter((t) => t.kind === "word") ?? [],
  );
  const total = createMemo(() =>
    words().reduce((sum, t) => sum + analyses(t, only(), compatible()).length, 0),
  );
  const bytes = createMemo(() => new TextEncoder().encode(text()).length);
  const limit = () => status()?.limits.text_bytes ?? 8000;

  function choose(index: number, data = result()) {
    setSelected(index);
    setVisible(20);
    const current = data?.records[index];
    const first =
      current &&
      analyses(current, only(), compatible()).flatMap((a) =>
        a.lemmas.flatMap((l) => matches(current, l)),
      )[0];
    setEntryId(first?.id);
  }
  function edit(value: string) {
    generation++;
    request?.abort();
    setBusy(false);
    setText(value);
    setError("");
    setResult(undefined);
    setEntryId(undefined);
  }
  async function analyze(value = text()) {
    request?.abort();
    request = new AbortController();
    const current = ++generation;
    setBusy(true);
    setError("");
    setResult(undefined);
    setEntryId(undefined);
    try {
      const data = await api<Result>(
        "analyze",
        { text: value, ...(suggestSpacing() ? { suggest_spacing: true } : {}) },
        request.signal,
      );
      if (current !== generation) return;
      setResult(data);
      choose(
        Math.max(
          0,
          data.records.findIndex((t) => t.kind === "word"),
        ),
        data,
      );
    } catch (e) {
      if (current === generation && (e as Error).name !== "AbortError")
        setError(
          e instanceof Error ? e.message : "Could not analyze this sentence.",
        );
    } finally {
      if (current === generation) setBusy(false);
    }
  }
  async function connect() {
    setConnectionError("");
    try {
      const data = await api<Status>("status");
      setStatus(data);
      if (text() === initial && !result()) void analyze();
    } catch {
      setConnectionError(
        "Cannot reach the local server. Check that klem-web is running, then retry.",
      );
    }
  }
  onMount(connect);
  onCleanup(() => {
    generation++;
    request?.abort();
  });
  function download() {
    const data = result();
    if (!data) return;
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(filteredResult(data, only(), compatible()), null, 2)], {
        type: "application/json",
      }),
    );
    const link = document.createElement("a");
    link.href = url;
    link.download = "klem-sentence.json";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function lemmaButton(current: Token, lemma: Lemma, candidate: number, lemmaIndex: number) {
    const entries = matches(current, lemma);
    return (
      <div class="lemma-part">
        <Show
          when={entries.length > 0}
          fallback={
            <span class="lemma-word" lang="ko">
              {lemma.text}
            </span>
          }
        >
          <button
            class="lemma-word linked"
            lang="ko"
            title={`Look up ${lemma.text}`}
            onClick={() => setEntryId(readingMatches(current, candidate, lemmaIndex)[0].id)}
          >
            {lemma.text}
            <span class="tiny-arrow">↗</span>
          </button>
        </Show>
        <span class="role">{label(lemma.kind)}</span>
        <Show when={status()?.dictionary}>
          <span
            classList={{ "lexical-status": true, found: entries.length > 0 }}
          >
            {entries.length
              ? `${entries.length} dictionary ${entries.length === 1 ? "entry" : "entries"}`
              : "No dictionary match"}
          </span>
        </Show>
      </div>
    );
  }

  return (
    <div class="shell">
      <header class="topbar">
        <a class="brand" href="/" aria-label="klem home">
          <span class="brand-mark">k</span>klem
          <span class="brand-divider" />
          <span class="brand-caption">KOREAN SENTENCE EXPLORER</span>
        </a>
        <span class="local-status">
          <i /> Runs on your computer
        </span>
      </header>
      <main>
        <section class="intro">
          <p class="eyebrow">A CLOSER LOOK AT KOREAN</p>
          <h1>Every word has a story.</h1>
          <p class="lede">
            Unpack a sentence. Explore its lemmas, endings, and meanings.
          </p>
        </section>
        <Show when={connectionError()}>
          <div class="notice error" role="alert">
            {connectionError()}{" "}
            <button onClick={connect}>Retry connection</button>
          </div>
        </Show>
        <section class="editor" aria-label="Sentence input">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void analyze();
            }}
          >
            <div class="editor-label">
              <label for="sentence">Your sentence</label>
              <span lang="ko">한국어</span>
            </div>
            <textarea
              id="sentence"
              value={text()}
              placeholder="Paste or type a Korean sentence…"
              spellcheck={false}
              onInput={(e) => edit(e.currentTarget.value)}
              onKeyDown={(e) => {
                if (
                  (e.ctrlKey || e.metaKey) &&
                  e.key === "Enter" &&
                  !busy() &&
                  text().trim() &&
                  bytes() <= limit() &&
                  status()
                ) {
                  e.preventDefault();
                  void analyze();
                }
              }}
              aria-describedby="input-hint"
            />
            <div class="editor-bottom">
              <span
                id="input-hint"
                classList={{ "input-hint": true, invalid: bytes() > limit() }}
              >
                {bytes() > limit()
                  ? "Please shorten your text (8,000 UTF-8 byte limit)."
                  : "A sentence or short passage. Ctrl / ⌘ + Enter to analyze."}
              </span>
              <button
                class="primary"
                type="submit"
                disabled={
                  busy() || !text().trim() || bytes() > limit() || !status()
                }
              >
                {busy() ? "Analyzing…" : "Analyze sentence"}
                <Arrow />
              </button>
            </div>
          </form>
        </section>
        <div class="examples">
          <span>TRY A SENTENCE</span>
          <For each={examples}>
            {(sample) => (
              <button
                lang="ko"
                onClick={() => {
                  edit(sample);
                  if (status()) void analyze(sample);
                }}
              >
                {sample}
              </button>
            )}
          </For>
        </div>
        <Show when={error()}>
          <div class="notice error" role="alert">
            {error()}
          </div>
        </Show>
        <Show when={status() && !status()!.dictionary}>
          <div class="notice">
            Dictionary not connected. You can explore every rule candidate;
            start the server with a dictionary to see definitions and filter
            matches.
          </div>
        </Show>
        <div aria-live="polite" class="sr-only">
          {busy()
            ? "Analyzing sentence"
            : result()
              ? `${words().length} words analyzed, ${total()} candidates`
              : ""}
        </div>
        <Show
          when={result()}
          fallback={
            <section class="empty-workspace">
              <Book />
              <h2>
                {busy()
                  ? "Looking inside your sentence…"
                  : "Start with a sentence."}
              </h2>
              <p>
                {busy()
                  ? "Finding possible readings and dictionary entries."
                  : "Your words and their possible readings will appear here."}
              </p>
            </section>
          }
        >
          <section class="reading" aria-label="Analyzed sentence">
            <div class="section-heading">
              <div>
                <span class="eyebrow">YOUR SENTENCE, UNPACKED</span>
                <p>Select a word to explore its readings.</p>
              </div>
              <span class="word-count">
                {words().length} words <span>·</span> {total()} candidates
              </span>
            </div>
            <div class="sentence" lang="ko">
              <For each={result()!.records}>
                {(record, index) => (
                  <Show
                    when={record.kind === "word"}
                    fallback={<span>{record.surface}</span>}
                  >
                    <button
                      classList={{
                        "sentence-word": true,
                        selected: selected() === index(),
                        unmatched: only() && !analyses(record, true, compatible()).length,
                      }}
                      aria-pressed={selected() === index()}
                      onClick={() => choose(index())}
                    >
                      {record.surface}
                    </button>
                  </Show>
                )}
              </For>
            </div>
          </section>
          <div class="workspace-toolbar">
            <label
              classList={{
                "filter-control": true,
                disabled: !status()?.dictionary,
              }}
            >
              <input
                type="checkbox"
                checked={only()}
                disabled={!status()?.dictionary}
                onChange={(e) => {
                  setOnly(e.currentTarget.checked);
                  if (!e.currentTarget.checked) setCompatible(false);
                  choose(selected());
                }}
              />
              <span class="switch" />
              <span>Dictionary matches only</span>
            </label>
            <label classList={{ "filter-control": true, disabled: !only() || !status()?.dictionary }}>
              <input type="checkbox" checked={compatible()}
                disabled={!only() || !status()?.dictionary}
                onChange={(e) => { setCompatible(e.currentTarget.checked); choose(selected()); }} />
              <span class="switch" />
              <span>Exclude known grammar conflicts</span>
            </label>
            <label classList={{ "filter-control": true, disabled: !status()?.dictionary }}>
              <input type="checkbox" checked={suggestSpacing()} disabled={!status()?.dictionary}
                onChange={(e) => { setSuggestSpacing(e.currentTarget.checked); void analyze(); }} />
              <span class="switch" />
              <span>Suggest missing spaces</span>
            </label>
            <button class="export" onClick={download}>
              Export JSON <span aria-hidden="true">↗</span>
            </button>
          </div>
          <Show when={compatible()}>
            <p class="panel-caption">Checks cover lexical roles, reviewed endings, and dictionary spelling evidence. Unknown classes remain; context and other grammar are not checked.</p>
          </Show>
          <SentenceBreakdown
            result={result()!}
            only={only()}
            compatible={compatible()}
            selected={selected()}
            onWord={choose}
            onEntry={setEntryId}
          />
          <SpacingSuggestions result={result()!} onWord={choose} onEntry={setEntryId} />
          <div class="workspace">
            <section class="analysis-panel" aria-label="Word analyses">
              <div class="panel-heading">
                <div>
                  <span class="eyebrow">POSSIBLE READINGS</span>
                  <h2 lang="ko">{token()?.surface ?? "No words"}</h2>
                </div>
                <span class="count-badge">
                  {candidates().length}{" "}
                  {candidates().length === 1 ? "reading" : "readings"}
                </span>
              </div>
              <p class="panel-caption">
                Each card is one alternative. Components within a card belong
                together.
              </p>
              <Show
                when={candidates().length}
                fallback={
                  <div class="no-matches">
                    <span>∅</span>
                    <h3>No matching readings</h3>
                    <p>
                      {compatible()
                        ? "This word has no dictionary reading without a known conflict. Turn off the conflict filter to inspect its candidates."
                        : only()
                        ? "This word has no complete dictionary match. Turn off the filter to explore all candidates."
                        : "Select a word in the sentence to see its analyses."}
                    </p>
                  </div>
                }
              >
                <div class="candidate-list">
                  <For each={candidates().slice(0, visible())}>
                    {(candidate, index) => (
                      <article class="candidate">
                        <div class="candidate-top">
                          <span class="candidate-number">
                            {String(index() + 1).padStart(2, "0")}
                          </span>
                          <span class="candidate-type">
                            {candidate.unchanged
                              ? "Original form"
                              : "Rule-derived reading"}
                          </span>
                        </div>
                        <div class="lemma-chain">
                          <For each={candidate.lemmas}>
                            {(lemma, i) => (
                              <>
                                <Show when={i() > 0}>
                                  <span class="plus">+</span>
                                </Show>
                                {lemmaButton(token()!, lemma, token()!.analysis!.analyses.indexOf(candidate), i())}
                              </>
                            )}
                          </For>
                        </div>
                        <Show when={candidate.morphemes.length}>
                          <div class="endings">
                            <span>Endings, particles & suffixes</span>
                            <div>
                              <For each={candidate.morphemes}>
                                {(m) => (
                                  <span
                                    class="morpheme"
                                    title={m.kind}
                                    lang="ko"
                                  >
                                    {m.form}
                                  </span>
                                )}
                              </For>
                            </div>
                          </div>
                        </Show>
                        <Show when={token()?.dictionary?.readings?.[token()!.analysis!.analyses.indexOf(candidate)]?.status === "incompatible"}>
                          <p class="reading-condition">Known dictionary class conflict. This reading remains available unless the conflict filter is enabled.</p>
                        </Show>
                        <For each={readingConditions(candidate)}>
                          {(id) => <p class="reading-condition">{result()!.rules[id]}</p>}
                        </For>
                        <details class="trace">
                          <summary>How this reading was found</summary>
                          <ul>
                            <For each={candidate.rules}>
                              {(id) => (
                                <li>
                                  <code>{id}</code>
                                  <p>{result()!.rules[id] ?? id}</p>
                                </li>
                              )}
                            </For>
                          </ul>
                        </details>
                      </article>
                    )}
                  </For>
                </div>
                <Show when={visible() < candidates().length}>
                  <button
                    class="show-more"
                    onClick={() => setVisible((n) => n + 20)}
                  >
                    Show more readings (
                    {Math.min(visible(), candidates().length)} of{" "}
                    {candidates().length})
                  </button>
                </Show>
              </Show>
              <p class="hypothesis-note">
                Candidates are possible analyses, not a prediction of the
                intended meaning. A dictionary match confirms a headword, not
                its use in this sentence.
              </p>
            </section>
            <aside class="dictionary-panel" aria-label="Dictionary definitions">
              <div class="dictionary-title">
                <Book />
                <span>Dictionary</span>
                <Show when={status()?.dictionary}>
                  <span class="source-tag">한국어기초사전</span>
                </Show>
              </div>
              <Show when={token()?.dictionary && status()?.dictionary}>
                <div class="entry-choices">
                  <For each={entryChoices()}>
                    {(e) => (
                      <button
                        classList={{ active: entryId() === e.id }}
                        aria-pressed={entryId() === e.id}
                        onClick={() => setEntryId(e.id)}
                      >
                        <span lang="ko">
                          {e.headword}
                          {e.homonym !== "0" && <sup>{e.homonym}</sup>}
                        </span>
                        <small>{e.pos || "Unspecified"}</small>
                      </button>
                    )}
                  </For>
                </div>
              </Show>
              <Show when={entry.error}>
                <div class="notice error" role="alert">
                  Could not load this entry.{" "}
                  <button onClick={() => retryEntry()}>Retry lookup</button>
                </div>
              </Show>
              <Show
                when={!!entryId() && !entry.loading && !entry.error && entry()}
                fallback={
                  <div class="dictionary-empty">
                    <Book />
                    <h3>
                      {entry.loading
                        ? "Opening the dictionary…"
                        : "Follow a word further."}
                    </h3>
                    <p>
                      {status()?.dictionary
                        ? "Choose a linked lemma or dictionary entry to read its definitions."
                        : "Connect a Korean Basic Dictionary database to explore meanings here."}
                    </p>
                  </div>
                }
              >
                {(loaded) => (
                  <div class="entry-content">
                    <div class="entry-heading">
                      <h2 lang="ko">
                        {loaded().headword}
                        <Show when={loaded().homonym !== "0"}>
                          <sup>{loaded().homonym}</sup>
                        </Show>
                      </h2>
                      <div class="entry-meta">
                        <span>{loaded().pos}</span>
                        <Show
                          when={loaded().level && loaded().level !== "없음"}
                        >
                          <span>{loaded().level}</span>
                        </Show>
                        <For each={loaded().origins}>
                          {(origin) => <span>{origin}</span>}
                        </For>
                      </div>
                    </div>
                    <ol class="senses">
                      <For each={loaded().senses}>
                        {(sense) => (
                          <li>
                            <p class="ko-definition" lang="ko">
                              {sense.definition}
                            </p>
                            <For
                              each={sense.translations.filter(
                                (t) => t.language === "영어",
                              )}
                            >
                              {(t) => (
                                <>
                                  <Show when={t.lemma}>
                                    <p class="english-gloss">{t.lemma}</p>
                                  </Show>
                                  <p class="english-definition">
                                    {t.definition}
                                  </p>
                                </>
                              )}
                            </For>
                            <Show when={sense.examples.length}>
                              <details class="examples-detail">
                                <summary>
                                  Examples ({sense.examples.length})
                                </summary>
                                <For each={sense.examples}>
                                  {(lines) => (
                                    <blockquote lang="ko">
                                      <For each={lines}>
                                        {(line) => <p>{line}</p>}
                                      </For>
                                    </blockquote>
                                  )}
                                </For>
                              </details>
                            </Show>
                            <Show
                              when={sense.notes.length || sense.patterns.length}
                            >
                              <details class="examples-detail">
                                <summary>Usage notes</summary>
                                <For each={[...sense.notes, ...sense.patterns]}>
                                  {(note) => <p lang="ko">{note}</p>}
                                </For>
                              </details>
                            </Show>
                          </li>
                        )}
                      </For>
                    </ol>
                    <Show when={loaded().forms.some((f) => f.written)}>
                      <details class="examples-detail forms">
                        <summary>Conjugated forms</summary>
                        <p lang="ko">
                          {loaded()
                            .forms.filter((f) => f.written)
                            .map((f) => f.written)
                            .join(" · ")}
                        </p>
                      </details>
                    </Show>
                    <a
                      class="source-link"
                      href={loaded().url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open original dictionary entry ↗
                    </a>
                  </div>
                )}
              </Show>
            </aside>
          </div>
        </Show>
        <footer>
          <span class="footer-brand">
            klem <span>Made for curious readers.</span>
          </span>
          <Show
            when={status()?.dictionary}
            fallback={<span>Rule-based Korean lemma exploration</span>}
          >
            {(dictionary) => (
              <span>
                Dictionary: 국립국어원 · {dictionary().metadata.snapshot} ·{" "}
                <a
                  href={dictionary().metadata.license_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  {dictionary().metadata.license}
                </a>
              </span>
            )}
          </Show>
        </footer>
      </main>
    </div>
  );
}
