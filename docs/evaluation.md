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

## Dictionary-backed lexical attachment evidence (COV-017aa)

The [finite policy](dictionary-attachments.md) adds per-reading entry evidence
and `--dict-compatible` in the library, CLI and browser. It preserves raw rule
hypotheses and the old headword-only policy, while checking broad lexical roles,
shared present-declarative attachments, six bare adjectival question families,
and the factual/command distinction for 아니다 + 라니/으라니. Valid homonyms,
unknown POS and token-initial separately written auxiliaries remain. Wish uses
of adjective commands/proposals are not categorically excluded.

A separate [dictionary-policy ledger](../tests/fixtures/dictionary-attachments.json)
contains **63 cases: 39 required / 24 forbidden**, with stable IDs and exact roles.
All required and forbidden paths are actually generated and headword-matched
before this optional filter; missing fixture entries cannot masquerade as fixes.
Eleven new attributed lexical entries complement the existing 53-entry fixture.
The raw ledger remains **2,614 cases: 1,541 required / 1,081 forbidden**; grammar
catalog and inventory counts remain unchanged (189 scoped / one gap / 525
unreviewed). Two existing source reviews link the new evidence.

The [report](dictionary-attachment-evaluation.json) compares **2,389 distinct
regression surfaces**. Unfiltered JSONL is byte-identical, and old headword-only
candidates and annotation fields are unchanged. The new filter removes 135
complete groups from 2,351 headword-matching analyses; every removal includes
entry-specific conflict evidence. This is not a contextual precision score.

On the pinned 81,758-word-token 무정 text, headword-only output retains 124,268
analyses, while the new filter retains 118,388. Complete-match token coverage
changes from 73,303 to 73,162. A source/representation audit of the losses found
that separately written auxiliaries must remain unknown; seven explicit cases
now preserve them. The remaining 141 tokens across 52 types expose adverbial-role
gaps (notably 아직도), older forms and unreviewed constructions; COV-018n tracks
the missing adverbial alternatives. Coverage counts do not measure correctness.

Three local release CLI runs per mode, including JSONL serialization to
`/dev/null`, had median times of **1.25 s before / 1.36 s after** for headword-only
output and **1.35 s** for the new filter. Peak RSS remained about **27–28 MiB**.
Per-reading evidence increases headword-only JSONL from 85.1 MB to 118.0 MB; the
new filter writes 113.0 MB. These are observations on one machine, not throughput
guarantees. Bulk processing still uses bounded caches and loads no definitions.

Formatting, Rust tests, Clippy, all **66,570 frozen corpus cases**, stress/memory
regressions, frontend production build, browser/HTTP checks and offline inventory
verification pass. `nix flake check` and `nix build .#web` pass on x86_64-linux;
other declared systems were not executed. The packaged full-dictionary preview
passes all **39 required / 24 forbidden** policy judgments and CLI/API parity.
Browser checks cover matching indices, filtered exports, the adjective 늦다 gloss,
separately written 싶었다, dictionary-free mode and mobile layout. Inspected
screenshots show factual 아니라니, adjectival 늦으냐니 and 싶 + 었 + 다, with no
JavaScript errors or horizontal overflow. The policy remains finite; broader
attachment work, independent Korean review and fresh-passage evaluation remain.

## Adverbial focus attachment (COV-018n)

[The review](adverb-focus-evaluation.json) adds lexical Adverbial alternatives
before 도/은/는/만/까지/부터 with compatible outer chains and reviewed range
particles after source-listed derived adverbs. Nominal/identity paths remain.
New adverbial paths do not inherit arbitrary noun-case marking; the dictionary
conflict filter now keeps 아직 + 도 while excluding its nominal-role hypothesis.
Genuine noun/adverb homonyms remain separately inspectable.

**55 new cases (38 required / 17 forbidden)** bring the raw ledger to **2,669
cases, 1,579 required / 1,098 forbidden**. A 28-entry dictionary fixture retains
all selected homonyms/senses. Five complete, unchanged KAIST/GSD development
sentences explicitly annotate six adverb-plus-particle tokens. Their lemma
strings already matched through nominal hypotheses, so no lemma-recall gain
is claimed. The separate 63-case dictionary-policy ledger remains unchanged.

All development case outcomes are identical: **102 KAIST / 150 GSD misses**.
Mean candidate counts increase from 5.837174 to **5.987264** (KAIST) and 5.374412
to **5.490239** (GSD). Across 82 focused/stress surfaces, 54 candidates are added,
none removed and no existing provenance changes. Three stress snapshots gain
four unknown-class adverbial hypotheses; each old hash/history is retained.
The inherited adverbial + particle + copula hypotheses remain unjudged under
COV-020. Corpus baselines are unchanged.

On the pinned novel, the conflict filter retains **119,554 analyses**, 1,166
more than before, with no losses. Complete filtered readings increase from
73,162 to **73,248 word tokens**: 86 gains across 18 types, including 58 아직도
tokens. These are lexical coverage figures, not contextual accuracy. The report
retains every newly matched type and its readings. 퍽's sound-word and intensifier
homonyms illustrate why POS compatibility cannot select a contextual sense.

Three local release CLI runs per mode, including JSONL serialization, give
median conflict-filter times of **1.29 s before / 1.32 s after**, with peak RSS
around **27–28 MiB**. Headword-only output grows from 118.0 MB to 122.6 MB and
conflict-filtered output from 113.0 MB to 113.9 MB. These are local observations,
not throughput guarantees. The grammar catalog is unchanged. Two new scoped
inventory reviews and four updated reviews leave **191 scoped / one observed
gap / 523 unreviewed** entries.

Formatting, Rust tests, Clippy, all **66,570 frozen corpus cases**, stress/memory
regressions, frontend build, browser/HTTP checks and offline inventory verification
pass. `nix flake check` and `nix build .#web` pass on x86_64-linux; other declared
systems were not executed. The packaged full-dictionary preview passes all
**38 required / 17 forbidden** new judgments with CLI/API parity. Browser checks
cover both dictionary policies, noun/adverb homonyms, ordered components, exports,
source entries and mobile layout. Inspected screenshots show 아직 + 도,
자세히 + 는, 일찍 + 부터 and 아직 + 까지 + 도, with no JavaScript errors or
horizontal overflow. Independent Korean review, fresh-passage validation and the
other open checklist families remain pending.

### COV-019i: contrastive 는 inside continuative auxiliary chains

The generator now preserves 고/어 + 는 before 있다/계시다, including existing
곤 expansion. Six direct KRDict examples establish the spaced constructions;
contracted and honorific forms are explicitly identified as compositional
inferences. Joined input exercises tolerant word analysis, not spacing repair.
See the [source and candidate review](continuative-topic-evaluation.json).

The batch adds 52 stable cases (33 required / 19 forbidden), bringing the raw
ledger to 2,721 cases with 1,612 required and 1,117 forbidden judgments. The
separate 63-case dictionary-policy ledger is unchanged. The 38-entry attributed
fixture exercises both dictionary filters and exact CLI/library annotation
parity; Unicode normalization, component ordering, class restrictions and unknown
heads are covered in `tests/continuative_topic.rs`.

All 106 additions across 82 focused/stress surfaces were inspected. There are no
removed analyses or changed existing provenance, and all thirty stress hashes
remain unchanged. Unknown lexical heads and existing 지만/지 + 말다 alternatives
remain visible as unjudged hypotheses; no precision claim is made. Development
outputs are unchanged, including per-case recovery, candidate means and the
102 KAIST / 150 GSD misses. No corresponding joined token in those development
sets provides a new recall result; the dictionary examples supply direct
construction evidence. Frozen corpus baselines are unchanged.

Validation: full Rust/web-feature tests, the full pinned corpus regression,
focused candidate/dictionary/stress tests, Clippy, formatting, frontend build,
and offline inventory verification. The source queue remains 191 scoped,
523 unreviewed and one unresolved gap; the three existing auxiliary/particle
reviews now link this additional scope.

Browser/HTTP regressions, `nix flake check` on x86_64-linux and `nix build .#web`
passed. The packaged preview with the full dictionary passed all 52 cases with
raw/filtered CLI/API parity, five displayed breakdowns, the internal particle's
source link, and desktop/mobile layout checks.

