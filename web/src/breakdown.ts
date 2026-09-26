import {
  analyses,
  matches,
  grammarHeadword,
  type Result,
  type Token,
} from "./model";

// Short teaching labels, paraphrased from KRDict. These describe common uses,
// not a contextually selected sense. Source IDs permit independent review.
export const grammarLabels: Record<string, [string, number]> = {
  "-들": ["Plural", 74906],
  "-님": ["Honorific", 88852],
  "-적": ["Relating to / having a quality", 88966],
  "-답다": ["Characteristic of", 92145],
  "-이": ["Adverb-forming suffix", 88927],
  들: ["Plural subjects", 86264],
  요: ["Polite", 86116],
  는: ["Topic / contrast", 85851],
  은: ["Topic / contrast", 86111],
  이: ["Subject marker", 86289],
  가: ["Subject marker", 66341],
  을: ["Object marker", 86355],
  를: ["Object marker", 85764],
  에: ["Place / time / destination", 86572],
  에서: ["Action location / from", 68853],
  의: ["Possession / relation", 86290],
  도: ["Also / even", 86258],
  만: ["Only / emphasis", 86554],
  와: ["With / and", 78628],
  과: ["With / and", 78624],
  "-어요": ["Polite informal", 86571],
  "-에요": ["Polite informal", 86106],
  "-어": ["Connective / informal", 86094],
  "-는": ["Noun modifier", 85853],
  "-은": ["Noun modifier", 80344],
  "-기": ["Nominalizer", 72222],
  "-음": ["Nominalizer", 78528],
  "-고": ["Connective / final", 78583],
  "-지": ["Connective / final", 78636],
  "-게": ["Connective / final", 77326],
  "-건대": ["Introducing a thought / wish", 78410],
  "-도록": ["Purpose / extent", 80286],
  "-듯": ["As / like", 80280],
  "-듯이": ["As / like", 80282],
  "-는다면": ["If / supposing", 68738],
  "-다가": ["While / then", 85740],
  "-어다가": ["Then / using the result", 86099],
  "-으려는": ["Intending / about to", 86717],
  "-자는": ["Quoted suggestion", 83896],
  "-고자": ["Purpose / intention", 78612],
  "-었-": ["Past / completed", 68719],
  "-시-": ["Subject honorific", 80330],
  "-겠-": ["Intention / conjecture", 90137],
  "-다": ["Plain / dictionary ending", 85041],
};
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
      return {
        form: stem ? lemma.text.replace(/다$/, "") : lemma.text,
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
    const label = grammarLabels[key];
    const entries = result.grammar[key] ?? [];
    const entry =
      entries.find((e) => e.id === `krdict:${label?.[1]}`) ?? entries[0];
    // 하 + 어/었 is displayed as 하 + 여/였. Keep canonical lookup/index intact.
    const previous = order[position - 1];
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
        label?.[0] ??
        {
          particle: "Particle",
          ending: "Ending",
          prefinal: "Prefinal ending",
          suffix: "Suffix",
        }[m.kind] ??
        m.kind,
      grammar: true,
      entry: entry?.id,
      hint: `${key} · Common function; other uses may apply.${label ? ` Label source: KRDict ${label[1]}.` : ""}`,
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
