# klem

A Rust library and CLI for explainable Korean lemma candidates. It reverses
conjugations and particles using explicit rules, enumerates alternative analyses,
and preserves their component grouping. No model, dictionary, or runtime network
connection is required.

**Candidates are hypotheses, not verified dictionary entries.** “All” means all
analyses licensed by the implemented grammar, not complete coverage of Korean.
There is no contextual ranking or silent candidate cutoff. An unchanged-word
hypothesis is retained and labeled `unchanged: true` unless explicitly filtered.

## Try it

Build or run directly with Nix (x86-64/ARM64 Linux and Apple Silicon macOS):

```sh
nix build
./result/bin/klem word '먹었어요' --format text
nix run . -- word '먹어봤어요'
nix run . -- text novel.txt > novel.jsonl
nix flake check
```

The default package/app and the named `.#klem` package/app are equivalent.
The Nix build vendors dependencies from `Cargo.lock` and runs the offline test
suite, including the small corpus fixtures. Full downloaded corpora and local
build caches are excluded. `nix flake check` builds and tests the package for the
current system. The first build may download pinned dependencies from the network.
Intel macOS is not exposed because the pinned nixpkgs no longer supports it.

For development or a direct Cargo build:

```sh
nix develop
cargo build --release --locked
./target/release/klem word '먹었어요' --format text
./target/release/klem word '먹어봤어요'
./target/release/klem text novel.txt > novel.jsonl
printf '학교에서는 책을 읽었어요.\n' | ./target/release/klem text -
./target/release/klem explain irregular.digeut
```

An installed Rust toolchain also works; the existing pinned Nix shell is the
tested development environment. It supplies Cargo, Rust, rustfmt, Clippy, and
rust-analyzer. With direnv, run `direnv allow` once to load it automatically.

`word` emits one JSON object by default; `text` emits JSON Lines, including
whitespace and punctuation. `--format text` provides a readable view. Diagnostics
go to stderr. Invalid UTF-8, unreadable files, and invalid arguments produce a
nonzero exit status. A streaming input error may follow valid records. Pipes
closed by downstream consumers terminate quietly.

## Offline dictionaries

Optional Korean Basic Dictionary annotations add entry IDs and POS compatibility
while preserving every candidate by default. Import the official JSON snapshot once:

```sh
bash tools/fetch-krdict.sh
nix run . -- dict import-krdict data/dictionaries/krdict/json \
  data/dictionaries/krdict/krdict.db --snapshot 2026-09
nix run . -- word 먹어봤어요 --dictionary data/dictionaries/krdict/krdict.db
nix run . -- word 먹어봤어요 --dictionary data/dictionaries/krdict/krdict.db --dict-only
nix run . -- dict lookup data/dictionaries/krdict/krdict.db 먹다
```

`--dict-only` keeps complete analyses whose components all have dictionary entries,
regardless of POS compatibility. Unmatched words keep empty analysis lists.
Definitions are available through `dict entry <db> <entry-id>`. Dictionary use
requires no runtime network connection; downloads and imports are explicit.
The `dictionary::Dictionary` trait supports other sources, and
`DictionarySession` caches lookups. See [dictionary integration](docs/dictionary.md)
for the API, source licensing, limitations and measured novel coverage.
`--dict-compatible` also excludes known lexical-role/ending conflicts, preserving
unknown classes and valid homonyms. The browser exposes this under its dictionary
filter. See the [scoped policy](docs/dictionary-attachments.md), including per-entry
written ㅎ inflection checks. Raw/headword-only candidates remain available.

## Browser app

Paste a Korean sentence, select a word, and explore its grouped analyses and
dictionary definitions in the SolidJS web interface:

```sh
nix run .#web -- --dictionary data/dictionaries/krdict/krdict.db
# Open http://127.0.0.1:8080
```

Omit `--dictionary` to explore rule candidates alone. The app includes the
dictionary-only filter, a segmented sentence view with glosses and grammar labels,
per-word reading selectors, up to 20 complete morphological combinations,
rule explanations, examples and JSON export. Contractions are marked as expanded
or normalized; dictionary hints do not resolve contextual meaning. It runs
locally and bundles its frontend assets and fonts. See [web app setup](docs/web.md)
for development, tests, limits and API details.

## Library

```rust
use klem::{Lemmatizer, Session};
use std::sync::Arc;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let engine = Arc::new(Lemmatizer::new());
    let result = engine.analyze_word("공부했어요")?;
    assert!(result.lemma_strings().contains(&"공부하다"));

    let mut session = Session::new(engine, 8 * 1024 * 1024);
    klem::analyze_reader("먹어봤어요.".as_bytes(), &mut session, |record| {
        // Store the span for reader highlights and analyses for dictionary lookup.
        println!("{}..{}: {}", record.span.start, record.span.end, record.surface);
        Ok(())
    })?;
    Ok(())
}
```