The pinned 81,758-word 무정 novel retains exactly the same aggregate filtered
output counts: 119,554 compatible-policy analyses and 73,248 tokens with at least
one such reading (130,363 / 73,303 for headword-only). No novel coverage gain is
claimed. Three sequential local Nix release runs per mode, including dictionary
lookup and JSONL serialization to `/dev/null`, measured median compatible-policy
time of 1.182s before and 1.209s after, with peak RSS around 28 MiB. These are
local observations, not throughput guarantees; raw measurements and input/dictionary
fingerprints are preserved in the source review.

### COV-017ac / COV-019h: adjectival question-family licenses

The six canonical 으냐/으냐는/으냐며/으냐면서/으냐니/으냔 forms now share
one bare-adjective check. This closes the plain 으냐/으냐는 exceptions without
removing general 냐 or verbal 느냐 alternatives. Known auxiliary Verb slots and
recovered prefinals cannot select the adjectival family; unknown lexical heads
and the optional dictionary policy's existing existential exceptions remain.
See the [21-entry source and candidate review](adjectival-question-evaluation.json).

There are 169 new stable cases (120 required / 49 forbidden), bringing the raw
ledger to 2,890 cases and 1,732 required / 1,166 forbidden judgments. The separate
63-case dictionary-policy ledger is unchanged. An 18-entry lexical fixture
checks both dictionary filters and complete CLI/library annotation parity.
All cases also exercise Unicode normalization and explainable component ordering.

Inspection of 187 focused/stress/observation surfaces accounts for 36 removals,
no additions and no changed existing provenance. Every removal selects the
adjectival question family after a recovered prefinal or known auxiliary Verb.
All thirty stress hashes and the fixed repeated-input stress checks remain.
Honorific 먹고있으신다네 and past-adnominal 앉아있은/눌러있은 are retained
as explicitly unjudged observations; this batch does not settle them.

Development recovery outcomes are identical for every case: misses remain
102 KAIST / 150 GSD. KAIST ambiguity is unchanged. GSD loses one non-gold
무다 + 하다 + 어/으냐는 hypothesis in 뭐하냐는; its gold 뭐하다 and general
냐는 path remain. The complete original `dev-s820` sentence is preserved and
tested. Mean GSD candidates change from 5.490239 to 5.490139; no recall gain is
claimed. Frozen corpus baselines remain untouched.

Full Rust/web-feature tests, the pinned full-corpus regression, Clippy,
formatting, frontend build, and offline inventory verification passed. Three
plain ending entries gain scoped reviews, making 194 scoped / 520 unreviewed /
one unresolved gap. The other eighteen reviewed expression entries have source
POS 품사 없음 and remain linked through their explicit grammar catalog mappings.

Browser/HTTP checks, `nix flake check` on x86_64-linux and `nix build .#web`
passed. The packaged full-dictionary preview passed all 169 cases with raw and
filtered CLI/API parity, five selected question breakdowns, source links and
mobile layout checks. A broader comparison of all 2,604 distinct ledger surfaces
found 37 removed analyses and no additions; the extra removal is the adjectival
으냐 hypothesis after 더 in 먹더냐. Its existing required general 냐 reading
remains.

The pinned 81,758-word 무정 benchmark loses eight filtered analyses across four
words: 네더냐, 계시냐, 주시더냐 and 아프더냐. All eight used 으냐 after
recovered 시 and/or 더. Every affected word retains other readings. Compatible
filter counts change from 119,554 to 119,546 analyses, with 73,248 tokens retaining
at least one reading; headword-only counts change from 130,363 to 130,355, with
73,303 matched tokens unchanged. Three sequential local Nix release runs per mode
measured compatible-policy median time of 1.294s before and 1.308s after, with
peak RSS around 28 MiB. These observations include dictionary lookup and JSONL
serialization to `/dev/null`; they are not throughput guarantees. Individual
removed and retained candidates, raw measurements and fingerprints are preserved
in the source review.

### Uncertain possibility and intention questions (COV-017ad)

[The comparison](uncertainty-evaluation.json) records 55 required and 37 forbidden
paths, all six grammar sources and the complete unchanged KAIST sentence.
KAIST development gains 같을는지 → 같다 (101 misses remain); GSD stays at
150 misses. No previously recovered gold group or component set is lost.
All thirty stress fingerprints remain unchanged. The main judgment ledger now
contains 2,982 cases with 1,787 required and 1,203 forbidden judgments; the separate
dictionary-policy ledger is unchanged. Catalog coverage is 315 canonical forms,
433 distinct source IDs and 434 offline grammar entries. The inventory has 196
scoped dispositions, one unresolved observed gap and 518 unreviewed entries.
These counts are scoped regression evidence, not a linguistic precision estimate.

The pinned 81,758-word-token novel gains 39 compatible-filtered analyses across
30 tokens (23 surface types), with no old reading removed. These include
unjudged inherited irregular and nominal/copula alternatives; source-backed
required judgments are reported separately. Three local Nix release runs give
compatible-mode median 1.2141 seconds versus 1.1912 before, with peak RSS below
29 MiB. Timing includes JSONL serialization and is a local observation, not a
throughput guarantee. Rust tests, Clippy, frozen corpora, browser/HTTP checks,
frontend build, `nix flake check` and the packaged web launcher passed on
x86_64-linux. Full-dictionary packaged API/CLI parity covers all 92 new cases;
desktop/mobile inspection covers five selected breakdowns and the grammar pane.

### Intention connectives and interrupted-intention auxiliaries (COV-017ae / COV-019j)

[The source/output comparison](intention-connectives-evaluation.json) records
130 required and 122 forbidden judgments across eight new canonical forms and
the existing 으려는 attachment check. The ledger has 3,234 cases / 1,917 required /
1,325 forbidden judgments; the separate dictionary-policy ledger is unchanged.
Across all 2,974 ledger/stress surfaces, 765 candidates are added and three
known nonverbal 으려는 paths removed, without provenance changes. All thirty
stress fingerprints remain unchanged. Candidate additions are not automatically
linguistic judgments; unknown stems and contextual ambiguities remain visible.

KAIST gains 하려다 → 하다. GSD gains the annotated 갈다 for 갈려는데,
but the complete sentence apparently intends 가다; that gain is incidental.
Development misses are 100 KAIST / 149 GSD with no prior group/component loss.
Two complete source sentences are retained without annotation changes. The
catalog has 323 forms, 451 distinct source IDs and 452 offline grammar entries.
The 715-entry review queue has 199 scoped dispositions, one unresolved gap and
515 unreviewed entries; the 16 new 품사 없음 expressions are reviewed explicitly
in the report/catalog rather than silently added to this POS-limited queue.

The pinned novel gains 24 compatible-filtered analyses and loses one represented
보 + 이다 + 으려는 hypothesis across 23 word occurrences (17 surface types).
Lexical 보이다 + 으려는 remains; no token loses all readings. Added 데다 and
뜨다 + 나다 alternatives remain unjudged in context. Three local Nix release
runs give compatible-mode median 1.2080 seconds versus 1.2275 before, with peak
RSS below 29 MiB. This is local timing evidence, not a speedup guarantee.
Rust, Clippy, frozen corpora, frontend, browser/HTTP and Nix checks pass on
x86_64-linux. The packaged full-dictionary API/CLI smoke covers all 252 cases;
desktop/mobile inspection covers five breakdowns, an auxiliary and a source pane.

### Result-transfer connectives (COV-017af / COV-019k)

[The source/output comparison](result-connectives-evaluation.json) records 51
required and 34 forbidden judgments. The main ledger now has 3,319 cases /
1,968 required / 1,359 forbidden judgments; the separate dictionary-policy ledger
is unchanged. Across 3,059 ledger/stress surfaces, 174 candidates are added,
23 unsupported full-form paths removed and 146 retained paths gain provenance.
One stress fingerprint changes: 의사다 gains an unknown predicate + 어다
hypothesis that full-dictionary headword filtering removes. Its noun-based
readings remain; the other 29 fingerprints are unchanged.

KAIST gains 가져다 → 가지다; GSD gains two 내려다 → 내리다 cases and
쳐다도 → 치다. The directional GSD compounds are annotation matches, not
proof of a generic 어다 + 보다 rule. Development misses are 99 KAIST / 146 GSD,
with no previously recovered gold group or component set lost. Frozen baselines
remain untouched. Catalog coverage is 324 canonical forms, 456 source IDs and
457 grammar entries. The inventory has 207 scoped reviews, one unresolved gap
and 507 unreviewed entries. These are bounded regression results, not a claim
of linguistic completeness or measured precision.

