# Reproducible corpus evaluation

The [coverage completion checklist](coverage-checklist.md) connects known gaps
to implementation priorities and the evidence needed to close each item.

Normal tests exercise hand-specified rules, invalid boundaries, ambiguity,
component grouping, Unicode/streaming/cache/CLI behavior, and gold records from
attributed annotated development excerpts. Those excerpts are adapter
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

## Pinned baseline results

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

The COV-017a present conditional batch adds eight ledger cases, reaching
**71 cases with 44 required and 33 forbidden judgments**. Three complete
development sentences protect 한다면 (KAIST MH2_0069-s53/7), 않는다면
(KAIST MH2_0149-s14/11), and 들리신다면 (GSD dev-s153/3). Exact boundary,
prefinal, and auxiliary paths are checked separately from the corpus adapter.
The [development comparison](conditional-evaluation.json) records 13 additional
KAIST and 6 additional GSD matches against commit `b9148b4`, with no lost groups
or component sets. Remaining development misses are 365 and 236. These are gold
group matches, not independent correctness judgments: for example, the gained
안쓴다면 → 안쓸다 annotation still needs lexical/segmentation review and is not
a required judgment in the ledger. All 66,570 frozen cases pass and all 30
output fingerprints remain unchanged; historical baselines/reports are retained.

The COV-017b shortened-adnominal batch adds eight ledger cases, reaching
**79 cases with 48 required and 37 forbidden judgments**. Three complete KAIST
development sentences protect 절약하려는 (MH2_0069-s151/10), 배우자는
(M2TA_089-s4/3), and the auxiliary group 바꿔보자는 (MH2_0169-s111/4).
The [development comparison](adnominal-evaluation.json) records 21 additional
KAIST and 3 additional GSD matches against the pre-COV-017b working tree,
with no lost groups or component sets. Remaining development misses are
344 and 233. All 66,570 frozen cases pass and all 30 output fingerprints
remain unchanged. Previous reports remain dated snapshots; these selected
development gains do not estimate precision or unseen accuracy.

The COV-017c -다가 batch adds eight ledger cases, reaching **87 cases with
52 required and 41 forbidden judgments**. Three offline positive cases protect
불렀다가 (KAIST MH2_0169-s159/3), 침략했다가 (KAIST MH2_0169-s718/5), and
갔다가 (GSD dev-s616/3). The [development comparison](daga-evaluation.json)
records 3 additional KAIST and 8 additional GSD matches against the pre-COV-017c
working tree, with no lost groups or component sets. Remaining development
misses are 341 and 225. The tempting 살겠다가 miss remains under COV-018:
its preserved annotation is 살+겠+다+가, with a subject particle. The forbidden
judgment targets only the erroneous 겠 + 다가 analysis, allowing a future
quoted-clause rule to recover the lexical group. All 66,570 frozen cases and
30 output fingerprints pass; historical reports/baselines remain unchanged.

The COV-017d quoted-question batch adds eight ledger cases, reaching **95 cases
with 56 required and 45 forbidden judgments**. Two complete KAIST development
sentences protect 아니냐는 (MH2_0069-s250/18) and 했느냐는 (MH2_0169-s383/9).
The [development comparison](quoted-question-evaluation.json) records two new
KAIST matches and one GSD match against commit `c2bf2e2`, with no lost groups
or component sets. Remaining development misses are 339 and 224. The GSD
뭐하냐는 → 뭐하다 match is an annotation match, not independent lexical or
contextual validation. All 66,570 frozen cases and 30 output fingerprints pass;
historical reports and baselines remain unchanged. Full -(으)냐는 adjective
allomorphy and retrospective -더냐 quotation remain outside this batch.

The COV-017e adjective/retrospective and COV-018a post-ending particle batches
add sixteen ledger cases, reaching **111 cases with 64 required and 53 forbidden
judgments**. The adjective examples are source-backed constructions; no new
development gold matches are attributed to them. Five complete source sentences
protect post-ending particles, including the 대다 + 주다 auxiliary group in
대주고는. The [development comparison](post-ending-evaluation.json) records
59 additional KAIST and 12 additional GSD gold groups against commit `051c0d7`,
with no lost groups or recovered component sets. Remaining development misses
are 280 and 212. The 부드러우다 and 해가지고는 annotations still need lexical
or segmentation review and were not promoted into required-candidate judgments.
All 66,570 frozen cases pass. Twenty-nine compatibility fingerprints remain
unchanged; 학교에서만은 gains four reviewed unknown-predicate hypotheses from
the new 어/어서 + 만 paths. Its old hash is retained and every previous analysis
and provenance item remains. Historical corpus reports/baselines are unchanged.