`Lemmatizer::analyze_text(&str)` is a lazy iterator for text already in memory.
`analyze_reader` streams any `Read` input without buffering a full line or book.
The engine is `Send + Sync`; create one `Session` per consumer for caching.
The CLI cache defaults to 8 MiB of charged allocation weight; set
`--cache-bytes 0` to disable it. Allocator overhead and retained container capacity
are outside that estimate. Memory scales with the cache plus the current token
and its candidates, rather than the length of the book.

## Output contract

Text records have `surface`, `span: {start, end}`, `kind`, and `analysis`.
Spans are half-open **UTF-8 byte offsets into the original input**, not character
or UTF-16 indices. Word analysis contains NFC `normalized` text and `analyses`.
Whitespace and punctuation have `analysis: null`; foreign words retain an
unchanged interpretation. Concatenating all surfaces reconstructs the input.

Within each analysis:

* `lemmas` contains ordered components that belong together. One analysis of
  `먹어봤어요` contains `먹다` plus auxiliary `보다`.
* `morphemes` contains recovered endings/particles in order. Canonical `어` covers
  아/어 and `었` covers 았/었.
* `rules` contains stable supporting rule IDs. Equivalent analyses merge their
  IDs; this sorted set is provenance, not an ordered derivation trace.
  `rule_explanation(id)` returns a description.
* `unchanged` distinguishes an unmodified vocabulary hypothesis. Categories are
  grammatical hypotheses; predicates are not definitely verbs or adjectives.

Different analysis objects are alternatives. Do not combine their components
into a single reading. `lemma_strings()` flattens alternatives for dictionary
lookups; `filtered(predicate)` keeps complete analyses whose components all pass
a caller-supplied filter. Filtering leaves cached results unchanged. Ordering is
deterministic, not a confidence ranking.

Derived vocabulary such as `공부하다` and compound nouns remain intact. Copulas
and licensed attached auxiliaries can have separate components. Contractions
receive a whole-token span rather than invented character alignments.
Joined auxiliary recognition also tolerates some nonstandard spacing, such as
`먹어야한다` → `먹다` + `하다`; it does not validate spelling or spacing.

## Validation and performance

```sh
cargo test --locked --offline
cargo clippy --locked --offline --all-targets -- -D warnings
cargo fmt --all --check
```

Fetch Cargo dependencies once before offline checks. Normal tests use curated
positive/negative boundary cases and small attributed annotated-corpus excerpts.
Full-corpus JSONL snapshots track individual gold groups and co-recovered component
identities; equal counts and improvements elsewhere cannot hide a regression.
A source-backed candidate ledger checks required/forbidden analyses and emits
unjudged candidates for review. Independent Korean-language review remains pending.

[Corpus evaluation](docs/evaluation.md) covers datasets, adapters, held-out
results, and regression commands. [Rule coverage](docs/rules.md) lists supported
families and gaps. The [coverage completion checklist](docs/coverage-checklist.md)
tracks verified gaps, priorities, and the evidence required to close them.
[Performance](docs/performance.md) gives measurements and
reproduction commands. Run `cargo doc --no-deps` for API documentation.

## Boundaries and licensing

Version 0.1 targets modern standard written Korean. Historical forms, broad
dialect coverage, spelling correction, whitespace repair, contextual selection,
arbitrary compound segmentation, EPUB extraction, and exhaustive derivational
morphology are outside this release. Text splits at whitespace and Unicode
punctuation/symbols, including decimals and punctuation-bearing names. Unknown
pronunciation at foreign-letter/number boundaries is represented by explicit
conditional candidates, not guessed from an English letter or last digit.
For example, `ABC는` can expose `ABC + 는` with a vowel-final pronunciation
condition, and `3은` can expose `3 + 은` with a consonant-final condition.
These conditions are in rule provenance and the browser; they are not spelling
recommendations. Names/numbers missing from the dictionary still fail
`--dict-only`. See [the supported scope](docs/rules.md#foreign-nominals-and-pronunciation-conditions-cov-014).
Exhaustive analysis is output-sensitive: unusually long or ambiguous individual
tokens can consume substantial work and memory.

Code is MIT OR Apache-2.0. Korean Basic Dictionary extracts retain separate
CC BY-SA 2.0 KR attribution. Corpus excerpts and corpus-derived evaluation records
retain separate CC BY-SA 4.0 attribution: see [fixture notices](tests/fixtures/README.md)
and [data notices](data/README.md).
