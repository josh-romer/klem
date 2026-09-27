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
optional exact morpheme sequences, optional `lemma_kinds` and `morpheme_kinds`,
required/forbidden verdicts, rationales, and primary-source links. Missing fields
leave that dimension unconstrained. Role lists must match their corresponding
text-list lengths when both are present. This lets identical 이 strings retain
distinct suffix and particle judgments. Older role-unspecified judgments preserve
their broad scopes. Overlapping contradictory judgments, duplicate IDs, and
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

## Factual endings and command prefinal licenses (COV-017l)

[Individual candidate comparison](prefinal-license-evaluation.json) records 63
reviewed surfaces against commit `1f3435d`. Factual 더 + 라 and 으리 + 라-family
paths now coexist with bundled endings. Recovered past/modal/retrospective
markers no longer license the reviewed command/request/proposal endings. The
separate sourced 더라는 bundle preserves 못하더라는 without the incorrect
더 + 으라는 command reading. Its complete KAIST test sentence is an offline
regression fixture; no corpus annotation or frozen baseline is rewritten.

The development comparison finds no lost groups or component sets and no new
grouped matches: remaining misses are **152 KAIST and 178 GSD**. Seventeen new
stable ledger cases bring the total to **300 cases, 167 required judgments and
139 forbidden judgments**. These are source-backed agent judgments; the unjudged
candidate queue and independent Korean-language review remain open.

One of thirty compatibility fingerprints changes: 먹었었겠더라 loses twenty
incompatible 더 + 어라/으라 paths and gains ten factual 더 + 라 paths with the
same lexical hypotheses and earlier markers. The prior hash is retained, and
every changed analysis is included in the report. Bundled 더라 and every other
analysis for that word remain. The other twenty-nine fingerprints and the
1,024-syllable memory stress test pass. All **66,570 frozen corpus cases** pass,
as do the offline Rust tests and Clippy.