The COV-018b outer-choice/quotative batch adds twelve ledger cases, reaching
**123 cases with 70 required and 59 forbidden judgments**. Four complete
source sentences protect 어디까지나, 이제부터라도, 사회주의라고, and 넣기라도.
The [development comparison](particle-chain-evaluation.json) records 36 new
KAIST and 3 new GSD grouped matches against the COV-018a working tree, with
no lost grouped matches or component recoveries. Remaining development misses
are 244 and 209. 보게나 is only a lemma match, not validation of a contextual
게 + 나 reading instead of imperative -게나. GSD 문여나 also remains a
segmentation review case. All 66,570 frozen cases pass and all 30 current
compatibility fingerprints are unchanged by COV-018b. Historical reports remain.

The fixture is agent-authored against the cited sources; **independent Korean-language
review is pending**. Reviewers can inspect the queue's complete analyses, add
source-backed judgments to the fixture, and rerun the command. Adding labels is
a review decision, not an automatic acceptance of current engine output.

Remaining misses include adverbial derivations, rarer endings, foreign-word
pronunciations, and differences in lexical segmentation. Runtime code never loads
corpus answer tables. See [data provenance and licenses](../data/README.md).

The COV-019a structural auxiliary catalog and internal-particle batch adds twelve
ledger cases, reaching **135 cases with 76 required and 65 forbidden judgments**.
Five full source sentences protect connector-specific auxiliary groups. The
[development comparison](auxiliary-evaluation.json) records 19 new KAIST and
2 new GSD grouped matches against the COV-018b working tree, with no lost groups
or component recoveries. Remaining development misses are **225 and 207**.
The new 일어났던 and 밀려나가게 matches remain lexical-segmentation review
cases, not required-candidate judgments. Source-backed synthetic examples cover
internal particles; the corpus adapter does not measure grammatical components.
All 66,570 frozen cases pass. Twenty-nine current output fingerprints remain
unchanged; 먹게하고있다 gains two unknown-stem hypotheses through 어 + 하다.
Every previous analysis remains and the old hash is retained. Historical
baselines/reports are unchanged. Rust candidate, dictionary, stress, and browser
checks pass; source-class and contextual restrictions remain open under COV-019.
`nix flake check` and `nix build .#web` pass on x86_64 Linux. The browser suite
also passes against the resulting Nix binaries. A full-dictionary browser smoke
check covers six new auxiliary/internal-particle examples and the -을/들 source
links; it checks display order, not contextual selection of lexical homonyms.

COV-020a direct nominalization/copula composition adds eight ledger cases,
reaching **143 cases with 80 required and 69 forbidden judgments**. Its full
KAIST sentence fixture protects 떠먹이기다 → 떠먹이다 + 이다. The
[development comparison](nominal-copula-evaluation.json) records that one new
KAIST group and no new GSD groups, with no lost groups or component sets;
remaining misses are **224 KAIST and 207 GSD**. The derived 학생다움이다 and
polite/auxiliary examples are source-backed synthetic cases, not new corpus gold.
All 66,570 frozen cases pass and all 30 current compatibility snapshots remain
unchanged. Rust, dictionary/CLI, stress, Clippy and browser checks pass, including
nominalizer source links. Historical baselines and evaluation reports remain.
`nix flake check` and `nix build .#web` pass on x86_64 Linux. A browser smoke
check of the packaged app with the full dictionary verifies five direct-copula
examples, dictionary-only filtering, selectable component order, and the -음/-기
source links. This does not validate contextual homonym or sense selection.