Rust/web-feature and Nix release tests, the frozen full-corpus regression,
Clippy, formatting, frontend build, browser/HTTP checks and inventory verification
passed. `nix flake check` and `nix build .#web` passed on x86_64-linux. The
packaged full-dictionary preview checks all 85 cases with CLI/API parity, five
selected breakdowns, dictionary source selection and desktop/mobile inspection.

The pinned 81,758-word-token novel gains 21 compatible-filtered analyses and
loses one unsupported noun 들 + copula 이다 + 어다가 path in 들여다가;
its lexical 들이다 reading remains. Another 159 retained analyses gain rule
provenance. No token loses all readings. Compatible totals become 119,628
analyses / 73,294 tokens with readings; headword-only totals become 130,449 /
73,349. New hypotheses include inherited irregular ambiguities and unjudged
lexical/contextual choices, so additions do not measure precision. Three local
Nix release runs give compatible median 1.195s versus 1.209s before, with peak
RSS below 29 MiB. Timing includes JSONL serialization and is a local observation,
not a throughput guarantee. Raw measurements and individual changes are in the
source report.

### Dictionary connective classes (COV-017ag)

The [source/output review](attachment-connectives-evaluation.json) adds 122
policy judgments (70 required / 52 forbidden), bringing the separate dictionary
ledger to 185 cases (109 / 76). Across 3,162 raw/stress/policy surfaces, raw and
headword-only candidates are unchanged. The compatible filter removes 52
individually tracked adjective conflicts; verb homonyms and unknown classes
remain. The broad comparison found 노래다 → 노랗다 + 어다, now paired with
a preservation judgment for 노래 + 이다 + 다. All 30 stress fingerprints and
the frozen corpus baselines remain unchanged. This policy change does not
claim a raw corpus recall gain; development misses remain 99 KAIST / 146 GSD.

The catalog adds -려는 (86688), giving 324 forms / 457 source IDs / 458 grammar
fixture entries. The review queue retains 207 scoped reviews and now records
three observed gaps with 505 unreviewed entries. Two new gaps are the missing
-(으)려나 question allomorphs; their full notes, separate expression homonyms
and raw probes are preserved under COV-017ah. Negative-auxiliary lexical-class
inheritance, contextual sense selection and independent Korean review remain open.

Rust/web-feature and release tests, frozen corpus regression, Clippy, formatting,
frontend build, browser/HTTP checks and inventory verification pass. Nix flake
checks and the packaged web build pass on x86_64-linux. The packaged full-dictionary
API/CLI checks all 122 new judgments; desktop/mobile inspection verifies the
unmatched adjective-only word remains visible, verb homonyms use their own gloss,
and auxiliary/copula components retain their order.

All novel candidates are identical under both filters: compatible totals remain
119,628 analyses / 73,294 matched tokens; headword-only totals remain 130,449 /
73,349, across 81,758 word tokens. Per-entry conflict evidence adds 2,368 JSONL
bytes per mode without removing valid homonym alternatives. Three sequential
local Nix release runs measured compatible median 1.197s versus 1.200s before,
with peak RSS below 29 MiB. This is a local timing observation, including JSONL
serialization, not a throughput guarantee. No novel precision or recall gain is
claimed. Raw measurements and comparisons are retained in the source report.

### Expectation questions and inference 보다 (COV-017ah / COV-019l)

[The source/candidate comparison](ryeona-evaluation.json) records 69 required
and 23 forbidden judgments across question/expression homonyms and inference
보다. The main ledger now has 3,411 cases / 2,037 required / 1,382 forbidden
judgments; the separate dictionary-policy ledger remains 185 cases. Across
3,253 distinct ledger/policy/stress surfaces, 313 candidates are added without
removing prior analyses or changing their provenance. All 30 stress fingerprints
remain unchanged. New candidates remain hypotheses rather than precision evidence.

All KAIST/GSD development rows are identical; misses remain 99 / 146. KAIST test
recovers 좋아지다 for 좋아지려나 in MH2_0010-s336/7, moving from 24,378 to
24,379 grouped matches out of 24,490 converted rows. No previous group or component
recovery is lost. The complete test sentence is now explicit regression evidence;
its source tags and segmentation are retained, and no held-out precision claim is
made. The gold lexical head lacks a dictionary entry, while 좋다 + 지다 remains
a tested dictionary-backed reading. Frozen corpus baselines are untouched.

The catalog has 325 canonical forms / 461 source IDs / 462 grammar entries.
Two prior question gaps become scoped reviews; new bounded reviews cover inference
보다 and polite 요, giving 211 scoped / 503 unreviewed / one unresolved gap.
The notes retain the question/expression distinction, modal composition limits,
other auxiliary/particle and copula-omission followups, and Korean review work.

Rust/web-feature and Nix release suites, frozen corpus regression, Clippy,
formatting, frontend build, browser/HTTP checks and inventory verification pass.
Nix flake checks and the packaged web build pass on x86_64-linux. The packaged
full-dictionary API/CLI checks all 92 judgments, with five selected desktop/mobile
breakdowns and source selection. Visual inspection also exposed COV-019m:
inference 보다 has the correct morphological class, but dictionary assessments
still admit its verbal homonym and display “try.” The exact assessment is retained;
this batch does not claim that auxiliary dictionary-class selection is complete.

The novel's compatible-filtered candidates are identical across 81,758 tokens.
Totals remain 119,628 analyses / 73,294 tokens with readings; headword-only totals
remain 130,449 / 73,349. Three sequential local Nix release runs measured compatible
median 1.209s versus 1.201s before, with peak RSS below 29 MiB. These local timings
include JSONL serialization and are not throughput guarantees. The novel does not
exercise a new matched path; no novel recall or precision gain is claimed.

## Auxiliary dictionary classes (COV-019m)

The [entry-policy review](auxiliary-dictionary-evaluation.json) resolves the
preceding batch's 오려나봐 mismatch. Dictionary assessment now shares the engine's
known auxiliary classes: inference 보다 supports the adjective homonym, trial
보다 supports the verb homonym, and known classes compose through negatives.
Unknown lexical/provider classes, ambiguous uses, separately written auxiliaries
and distinct copula inheritance remain preserved. KRDict's inference hint is
`boda`; this selects the supported entry without inventing a contextual translation.

The new ledger has 43 cases / 86 per-entry judgments, separate from raw validity
and whole-reading filter judgments. It tests connector ownership, internal
particles, 답다, repeated lemma slots, negative inheritance, copula resets,
missing homonyms, unknown providers, Unicode, bounded caching and CLI parity.
Across 3,286 surfaces, 324 entry assessments change on 245 surfaces. Raw,
headword-only and compatible candidate groups remain identical, as do all thirty
stress hashes. The complete frozen corpus regression passes without baseline edits.

The 81,758-word novel retains 130,449 headword-only analyses / 73,349 tokens with
readings and 119,628 compatible analyses / 73,294 tokens with readings. Both modes
change entry assessments for 722 tokens across 239 types, without losing a
candidate. Three sequential local Nix release runs measured compatible median
1.210s versus 1.238s before, with peak RSS below 28 MiB. Timing variation is not
evidence of a speedup; these measurements show no observed material regression.

Rust/web-feature tests, Clippy, formatting, frontend build, browser/HTTP tests,
inventory checks, x86_64-linux Nix flake checks and packaged web build pass.
The packaged full-dictionary viewer verifies all 86 judgments, five slot-specific
hints/source selections and desktop/mobile display. Existing inventory dispositions
link the new evidence; counts remain 211 scoped / 503 unreviewed / one gap.
Ordinary lexical-negative homonym consistency, contextual ranking, independent
Korean review and the remaining checklist families stay open.

## Independent 게/게서 particles (COV-018o)

The [source and candidate review](short-recipient-evaluation.json) adds independent
recipient/source particles 게 and 게서. 내게, 네게 and 제게 retain their represented
pronoun bases, following the dictionary and NIKL's explicit 네 + 게 analysis.
Existing outer particles, contracted topic/object particles and 게 + emphatic
다/다가 compose; predicate-ending 게 remains a separate candidate and source entry.

The 93 new ledger cases contain 77 required and 16 forbidden paths. Main totals
are 2,114 required / 1,398 forbidden judgments. Four full unchanged KAIST sentences
exercise the source's pronoun segmentation; alternative 나 + 에게 annotations in
other corpus rows are recorded without changing gold or silently expanding the
surface base. The grammar catalog now has 327 canonical forms / 463 distinct
source IDs / 464 grammar fixture entries. Two scoped source dispositions give
213 scoped / 501 unreviewed / one unresolved inventory gap.

