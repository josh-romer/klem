# Offline dictionary integration

The `dictionary` module annotates generated candidates with exact headword matches
from a local database. Dictionary matches do not prove grammatical or contextual
correctness. Missing entries remain visible by default; `--dict-only` explicitly
filters the output to matching analyses. The rule engine is unchanged.

## Import the Korean Basic Dictionary

```sh
bash tools/fetch-krdict.sh
cargo build --release --locked
./target/release/klem dict import-krdict data/dictionaries/krdict/json \
  data/dictionaries/krdict/krdict.db --snapshot 2026-09
./target/release/klem dict info data/dictionaries/krdict/krdict.db
```

The fetch script requires Bash, curl, jq, unzip and sha256sum. It verifies the
archive and every JSON member against `data/krdict.lock.json`. `--verify` checks
local JSON without networking. Downloads occur only through this explicit step.
The archive is about 81 MiB; extracted JSON is about 969 MiB. Keep additional disk
space for the resulting database (about 255 MiB). Full downloads and databases are
ignored by Git and excluded from Cargo/Nix package sources.

`import-krdict` accepts a JSON file or a directory of official LMF JSON files
(`LexicalResource > Lexicon > LexicalEntry`). This is different from the search
API's response format. It streams one entry at a time into a transaction, hashes
input bytes, and publishes a completed SQLite database without replacing an
existing path. Errors remove the temporary database. To update, import into a new
filename and switch consumers to it. `--snapshot` is a descriptive label; input
hashes and the manifest fingerprint identify the actual data. Importing arbitrary
local files does not certify them as an official complete release.

The September 2026 archive contains 56,555 LMF entries, including idioms and
proverbs. The importer retains headwords, homonym numbers, original POS labels,
levels, origins, grammatical notes/patterns, pronunciation text, conjugations,
senses, examples and multilingual equivalents. It decodes XML entities once.
Media files, media URLs, cross-reference relations, topic categories and the
export's loosely formatted `variant` field are not imported in this version.

Ordinary entry IDs are `krdict:<upstream-id>`. The export reuses parent word IDs
for idioms/proverbs; these receive `krdict:<parent-id>:<sha256>` derived from the
lexical-unit label and headword. Their source URL points to the parent page.
Duplicate resulting IDs fail the import. Homonyms with different upstream IDs
remain separate, and sense IDs are scoped to their entry.

## CLI lookup and annotations

```sh
./target/release/klem dict lookup data/dictionaries/krdict/krdict.db 가다
./target/release/klem dict entry data/dictionaries/krdict/krdict.db krdict:27500
./target/release/klem word 먹어봤어요 --dictionary data/dictionaries/krdict/krdict.db
./target/release/klem text novel.txt --dictionary data/dictionaries/krdict/krdict.db > novel.jsonl
./target/release/klem word 먹어봤어요 --dictionary data/dictionaries/krdict/krdict.db --dict-only
# The same commands work through the flake:
nix run . -- dict lookup data/dictionaries/krdict/krdict.db 가다
```

`lookup` returns entry summaries; `entry` returns full definitions and examples.
A missing headword returns an empty list. A missing entry ID produces an error.
`info` provides attribution, licensing, input hashes and the snapshot fingerprint.

`--dictionary` requires JSONL. It adds a `dictionary` field to the existing word
or token record; by default, all existing fields, candidate order, component grouping and
byte offsets are preserved. Whitespace/punctuation receive `dictionary: null`.
The annotation has `source`, `fingerprint`, and `lemmas`, keyed by unique
`{text, kind}` pairs. Each lemma has all matching entry summaries with
`pos_compatibility: compatible | incompatible | unknown`. Consumers join these
keys back to components of each existing analysis. No cross-product of senses
or definitions is copied into bulk output. Runs without the option retain their
previous output schema.

Add `--dict-only` to `word` or `text` to retain only complete analyses where
**every component has at least one dictionary entry**. It requires `--dictionary`
and JSONL output. Matching ignores POS compatibility, including unknown POS;
it establishes headword presence only. If any component is missing, the whole
analysis is removed rather than emitting a partial group. Remaining analyses keep
their order, and dictionary annotations include only their referenced lemmas.
An unmatched word keeps its record with `analyses: []` and an empty annotation
lemma list. Whitespace, punctuation, original surfaces and byte offsets remain
intact, so text can still be reconstructed. Cached analyses stay unfiltered.