COV-021a negative contractions and COV-017f confirmation expressions add eleven
ledger cases, reaching **154 cases with 86 required and 74 forbidden judgments**.
The [development comparison](negative-contraction-evaluation.json) records one
new KAIST group, 적잖은 → 적다 + 않다, and no new GSD groups. No prior groups
or component sets are lost; remaining misses are **223 KAIST and 207 GSD**.
Confirmation expressions have source-backed synthetic evidence, with no new
corpus gain attributed to them. All 66,570 frozen cases pass and all 30 current
compatibility fingerprints remain unchanged. Rust, Clippy, stress, dictionary/CLI,
frontend build and browser checks pass. Historical baselines/reports remain.
`nix flake check` and `nix build .#web` pass on x86_64 Linux. A full-dictionary
browser smoke check of the packaged app verifies seven selected readings,
including both 먹잖아요 analyses, the confirmation-expression source link, and
the preserved 괜찮다 lexical reading with dictionary-only filtering enabled.

COV-022a predicate-adverb expansion adds eight ledger cases, reaching **162 cases
with 90 required and 78 forbidden judgments**. Four complete KAIST sentences
protect 다분히 → 다분하다, 가벼이 → 가볍다, 적잖이 → 적잖다, and 상당히 →
상당하다. The [development comparison](adverb-expansion-evaluation.json) records
these four new groups and no new GSD groups, without losing prior groups or
component sets. Remaining development misses are **219 KAIST and 207 GSD**.
The corpus convention supports related predicate lookup; it does not establish
that 하 is a literal morpheme in the surface adverb. All 66,570 frozen cases
pass and all 30 current compatibility fingerprints remain unchanged. Rust,
Clippy, stress, dictionary/CLI, frontend build and browser checks pass. Historical
baselines and reports remain unchanged.
`nix flake check` and `nix build .#web` pass on x86_64 Linux. A full-dictionary
browser smoke check of the packaged app verifies five adverb readings, preserved
whole-word alternatives, normalized root display, and the -이/-히 source links.

COV-019b negative auxiliary particles and short prohibitives add fourteen ledger
cases, reaching **176 cases with 98 required and 84 forbidden judgments**. The
complete GSD dev-s312 fixture protects 마라 → 말다. The
[development comparison](negative-auxiliary-evaluation.json) records this one
new GSD group and no new KAIST groups, with no lost groups or component sets.
Remaining development misses are **219 KAIST and 206 GSD**. Internal-particle
and mood cases have source-backed synthetic evidence. No claim of contextual
mood/sense validation follows from the grouped-lemma score. All 66,570 frozen
cases and all 30 current compatibility snapshots pass. Rust, Clippy, stress,
dictionary/CLI, frontend build and browser checks pass, including -어라 and
internal 는 source links. Historical reports and baselines remain unchanged.
`nix flake check` and `nix build .#web` pass on x86_64 Linux. The packaged app's
full-dictionary browser smoke check verifies five negative-auxiliary readings,
normalized short forms, internal particle order, and -어라/는 source links.
Dictionary glosses still use a compatible entry's first sense; this check does
not validate contextual homonym selection.

COV-019c auxiliary adjective inflections and legacy-link review add fourteen
ledger cases, reaching **190 cases with 105 required and 91 forbidden judgments**.
Four complete GSD sentences preserve annotated auxiliary-adjective groups. The
[development comparison](auxiliary-class-evaluation.json) records no gained or
lost gold groups and no lost component sets; remaining misses stay at **219
KAIST and 206 GSD**. Candidate constraints are not measured as recall gains.
The report records all 15 removed analyses across the seven targeted rejection
cases, including unknown-head alternatives sharing the same invalid auxiliary
ending. Other candidates in those cases remain unchanged. This is a reviewed
sample, not a corpus-wide precision estimate. All 66,570 frozen cases and all
30 current compatibility fingerprints pass. Rust, Clippy, stress, dictionary/CLI,
and browser/API checks pass. Historical reports and baselines remain unchanged.
`nix flake check` and `nix build .#web` pass on x86_64 Linux. A full-dictionary
smoke check of the packaged app verifies six preserved readings, seven excluded
lemma groups, unchanged original-word candidates, and the -은 source link.
The preview is updated. Dictionary glosses remain hints rather than contextual
homonym or sense selection.