Across 3,377 tracked surfaces, 114 candidates are added on 104 surfaces, with no
removals or provenance changes; all thirty stress hashes remain intact. KAIST
development recovers M2TA_089-s64/2 제게 → 제, leaving 98 misses and 22,122/22,220
grouped matches. GSD remains at 146 misses and 9,843/9,989 matches. Other development
case outcomes are identical. Mean candidate counts become 6.008731 / 5.506858.
All frozen corpus regressions pass without baseline edits.

The novel gains 231 compatible candidates across 225 tokens / 64 types, with no
previous candidate removed. The report retains every changed analysis, including
unjudged lexical hypotheses such as 길 + 게 and 정답 + 게 and inherited copula
alternatives. These are not all precision gains: broad nominal POS does not
establish a person/animal referent. The viewer can still choose the noun hint
“creek” for 내; the exact assessment is retained as unresolved homonym selection.

Rust, Clippy, formatting, frontend/browser/HTTP tests, inventory verification,
x86_64-linux Nix flake checks and the packaged web build pass. The packaged
full-dictionary viewer verifies all 93 judgments, CLI/API parity, four displayed
words, particle source selection and desktop/mobile layout. Three local sequential
Nix release measurements give compatible median 1.215s versus 1.199s before,
with peak RSS below 29 MiB. These are local observations, not throughput guarantees.

## Literary assertions (COV-017ai / COV-020j)

The [source and candidate review](nira-evaluation.json) adds dictionary-listed
-(으)니라 and -느니라, their distinct boundary/prefinal licenses, known auxiliary
classes, and vowel-final omitted copulas. 그림자니라 recovers 그림자 + 이다 +
으니라. The optional dictionary policy separates bare lexical verb/adjective
conflicts while preserving valid homonyms, existential uncertainty and separately
written auxiliaries. KRDict's 되지는 않으니라 example prevents a blanket inherited
verb-class rejection for negative auxiliaries; further negative/existential
judgments remain open.

The batch adds 54 morphology judgments (37 required / 17 forbidden), 15 dictionary
policy judgments (12 required / 3 forbidden), and three complete unchanged KAIST
sentences. Main validity totals are 2,151 required / 1,415 forbidden; dictionary
policy totals are 121 required / 79 forbidden. Three source dispositions bring
the inventory to 216 scoped / 498 unreviewed / one unresolved gap. The catalog
has 329 canonical forms / 466 distinct source IDs / 467 grammar fixture entries.

Across 3,441 tracked surfaces, 373 candidates are added on 60 surfaces, with no
removals or provenance changes; all thirty stress hashes remain unchanged.
KAIST development recovers 사랑하느니라 and 그림자니라, giving 22,124/22,220
grouped matches and 96 misses. GSD remains at 9,843/9,989 and 146 misses. Mean
candidate counts become 6.016877 / 5.508860. Frozen corpus regressions pass
without baseline edits. These reused development cases are regression evidence,
not an independent precision estimate.

The novel gains 70 compatible candidates across 67 tokens / nine types, with
no prior candidate removed. In 57 아니라 tokens the added candidate is
아 + 이다 + 으니라, an unjudged nominal/copula hypothesis alongside the existing
아니다 reading. Other inherited particle/copula alternatives also remain
unjudged; additions are not all precision gains. Compatible totals become
119,929 analyses / 73,317 tokens with readings; headword-only totals become
130,825 / 73,372 across 81,758 word tokens.

Rust/web-feature tests, Clippy, formatting, frontend/browser/HTTP tests, inventory
verification, x86_64-linux Nix flake checks and the packaged web build pass.
The packaged full-dictionary preview checks all 69 judgments, CLI/API/export
parity, five displayed breakdowns, all three source entries and desktop/mobile
layout. Three sequential local release runs measured compatible median 1.258s
versus 1.227s before, with peak RSS below 29 MiB. These local measurements include
JSONL serialization and are not throughput guarantees. Independent Korean review,
contextual selection and the remaining checklist families stay open.

## Vocative particles (COV-018p)

The [source and candidate review](vocative-evaluation.json) adds nominal 이여,
시여 and 이시여, and records the existing 아/야/여 boundaries. Consonant/vowel
selection includes ㄹ as a consonant. Plural and honorific nominal suffixes
compose, while whole-word and copula alternatives remain. The six source entries
have explicit review dispositions, giving 222 scoped / 492 unreviewed / one gap.
The grammar catalog has 332 canonical forms / 469 source IDs / 470 fixture entries.

The 34 new judgments contain 21 required and 13 forbidden paths, bringing main
validity totals to 2,172 required / 1,428 forbidden. Two complete unchanged KAIST
sentences cover 검이여 and 젊은이여. The former development miss now matches,
giving 22,125/22,220 grouped matches and 95 misses; GSD remains at 9,843/9,989 and
146 misses. Mean candidate counts are 6.017012 / 5.508860. This motivating
development case is regression evidence, not held-out evaluation.

Across 3,475 tracked surfaces, 39 candidates are added on 19 surfaces, without
removals or provenance changes. All thirty stress hashes and frozen corpus
baselines remain unchanged. The raw additions include ordinary unknown-head and
nominalization hypotheses, such as 젊은 + 이여 and 보다 + 음 + 이여. They are
retained in the report without asserting contextual correctness. Noun POS does
not establish addressability, politeness or an intended sentence interpretation.

The novel gains five compatible readings across three types: 선생이시여 (three
tokens), 아버지시여 and 하느님이시여. All additions are the expected noun plus
respectful vocative particle; no prior candidates are removed. This does not
resolve competing contextual interpretations or certify every inherited particle,
nominalization or copula composition.

Compatible totals become 119,934 analyses / 73,322 tokens with readings;
headword-only totals become 130,830 / 73,377, across 81,758 word tokens.
Three sequential local Nix release runs measured compatible median 1.251s versus
1.267s before, with peak RSS below 28 MiB. These include JSONL serialization;
timing variation is not evidence of a speedup or a throughput guarantee.

Rust/web-feature tests, Clippy, formatting, frozen corpus regression, frontend
build, browser/HTTP tests, inventory verification, x86_64-linux Nix flake checks
and the packaged web build pass. The full-dictionary preview verifies all 34
judgments, CLI/API/export parity, five displayed breakdowns, particle sources
and desktop/mobile layout. Independent Korean review and the remaining checklist
families stay open.

## Emphatic time/place 에야 (COV-018q)

The [source and candidate review](eya-evaluation.json) adds KRDict's nominal
compound 에야 alongside NIKL's explicit 에 + 야 decomposition. Both compose with
following 만, recovering 때에야만 as 때 + 에야 + 만 and 때 + 에 + 야 + 만.
General particle ordering stays unchanged. Nominal suffixes, nominalizations and
copulas preserve the split component's position and owner.

There are 34 new judgments (26 required / eight forbidden), bringing main
validity totals to 2,198 required / 1,436 forbidden. Three complete unchanged KAIST
sentences retain their original annotations, including 때 + 에 + 야만. The
program's finer split preserves the lexical group without rewriting that gold.
The motivating development miss now matches, giving KAIST 22,126/22,220 grouped
matches and 94 misses. GSD remains at 9,843/9,989 and 146 misses; all other case
outcomes are unchanged. Mean candidate counts become 6.017192 / 5.508960.

Across 3,496 tracked surfaces, 31 candidates are added on 18 surfaces, with no
removals or provenance changes. All thirty stress hashes and frozen corpus
baselines stay unchanged. Raw unknown nominal and nominalization hypotheses
remain visible and unjudged. In the novel, sixteen compound readings are added
across eight types, each alongside an existing split reading. These additions
represent alternative granularity and do not increase lexical coverage.

One source disposition brings the inventory to 223 scoped / 491 unreviewed /
one gap. The catalog has 333 canonical forms / 470 source IDs / 471 grammar
fixture entries. Noun POS does not establish time/place semantics: the viewer
can select 때's “dirt” hint (14423) ahead of “time” (74123), because both entries
remain role-compatible. This observed homonym-selection limit is recorded;
source-backed morphology is not a contextual sense selector.

The novel's compatible total is 119,950 analyses / 73,322 tokens with readings;
headword-only totals are 130,846 / 73,377, across 81,758 word tokens.
Three sequential local Nix release runs measured compatible median 1.230s versus
1.233s before, with peak RSS below 29 MiB. Timings include JSONL serialization
and are local observations, not throughput guarantees.

