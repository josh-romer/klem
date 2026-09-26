import {
  analyses,
  matches,
  grammarHeadword,
  type Result,
  type Token,
} from "./model";

import labelCatalog from "./grammar-labels.json";

interface GrammarLabel {
  kind: string;
  label: string;
  sources: { id: number; headword: string; pos: string }[];
  note?: string;
}
// Teaching hints describe common functions, not a contextually selected sense.
export const grammarLabels: Record<string, GrammarLabel> = labelCatalog;
export interface Part {
  form: string;
  label: string;
  grammar: boolean;
  entry?: string;
  hint: string;
}
export function options(token: Token, only: boolean) {
  const kept = new Set(analyses(token, only));
  return (token.analysis?.analyses ?? [])
    .map((analysis, index) => ({ analysis, index }))
    .filter(({ analysis }) => kept.has(analysis));
}
export function preferred(token: Token, only: boolean) {
  const choices = options(token, only);
  return (
    choices
      .filter(({ analysis }) =>
        analysis.lemmas.every((l) =>
          matches(token, l).some((e) => e.pos_compatibility !== "incompatible"),
        ),
      )
      .sort(
        (a, b) => a.analysis.morphemes.length - b.analysis.morphemes.length,
      )[0] ?? choices[0]
  )?.index;
}
export function parts(
  result: Result,
  record: number,
  candidate: number,
): Part[] | null {
  const token = result.records[record];
  const a = token.analysis?.analyses[candidate];
  const order = result.breakdowns[record]?.[candidate];
  if (!a || !order) return null;
  return order.map((component, position) => {
    if ("lemma" in component) {
      const lemma = a.lemmas[component.lemma];
      const entries = matches(token, lemma);
      const entry =
        entries.find((e) => e.pos_compatibility === "compatible") ??
        entries.find((e) => e.pos_compatibility === "unknown");
      const stem = ["predicate", "auxiliary", "copula"].includes(lemma.kind);
      const next = order[position + 1];
      const adverbRoot = lemma.kind === "predicate" &&
        a.rules.includes("derivation.adverbial.hada") && next &&
        "morpheme" in next && a.morphemes[next.morpheme].kind === "suffix" &&
        ["이", "히"].includes(a.morphemes[next.morpheme].form);
      return {
        form: adverbRoot ? lemma.text.replace(/하다$/, "") : stem ? lemma.text.replace(/다$/, "") : lemma.text,
        label:
          (entry && result.glosses[entry.id]) ||
          (entry ? "No English gloss" : "No dictionary gloss"),
        grammar: false,
        entry: entry?.id,
        hint: `${lemma.text} · ${lemma.kind}. Dictionary hint only; click for all senses.`,
      };
    }
    const m = a.morphemes[component.morpheme];
    const key = grammarHeadword(m);
    const previous = order[position - 1];
    const concessiveMan =
      m.kind === "particle" && m.form === "만" &&
      a.rules.includes("particle.concessive") && previous &&
      "morpheme" in previous && a.morphemes[previous.morpheme].kind === "ending" &&
      ["다", "는다", "습니다", "냐", "느냐", "으냐", "자", "지", "더니"].includes(a.morphemes[previous.morpheme].form);
    const label = concessiveMan
      ? { ...grammarLabels[key], label: "But / although",
          sources: grammarLabels[key].sources.filter((s) => s.id === 86555) }
      : grammarLabels[key]?.kind === m.kind ? grammarLabels[key] : undefined;
    const entries = result.grammar[key] ?? [];
    const entry =
      label?.sources.map((s) => entries.find((e) => e.id === `krdict:${s.id}`))
        .find((e) => e !== undefined) ?? entries[0];
    // 하 + 어/었 is displayed as 하 + 여/였. Keep canonical lookup/index intact.
    const afterHa =
      previous &&
      "lemma" in previous &&
      a.lemmas[previous.lemma].text.endsWith("하다");
    const form = afterHa
      ? m.form.replace(/^어/, "여").replace(/^었/, "였")
      : m.kind === "suffix" && m.form === "답다"
        ? "답"
        : m.form;
    return {
      form,
      label:
        label?.label ??
        {
          particle: "Particle",
          ending: "Ending",
          prefinal: "Prefinal ending",
          suffix: "Suffix",
        }[m.kind] ??
        m.kind,
      grammar: true,
      entry: entry?.id,
      hint: `${key} · Common function; other uses may apply.${label ? ` Label sources: KRDict ${label.sources.map((s) => `${s.id} (${s.headword})`).join(", ")}.${label.note ? ` ${label.note}` : ""}` : ""}`,
    };
  });
}

// Count exactly without creating a Cartesian product. Expansion is explicitly
// requested and only allowed when every word has a reading and the count <= 20.
export function combinationCount(groups: number[][]): bigint {
  return groups.length ? groups.reduce((n, g) => n * BigInt(g.length), 1n) : 0n;
}
export function combinations(groups: number[][]): number[][] {
  const count = combinationCount(groups);
  if (count === 0n || count > 20n) return [];
  return groups.reduce<number[][]>(
    (rows, group) => rows.flatMap((row) => group.map((i) => [...row, i])),
    [[]],
  );
}