COV-015 inventories all **203 canonical grammar forms** (138 endings, 55 particles,
four prefinals, six suffixes) and adds **140 teaching labels**. The shared catalog
cites 232 unique KRDict entries through 258 source references. The attributed
233-entry fixture also includes the alternate -ㅂ시다 boundary source. Tests check
inventory equality and resolve every source, including kind-sensitive exceptions
for expressions, component bundles, and spaced/contracted dictionary headwords.
Ten browser examples verify labels, source panes, normalized component order,
and unchanged CLI candidates. This is presentation coverage, not a precision or
contextual translation benchmark.

The audit also exposed the legacy 습시다 spelling. COV-017g replaces it with
읍시다 and the correct vowel boundary, including ㄷ/ㅅ/ㅂ recovery. Eleven ledger
cases bring the total to **201 cases with 111 required and 96 forbidden judgments**.
The complete KAIST MH2_0159-s160 fixture preserves 봅시다 → 보다, which already
matched before the canonical-form correction. The [recorded comparison](grammar-label-evaluation.json)
finds no new/lost development groups or component sets; misses remain **219 KAIST
and 206 GSD**. It also records individual candidate additions/removals for thirteen
propositive inputs. All 66,570 frozen corpus cases and 30 current compatibility
fingerprints pass; no historical baseline was regenerated. Rust, Clippy, stress,
dictionary/CLI, frontend build, and browser/API checks pass. Further propositive
lexical-class and prefinal restrictions remain open under COV-017/019.
`nix flake check` and `nix build .#web` pass on x86_64 Linux. The updated packaged
preview passes a full-dictionary smoke check of eight readings/source links,
including 들읍시다/도웁시다 and the spaced -는 데다가 expression. Desktop and
mobile screenshots were inspected; labels wrap without horizontal overflow.
Lexical glosses still use the first compatible dictionary entry/sense (e.g. the
먹다 homonym hint can be “be deaf”); these checks do not certify contextual gloss
selection, which remains outside the current token-level scope.

COV-014 adds conditional particle and copula readings for spelled names, numbers,
and foreign words. The [comparison](foreign-nominal-evaluation.json) records
**17 new KAIST and 22 new GSD development matches**, with no lost gold groups or
component sets. Remaining misses are **202 KAIST and 184 GSD**. Complete source
sentences and a 39-token selection index protect these recoveries offline.
A recovered group is not verification of pronunciation: every non-Hangul
allomorph assumption is explicit, and source spellings such as Bilbe are retained
literally. Twelve ledger cases bring the total to **213 cases with 119 required
and 100 forbidden judgments**.

The report compares seventeen targeted surfaces, finding no removed component
groups; existing contracted copula readings gain explicit pronunciation
provenance. All 30 current output fingerprints and all 66,570 frozen corpus cases
pass. Rust, Clippy, stress, dictionary/CLI, frontend build, and browser/API checks
pass, including ten displayed boundary cases, condition-bearing JSON export,
unknown-base filtering, exact punctuation boundaries, and streaming byte offsets.
No historical baseline or prior evaluation report was regenerated. This does
not add transliteration, named-entity recognition, pronunciation selection, or
cross-punctuation token merging; those limits are stated in COV-014's scope.
`nix flake check` and `nix build .#web` pass on x86_64 Linux. The updated
packaged app passes a full-dictionary browser smoke check of eight readings,
including separation of copula and later auxiliary contraction conditions.
Condition-bearing JSON export, unmatched-word filtering, and mobile overflow
checks pass; desktop and mobile screenshots were inspected.

COV-017h adds intention/expectation and concessive endings: 으리라고, 을지라도,
and 자면. The [development comparison](intention-ending-evaluation.json) records
**10 new KAIST and one new GSD gold group**, with no lost groups or component
sets. Remaining development misses are **192 KAIST and 183 GSD**. Eleven complete
source sentences protect these recoveries offline. Fifteen new ledger cases
bring the total to **228 cases with 127 required and 107 forbidden judgments**.

The batch checks distinct allomorph and prefinal licenses, known adjective and
copula exclusions for 자면, -답다 spelling, and separation of an earlier
predicate's restrictions from a later auxiliary's ending. Unknown lexical
classes remain unclassified; the honorific extension of 자면 is explicitly
identified as composition requiring independent linguistic review. Six source
entries supply three new grammar labels, taking the current catalog to 206 forms.
The two 자면 homonyms remain distinguishable in the source pane; expression
bundles do not insert an implicit reporting predicate or select a contextual sense.