Rust/web-feature tests, Clippy, formatting, frozen corpus regression, frontend
build, browser/HTTP tests, inventory verification, x86_64-linux Nix flake checks
and the packaged web build pass. The first flake check terminated with signal 15;
after confirming it had stopped, a retry passed. The packaged full-dictionary
preview verifies all 34 judgments, CLI/API/export parity, four displayed words
with compound/split choices, source selection and desktop/mobile layout.
Independent Korean review and the remaining checklist families stay open.

## Conditional/concessive 라 and particle homonyms (COV-017aj/018r/020k)

The [source and candidate review](ra-condition-evaluation.json) adds copular
라도/라야/라야만 endings with distinct prefinal licenses. Nominal (이)라야 and
(이)라야만 particles preserve their separate roles; plain (이)라야 also accepts
source-supported adverbial attachment. Explicit particle + 만 decompositions
coexist with compounds. Factual 라 + 도 preserves the exact 교양 + 만 + 이 + 라
+ 도 corpus analysis without adding a particle license to command 으라.

There are 73 judgments across 72 cases (47 required / 26 forbidden), bringing
main validity totals to 2,245 required / 1,462 forbidden. Four complete unchanged
KAIST/GSD sentences preserve the source annotations. KAIST now matches
22,127/22,220 groups (93 misses); GSD matches 9,844/9,989 (145 misses). Mean
candidate counts are 6.028173 / 5.511763. Only 교양만이라도 and 자전거도로라도
change from misses to matches. GSD annotates the latter with a copula; preserving
that reading alongside the particle reading does not establish which is intended
in its sentence. These development cases are regression evidence, not held-out
precision evaluation.

Across 3,554 tracked surfaces, 605 candidates are added on 62 surfaces, with no
removals or provenance changes. All thirty stress hashes and frozen corpus
baselines stay unchanged. The novel gains 477 compatible-filtered readings
across 134 word tokens / 73 types. These include useful predicate paths and
unjudged nominal/copula alternatives such as 가 + 이다 + 더 + 라도 beside
가다 + 더 + 라도, plus particle-marked bases such as 마음 + 으로 + 이다 + 라도.
The report retains these alternatives without counting them all as precision gains.

Seven source dispositions bring the inventory to 230 scoped / 484 unreviewed /
one gap. The catalog has 340 canonical forms / 477 source IDs / 478 fixture
entries. The full-dictionary viewer initially glosses 먹다 as “be deaf” (15983)
ahead of “eat” (58272); both are verbs. This is a recorded contextual sense
selection limitation, separate from the verified ending and particle roles.

The novel's compatible-filtered total becomes 120,427 analyses / 73,327 tokens
with readings; headword-only totals become 131,372 / 73,382 across 81,758 word
tokens. Three sequential local release runs measured compatible median 1.236s
versus 1.250s before, with peak RSS below 29 MiB. Timings include startup and
JSONL serialization; local variation is not evidence of a speedup or a throughput
guarantee.

Rust/web-feature tests, Clippy, formatting, frozen corpus regression, frontend
build, browser/HTTP tests, inventory verification, x86_64-linux Nix flake checks
and the packaged web build pass. The packaged full-dictionary preview verifies
all 73 judgments, CLI/API/export parity, five displayed words with nine selections,
all seven grammar sources and desktop/mobile layout. Browser selection checks
both forms and grammatical roles because subject particle 이 and copula 이 can
print identically. Independent Korean review and the remaining checklist
families stay open.

## Nominal degree 깨나 (COV-018s)

The [source and candidate review](kkaena-evaluation.json) adds 깨나 after nominal
bases, including 땀깨나, 족보깨나 and 사람들깨나. Plural 들 stays separate;
깨 + 나, 깨다 + 나/으나, 깨나다 and 꽤 + 나 readings remain. Preceding case
peeling and bare predicate/adverbial attachment receive no new license.

The 27 new judgments contain 17 required and ten forbidden paths, bringing main
validity totals to 2,262 required / 1,472 forbidden. The source-attested
아씨들깨나 analysis remains available raw, but KRDict lacks 아씨. Both dictionary
filters remove that path, and the browser preserves the unmatched word in the
sentence and export. This dictionary coverage gap is tested explicitly.

Across 3,550 surfaces from both candidate ledgers, stress fixtures and additional
boundary probes, 31 candidates are added on 23 surfaces, with no removals or
provenance changes. All thirty stress hashes and frozen corpus baselines remain
unchanged. Unjudged additions include 따다/땋다 + 음 + 깨나 for 땀깨나 and
어 + 깨나 for 어깨나. Whole unknown nominal strings and inherited nominalization,
outer-particle and copula alternatives remain hypotheses, not precision gains.

The complete KAIST test sentence MH2_0110-s468 now recovers 족보 + 깨나. It was
inspected to develop this fix and is now an exposed regression case, not held-out
evidence. It is the only changed test-case outcome: matches become 24,382/24,490
from 24,381. Both development reports are unchanged: KAIST 22,127/22,220 and
GSD 9,844/9,989, with mean candidate counts 6.028173 / 5.511763.
The novel's compatible-filtered JSONL is byte-identical to the previous release:
120,427 analyses / 73,327 tokens with readings across 81,758 word tokens.

The inventory now has 231 scoped reviews / 483 unreviewed entries / one gap.
The catalog has 341 canonical forms / 478 source IDs / 479 fixture entries.
Rust/web-feature tests, Clippy, formatting, frozen corpus regression, frontend
build, browser/HTTP checks, inventory verification, x86_64-linux Nix checks and
the packaged web build pass. The packaged full-dictionary preview verifies all
27 judgments, both filters, the dictionary gap, CLI/API/export parity, three
selected breakdowns, source selection and desktop/mobile layout. Independent
Korean review, contextual meaning and the broader checklist remain open.

Three sequential local Nix release runs measured compatible median 1.200s versus
1.219s before, with peak RSS below 29 MiB. These include JSONL serialization;
variation is not evidence of a speedup or a throughput guarantee. The first
measurement process terminated with SIGTERM; after verifying it and its children
had stopped, the retry completed. Separate counts confirm unchanged output totals
for both dictionary filters; headword-only remains 131,372 analyses / 73,382 tokens
with readings.


## Core cases, internal emphasis and lexical uncertainty (COV-018t/019n/019o)

The [source and candidate review](core-case-evaluation.json) audits seventeen
core case/recipient entries and revisits auxiliary 하다. Bundled 게로/에게로/
한테로 coexist with split recipient + 로; 내/네/제 retain their written forms.
Finite emphatic adverb paths cover 도대체가, 맘껏을/매번을/매일을 and 빨리를/
곧이를. Full 를 after 어/게/지/고 and 가 after 지 compose with licensed auxiliaries,
including contracted ㄹ in 물얼봐야지 and 먹질않았다. 곧이 is absent from the
pinned dictionary, so its source-supported raw path disappears under both filters.

The main ledger gains 105 judgments (69 required / 36 forbidden), reaching
2,331 required / 1,508 forbidden. Six complete unchanged KAIST/GSD sentences are
exposed regressions. KAIST development matches remain 22,127/22,220. GSD moves
from 9,844 to 9,847/9,989: 속이지를 and 질리지가 recover their predicate groups,
but 강원체고를 is an incidental copula match in a school name, not a correctness
gain. 잘해서 gains only partial component recovery through an unjudged alternative;
its lexical 잘하다 path remains. Mean candidate counts are 6.064851 / 5.540294.
Frozen full-corpus baselines pass without modification.

Across 3,669 distinct ledger/stress/probe surfaces, 159 candidates are added on
81 surfaces, with no removals or provenance changes. One stress snapshot,
먹고싶은가를, gains the unknown predicate 먹고싶은가다 + 어 + 를. Its history
retains previous hashes; all previous candidates/provenance remain, and the full
dictionary removes that addition. The other 29 hashes and 64-ga probe are unchanged.

NIKL licenses some lexical verbs before 어 하다 (꺼려 하다 and 내키지 않아 하다),
so KRDict's adjective note alone cannot justify blanket verb pruning. Per-entry
assessment now marks this lexical verb attachment unknown, including through
class-preserving 지 negatives; other auxiliaries, copulas and suffixes reset the
dependency. Twenty-two additional policy cases bring that ledger to 222 cases
(143 required / 79 forbidden). These preserve uncertainty, not certify every path.
The browser now prefers a per-reading compatible homonym before broad POS evidence,
so 커한다 shows adjectival 크다 while its verbal entry remains inspectable.
Contextual senses remain unresolved: 내 can still show “creek” in 내게로 and 묻다
can show “bury” in 물얼봐야지 rather than the intended “ask”.

