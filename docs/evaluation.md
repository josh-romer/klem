# Reproducible corpus evaluation

The [coverage completion checklist](coverage-checklist.md) connects known gaps
to implementation priorities and the evidence needed to close each item.

Normal tests exercise hand-specified rules, invalid boundaries, ambiguity,
component grouping, Unicode/streaming/cache/CLI behavior, and 67 converted gold
records from small annotated development excerpts. Those excerpts are adapter
regressions, not a representative accuracy benchmark.

```sh
bash tools/fetch-corpora.sh
bash tools/fetch-corpora.sh --verify
cargo run --release --locked --example evaluate -- \
  kaist data/corpora/kaist/ko_kaist-ud-dev.conllu data/baselines/kaist-dev.jsonl \
  > /tmp/kaist-dev-candidate.jsonl
cargo test --release --locked --test corpus -- --ignored
```

The explicit downloader needs Bash, curl, and sha256sum. It verifies existing
files and replaces missing/corrupt data only after successful checksum validation.
Normal builds/tests never download data. The ignored regression test covers
development and test splits of both corpora. Omit the evaluator's optional
baseline argument to print a fresh report. The evaluator writes JSONL to stdout
and diagnostics to stderr; a failed comparison exits nonzero but still writes
the candidate report for inspection. Redirect to a separate file, never the
baseline being compared.

## Adapters and metrics

CoNLL-U `LEMMA` often contains `+`-separated morphemes. Separate adapters align
them with XPOS and prefer `OrigLemma` where UD simplified the lemma. They
concatenate nominal compounds/derivational material, append 다 to predicates,
remove grammatical endings/particles, and retain copulas and auxiliaries as
components. KAIST adjective suffix `xsm` and adverbial suffix `xsa` differ from
GSD's `XSA`; these distinctions are tested.

* **Adapter coverage:** converted records / eligible records. Punctuation/symbols
  and non-Hangul surfaces are excluded and counted. Unknown tags, bad alignment,
  missing morphology, and unsupported structures are reported separately.
* **Grouped lemma recall:** the expected ordered components coexist in one
  analysis. This does not measure exact morpheme/POS accuracy.
* **Lemma recall:** the maximum expected components recovered within one analysis,
  divided by expected components. Incompatible alternatives are not combined.
* **Transformed recall:** grouped recall where expected lemmas differ from the
  unchanged surface; identity cases cannot conceal conjugation/particle misses.
* **Ambiguity:** mean, p95, and maximum analyses. Extra candidates are not labeled
  false positives because annotations normally choose a contextual reading.

## Current pinned-corpus results

Measured 2026-09-25. Rules were developed using curated cases and development
data. Candidate-correctness audits added independent spelling, ending-boundary,
and auxiliary-component constraints, then checked all frozen partitions. Test-set misses remain evaluation
records; these repeatedly checked splits are regression benchmarks, not a fresh
unseen evaluation.

| Dataset/split | Converted / eligible | Grouped recall | Transformed recall | Mean candidates |
| --- | ---: | ---: | ---: | ---: |
| KAIST dev | 22,220 / 22,288 | 97.88% | 97.26% | 4.34 |
| KAIST test | 24,490 / 24,650 | 98.24% | 97.63% | 4.25 |
| GSD dev | 9,989 / 10,145 | 97.32% | 95.86% | 3.98 |
| GSD test | 9,871 / 10,034 | 97.42% | 96.02% | 4.03 |

All reports have p95 of 8 analyses; maxima are 19 for KAIST, 24 for GSD dev,
and 17 for GSD test. [Baselines](../data/baselines) contain exact counts, common
misses, and all converted case outcomes. GSD's
automatic morphology is secondary evidence, not independent manual ground truth.
Neither dataset establishes precision or completeness across Korean.

## Individual-case regression tracking