All 66,570 frozen corpus cases and all 30 current output fingerprints pass.
Rust, Clippy, stress, dictionary/CLI, frontend build, and browser/API checks pass.
The report also preserves the individual additions for 23 targeted surfaces,
with no previous analyses removed. Historical baselines/reports are unchanged.
`nix flake check` and `nix build .#web` pass on x86_64 Linux. The updated
packaged preview passes a full-dictionary smoke check of eight readings/source
links, including the -자면 expression homonym, -답다 derivation and a longer
auxiliary group. Desktop and mobile screenshots were inspected; the mobile
layout has no horizontal overflow. Dictionary glosses still use compatible
entry/sense hints, not contextual disambiguation.

COV-018c adds emphatic/concessive particles and ㄴ커녕 contraction, and corrects
the coda restriction on locative 서. COV-017i separately adds the homonymous
predicate ending -(으)나마. The [comparison](emphatic-particle-evaluation.json)
records **12 new KAIST and two new GSD grouped matches**, with no lost groups or
component sets; remaining misses are **180 KAIST and 181 GSD**. One gain,
GSD dev-s934/6 확약서 → 확약, remains a segmentation-review case: the sentence
concerns submission of a written pledge. Thirteen other new recoveries have
explicit offline corpus tests. No corpus gains are attributed to the separate
-(으)나마 ending; its evidence is source-backed synthetic cases.

Nineteen ledger cases bring the total to **247 cases with 137 required and 116
forbidden judgments**. The browser has twelve new reading/source-link checks,
including both 조금이나마 analyses and normalized 먹긴커녕. The catalog now
covers 214 canonical forms, with ten additional source entries. All previously
included source entries are unchanged. Locative ABC서 retains its analysis but
loses the old unnecessary vowel-pronunciation condition; this reviewed provenance
change is recorded separately from added candidates across 23 targeted surfaces.
No old component groups are removed in those cases.
Subject/object case phrases are excluded as bases for the new focus particles;
the ledger specifically rejects 조금 + 이 + 나마 while preserving its particle
and copular-ending alternatives. Bare 커녕 does not inherit the adverbial
particle-chain license of 은/는커녕.

All 66,570 frozen corpus cases and all 30 current output fingerprints pass.
Rust, Clippy, stress, dictionary/CLI, frontend build and browser/API checks pass.
Historical baselines and reports are unchanged. Contextual homonym selection,
further particle combinations and independent Korean-language review remain open.
`nix flake check` and `nix build .#web` pass on x86_64 Linux. The refreshed
packaged preview passes a full-dictionary smoke check of eight readings/source
links, including both 조금이나마 interpretations, locative 서울서 and contracted
먹긴커녕 with its provenance and ㄴ커녕 source entry. Desktop and mobile
screenshots were inspected; no horizontal overflow was found.

COV-018d definition particles and COV-017j short quotations add **24 new KAIST
and two new GSD grouped matches**. The [comparison](quoted-definition-evaluation.json)
records no lost groups/component sets; remaining development misses are **156
KAIST and 179 GSD**. Twenty-six complete source sentences and a stable-ID index
protect the recoveries. The isolated 이란 case has a separate Copula-role test;
its earlier nominal context is not inferred. Command, retrospective and scoped
conjectural forms have source-backed synthetic tests, not attributed corpus gains.

Twenty-one ledger cases bring the total to **268 cases with 148 required and 126
forbidden judgments**. Five new labels cover the two definition particles, two
quotation endings, and scoped 으리 prefinal, bringing the catalog to 219 forms.
Six new source entries are included without changing any earlier fixture entry.
Eight browser cases check alternate readings, normalization and source links.
The source's 행복하란 example is retained, rather than imposing a blanket
adjective-command ban; further mood and derivational constraints remain open.

