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
not contextual ranking. Short grammar labels cover
common uses, with generic role labels for uncovered endings. They are paraphrased
from KRDict; each label's source entry ID is in `web/src/breakdown.ts` and its
hover text. See the bundled [grammar label notice](../web/public/Grammar-labels-LICENSE.txt).

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
  headwords (particles, `-endings`, `-prefinals-`, `-suffixes`) to matching entry summaries.
  Lookup normally requires the matching grammar POS. Scoped bundled expressions
  -으려는 (86717), -자는 (83896), -냐는 (86030), and -느냐는 (86031)
  also admit their exact KRDict headword/ID
  with `품사 없음`, only for `Ending` components. This does not enable a general
  unclassified-entry fallback or admit other quoted-expression homonyms.
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
