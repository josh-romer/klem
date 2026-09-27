export interface Lemma {
  text: string;
  kind: string;
}
export interface Analysis {
  lemmas: Lemma[];
  morphemes: { form: string; kind: string }[];
  rules: string[];
  unchanged: boolean;
  spelling_paths?: { morpheme_index: number; class: "hieut_regular" | "hieut_irregular" | "digeut_regular" | "digeut_irregular" | "siot_regular" | "siot_irregular" | "bieup_regular" | "bieup_irregular" | "reu_eu_deletion" | "reu_doubling" | "reo_addition" | "reu_uncontracted" }[][];
}
export const readingConditions = (analysis?: Analysis) =>
  analysis?.rules.filter((id) =>
    id.startsWith("pronunciation.assumed_") || id === "copula.omitted_fragment",
  ) ?? [];
export interface EntrySummary {
  id: string;
  headword: string;
  homonym: string;
  pos: string;
}
export interface EntryMatch extends EntrySummary {
  pos_compatibility: string;
  reu?: { eu_deletion: string[]; rieul_doubling: string[]; reo: string[]; uncontracted: string[] };
  hieut?: { regular: string[]; irregular: string[] }; digeut?: { regular: string[]; irregular: string[] }; siot?: { regular: string[]; irregular: string[] }; bieup?: { regular: string[]; irregular: string[] };
}
export interface ReadingAssessment {
  status: "compatible" | "incompatible" | "unknown";
  lemmas: { lemma_index: number; status: string; entries: {
    id: string; status: string; conflicts: { rule: string; morpheme_index: number | null }[];
  }[] }[];
}
export interface Annotation {
  source: string;
  fingerprint: string;
  readings?: ReadingAssessment[];
  lemmas: { lemma: Lemma; entries: EntryMatch[] }[];
}
export interface Token {
  surface: string;
  span: { start: number; end: number };
  kind: string;
  analysis: { normalized: string; analyses: Analysis[] } | null;
  dictionary: Annotation | null;
}
export interface Result {
  records: Token[];
  rules: Record<string, string>;
  elapsed_ms: number;
  breakdowns: ((Component[] | null)[] | null)[];
  glosses: Record<string, string | null>;
  grammar: Record<string, EntrySummary[]>;
}
export type Component = { lemma: number } | { morpheme: number };
export const grammarHeadword = (m: { form: string; kind: string }) =>
  m.kind === "particle"
    ? m.form
    : `-${m.form}${m.kind === "prefinal" ? "-" : ""}`;
export interface Status {
  dictionary: {
    metadata: {
      attribution: string;
      license: string;
      license_url: string;
      snapshot: string;
      entries: number;
    };
    fingerprint: string;
  } | null;
  limits: { text_bytes: number; word_chars: number };
}
export interface Entry {
  id: string;
  headword: string;
  homonym: string;
  pos: string;
  url: string;
  level: string;
  origins: string[];
  notes: string[];
  forms: { kind: string; written: string; pronunciations: string[] }[];
  senses: {
    id: string;
    definition: string;
    translations: { language: string; lemma: string; definition: string }[];
    examples: string[][];
    notes: string[];
    patterns: string[];
  }[];
}
export const matches = (token: Token, lemma: Lemma) =>
  token.dictionary?.lemmas.find(
    (m) => m.lemma.text === lemma.text && m.lemma.kind === lemma.kind,
  )?.entries ?? [];
// Prefer entries supported by this exact lemma slot's ending, retaining all
// homonyms for inspection if every entry conflicts or evidence is unavailable.
export function readingMatches(token: Token, candidate: number, index: number) {
  const lemma = token.analysis?.analyses[candidate]?.lemmas[index];
  const entries = lemma ? matches(token, lemma) : [];
  const assessed = token.dictionary?.readings?.[candidate]?.lemmas.find(
    (l) => l.lemma_index === index,
  );
  if (!assessed) return entries;
  const supported = entries.filter((e) => assessed.entries.some(
    (a) => a.id === e.id && a.status !== "incompatible",
  ));
  return supported.length ? supported : entries;
}
export const analyses = (token: Token, only: boolean, compatible = false) =>
  (token.analysis?.analyses ?? []).filter(
    (a, index) => (!only && !compatible) || (
      a.lemmas.every((l) => matches(token, l).length > 0) &&
      (!compatible || token.dictionary?.readings?.[index]?.status !== "incompatible")
    ),
  );
export function filteredResult(result: Result, only: boolean, compatible = false): Result {
  if (!only && !compatible) return result;
  const indices = result.records.map((token) => {
    const kept = new Set(analyses(token, only, compatible));
    return (token.analysis?.analyses ?? []).flatMap((a, i) => kept.has(a) ? [i] : []);
  });
  return {
    ...result,
    breakdowns: result.records.map((token, i) => token.analysis
      ? indices[i].map((j) => result.breakdowns[i]?.[j] ?? null) : null),
    records: result.records.map((token, i) => {
      const kept = indices[i].map((j) => token.analysis!.analyses[j]);
      return {
        ...token,
        analysis: token.analysis ? { ...token.analysis, analyses: kept } : null,
        dictionary: token.dictionary
          ? {
              ...token.dictionary,
              readings: token.dictionary.readings
                ? indices[i].map((j) => token.dictionary!.readings![j]) : undefined,
              lemmas: token.dictionary.lemmas.filter((m) =>
                kept.some((a) => a.lemmas.some(
                  (l) => l.text === m.lemma.text && l.kind === m.lemma.kind,
                )),
              ),
            }
          : null,
      };
    }),
  };
}
export async function api<T>(
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(
    `/api/${path}`,
    body === undefined
      ? { signal }
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
          signal,
        },
  );
  const data = await response.json();
  if (!response.ok)
    throw new Error(data.error ?? "The request failed. Please try again.");
  return data;
}
