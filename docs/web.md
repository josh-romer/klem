# SolidJS sentence explorer

The browser tool uses the Rust lemmatizer and optional local Korean Basic
Dictionary database. Paste a sentence, choose a word, and inspect alternative
analyses. Each card preserves its component grouping. Linked lemmas open dictionary
entries with Korean definitions, English translations, examples and usage notes.
All homonyms remain selectable. Dictionary matches do not resolve contextual meaning.

## Run with Nix

```sh
nix run .#web -- --dictionary data/dictionaries/krdict/krdict.db
# Visit http://127.0.0.1:8080
```

The dictionary path refers to the database created by the
[dictionary importer](dictionary.md). It is never downloaded or embedded in the
application build. Without `--dictionary`, the UI still displays all rule
candidates and explains that dictionary features are unavailable.

`--port 8090` changes the listener port. The server binds only to `127.0.0.1`;
localhost is also accepted as a browser hostname. Stop it with Ctrl+C. This is a
local desktop tool, not an authenticated public web service.

`nix build .#web` produces the app launcher. `nix build .#web-assets` produces
static assets under `share/klem-web`. The regular package still runs the CLI by
default and now also includes the `klem-web` binary. `nix flake check` builds
both Rust binaries, runs their offline tests, and type-checks/builds the frontend.

## Use

- Click **Analyze sentence**, or press Ctrl/Command+Enter in the editor.
- Click a word in the sentence to select its analyses.
- The **Sentence breakdown** shows stems with dictionary glosses and grammar
  components with short teaching labels. Each word has an independent reading
  selector. Selecting a linked stem or grammar component opens its dictionary
  entry. Original spelling remains above each group; **Expanded / normalized**
  marks forms that are not a literal split of that spelling (e.g. 공부해요 →
  공부하 + 여요). The forms are not character-aligned annotations.
- **Show all combinations** appears when there are at most 20 combinations of
  the retained word analyses. Larger products are counted without enumeration;
  use the per-word selectors instead. A missing reading prevents a complete
  combination, but never hides the word. These combinations are independent
  morphological hypotheses, not validated sentence parses.
- **Dictionary matches only** keeps an analysis only when every lemma has a
  headword match, regardless of POS. Unknown words remain in the sentence; select
  one to see the empty-match explanation. Switch the filter off to explore them.
- Click a linked lemma or a dictionary-entry tab to read meanings and examples.
- Expand a card's rule explanation to inspect how it was recovered.
- **Export JSON** downloads the current result, with the filter applied. It
  preserves original token surfaces, UTF-8 byte offsets and analysis grouping.
  Ordered breakdowns are filtered alongside their corresponding analyses. The
  export includes every retained alternative, not just the selected diagram.

Glosses use the first English headword gloss from the first POS-compatible entry
(or an entry with unknown compatibility). They do not select a contextual sense,
and sense/homonym alternatives remain in the dictionary pane. Initial diagram
selection prefers analyses with compatible or unclassified dictionary matches,
then the fewest morphemes for a compact initial view. This is a display convenience,
not contextual ranking. All 434 currently emitted canonical grammar forms have
short teaching labels in the shared [catalog](../web/src/grammar-labels.json).
These paraphrase common KRDict uses; they are not contextual translations or
an exhaustive list of senses. Hover text lists each source ID and headword.
For grammar absent from the pinned dictionary, a label can cite primary articles
through `references` (title and HTTPS URL). The diagram shows a “Grammar source”
link, which also works without a connected dictionary. For example, 으리다
links to NIKL's discussion of its final-ending bundle; its API grammar-entry
list is empty. These references do not create dictionary matches or alter
candidate filtering. Bundled 으옵시/사옵시 similarly cite the actual NIKL
entries through references and preserve their single prefinal component.
The restricted 자옵/잡/자옵시 forms and 나이다 likewise have primary references
and empty API dictionary-entry lists. Reading choices preserve 듣잡다/받잡다
whole predicates alongside licensed segmented alternatives. The source-reviewed
modern subset is 듣다/묻다/받다/좇다; historical attachment distributions and
arbitrary compounds are not generalized. Bare 나이다 adjective conflicts use
the optional dictionary policy, preserving compatible homonyms and the source's
existential/honorific exceptions. Contextual register remains unresolved.
The literary question 나이까 uses its own primary reference, keeping
옵나이까/으옵나이까/사옵나이까 as prefinal plus question ending. Its optional
bare-adjective conflict is distinct from the 나이다 declarative conflict.
Bundled forms such as 기가 cite their component entries; joined 는데다가 links
to the spaced dictionary expression -는 데다가, and 어야죠 links to -어야지요.
The entry pane preserves the source's actual headword and POS. Generic role
labels remain a fallback for unknown forms, with inventory tests guarding all
current ending/particle tables and synthetic prefinal/suffix/copula forms.
See the bundled [grammar label notice](../web/public/Grammar-labels-LICENSE.txt).