Each version-2 `.jsonl` baseline contains a summary on the first line, followed
by one record per converted token, sorted by ID. A case stores `id`, `surface`,
ordered `expected` lemmas, `matched` (one analysis contains the exact group), and
`recovered` (the best component count within one analysis), and `recovered_sets`.
The latter stores sorted gold-index sets, each recovered together in one analysis.
Only maximal sets are retained: `[0]` adds no information if `[0,1]` exists.
Repeated lemmas consume separate gold indices, assigned in gold order. IDs use
`id:<sent_id>/<token_id>`; inputs without sentence IDs use
`ordinal:<sentence_number>/<token_id>`. Duplicate token IDs are rejected. File
paths are descriptive only; the SHA-256 of the exact input bytes identifies the
corpus, including annotations and sentence IDs.

Comparison rejects every previously matched case that loses its group, any
decrease in a case's best recovered component count, disappeared cases, and
changed expected lemmas or surfaces. Diagnostics name the affected case IDs.
A gain elsewhere cannot cancel a loss. Population/aggregate guards also remain.
Every old component set must be covered by a single current set. Replacing
`[0,1]` with `[0,2]` fails even though the count is unchanged; replacing it with
separate `[0]` and `[1]` alternatives also fails. A superset `[0,1,2]` passes.
This protects component identity and co-occurrence without freezing every
analysis. Exact ordered groups are protected separately by `matched`; full
morpheme paths are tested by candidate judgments below.

The reader rejects aggregate-only JSON and version-1 snapshots (which lack
component identities), unknown versions, duplicate records, invalid component
indices, redundant/noncanonical sets, inconsistent totals, and truncated snapshots.
Tests cover substitutions even when counts improve, multiplicity, alternative
separation, balanced gain/loss detection, adapter changes, and corpus identity.
The first migration captured case outcomes **before** changing the engine.
The audit then passed against all 66,570 frozen cases with no grouped or component
count regressions and 28 new grouped matches (KAIST dev/test: 10/4; GSD: 11/3).
Only after that comparison were snapshots updated to protect those gains too.
The second audit (ㅂ vowel choice, (으)리라, interrogative 니, and 어야 + 하다)
again passed all frozen cases with no grouped or component-count losses. It added
six grouped matches (KAIST dev/test: 0/0; GSD: 2/4); the snapshots now protect these
gains as well. Candidate-count changes are descriptive, not a precision score.
The version-2 migration used the unchanged engine: projecting the new snapshots
back to version 1 reproduced every old summary and case record exactly across
all four partitions. The migration adds evidence; it resets no regression floor.

To review a future change, save its candidate report, inspect the diagnostics and
case differences, and add a focused positive/negative rule test. A corpus or adapter
change needs an explicit review of its affected cases; do not overwrite baselines
just to pass. Snapshot records are development artifacts and never load at runtime.

## Candidate correctness

