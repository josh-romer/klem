import { For, Show } from "solid-js";
import { type Result, type SpacingHypothesis } from "./model";
import SentenceBreakdown from "./SentenceBreakdown";

export default function SpacingSuggestions(props: {
  result: Result;
  onWord: (index: number) => void;
  onEntry: (id: string) => void;
}) {
  const preview = (alternative: SpacingHypothesis): Result => ({
    ...props.result,
    records: alternative.records,
    breakdowns: alternative.records.map((record) => record.breakdowns),
  });
  const visible = () => props.result.records.some((r) =>
    r.spacing && (r.spacing.alternatives.length || !r.spacing.complete));
  return <Show when={visible()}>
    <section class="spacing-suggestions" aria-label="Missing-space suggestions">
      <span class="eyebrow">POSSIBLE MISSING SPACES</span>
      <p class="panel-caption">These are spacing hypotheses. Your original text is preserved. Dictionary hints do not validate sentence grammar or choose the intended meaning.</p>
      <For each={props.result.records}>
        {(record, index) => <Show when={record.spacing}>
          {(spacing) => <>
            <For each={spacing().alternatives}>
              {(alternative) => <article class="spacing-hypothesis">
                <h3 lang="ko">{alternative.spaced}</h3>
                <p class="panel-caption">Original: <span lang="ko">{record.surface}</span></p>
                <SentenceBreakdown result={preview(alternative)} only={true} compatible={true}
                  selected={-1} onWord={() => props.onWord(index())} onEntry={props.onEntry}
                  label={`Spacing breakdown for ${alternative.spaced}`} />
                <For each={alternative.joined_contexts}>
                  {(context) => <details class="auxiliary-spacing-context">
                    <summary>Auxiliary relationship</summary>
                    <p class="panel-caption">This combined reading supports the split above. The separate words can have other dictionary meanings.</p>
                    <SentenceBreakdown
                      result={{ ...props.result, records: [context], breakdowns: [context.breakdowns] }}
                      only={true} compatible={true} selected={-1}
                      onWord={() => props.onWord(index())} onEntry={props.onEntry}
                      label={`Auxiliary relationship for ${alternative.spaced}`} />
                  </details>}
                </For>
              </article>}
            </For>
            <Show when={!spacing().complete}>
              <p class="reading-condition">Search limit reached for <span lang="ko">{record.surface}</span>; additional suggestions may exist.</p>
            </Show>
          </>}
        </Show>}
      </For>
    </section>
  </Show>;
}