The teaching catalog now covers **221 canonical forms** using 258 primary KRDict
entries, with alternate propositive source 68883 bringing the source fixture to
259 entries. All earlier source entries are unchanged. Scope limits include
further 어라 exclamation licenses, 자 homonyms, lexical verb/adjective classes,
and contextual sense selection; see the [rule scope](rules.md#factual-라-family-and-command-prefinal-licenses-cov-017l).

The production frontend build, complete browser/HTTP regression suite,
`nix flake check`, and `nix build .#web` pass on x86_64-linux. A Chromium smoke
check of the packaged app with the full local dictionary verifies seven selected
readings and their source links, four forbidden paths, and desktop/mobile layout.
The flake's other declared platforms were not executed on this host.

## Omitted copulas and colloquial nominals (COV-020c)

[The evaluation](omitted-copula-evaluation.json) compares commit `a2cd23f` with
reviewed omitted-이 paths before 지/지요/죠, 면, ㄴ데, and ㅂ니다/ㅂ니까, plus
finite 거/것 alternatives before copulas. It records every added candidate for
41 audited surfaces. Four additional KAIST and five GSD development groups
match; no grouped recoveries or component sets are lost. Remaining development
misses are **148 KAIST and 173 GSD**. Nine complete source sentences protect the
individual gains, preserving original short versus expanded noun annotations.

Fourteen new ledger cases bring the total to **314 cases, 176 required and
144 forbidden judgments**. The 221-form teaching catalog is unchanged in size;
four short-allomorph sources bring its support to 262 primary entries, plus
alternate propositive source 68883 (263 fixture entries). Every prior source
entry is unchanged. The lexical fixture adds fifteen attributed primary entries
for filtered alternatives and homonym preservation. Headword-only and POS-only
filtering remain distinct: an unclassified identity is not a certified POS match.

All prior analyses remain in the thirty stress snapshots. Three fingerprints
each gain one omitted-copula path: nominal 먹어보 before 지 않다, 하 before
지 않았음 + 을, and 공부해야하 before ㅂ니다. These noun spellings are lexical
hypotheses, not a dictionary-membership claim. Every added analysis is recorded,
and earlier hashes and revision notes are retained. All 66,570 frozen corpus
cases, the 1,024-syllable memory test, offline Rust tests, and Clippy pass.
Independent linguistic review and the broader coverage checklist remain open.

The production frontend build and complete browser/HTTP suite pass, including
short/full nominal selectors and CLI parity. `nix flake check` and
`nix build .#web` pass on x86_64-linux. The packaged app's full-dictionary Chromium
smoke verifies seven readings, all four added short-allomorph source links,
three forbidden paths, lexical 거지 preservation, and desktop/mobile layout.
Other declared Nix platforms were not executed on this host.

## Adverb/repeated nominal bases and shortened adverbs (COV-022b)

[The source inventory](adverb-root-inventory.json) records 33 forms and their
actual dictionary entries. Eight adverb bases and twenty-one repeated nominal
bases gain adverbial suffix paths. 익히/특히 gain the documented 익숙히/특별히
recoveries with related predicate lookup lemmas; the full forms also work. The
[evaluation](adverb-root-evaluation.json) records every added analysis for 55
surfaces, with no removals. Fourteen base/role combinations lack compatible
entries in the pinned dictionary, including twelve absent bases and two
adverb-only homonyms. These remain explicit filtering limits.

Twelve new cases bring the ledger to **326 cases, 184 required and 148 forbidden
judgments**. Optional lemma/morpheme role constraints now distinguish suffix 이
from particle 이. Tests verify that unjudged homonyms stay in the review queue,
broader contradictory scopes are rejected, and malformed role lengths fail.
Existing role-unspecified scopes retain their previous meaning. Role-specific
source judgments remain agent-authored pending independent linguistic review.

The four offline corpus sentences keep whole-word adverb gold; they do not
supply independent derivational gold. Development recall remains **148 KAIST and
173 GSD misses**, without lost grouped recoveries or component sets. All thirty
current compatibility fingerprints, all 66,570 frozen cases, and the
1,024-syllable memory test pass. The Rust suite and Clippy pass. The 221-form
teaching catalog and its 263-entry grammar-source fixture remain unchanged;
a separate 52-entry attributed lexical fixture supplies the new dictionary tests.

Formatting, the frontend production build, the complete browser/HTTP suite,
`nix flake check`, and `nix build .#web` pass on x86_64-linux. The packaged app
with the full dictionary passes seven role-specific derivations and their suffix
source links, lexical default selection, and the missing-base 틈틈이 filtering
check. Desktop and mobile checks find no overflow or JavaScript errors. Other
declared Nix platforms were not executed on this host.

## Shortened 하다 nominalizations (COV-021b)

[The comparison](hada-ki-evaluation.json) records additions for 84 surfaces,
with no removed candidates, recovered groups or component sets, and thirty
unchanged stress fingerprints. Two complete development sentences verify
강구키 → 강구하다 and 조성키로 → 조성하다. GSD also gains an incidental match
for 이시가키와 → 이시가하다; its sentence names Ishigaki and Miyako as islands.
That annotation anomaly is recorded separately, not treated as evidence that
the generated predicate exists. Original-word and nominal alternatives remain.
The measured development misses are **147 KAIST and 171 GSD**; this is a gold
match count, not a candidate precision estimate.

Eight source-backed ledger cases bring the total to **334 cases, 188 required
and 152 forbidden judgments**. The rules preserve full/short nominalization
parity across eight bundles and three coda classes, ordinary particle/copula
composition and licensed auxiliary paths. Four attributed offline dictionary
entries support CLI filtering and browser checks; existing grammar labels and
source mappings are reused. Historical corpus baselines remain unchanged.

Formatting, the Rust suite, Clippy, all 66,570 frozen cases, the complete
browser/HTTP suite, `nix flake check` and `nix build .#web` pass on x86_64-linux.
The full-dictionary packaged app passes five normalized paths and their -기
source links, four rejected restorations, preservation of the 이시가키 nominal
alternative, and desktop/mobile checks without JavaScript errors or overflow.
Frontend production source is unchanged. Other Nix platforms were not executed.

## Polite informative and reported endings (COV-017m)

[The comparison](reporting-evaluation.json) records four additional development
recoveries: KAIST 넘었답니다/묻었답니다 and GSD 물어본답니다/좋았답니다. Four
complete, byte-identical annotated sentences supply offline regression evidence.
Development misses are **145 KAIST and 169 GSD**, without lost grouped matches
or recovered component sets. All thirty existing stress fingerprints remain
unchanged; historical corpus baselines are not regenerated.

Fourteen source-backed cases bring the ledger to **348 cases, 196 required and
158 forbidden judgments**. Tests cover present/tense allomorphs, honorific and
retrospective boundaries, copulas, known adjective auxiliaries and -답다,
reported-command homonyms, grouped auxiliary and lexical alternatives, and NFD.
The 225-form teaching catalog adds four canonical labels with nine attributed
source entries. The grammar fixture now has 272 entries, 271 supporting the
catalog plus the pre-existing propositive allomorph entry. An eleven-entry
lexical fixture supports dictionary/CLI parity. These are source-backed agent
judgments, pending independent linguistic review; gold recovery is not a
precision score or contextual sense judgment.

Formatting, the Rust suite, Clippy, all 66,570 frozen cases, frontend production
build, complete browser/HTTP suite, `nix flake check` and `nix build .#web` pass
on x86_64-linux. The full-dictionary packaged app passes eight choices (including
both 먹으시랍니다 readings), their four grammar-source families, four rejected
paths, and desktop/mobile checks without JavaScript errors or overflow. Other
Nix platforms were not executed on this host.

## Enumerative copular -요 (COV-020d)

[The comparison](copula-yo-evaluation.json) records **seven additional KAIST
lemma-group matches** and no GSD gains or lost groups/component recoveries.
Five source-supported connective uses (선배요, 아니요, 연장이요, 자화상이요,
아비요) have complete byte-identical sentence fixtures. Two sentence-final cases,
본분이요 and 사회요, match the lexical group incidentally; standard spelling
distinguishes terminal 오 from connective 요. They remain explicitly separated
from the five validated uses. Measured misses are **138 KAIST and 169 GSD**.

The ledger has **356 cases, 201 required and 161 forbidden judgments**. Role
constraints distinguish ending 요 from particle 요 and preserve the explicit
copula fragment. The 226-form catalog adds -요 with primary source 86117; the
273-entry grammar fixture retains every previous entry. Four attributed lexical
entries support CLI/library dictionary parity and browser reading selection.

Two of thirty stress snapshots add exactly one unknown-nominal copula hypothesis
each: 먹어봤어 + 이다 + 요 and 들으셨겠어 + 이다 + 요. These are structural
hypotheses, not assertions of lexical membership or the intended analysis. Each
addition was inspected individually; all previous candidates and provenance
remain, and all historical hashes/change notes are retained. The other 28
snapshots are unchanged. Frozen corpus baselines are not regenerated.

Formatting, the Rust suite, Clippy, all 66,570 frozen cases, frontend production
build, complete browser/HTTP suite, `nix flake check` and `nix build .#web` pass
on x86_64-linux. The full-dictionary packaged app passes four connective choices,
separate ending/particle source links and polite alternatives, filtering of the
two unknown snapshot nominals, and desktop/mobile checks without JavaScript
errors or overflow. Other Nix platforms were not executed on this host.

## Causal endings (COV-017n)

[The comparison](causal-evaluation.json) records two new GSD development
recoveries, 추천하길래 and 뽑길래, protected by complete byte-identical source
sentences. Remaining development misses are **138 KAIST and 167 GSD**. No
previous groups or recovered component sets are lost. The separate causal 기에
and nominalization 기 + 에 readings illustrate why lemma-group recall cannot
measure decomposition precision. All additions across 41 audited surfaces are
recorded, including unknown lexical hypotheses; none of those hypotheses is
certified merely by being generated.

Twelve new source-backed ledger cases bring the total to **368 cases, 208 required
and 166 forbidden judgments**. Tests cover prefinal differences, literal ㄱ
boundaries, explicit copulas, auxiliary/답다 composition, NFD, dictionary/CLI
parity and preserved nominalization alternatives. Two primary ending entries
bring the teaching catalog to **228 canonical forms**, supported by 274 source
entries; the grammar fixture contains 275 entries including the existing extra
propositive allomorph. Every earlier source entry remains unchanged. Nine
lexical entries supply the offline dictionary tests. The inventory queue now
records nine scoped reviews and 706 entries without a disposition in that
ledger. Independent linguistic review remains pending.

Formatting, the Rust suite, Clippy, all **66,570 frozen corpus cases**, all thirty
unchanged stress fingerprints and the 1,024-syllable memory test pass. Historical
corpus baselines and optimization snapshots are unchanged. The frontend build,
complete browser/HTTP suite, `nix flake check` (including the inventory integrity
check), and `nix build .#web` pass on x86_64-linux. Other declared Nix platforms
were not executed. The packaged app with the full dictionary passes eight causal
readings, two nominalization alternatives, both new source links, five forbidden
paths, and desktop/mobile checks without JavaScript errors or overflow.

Omitted copulas before these endings, shortened 하다 causal allomorphs, further
outer particles and contextual interpretation remain tracked as open work.

## Expressive auxiliary 하다 left class (COV-019d)

[The comparison](auxiliary-left-hada-evaluation.json) records 75 removed
hypotheses across 32 audited surfaces. Each removal has a known verb or
represented copula immediately before expressive 어 하다, including inherited
negative classes and internal particles. All eight newly forbidden ledger paths
were present before the change and are now absent; the four new required paths
remain. Unknown lexical heads remain unclassified, so dictionary presence alone
still does not certify the adjective sense required by this construction.

The ledger now contains **380 cases, 212 required and 174 forbidden judgments**.
The offline source fixture adds expressive sense 9 to auxiliary 하다 entry
62888, retaining its causative sense 1 and every earlier entry field. The
228-form teaching catalog and 275-entry grammar fixture are unchanged. The
persistent inventory records ten scoped reviews and 705 entries without a
manual disposition. The 하다 review specifically covers this boundary, not
all nine senses of the source entry.

Development grouped recovery and component sets are unchanged: **138 KAIST and
167 GSD misses** remain. The source-backed forbidden paths are agent-authored
judgments; the corpora do not independently validate them. All **66,570 frozen
cases**, all thirty unchanged stress fingerprints and the 1,024-syllable memory
test pass. Historical baselines and optimization snapshots are unchanged.

The Rust suite, formatting, Clippy, dictionary/CLI regressions and complete
browser/HTTP suite pass. `nix flake check` and `nix build .#web` pass on
x86_64-linux; other declared platforms were not executed. Frontend production
source is unchanged. The packaged app with the full dictionary passes four
expressive choices, six rejected paths, display of sense 9 and its exact source
link, and desktop/mobile checks without JavaScript errors or overflow.
Independent Korean-language review and other auxiliary attachment restrictions
remain open.

## Quoted alternatives (COV-017o)

[The comparison](quoted-alternatives-evaluation.json) records three new KAIST
development recoveries and one GSD recovery, leaving **135 KAIST and 166 GSD
misses**. Three complete byte-identical source sentences protect the four lemma
groups. No previous gold groups or recovered component sets are lost. Across
74 audited surfaces, 265 analyses are added and none removed; unknown lexical
hypotheses remain unjudged. All thirty stress fingerprints are unchanged, and
historical corpus baselines and optimization snapshots are preserved.

Ten source-listed expressions add eight canonical grammar forms, bringing the
teaching catalog to **236 forms** with 284 source entries. The grammar fixture
contains 285 entries and retains all prior entries unchanged. Twenty-two new
ledger cases bring the total to **402 cases, 224 required and 184 forbidden
judgments**. Tests distinguish present allomorphs, command vowel boundaries,
copular/factual alternatives, prefinal licenses and known auxiliary/adjective
classes, including honorific composition. Bundled expressions do not insert
an implicit 하다 lemma or choose a contextual quotation sense.

These ten expression entries fall outside the four POS classes of the persistent
715-entry inventory. Their individual source dispositions are recorded in this
comparison; the inventory still has ten scoped reviews and 705 entries without
a manual disposition. Independent Korean-language review remains pending.

The full dictionary lacks 해방시키다: its unfiltered recovery from
해방시킨다거나 succeeds, while dictionary-only mode correctly returns no
readings. The connective-clause/copula case 위해서라거나 remains a measured
miss under COV-020. Neither gap is hidden by changing the dictionary or corpus.

Formatting, the Rust suite, Clippy, all **66,570 frozen corpus cases**, the
1,024-syllable memory test, frontend production build and complete browser/HTTP
suite pass. `nix flake check` and `nix build .#web` pass on x86_64-linux; other
declared platforms were not executed. The packaged app with the full dictionary
passes eight quoted-alternative choices and source links, five forbidden paths,
the dictionary-miss empty state, and desktop/mobile checks without JavaScript
errors or overflow.

## Enumerative particles and choice ending (COV-018e/017p)

[The comparison](enumerative-particle-evaluation.json) records six new particle
forms and the literal ending -든가, retaining copular and bundled quoted
alternatives. Three selected KAIST **training** tokens now recover their gold
groups: 것이라든가, 취미라든가 and 않든가. Complete byte-identical sentences
protect those cases; they are not a held-out score. Development recovery remains
**135 KAIST and 166 GSD misses**, with no lost gold groups or component sets.

The ledger now contains **433 cases, 241 required and 198 forbidden judgments**,
including 31 new cases. The candidate review records 500 additions and three
removals across 78 surfaces. The removed paths are known adjective/copula
classes before present 는다 after honorific 시. Composition with particle 든가
exposed this existing boundary gap; both the standalone and composed paths are
now checked. Unknown lexical head classes remain unjudged. Subject/object case
splitting is also excluded for the new particles where the source requires a
nominal/adverbial or listed final-ending base.

The teaching catalog has **243 canonical forms**, with 289 dictionary source
entries and 290 grammar-fixture entries. Every previous source entry is retained.
The pinned dictionary lacks separate 라든가 and 이든가 particle headwords;
explicit related-form mappings link existing entries, supported by NIKL form
tables. Ending and particle homonyms retain separate labels and source panes.
Six new scoped inventory reviews bring the ledger to **16 reviewed entries and
699 without a disposition**. These are scoped judgments, not certification of
all senses or attachments. Independent Korean-language review remains pending.

Formatting, the Rust suite, Clippy, all **66,570 frozen corpus cases**, all thirty
unchanged stress fingerprints, the 1,024-syllable memory test, frontend production
build and complete browser/HTTP suite pass. Historical baselines and optimization
snapshots are unchanged. `nix flake check` and `nix build .#web` pass on
x86_64-linux; other declared platforms were not executed. The packaged app with
the full dictionary passes eleven reading choices, distinct particle/ending and
related-form source links, nine forbidden paths, and desktop/mobile checks
without JavaScript errors or overflow.

## Destination and recipient particles (COV-018f)

[The comparison](destination-particle-evaluation.json) records **two new KAIST
and one new GSD development recovery**: 강에다, 노동자보고 and 거기에다.
Three complete byte-identical source sentences protect those gold groups.
Remaining development misses are **133 KAIST and 165 GSD**, with no lost groups
or component recoveries. Across 66 audited surfaces, 121 analyses are added and
none removed. Bundled and component paths remain alternatives, and unjudged
lexical hypotheses are retained explicitly in the report.

Twenty-four new judgment cases bring the ledger to **457 cases, 257 required
and 206 forbidden judgments**. Tests cover case/allomorph boundaries, recipient
particles, nominalization/suffix composition, outer particles, NFD, foreign-base
pronunciation conditions, and preserved predicate readings. Separate emphatic
다/다가 is limited to eight reviewed case forms and seven deictic bases; it
does not license arbitrary nominal, adverbial or predicate-ending stripping.
The recipient's contextual suitability and the deictic headword's intended sense
are not inferred from a dictionary match.

The catalog now has **255 canonical grammar forms**, supported by 301 source
entries. The grammar fixture contains 302 entries and retains every earlier
entry unchanged. Twelve scoped particle reviews bring the persistent inventory
to **28 scoped entries and 687 without a disposition**. All source senses and
attachment notes remain visible; these reviews do not certify every sense or
combination. Independent Korean-language review and further particle/adverbial
coverage remain open.

Formatting, the Rust suite, Clippy, all **66,570 frozen corpus cases**, all thirty
unchanged stress fingerprints, the 1,024-syllable memory test, frontend production
build and complete browser/HTTP suite pass. Historical baselines and optimization
snapshots remain unchanged. `nix flake check` and `nix build .#web` pass on
x86_64-linux; other declared platforms were not executed. The packaged app with
the full dictionary passes fifteen reading choices, distinct particle/ending
source links, six forbidden paths, preservation of the 돌보다 verb reading,
and desktop/mobile checks without JavaScript errors or overflow.

## Enumerative 다/이다 particles (COV-018g)

[The comparison](enumerative-da-evaluation.json) records **72 added analyses and
one merged-provenance change across 39 audited surfaces**, with no removed paths
or provenance. Enumerative 다/이다 accepts vowel/consonant nominal boundaries,
respectively, retaining emphatic and copular alternatives. Identical 저기 + 다
paths retain both enumerative and emphatic provenance. The browser shows both
functions, while represented copulas prefer KRDict's copula homonym over the
separately tagged enumerative particle.

Development recovery remains **133 KAIST and 165 GSD misses**, with no lost
component sets. Mean candidates increase from 5.7428 to 5.7933 in KAIST and
5.2791 to 5.3130 in GSD. These are ambiguity measurements, not linguistic
precision scores. A complete byte-identical GSD training sentence preserves the
existing copular gold for 옷이다; it is not relabeled as enumeration.

The ledger contains **473 cases, 265 required and 214 forbidden judgments**,
including sixteen new cases. The catalog has **256 canonical forms**, 303 source
entries and 304 grammar-fixture entries. All previous source entries remain
unchanged. Two new scoped reviews bring the inventory to **30 scoped entries
and 685 without a disposition**. Lexical nominal identity, surrounding enumeration,
contextual sense and broader attachment combinations remain open.

Three stress fingerprints change: 의사다 gains 의사 + 다; 2년만이다 gains
unverified 2년만 + 이다 and 2년만이 + 다 hypotheses; 공부해야합니다 gains
unverified 공부해야합니 + 다. Every previous analysis, provenance and hash is
preserved. The remaining 27 fingerprints and historical corpus baselines are
unchanged. These additions illustrate why raw rule candidates and contextual
correctness must remain separate.

Formatting, the Rust suite, Clippy, all **66,570 frozen corpus cases**, reviewed
stress checks, the 1,024-syllable memory test, frontend production build and
complete browser/HTTP suite pass. `nix flake check` and `nix build .#web` pass on
x86_64-linux; other declared platforms were not executed. The final packaged app
with the full dictionary passes ten reading choices, merged source references,
copula/particle source switching, six forbidden paths, four homonym checks, and
desktop/mobile inspection without JavaScript errors or overflow. Independent
Korean-language review and fresh-passage evaluation remain pending.

## Further omitted copulas and connective 은 (COV-020e/018h)

[The comparison](omitted-connective-evaluation.json) records **six KAIST and three
GSD development grouped gains**, leaving **127 and 162 misses**, respectively.
There are no lost gold groups or component sets. The GSD gains include an
incidental match to an apparent annotation error for the place name 테르니;
that match is not counted as linguistic evidence for a copula. Nine complete
byte-identical sentences preserve the annotations. 어디서고 composes through
an existing particle-marked copula base; broader eligibility remains for review.

The ledger now has **503 cases, 283 required and 226 forbidden judgments**, with
thirty new cases covering omission, nominalization, ending homonyms and 은/는
boundaries. No valid but unsupported honorific omission is labeled forbidden.
The pinned dictionary lacks 엘리트주의: raw recovery for 엘리트주의니 succeeds,
while dictionary-only mode remains empty. Dictionary/CLI regressions preserve
that distinction rather than manufacturing a vocabulary entry.

Across 114 audited surfaces, **115 analyses are added and none removed**.
Four stress fingerprints gain individually recorded nominal/copula hypotheses;
prior candidates, provenance and hashes are retained. Some auxiliary or
particle-marked hypotheses remain explicitly unjudged, especially represented
copula + progressive 고 있다/계시다. Internal 는 before 싶다 remains a separate
visible gap. The remaining 26 fingerprints and historical corpus baselines are
unchanged. Mean development candidates rise from 5.7933 to 5.8345 in KAIST and
5.3130 to 5.3569 in GSD; these are ambiguity measures, not precision estimates.

The catalog still has **256 canonical forms**, now supported by 304 source entries
and 305 grammar-fixture entries. Earlier source entries are unchanged. Twelve
new scoped dispositions bring the review queue to **42 scoped entries and 673
without a disposition**. Two expression sources are recorded in the evaluation
outside the queue's 715-entry POS scope. Independent Korean-language review,
other omission families and broader attachment constraints remain pending.

Formatting, the Rust suite, Clippy, all **66,570 frozen corpus cases**, reviewed
stress checks, the 1,024-syllable memory test, frontend production build and full
browser/HTTP suite pass. `nix flake check` and `nix build .#web` pass on
x86_64-linux; other declared platforms were not executed. The final packaged app
with the full dictionary passes twelve normalized reading choices, related
allomorph source lookup, six forbidden paths, missing-vocabulary empty state,
and desktop/mobile inspection without JavaScript errors or overflow.

## Honorific copula omission (COV-020f)

[The comparison](honorific-copula-evaluation.json) records recovery of the omitted
copula before honorific 시, including 선수셨다 and 의사셨어요, and the bundled
short ending in 의사세요. Across 66 audited surfaces, **72 analyses are added
and none removed**, with no changes to existing provenance. Development recovery
is unchanged at **127 KAIST and 162 GSD misses**. Three complete annotated
sentences preserve lexical 마시다/주다 alternatives; these are preservation
checks, not new gold recoveries or held-out precision evidence.

The candidate ledger has **529 cases, 297 required and 238 forbidden judgments**,
including 26 new cases. The catalog retains **256 canonical forms**, with 306
source entries and 307 grammar-fixture entries. Four scoped source reviews bring
the inventory to **46 scoped entries and 669 without a disposition**. Honorific
referent suitability, other omitted prefinals and broader copula/auxiliary
attachment restrictions remain unresolved.

One stress fingerprint changes: 들으셨겠어요 gains two unverified nominal
들으 + 이다 + 시 + 었 + 겠 paths, with bundled 어요 or separated 어 + 요.
Every prior candidate, provenance and hash is retained. The other 29 fingerprints
and historical corpus baselines are unchanged.

Formatting, the Rust suite, Clippy, all **66,570 frozen corpus cases**, stress
checks, the 1,024-syllable memory test, frontend production build and complete
browser/HTTP suite pass. `nix flake check` and `nix build .#web` pass on
x86_64-linux; other declared platforms were not executed. The packaged app with
the full dictionary passes ten normalized reading choices, honorific/polite
allomorph source links, six forbidden paths and foreign-pronunciation conditions.
Desktop and mobile screenshots were inspected; no JavaScript errors or horizontal
overflow occurred. Independent Korean-language review and fresh-passage
evaluation remain pending.

## Contrastive desire links (COV-019e)

[The comparison](desire-topic-evaluation.json) records **71 added analyses
across 37 audited surfaces**, with no removed candidates or provenance changes.
The direct dictionary example 놀고는 싶지만 supports one contrastive 는
between 고 and 싶다. Existing 곤 contraction, prefinals, trial/negative/expressive
chains and represented copulas compose with the new link. Joined forms remain
tolerant input analyses, not recommendations to remove standard spacing.

Both development reports are byte-identical to the preceding batch, retaining
**127 KAIST and 162 GSD misses** and the same mean candidate counts. No new
annotated recovery is claimed. All 30 stress fingerprints and the historical
corpus baselines are unchanged. The ledger contains **542 cases, 306 required
and 242 forbidden judgments**, including thirteen new cases. Three scoped
source reviews bring the inventory to **49 scoped entries and 666 without a
disposition**. The source catalog and attributed lexical fixtures are unchanged.

Formatting, the Rust suite, Clippy, all **66,570 frozen corpus cases**, stress
and memory regressions, and the complete browser/HTTP suite pass. `nix flake
check` and `nix build .#web` pass on x86_64-linux; other declared platforms were
not executed. The packaged app passes nine full-dictionary reading choices,
particle source links, contraction notices and five forbidden-path checks.
Desktop/mobile screenshots were inspected without JavaScript errors or overflow.

Additional auxiliary left-class restrictions remain open. The audit records
먹고는싶어있는다 generating a known adjective auxiliary before 어 있다;
that path needs a separate source review and is not certified by this batch.
Independent Korean-language review, fresh-passage evaluation and the remaining
inventory dispositions are still pending.

## Continuative auxiliary left classes (COV-019f)

[The comparison](continuative-class-evaluation.json) records **188 removed
analyses across 83 targeted surfaces**, with no added analyses or changed
provenance on retained candidates. All 44 adjective/copula matrix paths were
present in the preceding binary and are now rejected. Both 어 and 고 before
있다/계시다 check the immediately preceding known class, including inherited
negatives, explicit 답다 derivation and represented copulas. Expressive and
causative 하다 restore a verb class; those continuation paths remain.

Development gold recovery is unchanged at **127 KAIST and 162 GSD misses**, with
no lost groups or component sets. Mean KAIST candidates decrease from 5.835824
to 5.835734; GSD remains 5.368806. These are ambiguity measures, not precision
estimates. Two stress fingerprints change: 먹어보고있다 and 먹게하고있다
lose their previously unjudged unknown-nominal + copula + 고 + 있다 alternatives.
All ordinary lexical/trial/causative readings and prior hashes remain recorded.
The other 28 fingerprints and historical corpus baselines are unchanged.

Twenty new ledger cases bring the total to **562 cases, 314 required and 254
forbidden judgments**. Two scoped reviews bring the inventory to **51 scoped
entries and 664 without a disposition**. Six specific expression sources remain
separately attributed outside the 715-entry grammar-POS queue. The source catalog
and lexical fixtures are unchanged. Unknown lexical heads remain candidates;
a dictionary match does not establish their contextual class or sense. Verb
selection alone does not settle transitivity, lexical subsets, aspectual meaning,
or every prefinal/particle condition.

Formatting, the Rust suite, Clippy, all **66,570 frozen corpus cases**, stress
and memory regressions, and the complete browser/HTTP suite pass. `nix flake
check` and `nix build .#web` pass on x86_64-linux; other declared platforms were
not executed. The packaged app with the full dictionary passes seven preserved
reading choices, twelve forbidden-group checks and original-word preservation.
Desktop/mobile screenshots were inspected; there were no JavaScript errors or
horizontal overflow. Independent Korean-language review and fresh-passage
validation remain pending.

## Sequential/emphatic connectives and their particles (COV-017q/018i)

[The comparison](seo-connective-evaluation.json) records **191 added analyses
across 59 audited surfaces**, with no removed candidates or changed provenance.
Literal 고서 and vowel-boundary 어서야 preserve separate 어서 + 야 readings;
reviewed connective slots admit emphatic 야, temporal 부터 and comparative
보다. Known class and prefinal restrictions on 고서 have positive and negative
regressions. Broader 어서야 prefinal licenses remain unreviewed.

Nine complete, byte-identical KAIST development sentences become exact grouped
matches, leaving **118 KAIST and 162 GSD misses**. No prior gold groups or
component sets are lost. Mean candidates change from 5.835734 to 5.837579 for
KAIST and from 5.368806 to 5.369106 for GSD; these measure ambiguity, not
precision. All 30 stress fingerprints and historical corpus baselines remain
unchanged.

Twenty-nine new ledger cases bring the total to **591 cases, 334 required and
263 forbidden judgments**. Seven scoped reviews bring the inventory to
**58 scoped entries and 657 without a disposition**. The catalog contains
258 canonical forms and 310 distinct source entries; the attributed grammar
fixture contains 311 entries, with every previous entry preserved. A separate
46-entry lexical fixture verifies dictionary filtering and CLI/library parity.

Formatting, the Rust suite, Clippy, all **66,570 frozen corpus cases**, stress
and memory regressions, frontend production build and the complete browser/HTTP
suite pass. `nix flake check` and `nix build .#web` pass on x86_64-linux; other
declared platforms were not executed. The packaged app with the full dictionary
passes ten reading choices, bundled/component alternatives, allomorph source
links and nine forbidden paths. Desktop/mobile screenshots were inspected
without JavaScript errors or horizontal overflow. The browser expectations
explicitly distinguish displayed 여서/여서야 after 하 from canonical 어서/어서야
used for lookup. Independent Korean-language review, fresh-passage evaluation,
other particle slots and remaining inventory dispositions are still pending.

## Modal and retrospective copula omission (COV-020g)

[The comparison](prefinal-copula-evaluation.json) records **94 added analyses
across 46 audited surfaces**, with no removed candidates or changed provenance.
Omitted 이 before 겠/더 preserves represented copula roles and the existing
prefinal order. Reviewed retrospective bundles retain separate decomposed
readings. Consonant-final omission, predicate irregular changes to nominal bases,
reversed prefinal order and fabricated lexical copula verbs have regressions.

Three complete byte-identical development sentences recover 마찬가지겠지만
(KAIST), 최고더군요 and 어디더라 (GSD), leaving **117 KAIST and 160 GSD
misses**. No earlier gold group or component set is lost. Mean candidates change
from 5.837579 to 5.842574 for KAIST and from 5.369106 to 5.377415 for GSD.
These are ambiguity measures, not precision estimates. All thirty stress
fingerprints and historical corpus baselines remain unchanged.

Thirty-five new cases bring the ledger to **626 cases, 358 required and 274
forbidden judgments**. Eight scoped grammar reviews bring the inventory to
**66 scoped entries and 649 without a disposition**. Three expression sources
are attributed separately; the existing label catalog and grammar fixture remain
unchanged. A 29-entry lexical fixture preserves homonyms, including the 누구
pronoun rather than the unrelated idiom that reuses its numeric export ID.

Formatting, the Rust suite, Clippy, all **66,570 frozen corpus cases**, stress
and memory regressions, and the complete browser/HTTP suite pass. `nix flake
check` and `nix build .#web` pass on x86_64-linux; other declared platforms were
not executed. The inventory drift check caught a documentation hash change;
regenerating the evidence queue resolved it. The packaged full-dictionary app
passes nine ordered reading choices, prefinal/bundle source links and eleven
forbidden paths. Desktop/mobile screenshots were inspected without JavaScript
errors or horizontal overflow.

Broader prefinal-ending restrictions remain open, including the recorded
더 + 다 problem in lexical and explicit/omitted copula paths. Bare 던/더라는
omission is not added. Full-form parity does not certify contextual grammar;
independent Korean-language review, fresh passages and remaining inventory
dispositions are still completion requirements.

## Retrospective following-ending licenses (COV-017r)

[The comparison](retrospective-license-evaluation.json) records **464 removed
analyses across 184 audited surfaces**, with no added analyses or changed
provenance on retained paths. Every removal contains a recovered 더 immediately
before one of the 33 reviewed incompatible endings. The 132-path matrix covers
verbs, adjectives and explicit/omitted copulas: 128 targets were present in the
previous binary, while four double-더라는 paths were already excluded. Auxiliary
chains, internal/outer particles and earlier prefinals cannot bypass the check.
Licensed retrospective followers, literal bundles and lexical stems remain.

Development gold recovery is unchanged at **117 KAIST and 160 GSD misses**, with
no lost gold groups or component sets. Mean candidates decrease from 5.842574
to 5.824167 for KAIST and from 5.377415 to 5.361898 for GSD. These are ambiguity
measures, not precision estimates. Four complete unchanged annotated development
sentences protect negative, connective, honorific and auxiliary readings. All
thirty stress fingerprints and historical corpus baselines are unchanged.

Eighty-one new cases bring the ledger to **707 cases, 375 required and 338
forbidden judgments**. The source review includes 46 entries: twenty grammar
entries gain scoped dispositions, twelve existing reviews add evidence while
preserving their earlier scope, and fourteen expression entries remain outside
the grammar-POS queue. The inventory now has **86 scoped entries and 629 without
a disposition**. The label catalog and dictionary fixtures are unchanged.

Formatting, the Rust suite, Clippy, all **66,570 frozen corpus cases**, stress
and memory regressions, and the complete browser/HTTP suite pass. `nix flake
check` and `nix build .#web` pass on x86_64-linux; other declared platforms were
not executed. The packaged full-dictionary app passes nine preserved reading
choices, prefinal/bundle source links and all 64 new forbidden-path judgments.
Desktop/mobile screenshots were inspected without JavaScript errors or horizontal
overflow. Dictionary/CLI and browser checks compare exact paths, preserving
unjudged alternatives instead of rejecting every reading with the same lemma.

The recorded 더 + 다 gap is closed for the reviewed standard-language paths.
Other followers remain open: 먹더나요 retains the separately represented,
unjudged 더 + 나 + 요 path, and nominalizing 기 needs its own review. Independent
Korean-language review, fresh passages and remaining inventory dispositions are
still completion requirements.

## Retrospective nominalization and connectives (COV-017s)

The [comparison](retrospective-connective-evaluation.json) audits **211 surfaces**:
**416 candidates removed, none added**, with no changed provenance on retained
paths. Every removed candidate contains recovered 더 immediately before one of
33 newly reviewed incompatible endings. All 132 targets in the verb/adjective/
explicit-copula/omitted-copula matrix were present in the preceding binary.
Nominal particles, later copulas, auxiliaries and earlier prefinals cannot bypass
the condition. Valid nominalizations and bundled/component alternatives remain.

Development gold recovery stays at **117 KAIST and 160 GSD misses**, without lost
groups or component sets. KAIST mean candidates decreases from 5.824167 to
5.823987; GSD stays at 5.361898. These are ambiguity measures, not precision
estimates. Four complete unchanged annotated sentences preserve 장손이기,
제한적이었음을, 먹게 and 먹기. All thirty stress fingerprints and historical
corpus baselines remain unchanged.

The 107 added cases bring the ledger to **814 cases, 413 required and 407 forbidden
judgments**. Thirty-seven source entries support this review; 29 grammar entries
gain scoped dispositions and six existing reviews add evidence. Two expression
entries remain separately attributed outside the grammar-POS queue. The inventory
now has **115 scoped entries and 600 without a disposition**. Short 며/면서/므로
sources join their existing canonical labels: 258 forms, 313 source entries and
314 grammar fixture entries, with all prior fixture entries preserved.

Formatting, the complete Rust suite, Clippy, all **66,570 frozen corpus cases**,
stress/memory regressions, frontend production build and complete browser/HTTP
suite pass. `nix flake check` and `nix build .#web` pass on x86_64-linux; other
declared systems were not executed. The packaged full-dictionary app passes
eight reading selections, short-allomorph source checks and all 69 new forbidden
paths. Desktop/mobile screenshots were inspected with no horizontal overflow
or JavaScript errors. The existing first-homonym gloss choice can still show
“be deaf” for 먹다; contextual sense ranking remains outside these morphology
checks and reader-visible gloss quality remains part of the completion review.

This closes the separately represented 더 + 나 + 요 and nominalizing 기 gaps
recorded by COV-017r. Adnominal and other following endings still need review.
The source-backed distinction between lexical 기로 하다 and auxiliary connectors
is preserved by a spaced-text regression; no joined auxiliary rule is inferred
from that main-verb construction. Independent Korean-language review, fresh
passages and remaining inventory dispositions are still pending.

## Retrospective adnominal and question alternatives (COV-017t)

The [comparison](retrospective-adnominal-evaluation.json) reviews **157 surfaces**:
**215 candidates removed and 85 added**, with no changed provenance on retained
analyses. Every removal contains recovered 더 before one of the 17 reviewed
present/prospective endings. Every added candidate contains 던가 or 던지 and has
a corresponding split analysis. The 68-path four-class matrix was present before
this change; the new bundles also reject a doubled retrospective marker.

The source review preserves 더 + 은/은데/은가/은지-family analyses rather than
inferring a prohibition from ordinary adnominal attachment notes alone. It adds
bundled 던가/던지, their copula and particle compositions, and 던가 before
conjectural 보다/싶다 with the existing adjective restriction. Choice 든가/든지
remain separate. 던지 is not introduced as an auxiliary connector, and neither
new bundle is treated as a productive copula base.

Development gold recovery remains **117 KAIST and 160 GSD misses**, without lost
groups or component sets. KAIST mean candidates rises from 5.823987 to 5.826103
as dictionary bundles become alternatives; GSD remains at 5.361898. These are
ambiguity measures, not precision estimates. Four complete unchanged annotated
sentences preserve 정도였던가, 아니었던가요, 먹던 and 별로였던. All thirty
stress fingerprints and historical corpus baselines remain unchanged.

The 144 added cases bring the ledger to **958 cases, 500 required and 464 forbidden
judgments**. Thirty-two KRDict entries and five NIKL references support the review.
Twenty-two grammar entries gain scoped dispositions and four existing reviews
add evidence; six expression entries remain separately attributed outside the
grammar-POS queue. The inventory now has **137 scoped entries and 578 without a
disposition**. Two new canonical forms and eleven new sources bring the catalog
to 260 forms and 324 source entries; all 314 previous grammar-fixture entries are
preserved, with eleven additions. Existing lexical and auxiliary fixtures are
merged by entry ID for dictionary/CLI parity.

Formatting, the full Rust suite, Clippy, all **66,570 frozen corpus cases**,
stress/memory regressions, frontend production build and complete browser/HTTP
suite pass. `nix flake check` and `nix build .#web` pass on x86_64-linux; other
declared systems were not executed. The packaged full-dictionary app passes ten
reading selections, split/bundle and short-allomorph source checks, and all 57 new
forbidden paths. Desktop/mobile screenshots were inspected with no JavaScript
errors or horizontal overflow.

These are bounded attachment and representation checks. Bare omitted-copula
의사던 remains unjudged; the question/connective sources do not certify that
adnominal boundary. Other retrospective followers, lexical/class restrictions,
independent Korean-language review, fresh passages and the broader inventory
review remain open.

## Omitted copula in attached questions (COV-020h)

The [comparison](question-copula-evaluation.json) reviews **105 surfaces** and
accounts for **132 added candidates**, with no removals or changed provenance
on existing analyses. Every addition carries the omitted-copula rule and a
represented copula before one of six reviewed question forms. The 48-pair matrix
checks full-form parity across eight nominal bases; composition tests cover
particles, nominalized predicates, auxiliaries, invalid boundaries and lexical
alternatives.

Two GSD development gold groups are newly recovered: **뭔지 and 뭔가 → 뭐 + 이다**.
Development misses are now **117 KAIST and 158 GSD**, with no lost groups or
component sets. Mean candidates increase from 5.826103 to 5.833843 for KAIST and
from 5.361898 to 5.368405 for GSD. These measure ambiguity, not linguistic
precision. Four complete byte-identical annotated sentences capture the two gains
and preserve the explicit 무엇일까/일부인지 forms.

Twenty-nine stress fingerprints are unchanged. 먹고싶은가를 gains one unverified
nominal 먹고싶으 + 이다 + 은가 + 를 hypothesis. Its former hash and earlier
history are retained, and the report records the exact addition. Every previous
analysis and its provenance remains. A dictionary regression excludes the
unmatched nominal while retaining the established 먹다 + 싶다 predicate group.
Historical corpus baselines are unchanged.

The 95 added cases bring the ledger to **1,053 cases, 574 required and 485 forbidden
judgments**. Seven KRDict entries and NIKL's explicit 뭘까 analysis support the
review. Six existing grammar dispositions add evidence; the queue remains at
**137 scoped entries and 578 without a disposition**. The grammar catalog keeps
260 forms and adds short ㄹ까요 source 82350, correctly classified as an
expression: 325 sources and 326 grammar-fixture entries. All previous entries
remain. The new lexical fixture contains 39 entries with their homonyms and
senses preserved.

Formatting, the full Rust suite, Clippy, all **66,570 frozen corpus cases**,
stress/memory regressions, frontend production build and complete browser/HTTP
suite pass. `nix flake check` and `nix build .#web` pass on x86_64-linux; other
declared systems were not executed. The packaged full-dictionary app passes nine
reading selections, question/allomorph source checks and all 21 new forbidden
paths. Desktop/mobile screenshots were inspected without JavaScript errors or
horizontal overflow. 뭔지 visibly retains 뭐 + 이 + 은지 under dictionary-only
filtering. The existing missing short English gloss for copular 이 remains a
reader-facing limitation outside this morphology change.

This batch restores the missing copula without extending general synonym or
long-form pronoun normalization. Other pronoun contractions, nominal bases,
attachment/class restrictions, independent Korean review and fresh-passage
evaluation remain open.

## 놓아 → 놔 contraction (COV-017u)

The [comparison](noh-contraction-evaluation.json) reviews **119 surfaces** and
accounts for **192 added candidates**, with no removals or changed provenance on
existing candidates. Each addition carries `contraction.noh` and a recovered
놓다-final predicate. Forty-eight short/full-form pairs exercise four lexical
heads, terminal endings, past and double-past markers, particles and auxiliary
composition. Thirteen forbidden paths protect the lexical and 아/어 boundary;
좋아 → 좌 and pronunciation-spelled 노아 are not generalized. Lexical 놔두다
and split 놓다 + 두다 alternatives remain separate.

KAIST development **놨었지요 → 놓다** is newly recovered. Development misses
are now **116 KAIST and 158 GSD**, without lost gold groups or component sets.
KAIST mean candidates changes from 5.833843 to 5.833933; GSD remains 5.368405.
These measure ambiguity, not linguistic precision. Two complete unchanged
annotated KAIST sentences capture the new recovery and preserve full 내놓아야.
All thirty stress fingerprints and historical corpus baselines remain unchanged.

The 64 added ledger cases bring totals to **1,117 cases, 625 required and 498
forbidden judgments**. Article 35 supplement 1 supports the spelling exception;
eight KRDict entries document the lexical and auxiliary contexts. The offline
lexical fixture contains 26 entries with all homonyms/senses retained. The new
scoped review for auxiliary 놓다 preserves its verb sense and its adjective/이다
sense, bringing the inventory to **138 scoped entries and 577 unreviewed**.
No grammar catalog additions are needed.

Formatting, full Rust tests, Clippy, all **66,570 frozen corpus cases**,
stress/memory regressions, frontend production build, browser/HTTP checks and
inventory verification pass. `nix flake check` and `nix build .#web` pass on
x86_64-linux; other declared systems were not executed. The packaged full-dictionary
app passes eight reading selections, source links and all 13 forbidden paths.
Desktop/mobile screenshots were inspected without JavaScript errors or horizontal
overflow; 놨었지요 visibly yields 놓 + 었 + 었 + 지요 under dictionary-only filtering.

This change does not normalize internal lexical contractions or establish
contextual senses. Unknown compound hypotheses, broader auxiliary restrictions,
independent Korean-language review and fresh-passage evaluation remain open.

## Informative and reported 다네/다는데 families (COV-017v)

The [comparison](report-ne-evaluation.json) accounts for **954 added candidates
on 186 surfaces**, with no removed candidates or changed prior provenance.
Each addition carries the new reported-family provenance and one of ten reviewed
canonical components. The tests require 119 paths and reject 68 exact invalid
paths, including wrong ㄴ/는 and (으)라 boundaries, prefinal order, known
auxiliary/adjective/copula roles and unlicensed composition. Unjudged lexical
hypotheses remain visible; these counts are not a precision estimate.

The implementation preserves informative/reported homonyms, separate factual
and command 라 forms, retrospective bundle/component alternatives, polite 요,
and source-listed concessive 도 composition. It does not insert a reporting
하다. The shorter 라는데 entry's attachment note is narrower than the related
더라는데/라는데요/라는데도 entries; the report explains the source-supported
family interpretation and the compositional inference for split 으리 + 라는데.
Unknown lexical classes and broader honorific judgments remain unverified.

Five development groups newly match: KAIST **대부분이라는데, 풍속이었다네,
있다는데**, and GSD **판매한다네요, 단골집이라는데**. Remaining misses are
**113 KAIST and 156 GSD**, with no lost gold groups or component sets. Mean
candidate counts are 5.834653 and 5.369607 respectively. Five complete
byte-identical annotated sentences preserve these gains. All thirty stress
fingerprints and historical corpus baselines remain unchanged.

The 187 new ledger cases bring totals to **1,304 cases, 744 required and 566
forbidden judgments**. Twenty-nine grammar/expression/particle entries and two
additional lexical-entry examples support the source review. The lexical fixture
contains 45 entries with all homonyms/senses retained. Ten canonical labels and
16 new sources bring the catalog to **270 forms, 341 source IDs and 342 grammar
fixture entries**, preserving every earlier entry. The command 으라네 label
excludes the factual-only 라네 homonym 75476. Four scoped dispositions bring
the inventory to **142 scoped entries and 573 without a disposition**.

Formatting, full Rust tests, Clippy, all **66,570 frozen corpus cases**,
stress/memory regressions, frontend production build, full browser/HTTP checks,
and inventory verification pass. `nix flake check` and `nix build .#web` pass
on x86_64-linux; other declared systems were not executed. The packaged
full-dictionary app passes nineteen reading selections, homonym/allomorph source
links and all 68 forbidden paths. Desktop/mobile screenshots were inspected
without JavaScript errors or horizontal overflow; 판매한다네요 visibly yields
판매하 + 는다네 + 요 under dictionary-only filtering.

Other quoted families and particle combinations, independent Korean-language
review, fresh-passage evaluation and the broader inventory audit remain open.

## Literal 되 and licensed 으되 (COV-017w)

The [comparison](doe-evaluation.json) accounts for **132 added candidates on
67 surfaces**, with no removals or changes to existing provenance. Canonical
으되 represents literal 되 after ordinary stems/honorific 시 and full 으되
after bare 있다/없다 compounds or past/modal markers. It does not invoke a
general 으-boundary recovery. The 32 required and 22 forbidden paths preserve
stem consonants, prefinal order, auxiliaries, copulas, -답다 and polite 요.
Short existential 있되/없되 and compounds remain explicitly **unjudged** under
the report's `doe-short-existential` followup; omitted copulas and further
particles have a separate followup. Test success does not settle those questions.

Two development groups newly match: KAIST **치렀으되 → 치르다** and GSD
**그리되 → 그리다**. The complete source sentences respectively describe a
past ceremony and drawing a planar graph. Remaining misses are **112 KAIST and
155 GSD**, with no lost groups or recovered component sets. Mean candidates are
5.834788 and 5.369707; these are ambiguity measures, not precision estimates.
Both unchanged annotated sentences are retained as offline fixtures. All thirty
stress fingerprints and historical corpus baselines remain unchanged.

The 54 added cases bring totals to **1,358 cases, 776 required and 588 forbidden
judgments**. The lexical fixture preserves 38 entries and their homonyms/senses.
One canonical label links 되/으되 (80289/80291), bringing the catalog to
**271 forms, 343 source IDs and 344 grammar fixture entries**. Every previous
label and fixture entry remains. Two scoped grammar reviews bring the inventory
to **144 scoped entries and 571 without a disposition**.

Formatting, full Rust tests, the new annotated-corpus test, Clippy, all **66,570
frozen corpus cases**, stress/memory regressions, frontend production build,
full browser/HTTP checks and inventory verification pass. `nix flake check` and
`nix build .#web` pass on x86_64-linux; other declared systems were not executed.
The packaged full-dictionary app passes seven reading selections, both allomorph
source links and all 22 forbidden paths. Desktop/mobile screenshots were
inspected without JavaScript errors or horizontal overflow.

The named unresolved allomorph/composition questions, broader grammar inventory,
independent Korean-language review and fresh-passage evaluation remain open.


## Noun-attached 치고 family (COV-018j)

[The comparison](chigo-evaluation.json) accounts for **113 added candidates on
70 surfaces**, with no removed candidates or changed existing provenance.
The three dictionary particles retain separate labels and noun attachment.
The 32 required and 31 forbidden paths cover plurals, bundles, topic/polite
composition, intervening cases, bare predicate endings and lexical ambiguity.
Other generated combinations remain explicitly unjudged; these counts are not
a precision estimate. The pinned sources were read locally because live KRDict
pages were inaccessible through the web tool.

GSD **아파트치고 → 아파트** newly matches its annotated group. Remaining
development misses are **112 KAIST and 154 GSD**, with no lost gold groups or
component sets. Mean candidates are 5.835374 and 5.370007 respectively. One
complete unchanged GSD sentence preserves the gain. All thirty stress
fingerprints and historical corpus baselines remain unchanged.

The 63 new cases bring the ledger to **1,421 cases, 808 required and 619
forbidden judgments**. The lexical fixture retains 29 entries with their
homonyms and senses. Three labels/source entries bring the catalog to
**274 forms, 346 source IDs and 347 grammar fixture entries**, preserving all
previous labels and entries. Three scoped inventory dispositions bring the
queue to **147 reviewed entries and 568 without a disposition**.
The source-backed 교수님 plural paths have a recorded dictionary headword gap;
dictionary-only filtering correctly removes those whole-base paths while
retaining 교수 + 님 + 들 alternatives. Further outer particles,
nominalization semantics, independent Korean review and fresh passages remain open.

Formatting, full Rust tests, Clippy, all **66,570 frozen corpus cases**,
stress/memory regressions, frontend production build, browser/HTTP checks and
inventory verification pass. `nix flake check` and `nix build .#web` pass on
x86_64-linux; other declared systems were not executed. The final Nix test run
includes the new honorific/plural and annotated-corpus regressions. The packaged
full-dictionary app passes eight reading selections, source links and all 31
forbidden paths. Desktop/mobile screenshots were inspected without JavaScript
errors or horizontal overflow; 아이들치고서 visibly yields 아이 + 들 + 치고서.


## Case marking after range particles (COV-018k; COV-018l followup)

[The comparison](range-case-evaluation.json) accounts for **84 added candidates
on 65 surfaces**, no removed candidates, and two provenance-only changes to
existing contracted 를 paths. The five reviewed pairs are 까지 + 가/를/에/로
and 부터 + 가. Sixteen dictionary entries supply direct example evidence,
separate from the grammar-entry attachment notes. Thirty required and seventeen
forbidden paths cover composition, immediate allomorphs and invalid boundaries;
other lexical/compositional hypotheses remain unjudged.

KAIST **역사까지를 → 역사** newly matches. Remaining development misses are
**111 KAIST and 154 GSD**, with no lost gold groups or component sets.
Mean candidates are 5.835419 and 5.370007 respectively. All thirty stress
fingerprints and historical corpus baselines remain unchanged. Two complete
unchanged KAIST sentences preserve the gain and the separate unjudged
편마다에도 observation. The latter is not silently counted as implemented or
converted into a forbidden judgment; its distribution remains COV-018l.

The 47 new cases bring the ledger to **1,468 cases, 838 required and 636
forbidden judgments**. The lexical fixture retains 37 entries and all their
homonyms/senses. The 274-form grammar catalog is unchanged. Five new scoped
reviews, an extended 부터 review and one explicit 마다 gap bring the inventory
to **152 scoped entries, one gap and 562 unreviewed**. The gap's linguistic
acceptability still needs review; dictionary absence and raw hypotheses for
6세/ABC also remain separate from correctness.

Formatting, full Rust tests, Clippy, all **66,570 frozen corpus cases**,
stress/memory regressions, frontend production build, browser/HTTP checks and
inventory verification pass. `nix flake check` and `nix build .#web` pass on
x86_64-linux; other declared systems were not executed. The final Nix run also
includes the new annotated-corpus test. The packaged full-dictionary app passes
eight reading selections, source links and all 17 forbidden paths. Desktop/mobile
screenshots were inspected without JavaScript errors or horizontal overflow;
역사까지를 visibly yields 역사 + 까지 + 를 under dictionary-only filtering.

An additional local debug probe on synthetic 학교 + repeated 까지가 inputs
completed at 26/194/770 syllables, yielding 18/130/514 candidates. The report
records single-run timings; these unjudged inputs check termination and growth,
not linguistic accuracy or novel throughput. Fresh-passage evaluation and
independent Korean review remain open.


## Comparison and extent particles (COV-018m)

[The comparison](extent-evaluation.json) records **123 added candidates on
81 surfaces**, with no removals or changed prior provenance. Noun-only 토록
and 마냥, noun/particle 만치, and explicit 어서 + 만치/만큼 retain their
separate roles. Whole lexical/adverb alternatives and prior shortened 하다
paths remain. Thirty-eight required and twenty-five forbidden judgments cover
attachment, suffixes, allomorphs and homonym boundaries; these counts do not
measure precision. Further connectors and semantic restrictions remain unjudged.

KAIST **필생토록 → 필생** newly matches. Development misses are now
**110 KAIST and 154 GSD**, with no lost gold groups or component sets. Mean
candidate counts are 5.835554 and 5.370007. Two complete unchanged KAIST
sentences preserve the duration gain and lexical 그토록 gold. All thirty
stress fingerprints and historical corpus baselines remain unchanged.

The 63 new ledger cases bring totals to **1,531 cases, 876 required and 661
forbidden judgments**. The lexical fixture retains 73 entries and all their
homonyms/senses. Three labels/source entries bring the catalog to **277 forms,
349 source IDs and 350 grammar fixture entries**; all previous entries remain.
Four scoped dispositions bring the inventory to **156 scoped entries, one
observed gap and 558 unreviewed**. Bound-noun joining, other particle/connector
combinations, independent Korean review and fresh passages remain open.

Formatting, full Rust tests, Clippy, all **66,570 frozen corpus cases**,
stress/memory regressions, frontend production build, browser/HTTP checks and
inventory verification pass. `nix flake check` and `nix build .#web` pass on
x86_64-linux; other declared systems were not executed. The final Nix tests
include the new corpus regression. The packaged full-dictionary app passes
eight breakdown selections, a whole-word 그토록 selection, source/homonym
separation and all 25 forbidden paths. Desktop/mobile screenshots were inspected
without JavaScript errors or horizontal overflow; 필생토록 visibly yields
필생 + 토록 under dictionary-only filtering.


## Nominal approximation suffix (COV-020i)

[The comparison](approximation-evaluation.json) records **53 added candidates
on 55 surfaces**, with no removals or changed prior provenance. Nominal -쯤
preserves lexical readings and composes with the existing bounded nominal
suffixes, particles and copulas. The nine forbidden paths check outer allomorphs
against the immediate ㅁ boundary; broader suffix order and semantic restrictions
remain unjudged. Numeric/foreign bases keep their spelling without guessing
pronunciation where 쯤 already determines the outer boundary.

KAIST **번쯤 → 번** newly matches, leaving **109 KAIST and 154 GSD development
misses**, with no lost groups or component sets. Mean candidate counts are
5.835734 and 5.370007. One complete byte-identical KAIST sentence retains the
original jxc annotation; the engine's suffix role comes from KRDict. All thirty
stress fingerprints and historical corpus baselines are unchanged.

The 39 new ledger cases bring totals to **1,570 cases, 906 required and 670
forbidden judgments**. A 44-entry lexical fixture retains every selected
homonym/sense. One source/label brings the catalog to **278 forms, 350 source
IDs and 351 grammar fixture entries**, preserving all prior mappings. The
715-entry grammar-POS queue is unchanged in scope: suffixes are outside it.
Independent Korean review, fresh passages and further attachment work remain.

Formatting, full Rust tests, Clippy, all **66,570 frozen corpus cases**,
stress/memory regressions, the frontend production build, browser/HTTP checks
and inventory verification pass. `nix flake check` and `nix build .#web` pass
on x86_64-linux; the other declared systems were not executed. The final Nix
suite includes the new annotated corpus regression. The packaged full-dictionary
app passes six split readings, a whole 그쯤 selection, suffix source lookup and
all nine forbidden paths. Desktop/mobile screenshots show 번 + 쯤 without
JavaScript errors or horizontal overflow. Its lexical gloss currently displays
`beon` from the dictionary's first sense; contextual selection of the counting
sense remains separate from morphological recovery.


## Quoted and confirmatory -며/-면서 families (COV-017x)

[The comparison](report-myeo-evaluation.json) records **1,125 added candidates
on 239 surfaces**, with no removals or changed prior provenance. Eighteen
canonical components retain statement, factual/copular, command, proposal,
question and retrospective roles. Known auxiliary/derived-adjective classes
and prefinal/allomorph licenses are checked separately. Source-attested 있다/
계시다 stative report possibilities survive, including inherited negatives.
Unknown lexical classes and retrospective question compounds remain unjudged.

KAIST gains **지원한다며, 필요하다면서, 모자란다면서도**; GSD gains **줄이라며,
현실이라며, 극복하겠다며**. Development misses are now **106 KAIST and 151
GSD**, with no lost groups or component sets. Mean candidate counts are
5.836229 and 5.372310. Six complete byte-identical sentences preserve these
annotations. All thirty stress fingerprints and historical baselines remain
unchanged; no corpus recall result is presented as overall candidate precision.

The 235 new ledger cases bring totals to **1,805 cases, 1,063 required and 748
forbidden judgments**. The lexical fixture retains 44 entries and all selected
homonyms/senses. Eighteen labels and 34 source entries bring the catalog to
**296 forms, 384 source IDs and 385 grammar fixture entries**. Fourteen scoped
inventory dispositions bring the queue to **170 scoped, one observed gap and
544 unreviewed**. COV-019g records older stative auxiliary report restrictions;
additional attachment review, independent Korean review and fresh passages
remain open.

Formatting, full Rust tests, Clippy, all **66,570 frozen corpus cases**,
stress/memory regressions, the frontend production build, browser/HTTP checks
and inventory verification pass. `nix flake check` and `nix build .#web` pass
on x86_64-linux; the other declared systems were not executed. The final Nix
suite includes both new annotated-corpus tests. The packaged full-dictionary
app passes 29 reading selections covering all eighteen labels, all six corpus
gains, auxiliary statives and split/bundled retrospective alternatives, plus
all 78 forbidden paths. Every mapped source remains accessible. Inspected
desktop/mobile screenshots show 필요하 + 다면서 with its source homonyms,
without JavaScript errors or horizontal overflow.


## Stative auxiliary reports and declaratives (COV-019g)

[The review](stative-report-evaluation.json) accounts for **96 added and 50
removed analyses across 178 surfaces**, with no provenance-only changes.
Auxiliary 있다/계시다 now preserve older plain-다 reports, including inherited
negatives; later dynamic auxiliaries reset the permission. Direct bare auxiliary
있다 rejects the reviewed 는다 declaratives while lexical 있다, 계신다,
있지 않는다 and nondeclarative endings retain their distinct behavior.
The report explicitly distinguishes direct usage evidence from inferred paradigm
extensions and retains the COV-019h prefinal/question/adnominal followups.

Development recall and candidate means are unchanged: **106 KAIST and 151 GSD
misses**, means 5.836229 and 5.372310, with no lost gold groups or component sets.
No new annotated-corpus recovery is claimed. All thirty stress fingerprints
remain byte-identical to the prior revision and historical baselines stay intact.

The **166 new cases** bring totals to **1,971 cases, 1,171 required and 806
forbidden judgments**. A 40-entry offline fixture preserves all selected lexical
homonyms/senses for dictionary/CLI and browser verification. No grammar labels
or source mappings change. The existing two auxiliary inventory dispositions
gain evidence, leaving **170 scoped, one observed gap and 544 unreviewed**.
Independent Korean review, fresh passages and the other open coverage families
remain pending.

Formatting, full Rust tests, Clippy, all **66,570 frozen corpus cases**,
stress/memory regressions, the frontend production build, browser/HTTP checks
and inventory verification pass. `nix flake check` and `nix build .#web` pass
on x86_64-linux; the other declared systems were not executed. The final Nix
suite includes all 166 new judgments and the exact-role dictionary parity test.
The packaged full-dictionary app passes eleven reading selections and all
58 forbidden paths. Source homonyms remain accessible. Inspected desktop/mobile
screenshots show 지내 + 고 + 있 + 다네 without JavaScript errors or horizontal
overflow. The auxiliary's dictionary gloss is `itda`; contextual English gloss
selection remains separate from morphological correctness.


## Shared present-declarative licenses (COV-017y / partial COV-019h)

[The review](present-license-evaluation.json) records **306 removed candidates
across 343 surfaces**, with no additions or changed surviving provenance. It
covers recovered non-honorific prefinals (167 removals), explicit/inherited
copulas (120), auxiliary adjectives (13), and explicit 답다 derivations (six).
Past/modal plain-다 counterparts, honorific verbal readings, later class-changing
auxiliaries and unknown lexical alternatives remain. The broader existential
honorific/question/adnominal questions remain COV-019h.

There are no lost development gold groups or component sets: **106 KAIST and
151 GSD misses** remain. Mean candidate counts are 5.836229 and 5.372109. All thirty
stress fingerprints remain byte-identical to the prior revision; historical
baselines are unchanged. No new annotated-corpus recovery is claimed.

The **338 new cases** bring totals to **2,309 cases, 1,340 required and 977
forbidden judgments**. A 39-entry lexical fixture preserves every selected
homonym/sense. Nine source additions bring the grammar catalog to **296 forms,
393 source IDs and 394 grammar fixture entries**. Nine new scoped dispositions
and nine updated reviews leave **179 scoped, one observed gap and 535 unreviewed**
in the persistent queue. Contextual sense selection, independent Korean review,
fresh passages and the other open coverage families remain pending.

A separate comparison of all 7,266 unique converted GSD development surfaces
finds two changes: 들리신다면 and 가신다면 each lose an omitted-copula
reading. Two complete byte-identical sentences and role-specific judgments
preserve their annotated verb readings. The visit-context 들리다 spelling and
source POS tags remain unchanged; this is no claim of contextual spelling
correctness. All six 들리다 source entries, including the redirect to 들르다,
remain in the dictionary fixture.

Formatting, full Rust tests, Clippy, all **66,570 frozen corpus cases**,
stress/memory regressions, frontend production build, browser/HTTP checks and
inventory verification pass. `nix flake check` and `nix build .#web` pass on
x86_64-linux; other declared systems were not executed. The final Nix suite
includes the two annotated-sentence regressions and all 338 new ledger cases.
The packaged full-dictionary app passes eleven reading selections and all
**169 required / 171 forbidden** new judgments. All nine added source entries
are selectable in the browser. Inspected desktop/mobile screenshots show
가 + 시 + 는다면 alongside the short -ㄴ다면 source, with retained alternatives,
no JavaScript errors and no horizontal overflow.


## Surprise and quoted -니 families (COV-017z)

[The source/candidate review](report-ni-evaluation.json) adds eight components
alongside existing 다니, preserving bare-verbal surprise and the distinct
statement, factual/copular, command, proposal and question licenses. Split
더 + 라니 and bundled 더라니 coexist. Polite surprise readings have separate
source evidence; homonym-specific speech levels are not inferred globally.

Three development gold groups newly match: KAIST **따라가자니, 상대하자니**
and GSD **하신다니**. No groups or recovered component sets are lost; remaining
misses are **104 KAIST / 150 GSD**. Mean candidates are 5.836499 and 5.372610.
Three complete, unchanged annotated sentences preserve those recoveries.
A separate probe of all 277 development surfaces containing 니 changes only
those three surfaces and 있다니 (provenance only). All 30 stress snapshots are
unchanged, and frozen historical corpus baselines are preserved.

There are **163 new cases: 109 required / 54 forbidden**, bringing the ledger
to **2,472 cases: 1,449 required / 1,031 forbidden**. The 53-entry lexical fixture
supports dictionary-only CLI/library parity. The grammar catalog contains
**304 canonical forms / 417 source IDs / 418 fixture entries**, with 24 added
sources. Seven new scoped inventory reviews and two updates leave **186 scoped,
one observed gap, 528 unreviewed**. Expression sources remain separately
attributed outside the queue's grammar-POS scope.

The 163-surface candidate comparison records 727 additions, no removals and
106 changes that only add the explanatory rule to existing 다니 readings.
Of the additions, 117 have dictionary headwords for every lemma; this is not a
precision estimate. The report distinguishes tested paths from unresolved
lexical-class, particle/copula and existential hypotheses. COV-017aa now tracks
lexical attachment review explicitly. Independent Korean review, fresh passages,
contextual sense selection and the other open families remain pending.

Formatting, Rust tests, Clippy, all **66,570 frozen corpus cases**, stress/memory
regressions, the frontend production build, browser/HTTP checks and offline
inventory verification pass. `nix flake check` and `nix build .#web` pass on
x86_64-linux; other declared systems were not executed. The Nix suite includes
all 163 new cases and the three complete annotated sentences. The packaged
full-dictionary app passes 18 reading selections and all **109 required / 54
forbidden** judgments. Source panes resolve all mapped homonyms. Inspected
desktop/mobile screenshots show 하 + 시 + 는다니 with the short -ㄴ다니 source
selected, no JavaScript errors and no horizontal overflow.


## Short quoted modifiers and change/conditionals (COV-017ab)

[The review](short-clause-evaluation.json) adds 단/는단/잔/냔/느냔/으냔/다간/
다가는, preserving quoted and change/conditional homonyms. Bare verbs remain
valid before conditional 단; present quotations use full 는 or attached ㄴ.
The generic question source explicitly supports omitted copula in 누구냔.
Noun suffix -단 is excluded from ending lookups.

KAIST **된단 → 되다** and **노력했단 → 노력하다** newly match their annotated
groups. No groups or recovered component sets are lost; remaining development
misses are **102 KAIST / 150 GSD**. Mean candidates are 5.837174 and 5.374412.
Two complete, unchanged source sentences preserve these recoveries. All 30
stress snapshots and frozen historical corpus baselines are unchanged.

There are **142 new cases: 92 required / 50 forbidden**, bringing the ledger
to **2,614 cases: 1,541 required / 1,081 forbidden**. A five-entry fixture (four lexical entries plus the unrelated -단 suffix as a
negative source control) complements the reused 53-entry -니 fixture. Dictionary-only CLI/library parity
covers all new judgments. The catalog now contains **312 canonical forms / 427
source IDs / 428 grammar fixture entries**, with ten new source IDs. Three new
scoped reviews leave **189 scoped, one observed gap, 525 unreviewed** in the
715-entry grammar-POS queue; expression sources remain separately attributed.

The 151-surface comparison records 599 added candidates and no removals or
changed existing provenance. Of those additions, 105 have dictionary headwords
for every lemma; this is not a precision estimate. A separate probe of all 17
converted development surfaces ending in the new spellings records 16 changes,
including noun-context 세단/판단. Whole-word readings remain, and no contextual
sense or suffix segmentation is inferred. The report keeps lexical-class,
particle/copula, existential and shortening followups open. Independent Korean
review and fresh-passage evaluation remain pending.

Formatting, Rust tests, Clippy, all **66,570 frozen corpus cases**, stress/memory
regressions, frontend production build, browser/HTTP checks and offline inventory
verification pass. `nix flake check` and `nix build .#web` pass on x86_64-linux;
other declared systems were not executed. The final Nix suite includes all 142
new cases and both complete annotated sentences. The offline browser fixture
contains suffix 73350 and asserts its presence before checking its exclusion
from the -단 ending sources. The packaged full-dictionary app passes thirteen
reading selections and all **92 required / 50 forbidden** judgments. Inspected
desktop/mobile screenshots show 노력하 + 였 + 단 with the quoted expression
source selected, no JavaScript errors and no horizontal overflow. The final
fixture-only rebuild produces a byte-identical web executable to that preview.
An interrupted final Nix/browser run was confirmed stopped and rerun successfully;
no interrupted run is counted as a passing check.