Annotated corpora usually label one contextual analysis and cannot enumerate
every valid alternative. Candidate soundness therefore has a separate suite in
`tests/candidate_correctness.rs`, with source-backed positive/negative boundaries
and ambiguity-preservation checks; see [the rule audit](rules.md#candidate-correctness-audit).
It rejects specific impossible lemma recoveries without declaring every extra
dictionary-free hypothesis a false positive. This is a targeted correctness
audit, not a precision estimate or proof of the entire grammar.

### Candidate judgment ledger and review queue

```sh
cargo run --release --locked --example evaluate_validity -- \
  tests/fixtures/validity.json > /tmp/klem-validity-review.json
```

The structured ledger supplies stable case/judgment IDs, ordered lemma groups,
optional exact morpheme sequences, required/forbidden verdicts, rationales, and
primary-source links. Missing morphemes mean that the judgment covers all paths
for that lemma group. Overlapping contradictory judgments, duplicate IDs, and
missing evidence are rejected. Normal tests run the ledger offline.

The initial 16 cases have 11 required and 10 forbidden judgments. All pass; 11
of 72 emitted nonidentity analyses match judgments, leaving 61 in the review
queue. These counts are **judgment coverage, not precision**. An unjudged output
is unknown, not automatically valid or invalid. Identity hypotheses are excluded
from these counts because retaining the input is an API contract. The example
emits the report even when judgments fail and exits nonzero.
The [initial review report](validity-review.json) retains those unjudged analyses
and source links; rerun the command after changing the grammar or fixture.

The nominal-plural extension added five cases, reaching 21 cases with 14 required
and 12 forbidden judgments. The stable `nominal-plural-*` IDs track the reported
지식인들을 failure, bare plurals, copulas, particle allomorphs, and repeated
suffix rejection. The linked initial report predates these cases.

The P1 particle/pronoun extension adds eleven cases, reaching 32 cases with
22 required and 16 forbidden judgments. Role and morpheme-kind assertions are
also tested in `tests/particles.rs` and the dictionary/browser suites. The full
66,570-case corpus regression comparison passes without removing prior grouped
or component recoveries. Corpus baselines and their dated recall measurements
are unchanged; this comparison is not a new precision evaluation.

The COV-010 suffix extension adds eight cases, reaching **40 cases with 27
required and 19 forbidden judgments**. These cover honorific/plural order,
relational suffixes before copulas, and the known ㅂ-irregular -답다 suffix.
`tests/derivation.rs` also checks morpheme kinds, component order, boundary
violations, and whole-word preservation. Dictionary tests use actual 정답다
conjugations from the attributed offline excerpt. These source forms provide
lexical evidence, not independently annotated sentences or contextual judgments.
The full 66,570-case corpus regression comparison also passes after this batch;
all 30 reviewed output fingerprints remain unchanged from the P1 state. No corpus
baseline or existing fingerprint was regenerated for the suffix extension.

The COV-011 하다 shortening batch adds nine cases, reaching **49 cases with 32
required and 23 forbidden judgments**. Tests compare source-described short and
full forms and reject wrong coda classes or a spurious omitted-copula reading.
Nine compatibility fingerprints were individually reviewed and updated for
additive `deletion.ha` hypotheses, retaining prior hashes; all prior analyses and
provenance remain. These new lexical hypotheses are not automatically judged
correct. Corpus baselines remain unchanged.
All 66,570 frozen corpus cases pass the regression comparison after this batch;
this verifies retained recoveries, not the precision of the added hypotheses.

The COV-012 adverb batch adds eight cases, reaching **57 cases with 37 required
and 26 forbidden judgments**. New offline corpus tests check three previously
missed annotated KAIST development tokens: M2TA_069-s19/2 (같이 → 같다),
M2TA_089-s68/8 (없이 → 없다), and MH2_0069-s41/7 (달리 → 다르다).
Their complete sentences are preserved in `tests/fixtures/kaist-adverbs.conllu`;
the project-authored tests additionally check suffix kinds and component order.
The whole-word adverbs remain alternatives. These selected development gains
are not an independent test-set estimate or a linguistic precision score.
The 66,570-case regression comparison passes with no lost prior recoveries;
all 30 compatibility fingerprints remain unchanged from COV-011. Corpus
baselines and their dated metrics were not regenerated.

The COV-013 inventory pass and COV-016 comparative endings add six ledger cases,
reaching **63 cases with 40 required and 29 forbidden judgments**. Two complete
KAIST sentences protect both saved 보듯이 → 보다 misses, including exact stable
IDs. Fresh development reports compared against the pre-COV-016 engine show
15 additional KAIST and 4 additional GSD grouped matches, with no lost groups
or component sets. Remaining development misses number 378 and 242. The
[inventory audit](inventory-audit.md) records the new matches and clusters
remaining annotations; clusters are not independent linguistic judgments.
All 66,570 frozen corpus cases still pass, and all 30 output fingerprints are
unchanged. The frozen baselines and their historical metric table above were
not replaced. These development gains are not unseen accuracy or precision.

The fixture is agent-authored against the cited sources; **independent Korean-language
review is pending**. Reviewers can inspect the queue's complete analyses, add
source-backed judgments to the fixture, and rerun the command. Adding labels is
a review decision, not an automatic acceptance of current engine output.

Remaining misses include adverbial derivations, rarer endings, foreign-word
pronunciations, and differences in lexical segmentation. Runtime code never loads
corpus answer tables. See [data provenance and licenses](../data/README.md).