The compatible novel output adds 337 candidates across 290 tokens / 97 types,
with no removals or provenance changes. Including evidence-only changes, 698
records / 169 types differ. It contains 120,764 candidates over 73,356 tokens with
readings out of 81,758 word tokens. Headword-only output has 131,950 candidates
and 73,413 tokens with readings. These are coverage/ambiguity counts, not precision.
Three sequential local Nix release runs per mode measured compatible median
1.303s versus 1.309s before, and headword-only median 1.317s versus 1.305s.
Peak RSS remained below 29 MiB. Measurements include JSONL serialization; small
variation is not evidence of a speedup or a throughput guarantee.

The inventory has 246 scoped reviews / 468 unreviewed entries / one gap; the
catalog has 344 canonical forms / 481 source IDs / 483 grammar fixture entries.
Rust/web-feature tests, focused entry/unknown/class-reset regressions, Clippy,
formatting, frozen corpus checks, frontend build, full browser/HTTP suite,
inventory verification and x86_64-linux Nix checks pass. The packaged preview
checks all new morphology/policy judgments, both filters, eighteen selected
breakdowns and source links, compatible homonym hints, dictionary gaps, CLI/API/
export parity and desktop/mobile layout. Broader semantic/lexical restrictions,
independent Korean review, fresh-prose evaluation and the remaining checklist
items remain open.


## Source compounds and role/means audit (COV-018u)

The [source/candidate review](source-particle-evaluation.json) audits nine entries
and adds bundled 로부터/으로부터/에서부터/서부터 alongside their split case +
부터 alternatives. The compound's inner case boundary and outer source boundary
remain distinct, preserving existing inner 만/까지/에게 and outer topic/focus/
genitive/subject behavior. Existing (으)로서 and (으)로써 allomorphs, 음 nominalization
and locative 서 are covered without conflating their source senses.

The main ledger gains 99 judgments (73 required / 26 forbidden), reaching
2,404 required / 1,534 forbidden. An 868-surface equivalence check verifies both
split-to-bundled and bundled-to-split alternatives, including unknown-script
pronunciation assumptions, nominalizations and nested copulas. Five complete
unchanged KAIST/GSD development sentences preserve both annotation conventions;
they are exposed regressions, not held-out evidence. Every development-case outcome
is unchanged: KAIST 22,127/22,220 and GSD 9,847/9,989, with mean candidate counts
6.068632 / 5.541696. Frozen corpus baselines and all thirty stress snapshots pass
without modification; the 64-ga probe is also unchanged.

Across 3,747 distinct ledger/stress/probe surfaces, 112 candidates are added on
58 surfaces, with no removals or provenance changes. The compatible novel output
adds 27 candidates across 27 tokens / 18 types, also with no removals or provenance
changes. Every changed novel token now has a validated original UTF-8 byte span.
Individual observations retain nearby context for 와서부터/와서부터는/나서부터:
the nominal 와/나 + 서부터 alternatives do not establish the intended reading,
and the existing predicate ending + 부터 paths remain. Preexisting 학교+가+로써
and 선생님+이+로서 receive separate unjudged observation IDs. Broader inner-particle
acceptability, semantic selection and count-emphasis 서 remain open.

The novel has 120,791 compatible candidates over 73,356 tokens with readings out
of 81,758 word tokens; headword-only output has 131,978 candidates over 73,413
such tokens. Token coverage is unchanged. Three sequential local Nix release runs
per mode measured compatible median 1.320s versus 1.290s before, and headword-only
median 1.329s versus 1.312s. Peak RSS stayed below 29 MiB. These measurements include
JSONL serialization and are not a throughput guarantee or a precision estimate.

The inventory now has 255 scoped reviews / 459 unreviewed entries / one gap.
The catalog has 348 canonical forms / 485 source IDs / 487 grammar fixture entries.
Rust/web-feature tests, Clippy, formatting, full corpus regressions, frontend build,
full browser/HTTP checks, inventory verification and x86_64-linux Nix checks pass.
The packaged full-dictionary preview verifies all new judgments, both filters,
four bundled/split pairs plus six role/means/locative breakdowns, all nine source
links, CLI/API/export parity and desktop/mobile layout. Contextual precision,
independent Korean review and the wider completion checklist remain open.

## Concessive and designation particle audit (COV-018v)

The [source and candidate report](concessive-designation-evaluation.json) reviews
11 KRDict particle entries and NIKL's retained-이 and -질랑 guidance. The 98
individual judgments (68 required / 30 forbidden) bring the main ledger to
**2,472 required / 1,564 forbidden**. A further 149-surface equivalence check
preserves split and bundled 은 forms across nominal, ending, auxiliary and
copular paths. Dictionary-filtered CLI parity, NFD and ordered components are
checked. The dictionary-policy ledger is unchanged.

The 3,832-surface raw comparison finds 84 changed surfaces, 386 added candidates,
no removals and no provenance changes. All 30 stress snapshots remain unchanged.
Development gold recovery is unchanged: KAIST **22,127/22,220**, GSD
**9,847/9,989**. Mean candidates rise from **6.0686318632 to 6.0698019802** and
**5.5416958655 to 5.5430974071**, respectively. No target particle annotations
were found in the searched training/development data; no recall gain is claimed.
KAIST training MH2_0092-s333 instead exposes the still-missing predicate -ㄴ들.

On the pinned 무정 passage, compatible filtering adds 15 readings at 11 tokens
(10 types), removing none. Every changed token has a verified UTF-8 byte span,
nearby context and stable observation ID. 거기인들/눈물인들/한숨인들/지금인들/
일을랑/언제인들 fit concessive/designation uses in agent review; 악인들/만들
and the missing predicate 간들/한들 demonstrate contextual alternatives that a
headword or POS filter cannot resolve. All observations remain unjudged pending
independent review; these are not a precision estimate or new unseen prose.

The catalog now has **359 canonical forms / 496 source IDs / 498 grammar fixture
entries**. Inventory dispositions are **266 scoped / 448 unreviewed / one gap**.
Rust/web-feature tests, full corpus regressions, Clippy, formatting, frontend
build and browser checks passed. Browser coverage includes all 98 judgments,
17 selected decompositions, 11 grammar links, both filters, CLI/export parity
and mobile layout. Wider attachment, predicate -ㄴ들/-은들 and independent
Korean review remain open.

The final Nix flake check and web package build passed on x86_64-linux. The
packaged preview with the full dictionary passed the 98 distinct judgments and
all browser selection/source/export checks. Three sequential release runs over
81,758 novel word tokens gave median compatible-filter times **1.321 seconds
before / 1.321 after**; headword-only times were **1.342 / 1.343 seconds**.
Peak RSS was below **28 MiB**. These include JSONL serialization and dictionary
work; the separately counted outputs and every timing are retained in the report.
Other architectures and independent performance environments were not measured.

## Concessive predicate and counterfactual audit (COV-017ak)

The [source and candidate report](concessive-ending-evaluation.json) reviews
seven KRDict entries for -ㄴ들/-은들, -(으)ㄹ망정, -(으)ㄹ지언정 and -던들.
NIKL Q&A 330951 confirms 있은들/없은들 rather than -는들. The 130 distinct
judgments (106 required / 24 forbidden) bring the main ledger to **2,578 required
/ 1,588 forbidden**. They cover written allomorphs, irregular stems, finite
prefinal licenses, explicit copulas, 아니다, auxiliary grouping, 답다 derivatives
and polite 요. Particle 인들 remains separate from copula + 은들.

Six complete unchanged UD 2.15 training sentences expose six targeted misses:
KAIST grouped matches rise **59/65 → 64/65**, and GSD **13/14 → 14/14**. Every
target becomes an exact grouped match; one unrelated KAIST miss remains. These
are exposed regression fixtures, not unseen evaluation. Full development results
remain **22,127/22,220** for KAIST and **9,847/9,989** for GSD, with unchanged
per-case gold recovery. Mean candidates rise **6.0698019802 → 6.0703420342** and
**5.5430974071 → 5.5443988387**, respectively. Frozen corpus baselines and all
30 stress snapshots remain unchanged.

