import {
  For,
  Show,
  createMemo,
  createSignal,
  createEffect,
  on,
} from "solid-js";
import {
  combinationCount,
  combinations,
  options,
  parts,
  preferred,
  type Part,
} from "./breakdown";
import type { Result } from "./model";

export default function SentenceBreakdown(props: {
  result: Result;
  only: boolean;
  selected: number;
  onWord: (index: number) => void;
  onEntry: (id: string) => void;
}) {
  const [choices, setChoices] = createSignal<Record<number, number>>({});
  const [expanded, setExpanded] = createSignal(false);
  createEffect(
    on(
      () => props.result,
      () => {
        setChoices({});
        setExpanded(false);
      },
    ),
  );
  const words = createMemo(() =>
    props.result.records
      .map((token, index) => ({ token, index }))
      .filter(({ token }) => token.kind === "word"),
  );
  const groups = createMemo(() =>
    words().map(({ token }) => options(token, props.only).map((o) => o.index)),
  );
  const count = createMemo(() => combinationCount(groups()));
  const all = createMemo(() => (expanded() ? combinations(groups()) : []));
  const selected = (index: number) => {
    const token = props.result.records[index];
    const chosen = choices()[index];
    return options(token, props.only).some((o) => o.index === chosen)
      ? chosen
      : preferred(token, props.only);
  };
  const reading = (index: number, choice = selected(index)) =>
    choice === undefined ? null : parts(props.result, index, choice);
  const title = (index: number, choice: number) => {
    const a = props.result.records[index].analysis!.analyses[choice];
    return (
      parts(props.result, index, choice)
        ?.map((p) => p.form)
        .join(" + ") ?? a.lemmas.map((l) => l.text).join(" + ")
    );
  };
  function component(part: Part, index: number) {
    return (
      <button
        classList={{
          "breakdown-part": true,
          grammatical: part.grammar,
          lexical: !part.grammar,
        }}
        disabled={!part.entry}
        title={part.hint}
        onClick={() => {
          props.onWord(index);
          if (part.entry) props.onEntry(part.entry);
        }}
      >
        <span class="part-form" lang="ko">
          {part.form}
        </span>
        <span class="part-gloss">{part.label}</span>
      </button>
    );
  }
  return (
    <section class="breakdown" aria-label="Sentence breakdown">
      <div class="section-heading">
        <div>
          <span class="eyebrow">SENTENCE BREAKDOWN</span>
          <p>Explore one possible reading, word by word.</p>
        </div>
      </div>
      <p class="breakdown-note">
        Stems and endings are normalized; contractions may be expanded. Glosses
        are dictionary hints, not a sentence translation. Grammar labels
        describe common uses.{" "}
        <a href="/Grammar-labels-LICENSE.txt" target="_blank" rel="noreferrer">
          Label sources
        </a>
        .
      </p>
      <div class="breakdown-sentence">
        <For each={props.result.records}>
          {(token, index) => (
            <Show
              when={token.kind === "word"}
              fallback={
                <span class="breakdown-separator">{token.surface}</span>
              }
            >
              <div
                classList={{
                  "breakdown-word": true,
                  selected: props.selected === index(),
                }}
              >
                <div class="breakdown-surface">
                  <span lang="ko">{token.surface}</span>
                  <Show
                    when={
                      reading(index()) &&
                      reading(index())!
                        .map((p) => p.form)
                        .join("") !== token.surface.normalize("NFC")
                    }
                  >
                    <small>Expanded / normalized</small>
                  </Show>
                </div>
                <div class="breakdown-parts">
                  <Show
                    when={reading(index())}
                    fallback={
                      <span class="breakdown-unavailable">
                        {options(token, props.only).length
                          ? "Ordered breakdown unavailable"
                          : "No matching reading"}
                      </span>
                    }
                  >
                    {(segments) => (
                      <For each={segments()}>
                        {(part) => component(part, index())}
                      </For>
                    )}
                  </Show>
                </div>
                <label class="reading-selector">
                  <span>{options(token, props.only).length} readings</span>
                  <select
                    aria-label={`Reading for ${token.surface} (word ${words().findIndex((w) => w.index === index()) + 1})`}
                    value={selected(index()) ?? ""}
                    disabled={!options(token, props.only).length}
                    onChange={(e) => {
                      setChoices((c) => ({
                        ...c,
                        [index()]: Number(e.currentTarget.value),
                      }));
                      props.onWord(index());
                    }}
                  >
                    <Show when={!options(token, props.only).length}>
                      <option value="">No match</option>
                    </Show>
                    <For each={options(token, props.only)}>
                      {(o, n) => (
                        <option value={o.index}>
                          {n() + 1}. {title(index(), o.index)}
                        </option>
                      )}
                    </For>
                  </select>
                </label>
              </div>
            </Show>
          )}
        </For>
      </div>
      <div class="combination-controls">
        <Show
          when={count() > 0n}
          fallback={
            <span>
              No complete combination under this filter. Unmatched words remain
              visible.
            </span>
          }
        >
          <span>
            {count().toLocaleString()} morphological combinations. Senses are
            explored separately in the dictionary.
          </span>
          <Show
            when={count() <= 20n}
            fallback={
              <span>
                More than 20: use each word’s reading selector to explore.
              </span>
            }
          >
            <button class="export" onClick={() => setExpanded(!expanded())}>
              {expanded() ? "Hide combinations" : "Show all combinations"}
            </button>
          </Show>
        </Show>
      </div>
      <Show when={all().length}>
        <p class="breakdown-note">
          These are combinations of independent word analyses; sentence grammar
          has not been validated.
        </p>
        <ol class="combination-list">
          <For each={all()}>
            {(row) => (
              <li>
                <span lang="ko">
                  {props.result.records
                    .map((token, index) => {
                      const position = words().findIndex(
                        (w) => w.index === index,
                      );
                      return position < 0
                        ? token.surface
                        : title(index, row[position]);
                    })
                    .join("")}
                </span>
                <button
                  onClick={() =>
                    setChoices(
                      Object.fromEntries(
                        words().map((w, i) => [w.index, row[i]]),
                      ),
                    )
                  }
                >
                  Use this combination
                </button>
              </li>
            )}
          </For>
        </ol>
      </Show>
    </section>
  );
}