The same report reviews eight remaining 라는 cases. Three corpus noun + particle
annotations differ from the existing sourced copula + ending analysis; the other
five require quoted-clause or omitted-copula-fragment review. None is converted
into a required particle merely to improve recall. All 30 current output
fingerprints and all 66,570 frozen corpus cases pass. Rust, Clippy, stress,
dictionary/CLI, frontend build and browser/API checks pass. Individual additions
for 22 targeted surfaces are recorded, with no prior analyses removed.
Historical reports/baselines remain unchanged; independent linguistic review
and the broader inventory audit remain open.
`nix flake check` and `nix build .#web` pass on x86_64 Linux. The refreshed
packaged app passes eight full-dictionary reading/source-link checks, including
both particle and copular definition readings, quoted commands, retrospective
quotation and the conjectural prefinal. The explicit standalone 이란 copula role
also passes an API check. Desktop and mobile screenshots were inspected; there
is no horizontal overflow or browser error.

COV-020b adds conditional omitted-copula 라는 and explicit 이라는 fragments.
The [comparison](copula-fragment-evaluation.json) records **two new KAIST grouped
matches**, leaving **154 KAIST and 179 GSD development misses**. No previously
recovered group or component set is lost. Two complete, byte-identical source
sentences cover the gains; tokenization, punctuation and streaming offsets have
separate regression checks. The ledger now contains **271 cases with 150
required and 127 forbidden judgments**.

All 30 current output fingerprints and all 66,570 frozen corpus cases pass.
Rust, Clippy, dictionary/CLI, stress, frontend build and browser/API checks pass.
The browser verifies both Copula-role choices, the omitted-context condition,
normalized display, existing grammar source and filtered export. Fourteen
individual surfaces are compared: only 이라는 and 라는 gain candidates, and
no prior analyses are removed. No new grammar labels or source entries are
needed. Historical baselines and reports remain unchanged. Additional quoted
clause attachment and independent Korean-language review remain open.
`nix flake check` and `nix build .#web` pass on x86_64 Linux. A full-dictionary
packaged-browser check uses a complete sentence containing both explicit and
omitted fragments. Both Copula-role alternatives, the context condition,
grammar source links, filtered export and original punctuation pass. Desktop
and mobile screenshots were inspected with no overflow or browser errors.
Dictionary hints remain context-free: for example, 사랑 can display the
reception-room homonym in this sample, so successful decomposition does not
establish the intended dictionary sense.

COV-017k adds the prefinal-position necessity/intention bundle 어야겠. The
[comparison](obligation-evaluation.json) records **two new KAIST and one new GSD
grouped match**, leaving **152 KAIST and 178 GSD development misses**. No earlier
group or component set is lost. Five complete, byte-identical source sentences
preserve the three recoveries and two GSD cases whose gold includes implicit
하다. The latter remain measured differences rather than changing the adapter
or inserting an unspelled auxiliary to force a match.

Twelve new ledger cases bring the total to **283 cases with 158 required and
131 forbidden judgments**. One label covers the canonical prefinal-position
bundle, bringing the catalog to **220 forms**; three source entries are added
without altering any previous fixture entry. Twenty-seven surfaces have
individual candidate comparisons, with no previous analyses removed. The
progressive boundary check rejects the new necessity + 고 있다/계시다 route
while preserving progressive + necessity.

Rust, Clippy, stress, dictionary/CLI, frontend build and browser/API checks pass.
All 30 current output fingerprints and all 66,570 frozen corpus cases pass.
Nine browser cases cover contractions, auxiliary grouping, copulas, suffixes,
honorific/past markers, 하 + 여 display normalization and source links. Historical baselines and reports are
unchanged. Inherited ending/prefinal and auxiliary constraints and independent
Korean-language review remain open.
`nix flake check` and `nix build .#web` pass on x86_64 Linux. The refreshed
packaged app passes eight full-dictionary reading/source-link checks and resolves
all three expression entries. The viewer's existing 하 + 여 normalization is
verified separately from canonical API 어야겠. Desktop and mobile screenshots
were inspected; there are no browser errors or horizontal overflow.

The inspected 해야겠더라 output also makes a remaining candidate-audit issue
visible: besides the sourced retrospective ending, inherited rules generate
더 + 어라/으라 alternatives. These are recorded among this report's individual
candidate additions, not certified by the corpus recall gains. Their prefinal
and mood licenses belong to the open COV-017 ending audit.