Across 3,960 raw probe surfaces, 150 change, with 700 added candidates and no
removals or provenance changes. Compatible filtering on the pinned 무정 passage
adds 28 readings at 24 tokens (23 types), removing none. Verified byte spans,
context and stable observation IDs preserve every change. The previously tracked
간들/한들 predicate misses now have 가다/하다 + 은들 readings. Counterfactual
그리하였던들/있었던들 and others gain past + 던들 paths. Contextual alternatives
remain: 악인들/어른들 are plurals in the passage, 만들 is an adnominal 만들다,
and 들어왔던들 retains multiple lexical/auxiliary hypotheses. 딸이었던들 also
exposes the inherited 따다 + 어 + 를 + 이다 path for further COV-020 review.
These observations remain unjudged pending independent review.

Rust/web-feature tests, the full pinned corpus gate, Clippy, formatting, frontend
build, browser/HTTP checks and Nix checks passed. Packaged full-dictionary checks
cover all 130 judgments under both filters, 10 selected decompositions, all seven
source links, CLI/API/export parity and desktop/mobile layout. The catalog has
**363 canonical forms / 503 source IDs / 505 grammar fixture entries**; inventory
reviews are **273 scoped / 441 unreviewed / one gap**. Broader 은들 prefinals,
omitted copulas, discourse conditions and independent Korean review remain open.

Three sequential local Nix release runs over 81,758 novel word tokens gave median
compatible-filter times **1.325 seconds before / 1.322 after**; headword-only times
were **1.340 / 1.341 seconds**. Peak RSS was below **29 MiB**. These include
startup, dictionary work and JSONL serialization. Separate count passes find
**120,806 → 120,834** compatible-filter analyses and **73,359 → 73,372** word
tokens with a reading. The report retains every sample and documents the
interrupted measurement harness and resumption. These local measurements do not
establish performance on other machines or architectures.

## Connective clauses before copulas (COV-020l)

The [source and candidate report](connective-copula-evaluation.json) adds direct
-아/어/여서 + 이다 composition, following NIKL OpenDict's temporal and causal
examples. The connective retains its Ending role and a distinct
`copula.connective_seo` explanation. Existing nominalization, auxiliary,
derivational and explicit/omitted-copula paths remain available.

The 53 judgments (46 required / 7 forbidden) bring the main ledger to **2,624
required / 1,595 forbidden**. Both dictionary filters, CLI parity, NFD, identity,
ordered nested components and provenance are tested. Six full unchanged training
sentences recover all six target misses: both KAIST and GSD fixture grouped
matches rise **30/33 → 33/33**. Full KAIST development recovery rises
**22,127/22,220 → 22,132/22,220**, while GSD remains **9,847/9,989**, without
lost recoveries. Mean candidates rise **6.0703420342 → 6.0716471647** and
**5.5443988387 → 5.5444989488**, respectively. These are exposed regression
results. The report also records incidental exposure to five test-partition rows;
those rows must not later be described as unseen.

Across 4,008 probe surfaces, 62 change, adding 175 candidates with no removals or
provenance changes. All 30 stress snapshots remain unchanged. On the pinned novel,
compatible filtering adds 53 candidates at 23 tokens (17 types). Every changed
token has a verified byte span and stable observation ID. The additions include
contextually unintended alternatives for lexical 나서다/들어서다/돌아서다
and connective-plus-particle constructions; they remain unjudged. No novel
precision gain is claimed. The original 딸이었던들 case-clause alternative
remains unresolved: the sources do not justify a blanket ban on non-noun copula
bases. Other connective, quoted and adverbial bases still require review.

Rust/web-feature tests, the full pinned corpus gate, Clippy and formatting pass.
Inventory dispositions and the grammar catalog are unchanged: this extends
composition of existing components, not a new grammar form.

The full browser/HTTP suite and packaged full-dictionary preview passed all 53
judgments, both filters, six selected breakdowns and CLI/API/export parity, with
desktop/mobile screenshots inspected. Nix flake checks and the web package build
passed on x86_64-linux. Frontend assets were unchanged; the cached asset check
passed. Other architectures were not exercised. The report records `제법이다`
as a remaining adverbial-base miss for the next copula audit.

Three sequential release runs on 81,758 word tokens gave median compatible-filter
times **1.334 seconds before / 1.326 after**; headword-only medians were
**1.355 / 1.351 seconds**. Peak RSS across these runs was **27.94 MiB**.
Separate count passes find **120,834 → 120,887** compatible-filter analyses and
**73,372 → 73,377** words with readings. Timings include startup, dictionary work
and JSONL serialization; every sample and count is retained in the report. These
local observations are not guarantees for other workloads or machines.

## Adverbial copula bases and 냐 questions (COV-020m)

The [source and candidate report](adverb-copula-evaluation.json) adds 13 attested
adverbial bases before 이다 while preserving nominal homonyms. 제법이다 now
survives compatible filtering. The same audit adds vowel-final 냐/냐고 omission
and rejects bare copula + 느냐, retaining the licensed 시/었/겠 forms.

The 72 judgments (61 required / 11 forbidden) bring the main ledger to **2,685
required / 1,606 forbidden**. Both filters, CLI parity, NFD, component order and
provenance are tested. Nine complete unchanged corpus sentences retain their
annotations. KAIST excerpt grouped matches rise **5/6 → 6/6** (왜냐고); GSD
remains **58/58**. A separate role audit finds **0 → 21** compatible
Adverbial + Copula matches among 26 observed training/development rows. Two 짱
POS mismatches, nonstandard 그닥/별루 and the erroneous 다이아 split remain
individually recorded. This role audit must not be conflated with lemma recall.

Full development grouped recovery remains **22,132/22,220** for KAIST and rises
**9,847/9,989 → 9,848/9,989** for GSD (뭐냐), without lost recoveries. Mean
candidates rise **6.0716471647 → 6.0720972097** and **5.5444989488 → 5.5452998298**.
Across 4,074 probes, 83 surfaces change, with 102 additions, six removals and no
provenance-only changes. All six removals are documented bare-copula 느냐
hypotheses. All 30 stress snapshots and frozen corpus baselines remain unchanged.

Compatible filtering on the pinned novel adds 37 readings at 36 tokens (20 types),
removing none. Verified byte spans, context and stable observation IDs retain
all changes. 그만 copulas and omitted questions gain relevant options; noun/adverb
homonyms, nominal suffix 이 alternatives, and new copular interpretations of
하냐/계시냐/오냐/왜요 remain contextual alternatives. The report keeps every
observation unjudged pending independent review and claims no precision estimate.

Rust/web-feature tests, Clippy, formatting, the full pinned corpus gate and the
full browser/HTTP suite pass. The catalog is unchanged; inventory reviews are
**274 scoped / 440 unreviewed / one gap**. The finite adverb inventory, broader
particle/copula attachment and independent Korean review remain open.

Nix flake checks and the web package build passed on x86_64-linux. Packaged
full-dictionary checks passed all 72 judgments under both filters, seven explicitly
selected adverbial readings, dictionary source access, and CLI/API/export parity.
Desktop/mobile screenshots were inspected. Tests distinguish adverbial and noun
roles even when their displayed component strings are identical. Frontend assets
were unchanged; no other architectures were measured.

Three sequential release runs on 81,758 word tokens gave median compatible-filter
times **1.343 seconds before / 1.341 after**; headword-only medians were
**1.371 / 1.354 seconds**. Peak RSS across these runs was **27.99 MiB**.
Separate count passes find **120,887 → 120,924** compatible-filter analyses and
**73,377 → 73,379** words with readings. Samples include startup, dictionary work
and JSONL serialization; all timings and counts are retained in the report. These
local measurements are not guarantees for other machines or workloads.

## Fixed complex-coda 하다 shortening (COV-021c)

The [source and candidate report](hada-complex-evaluation.json) extends the 22
existing shortening endings to eight fixed complex-coda classes: ㄳ/ㄺ/ㄿ/ㅄ
use deletion, and ㄵ/ㄻ/ㄽ/ㄾ use aspiration. This is an inference from the
published spelling and pronunciation rules. The dictionary supplies three actual
하다 heads (한몫하다, 값하다, 꼴값하다); structural tests for other classes
include hypothetical words without asserting dictionary membership.

Review also fixed a restored-predicate bug in -찮- expansion: inserted 하 cannot
become a noun before an invented copula. Fifty-four judgments (28 required /
26 forbidden) bring the main ledger to **2,713 required / 1,632 forbidden**.
The 22-entry lexical fixture preserves all senses and pronunciation forms.
One complete unchanged KAIST training sentence retains 값하고, with grouped
recovery unchanged at **9/9**. No shortened corpus attestation is claimed.

