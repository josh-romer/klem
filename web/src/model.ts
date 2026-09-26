export interface Lemma {
  text: string;
  kind: string;
}
export interface Analysis {
  lemmas: Lemma[];
  morphemes: { form: string; kind: string }[];
  rules: string[];
  unchanged: boolean;
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
}
export interface Annotation {
  source: string;
  fingerprint: string;
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
export const analyses = (token: Token, only: boolean) =>
  (token.analysis?.analyses ?? []).filter(
    (a) => !only || a.lemmas.every((l) => matches(token, l).length > 0),
  );
export function filteredResult(result: Result, only: boolean): Result {
  if (!only) return result;
  return {
    ...result,
    breakdowns: result.records.map((token, i) =>
      token.analysis
        ? (result.breakdowns[i] ?? []).filter((_, j) =>
            analyses(token, true).includes(token.analysis!.analyses[j]),
          )
        : null,
    ),
    records: result.records.map((token) => {
      const kept = analyses(token, true);
      return {
        ...token,
        analysis: token.analysis ? { ...token.analysis, analyses: kept } : null,
        dictionary: token.dictionary
          ? {
              ...token.dictionary,
              lemmas: token.dictionary.lemmas.filter((m) =>
                kept.some((a) =>
                  a.lemmas.some(
                    (l) => l.text === m.lemma.text && l.kind === m.lemma.kind,
                  ),
                ),
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