The UI shows 20 readings at a time with an explicit “show more” control. All
candidates remain available and are included in export. Editing the text clears
old results; canceled or stale responses cannot replace the new draft.

The sentence API accepts at most 8,000 UTF-8 bytes and 64 Unicode scalar values
per word. Oversized requests are rejected with an explanation, never silently
truncated. The CLI/library retain their existing unrestricted exhaustive behavior
and are the appropriate interfaces for novels and unusually long tokens.

## Develop without a Nix app build

The Nix development shell provides Rust and Node.js. Frontend dependencies and
builds use `web/package-lock.json`; the Nix package additionally pins the npm
cache hash. HTTP support is behind the Cargo `web` feature.

```sh
nix develop
npm ci --prefix web
npm run build --prefix web
cargo run --features web --bin klem-web -- \
  --dictionary data/dictionaries/krdict/krdict.db
```

For hot reload, keep that Rust server running on port 8080, then run
`npm run dev --prefix web` and open Vite's printed address. Its `/api` proxy
forwards requests to the Rust server and rewrites the development origin. For a
custom asset location use `--assets DIRECTORY` or `KLEM_WEB_ASSETS`.

The production server serves a built Vite/SolidJS frontend from the same origin.
No CDN, analytics, remote font, dictionary service, or external model request is
needed. Pasted text is sent only to the local server and is not logged or written
to disk. Dictionary entry links intentionally open the external source website.

## API

- `GET /api/status`: version, dictionary metadata/fingerprint (or null), limits.
- `POST /api/analyze` with `{"text":"먹어봤어요."}`: `records`, rule explanations
  keyed by ID, and elapsed milliseconds. Records match the CLI's unfiltered
  JSONL objects, including dictionary annotations. Filtering is a client-side view.
  Additional sidecars: `breakdowns[record_index][analysis_index]` contains ordered
  `{lemma: index}` / `{morpheme: index}` references, or null when unavailable;
  `glosses` maps entry IDs to English hints or null; `grammar` maps dictionary
  canonical grammar keys (particles, `-endings`, `-prefinals-`, `-suffixes`) to
  entry summaries. Lookup normally requires the matching headword and grammar
  POS. The shared label catalog additionally permits reviewed expression and
  component sources with exact kind, ID, headword, and POS matching. For example,
  `-네요` includes expression 85934, `-기가` includes -기 and 가, and
  `-는데다가` includes the spaced headword -는 데다가 (72714).
  Entry summaries retain their original headword/POS, which can differ from
  the map key. This does not enable a general unclassified-entry fallback;
  unreviewed quoted homonyms such as -는다면 68841 remain excluded.
  The library exposes the same ordering through `Analysis::breakdown()`.
  Derivational suffixes remain grammatical morphemes: canonical `답다` is a
  `suffix` before its prefinals/ending, displayed as 답 and looked up as -답다.
  Whole-word and deeper suffix readings coexist in the per-word selector.
  Adverb-forming `이` follows its predicate base directly without an ending;
  달리 may be shown as 다르 + 이 with the normalized-expansion notice. The
  suffix link selects KRDict 88927 among the homonymous -이 entries.
- `POST /api/entry` with `{"id":"krdict:27500"}`: full dictionary entry.

POST requests require JSON. Invalid input receives a structured `error` string.
The server checks Host/Origin, does not enable CORS, and serves assets only from
the configured directory. Request bodies are capped at 32 KiB. The server processes
one analysis request at a time, appropriate for local sentence exploration.

## Tests