Across 4,223 raw probes, 70 surfaces change: **87 additions / six removals**,
with no provenance-only changes. All six removed copula paths are recorded
individually. Full development grouped recovery stays **22,132/22,220** (KAIST)
and **9,848/9,989** (GSD), without changed case-level recoveries. Mean candidate
counts move **6.0720972097 → 6.0756975698** and remain **5.5452998298**,
respectively. All 30 stress snapshots and frozen corpus baselines are unchanged.

On the pinned novel, compatible filtering removes exactly two readings and adds
none. 귀찮은 and 귀찮게 lose nominal 귀하 + 이다 + 지 + 않다 paths and keep
the intended adjective 귀찮다. Verified byte spans, context and individual ledger
cases track both removals. This is a source-backed agent review, not an independent
precision estimate. Other contextual alternatives and previous open observations
remain unresolved.

Rust/web-feature tests, dictionary filters and CLI parity, formatting, Clippy and
the full pinned corpus gate pass. Inventory dispositions and grammar-label counts
are unchanged. ㄼ exceptions, ㄶ/ㅀ before 하, further ending/particle families
and independent linguistic review remain open.

The full browser/HTTP suite and packaged full-dictionary preview pass all 54
judgments across 52 cases, both filters, six explicit breakdown selections,
dictionary source access and CLI/API/export parity. Desktop/mobile screenshots
were inspected. Nix flake checks and the web package build pass on x86_64-linux;
frontend assets are unchanged and other architectures were not exercised.

Three sequential local release runs on 81,758 word tokens gave median
compatible-filter times **1.293 seconds before / 1.320 after**; headword-only
medians were **1.312 / 1.307 seconds**. Peak RSS across runs was **28.09 MiB**.
Separate count passes record **120,924 → 120,922** compatible-filter analyses,
with **73,379** words retaining readings in both versions. All samples and counts
are recorded, including startup, dictionary work and serialization. These local
observations are not performance guarantees or a statistical speed comparison.

## Existing comparison particles (COV-018w)

The [source audit](comparison-particle-audit.json) checks all 24 distinct surfaces
from the five senses of KRDict 같이 (22776), 대로 (48410), and 처럼 (68275).
Nine direct predicate-ending attachments are forbidden by role-specific
judgments. The ledger now contains **2,737 required / 1,641 forbidden** judgments;
these are agent-authored source reviews, with independent Korean review pending.
The inventory now has **277 scoped / 437 unreviewed / one unresolved gap**.
There is no runtime rule or catalog change, and no corpus baseline was rewritten.

Both dictionary filters preserve the required paths and agree with the CLI.
The browser regressions cover the same cases plus ordered display, source links
and export parity. Contextual senses remain distinct from morphology: the
inspected 새처럼 default gloss uses the gap/space homonym of 새, although the
source sentence refers to a bird. That reader-facing limitation is recorded as
`comparison-particle-sae-gloss`; the dictionary still exposes the alternatives.

## Additive distribution (COV-018x)

The [review](additive-particle-evaluation.json) records 50 source-backed judgments
(42 required, eight forbidden), bringing the ledger to **2,779 required /
1,649 forbidden**. Ten complete KAIST training sentences preserve ten additive
targets, recovering four previously missing connective cases. The fixture's
unrelated 있을라치면 miss remains visible; these exposed examples are not an
unseen benchmark. All 66,570 frozen cases retain their matches and component
sets. A 4,306-surface comparison adds 68 analyses on 27 surfaces and removes
none. Those additions include unverified lexical hypotheses; the report does
not equate candidate growth with correctness. Compatible-filtered output for
the existing 무정 passage is byte-for-byte unchanged.

The inventory now has **279 scoped / 435 unreviewed / one unresolved gap**.
The source dictionary lacks proper name 승규, so both dictionary filters remove
that raw valid morphology path. The thesis's conflicting prose and ambiguous
밖에 segmentation are recorded explicitly. Further comparison-particle case
chains are tracked under COV-018y rather than being silently treated as covered.

## Case/comparison particle chains (COV-018y)

The [evaluation](comparison-case-evaluation.json) adds 18 required and four
forbidden judgments, bringing the ledger to **2,797 required / 1,653 forbidden**.
Six complete KAIST training sentences preserve five newly recovered targets and
a sixth with a surface/annotation spelling disagreement. An unrelated 원리을
row is also retained literally. These are exposed regression fixtures.

The four frozen partitions preserve all prior matches and component sets, and
gain two KAIST test matches (청에서처럼, 문명세계에서처럼). Across 4,326 raw
probe surfaces, 17 change with 33 additions and no removals. The whole 무정 novel
produces byte-identical compatible-filtered JSONL before and after. Hypothetical
nominal heads and the existing 읽하다 shortening remain unjudged, with the full
review queue retained. 모스크바 and 로스앤젤레스 are recovered raw but removed
by both dictionary filters because the pinned KRDict lacks those headwords.

The short 서 combination is marked as inference, rather than a primary-source
quotation. Independent linguistic review and further case/comparison pairs remain
open.

Rust/web tests, the full pinned corpus gate, all 30 stress snapshots, Clippy,
formatting, inventory checks, browser tests and Nix CLI/web builds pass on
x86_64 Linux. The packaged app also passes full-dictionary API/CLI/filter/export
checks and desktop/mobile inspection. Three interleaved release samples per
version/filter give after medians of 1.283 seconds (headword) and 1.268 seconds
(compatible), with peak RSS below 29 MiB. This is a bounded performance check,
not a claim of statistical speed equivalence.

## Recurring conditions (COV-017al)

The [evaluation](llachimyeon-evaluation.json) adds **29 required / 13 forbidden**
raw judgments, bringing the main ledger to **2,826 / 1,666**. Ten separate
dictionary-policy cases bring that ledger to **148 required / 84 forbidden**.
Raw and headword-only hypotheses remain; compatible filtering evaluates lexical
adjective entries separately, preserves existential 있다, distinguishes 늦다
homonyms and carries the requirement through 지-negatives. A different auxiliary
resets the class dependency.

Two complete KAIST training sentences recover 먹을라치면 and 있을라치면; all
37 converted rows now match. The latter closes the COV-018x observed miss. The
four frozen corpus partitions retain every prior match and recovered component
set. Across 4,376 raw probes, 48 surfaces gain 200 candidates with no removals.
Compatible-filtered 무정 output remains byte-identical across all 179,112 records.
The raw review queue remains explicitly unjudged; passing required cases does
not certify all added candidates.

Rust/web tests, all 30 stress snapshots, the pinned corpus gate, Clippy, formatting,
TypeScript/Vite, browser checks and Nix CLI/web builds pass on x86_64 Linux. The
packaged full-dictionary app passes all 52 new cases with both filters, source
selection and API/CLI/export parity. Desktop/mobile screenshots were inspected.
Three interleaved release samples per version/filter give after medians of
1.283 seconds (headword) and 1.314 seconds (compatible), below 29 MiB peak RSS.
The small sample does not establish statistical speed equivalence.

## Necessity ending (COV-017am)

The [review](necessity-ending-evaluation.json) adds **53 required / 13 forbidden**
judgments, bringing the main ledger to **2,879 / 1,679**. All pass. Both dictionary
filters and library/CLI parity pass for covered heads; the source-attested but
missing 되돌려받다 remains a raw candidate with unknown evidence and is removed
by either dictionary filter. No fabricated dictionary entry supplies it.

Across 4,438 raw probes, 54 surfaces gain 260 analyses with no removals or
provenance changes. All four frozen corpus partitions remain unchanged. The
training search found no annotated necessity-ending target; the separate
못하다고밖에 quoted-clause miss is tracked as COV-018z. In 무정, only one
of 179,112 records changes: 줄밖에 gains token-local 주다/줄다 ending
hypotheses. Its context supports dependent noun 줄 + particle 밖에. These
additions are ambiguity, not a claimed contextual accuracy improvement.

The 685 remaining unjudged candidates in this batch's raw review queue are
preserved. Independent Korean review and contextual interpretation remain open.
Full Rust/web tests, all 30 stress snapshots and the memory-limited case, the
pinned corpus gate, Clippy, formatting, TypeScript/Vite, browser checks and Nix
CLI/web builds pass on x86_64 Linux. The packaged full-dictionary app passes all
66 cases with both filters, source selection and API/CLI/export parity; four
desktop/mobile screenshots were inspected.

Three interleaved release runs per version/filter give after medians of
1.232 seconds (headword) and 1.236 seconds (compatible), with peak
RSS of 28.1 MiB. The small sample is a bounded performance
check, not evidence of statistical speed equivalence.
