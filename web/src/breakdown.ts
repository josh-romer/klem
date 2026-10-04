import {
  analyses,
  matches,
  readingMatches,
  grammarHeadword,
  type Result,
  type Token,
} from "./model";

import labelCatalog from "./grammar-labels.json";

interface GrammarLabel {
  kind: string;
  label: string;
  sources: { id: number; headword: string; pos: string }[];
  references?: { title: string; url: string }[];
  note?: string;
}
// Teaching hints describe common functions, not a contextually selected sense.
export const grammarLabels: Record<string, GrammarLabel> = labelCatalog;
export interface Part {
  form: string;
  label: string;
  grammar: boolean;
  entry?: string;
  references?: { title: string; url: string }[];
  hint: string;
}
export function options(token: Token, only: boolean, compatible = false) {
  const kept = new Set(analyses(token, only, compatible));
  return (token.analysis?.analyses ?? [])
    .map((analysis, index) => ({ analysis, index }))
    .filter(({ analysis }) => kept.has(analysis));
}
export function preferred(token: Token, only: boolean, compatible = false) {
  const choices = options(token, only, compatible);
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
      const fanRoot = component.lemma === 1 && lemma.kind === "root" &&
        lemma.text === "선" && a.rules.includes("derivation.nominal.root_compound");
      const entries = readingMatches(token, candidate, component.lemma);
      // KRDict tags both enumerative 이다 and the copula as 조사. This path
      // already represents a copula, so prefer its explicit source homonym.
      const copulaEntry = lemma.kind === "copula" && lemma.text === "이다"
        ? entries.find((e) => e.id === "krdict:86232") : undefined;
      const assessment = token.dictionary?.readings?.[candidate]?.lemmas
        .find((l) => l.lemma_index === component.lemma);
      let entry =
        copulaEntry ??
        entries.find((e) => assessment?.entries.some(
          (a) => a.id === e.id && a.status === "compatible",
        )) ??
        entries.find((e) => e.pos_compatibility === "compatible") ??
        entries.find((e) => e.pos_compatibility === "unknown") ??
        entries.find((e) => token.dictionary?.readings?.[candidate]?.lemmas
          .find((l) => l.lemma_index === component.lemma)?.entries
          .some((a) => a.id === e.id && a.status === "unknown"));
      if (entry && assessment?.entries.some(
        (a) => a.id === entry?.id && a.status === "incompatible" &&
          (fanRoot || (lemma.kind === "root" && a.conflicts.some(
            (c) => c.rule === "derivational_root",
          ))),
      )) entry = undefined;
      const stem = ["predicate", "auxiliary", "copula"].includes(lemma.kind);
      const next = order[position + 1];
      const derivedRoot = lemma.kind === "predicate" &&
        (a.rules.includes("derivation.adverbial.hada") ||
          (component.lemma === 0 && a.rules.includes("derivation.nominal.related_root"))) && next &&
        "morpheme" in next && a.morphemes[next.morpheme].kind === "suffix" &&
        ["이", "히"].includes(a.morphemes[next.morpheme].form);
      return {
        form: derivedRoot ? lemma.text.replace(/(?:하다|거리다)$/, "") : stem ? lemma.text.replace(/다$/, "") : lemma.text,
        label:
          (entry && result.glosses[entry.id]) ||
          (entry ? "No English gloss" : fanRoot ? "Fan (bound root)" : lemma.kind === "root" ? "Root" : "No dictionary gloss"),
        grammar: false,
        entry: entry?.id,
        references: fanRoot ? [{ title: "KBS: 허풍선이 formation", url: "https://world.kbs.co.kr/service/contents_view.htm?board_seq=229261&id=&lang=k&menu_cate=learnkorean" }] : undefined,
        hint: fanRoot ? "선 (扇) · Source-listed bound root meaning fan. Recorded origins of other 선 homonyms do not supply this root; all entries remain available for inspection." : `${lemma.text} · ${lemma.kind}. Dictionary hint only; click for all senses.`,
      };
    }
    const m = a.morphemes[component.morpheme];
    const key = grammarHeadword(m);
    const previous = order[position - 1];
    const concessiveMan =
      m.kind === "particle" && m.form === "만" &&
      a.rules.includes("particle.concessive") && previous &&
      "morpheme" in previous && a.morphemes[previous.morpheme].kind === "ending" &&
      ["다", "는다", "습니다", "냐", "느냐", "으냐", "으랴", "자", "지", "더니"].includes(a.morphemes[previous.morpheme].form);
    const previousMorpheme = previous && "morpheme" in previous
      ? a.morphemes[previous.morpheme] : undefined;
    const previousLemma = previous && "lemma" in previous
      ? a.lemmas[previous.lemma] : undefined;
    // Provenance is analysis-wide. Check this component's immediate base too,
    // so nested nominalizations do not borrow another 다's source sense.
    const enumerativeDa = m.kind === "particle" && m.form === "다" &&
      a.rules.includes("particle.enumerative_da") &&
      previousMorpheme?.kind !== "particle" && previousLemma?.kind !== "adverbial";
    const emphaticDa = m.kind === "particle" && m.form === "다" &&
      a.rules.includes("particle.emphatic_adverbial") &&
      ((previousMorpheme?.kind === "particle" &&
        ["에", "에서", "서", "에게", "한테", "께", "로", "으로"].includes(previousMorpheme.form)) ||
       (previousLemma && ["여기", "거기", "저기", "어디", "이리", "그리", "저리"].includes(previousLemma.text)));
    const beforePrevious = order[position - 2];
    // The finite adnominal noun base ends in ㄴ rather than immediately in
    // its lexical head. Keep the noun suffix's source separate from adverb -이.
    const adnominalBase = a.rules.includes("derivation.nominal.adnominal") &&
      previousMorpheme?.kind === "ending" && previousMorpheme.form === "ㄴ" &&
      beforePrevious && "lemma" in beforePrevious && beforePrevious.lemma === 0;
    const nominalI = m.kind === "suffix" && m.form === "이" &&
      a.rules.includes("suffix.nominal.i") &&
      (adnominalBase || (previous && "lemma" in previous &&
        previous.lemma === (a.rules.includes("derivation.nominal.compound") || a.rules.includes("derivation.nominal.root_compound") ? 1 : 0)));
    const adverbI = m.kind === "suffix" && m.form === "이" && a.rules.includes("suffix.adverbial.i");
    const label = nominalI || adverbI
      ? { ...grammarLabels[key], label: nominalI ? "Noun-forming suffix" : "Adverb-forming suffix",
          sources: grammarLabels[key].sources.filter((source) => source.id === (nominalI ? 88924 : 88927)) }
      : enumerativeDa || emphaticDa
      ? { ...grammarLabels[key],
          label: enumerativeDa ? (emphaticDa ? "Enumeration / emphasis" : "Enumeration") : "Adverbial emphasis",
          sources: grammarLabels[key].sources.filter((s) =>
            (enumerativeDa && s.id === 85738) || (emphaticDa && s.id === 41693)) }
      : concessiveMan
      ? { ...grammarLabels[key], label: "But / although",
          sources: grammarLabels[key].sources.filter((s) => s.id === (m.form === "마는" ? 86552 : 86555)) }
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
      : m.kind === "suffix" && ["답다", "되다"].includes(m.form)
        ? m.form.replace(/다$/, "")
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
          prefix: "Prefix",
        }[m.kind] ??
        m.kind,
      grammar: true,
      entry: entry?.id,
      references: label?.references,
      hint: `${key} · Common function; other uses may apply.${label ? `${label.sources.length ? ` Label sources: KRDict ${label.sources.map((s) => `${s.id} (${s.headword})`).join(", ")}.` : ""}${label.references?.length ? ` References: ${label.references.map(r => r.title).join("; ")}.` : ""}${label.note ? ` ${label.note}` : ""}` : ""}`,
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