```sh
cargo test --locked --offline --features web
cargo clippy --locked --offline --all-targets --features web -- -D warnings
npm run build --prefix web
cargo build --locked --offline --features web
CHROMIUM_PATH=/path/to/chromium npm test --prefix web
```

Without `CHROMIUM_PATH`, Playwright uses its installed Chromium browser; install
it explicitly with `cd web && npx playwright install chromium` if needed. Browser
tests launch temporary local servers and import the small attributed dictionary
fixture. They do not require the full dictionary or novel. `KLEM_WEB_BIN` and
`KLEM_BIN` can override test binary paths (default: Cargo debug binaries).

The browser suite verifies API/CLI record equality, filtering entire component
groups, unknown-word visibility, definitions, rule details, exported JSON,
ordered glosses, contractions, reading selectors, bounded combinations,
input limits, errors/retry, stale requests, dictionary-free mode and mobile
layout. Screenshots go to ignored `web/test-results/`. Pure Rust API tests also
run during `nix flake check`; Chromium tests are a separate explicit check.

## Fonts and attribution

The SolidJS source is under the project's MIT OR Apache-2.0 license. DM Sans
(the DM Sans Project Authors) and Newsreader (the Newsreader Project Authors)
are bundled via Fontsource under SIL Open Font License 1.1. Their full notices
are included in `web/public/DM-Sans-LICENSE.txt` and
`web/public/Newsreader-LICENSE.txt` and copied into production assets. Korean
text uses the device's available Korean fonts. Dictionary text retains its
separate [source license and attribution](dictionary.md#data-licensing).

Comparative endings -듯/-듯이 (COV-016) display as one ending component after
the predicate stem, for example 보 + 듯이. Their “As / like” labels open KRDict
80280/80282 respectively, restricted to ending entries. They are not displayed
as the independent bound noun 듯 plus an 이 suffix.

Present conditional allomorphs -ㄴ다면/-는다면 (COV-017a) share canonical
는다면, labeled “If / supposing”. Thus 한다면 displays 하 + 는다면 with the
existing expanded/normalized notice, while 먹는다면 displays 먹 + 는다면.
The grammar link opens ending entry 68738; the homonymous quoted expression
68841 (품사 없음) is excluded by the ending-kind lookup.

COV-017b displays shortened adnominal expressions as single components:
먹 + 으려는 (“Intending / about to”) and 먹 + 자는 (“Quoted suggestion”).
살려는 displays 살 + 으려는 with the canonical-expansion notice. Their full
dictionary definitions explain the shortened expressions; the display does
not insert an implicit 하다 component or select a contextual sense. Expression
metadata retains the source's 품사 없음 label. The lookup exception is restricted
to the reviewed canonical IDs and does not affect lexical dictionary filtering.

COV-017c keeps -다가 and -어다가 as separate ending components, labeled
“While / then” (85740) and “Then / using the result” (86099). Both readings of
가다가 remain selectable. Past and honorific components remain separate, e.g.
갔다가 → 가 + 었 + 다가, with the existing normalized-expansion notice.

COV-017d labels -냐는 and -느냐는 “Quoted question”, linking to expression
entries 86030 and 86031. 아니냐는 displays 아니 + 냐는; 했느냐는 displays
하 + 였 + 느냐는 with the normalization notice. Honorifics, modals, and
auxiliary components stay separate. The source's 품사 없음 classification is
preserved through the same narrow expression lookup exception.

COV-017e adds canonical 으냐는 (“Quoted question”, 86032): 추우냐는 displays
춥 + 으냐는 with the normalization notice. Retrospective 더 remains a separate
prefinal in 먹더냐는. COV-018a distinguishes concessive 만 (“But / although”,
86555) after final endings from nominal/restrictive 만 (“Only / emphasis”,
86554). Full 마는 links to 86552. This uses component position and rule
provenance; headword matches alone cannot distinguish these homonyms.

COV-018b displays choice particle chains such as 어디 + 까지 + 나 and
이제 + 부터 + 라도. Particle (이)라고 has a “Quotation / emphasis” label,
separate from the copular ending -라고. 학생이라고 can therefore show
학생 + 이라고 or 학생 + 이 + 라고, preserving both readings in the selector.
The labels combine common functions; the app does not infer which dictionary
sense is intended by the sentence.

COV-019a preserves ordered auxiliary components and internal particles:
먹어들봐요 displays 먹 + 어 + 들 + 보 + 어요 and links 들 to its particle
entry (86264). 먹고야말았다 displays 먹 + 고 + 야 + 말 + 었 + 다.
먹곤했다 expands contracted 곤 to 고 + 는 with a normalization notice.
Adnominal auxiliaries use the existing predicate/auxiliary dictionary cards;
-을 has the label “Prospective noun modifier” and links to ending 69058.
Bundled and decomposed readings remain selectable; neither the label nor
headword filtering validates lexical attachment classes or chooses a sense.

COV-020a adds direct nominalization/copula display paths without changing the
representation: 학생다움이다 can display 학생 + 답 + 음 + 이 + 다 and
먹기예요 can display 먹 + 기 + 이 + 에요. Both use the expanded/normalized
notice. The reading selector preserves compact whole-word alternatives.
Nominalizer links are kind-specific endings -음 (78528) and -기 (72222),
separate from their noun-forming suffix homonyms. Auxiliary order is preserved
in 먹어보기였다 → 먹 + 어 + 보 + 기 + 이 + 었 + 다.

COV-021a exposes expanded negative contractions as selectable readings:
적잖은 can display 적 + 지 + 않 + 은 and 만만찮았다 can display
만만하 + 지 + 않 + 었 + 다. Lexical readings remain selectable and the browser's
existing compact-reading preference is unchanged. Expanded displays retain the
normalization notice and negative auxiliary dictionary cards.

COV-017f labels the bundled -잖아/-잖아요 expressions “Confirming / correcting”
(with a polite marker for 잖아요), linking to 86756/86757. 먹잖아요 can show
먹 + 잖아요 or 먹 + 지 + 않 + 어요; these readings must not be silently merged
or presented as a contextual decision. The narrow grammar-expression exception
preserves the dictionary's 품사 없음 classification.

COV-022a retains compact lexical adverbs as the initial reading. Selecting the
derived alternative shows 가까이 as 가깝 + 이, and 적잖이 as 적잖 + 이.
Source-listed 하다-root adverbs display their actual roots: 깨끗 + 이 and
조용 + 히. The root card links the related adjective 깨끗하다/조용하다, while
exported JSON retains that lookup lemma and `derivation.adverbial.hada`
provenance. This is a root-to-lemma relationship, not an inserted 하 segment.
The 히 suffix label opens adverb-forming entry 88504, preserving its distinction
from causative/passive homonyms. Existing 이 labels continue to open 88927.

Foreign-letter/number splits (COV-014) can carry a pronunciation condition in
`analysis.rules`. The browser displays the corresponding `result.rules` text
both beside the selected breakdown and on candidate cards. Switching back to an
unconditional reading removes that note. Export preserves each candidate's rule
IDs and explanations; it does not turn a condition into verified pronunciation.
Try ABC는 or 3은 with dictionary-only filtering off. With filtering on, unknown
bases remain visible as unmatched words, not fabricated dictionary matches.

Quoted copula fragments also expose reading conditions: selecting standalone
라는 → 이다 + 라는 displays that preceding quoted material is assumed. The
same `copula.omitted_fragment` rule and explanation survive dictionary-filtered
JSON export. The normalized display expands omitted 이 without assigning it a
surface span; punctuation and original token offsets stay unchanged. Explicit
이라는 → 이다 + 라는 requires no omission notice.

The conflict filter also checks reviewed written ㅎ/ㄷ/ㅅ/ㅂ/르/러 spelling profiles against
component-owned recovery requirements. Raw choices remain inspectable with the
filter disabled. Export preserves optional `spelling_paths` and per-entry `hieut`, `digeut`, `siot` and
`bieup` and `reu` evidence; see [the dictionary contract](dictionary-attachments.md#written-르러-inflection-compatibility-cov-021g).

The optional conflict filter also applies the finite
[short-stem restrictions](dictionary-attachments.md#restricted-short-stem-endings-cov-021h).
It preserves unrelated homonyms and short-stem purpose endings, and exports
`short_stem_ending` conflicts with their owning morpheme index. Normative
source disagreements remain documented; headword-only filtering retains the
original hypotheses.