Lookup performs NFC normalization only. Spaces, prefix/suffix hyphens and
homonyms are not collapsed. Conjugations are retained for inspection/testing,
but are not indexed as extra lemma headwords. Multiword entries support explicit
lookup; recognizing multiword expressions across text tokens is future work.

The CLI uses an additional 4 MiB FIFO cache of headword summaries, including
negative lookups, alongside its existing lemma cache. The budget accounts for
payload/container sizes, excluding allocator and SQLite overhead. Definitions
are loaded only through `entry`. Open one SQLite connection per worker.

## Library

```rust,no_run
use klem::{Lemmatizer, dictionary::{Dictionary, DictionarySession, SqliteDictionary}};

fn main() -> klem::dictionary::Result<()> {
    let dictionary = SqliteDictionary::open("krdict.db")?;
    let mut lookups = DictionarySession::new(&dictionary, 4 * 1024 * 1024);
    let candidates = Lemmatizer::new().analyze_word("먹어봤어요")?;
    let annotation = lookups.annotate(&candidates)?;
    let entries = dictionary.lookup("먹다")?;
    if let Some(summary) = entries.first() {
        let details = dictionary.entry(&summary.id)?;
        println!("{details:?}");
    }
    // An explicit caller policy; annotation itself never filters candidates.
    let lexically_attested = candidates.filtered(|lemma| annotation.has_match(lemma, false));
    println!("{lexically_attested:?}");
    Ok(())
}
```

Implement `Dictionary` to supply a different source. The interface exposes
metadata, a snapshot fingerprint, headword summaries and full entry retrieval.

POS compatibility is deliberately broad: nominal roles accept nouns, pronouns,
numerals and dependent nouns; predicates accept verbs/adjectives; auxiliaries
accept auxiliary verbs/adjectives. Copulas special-case 이다/조사 and 아니다/형용사.
Unclassified candidates and unknown dictionary labels yield `unknown`.
Compatibility does not validate an ending, sense, syntactic construction or
usage in context. Strict POS filtering (`has_match(lemma, true)`) also rejects
unknowns, so it can remove correct readings, notably unchanged adverbs.

## Validation and measured coverage

```sh
cargo test --locked --offline --test dictionary
cargo run --release --locked --offline --example dictionary_coverage -- \
  data/dictionaries/krdict/krdict.db data/books/mujeong.txt
```

Offline tests use a small attributed slice of the real LMF export, covering
singleton/array fields, homonyms, shared parent IDs, conjugation recovery,
Unicode normalization, affix boundaries, POS roles, unknown words, CLI record
preservation, cache equivalence, input hashes and failed imports. Synthetic
malformed inputs test rejection and preservation of existing databases.

The complete September snapshot was imported and evaluated on the pinned 무정
text. [Raw report](dictionary-coverage.json) records hashes and all denominators:

| Metric | Result |
|---|---:|
| Word tokens | 81,758 |
| At least one candidate lemma matches | 72,502 (88.68%) |
| Every lemma in at least one complete analysis matches | 71,268 (87.17%) |
| Complete analysis with compatible POS for every lemma | 57,925 (70.85%) |
| Distinct word types with a complete matching analysis | 16,151 / 21,291 (75.86%) |

One release-mode run took about 0.77 seconds for analysis, lookup and coverage
aggregation; this excludes import, startup and full JSON serialization. This is
a single observation, not a benchmark guarantee. The report retains only the 50
most frequent unmatched forms; aggregation memory grows with distinct word types,
whereas the ordinary CLI streams records.

These are **lexical coverage measurements, not accuracy scores**. Any matching
alternative counts, even if wrong in context. The historical novel contains
names and older spellings; many frequent misses are forms of 영채, 선형 and 병욱.
The strict-POS number additionally excludes unchanged/unclassified hypotheses.
Coverage alone does not establish whether a larger dictionary improves precision.
A useful next comparison is Urimalsaem for older vocabulary and a user vocabulary
source for names, while retaining unknown candidates in reading applications.

## Data licensing

Dictionary data is separate from the MIT/Apache-2.0 code. Attribute the National
Institute of Korean Language (국립국어원), Korean Basic Dictionary (한국어기초사전).
Text is licensed under [CC BY-SA 2.0 KR](https://creativecommons.org/licenses/by-sa/2.0/kr/),
subject to the [source policy](https://krdict.korean.go.kr/kor/kboardPolicy/copyRightTermsInfo).
Retain attribution, license links and modification notices when distributing
extracted data. Media have individual terms and are omitted. Fixture provenance
is documented in [the fixture notices](../tests/fixtures/README.md).
