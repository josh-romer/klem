# Grammar inventory triage (COV-013)

Measured 2026-09-26 against the local September 2026 KRDict snapshot and pinned
UD 2.15 **development** partitions. [The compact report](inventory-audit.json)
records input/source hashes, inventory counts, stable IDs for the 19 new matches,
and examples from the largest remaining annotation signatures. This is an
initial inventory pass, not completion of the linguistic audit.

## Persistent entry review queue

The [current queue](inventory-review-queue.json) contains all 715 source entries,
with separate IDs/POS for homonyms, every sense's definition and attachment
notes, patterns, and up to two source example groups per sense. The full source
example count is retained. Source text is from the National Institute of Korean
Language's Korean Basic Dictionary, September 2026 export, under
[CC BY-SA 2.0 KR](https://creativecommons.org/licenses/by-sa/2.0/kr/).
The generated queue is an attributed selection of that data under the same
license; the Python tooling retains the repository's code license.

The [manual ledger](inventory-reviews.json) currently contains **137 scoped
reviews**, with **578 entries unreviewed in this ledger**. This does not imply
that those entries are unimplemented. Each disposition records its supported
scope, remaining limits, checklist item, named Rust tests, evaluation evidence
and source-specific candidate judgments. Independent Korean-language review
remains pending. The sections below preserve the history of earlier batches.

The generated queue links source entries to the teaching catalog, source-citing
candidate judgments and the earlier 54-entry auxiliary inventory. These links
are evidence navigation aids, not coverage certifications. A source citation can
support one narrow forbidden path without establishing the rest of an entry's
attachment behavior. Current link counts are in the queue's summary.

```sh
python3 -m unittest discover -s tools -p 'test_review_inventory.py'
python3 tools/review_inventory.py --verify
python3 tools/review_inventory.py --dictionary data/dictionaries/krdict/krdict.db \
  > /tmp/klem-inventory-review-queue.json
diff -u docs/inventory-review-queue.json /tmp/klem-inventory-review-queue.json
```

The first two commands need no downloaded dictionary and also run in
`nix flake check`. Offline verification checks stored source hashes, current
evidence hashes and references, review status/counts, and every generated link.
The final two commands additionally reproduce the entire inventory from the
read-only local dictionary, checking its entry IDs/headwords/POS and retaining
its source manifest. Offline verification alone cannot establish that the
stored source selection matches the upstream dictionary.

To review another entry, inspect its source notes and existing paths, add tests
or fixes where needed, then add an explicit disposition to the manual ledger.
Use `scoped` for implemented behavior with linked judgments, `gap` for a reviewed
missing capability, or `deferred` with a reason in the scope/remaining fields.
Every disposition needs nonempty scope, limitations, checklist references and
evidence; none means complete coverage. Pin `source_sha256` to the queue row's
source hash after reviewing that text. Judgment references must cite that exact
dictionary ID; homonymous source entries cannot substitute for one another.
After reviewing changed sources or evidence, regenerate into a temporary file,
inspect the diff, and replace the queue. Do not regenerate just to silence an
unexpected source change. Named test references check existence; the relevant
test suite must still be run to establish passing behavior.

This queue is separate from the original `inventory-audit.json` and historical
corpus reports. Neither those reports nor the application runtime are changed
by generating it. Expressions and derivational sources outside the four audited
POS classes still need separate inventories; COV-013 remains open.

## Reproduce

From the repository root, with the dictionary and corpora already downloaded
(the Nix development shell supplies Python 3):

```sh
cargo build --locked --offline --example evaluate
./target/debug/examples/evaluate kaist data/corpora/kaist/ko_kaist-ud-dev.conllu \
  data/baselines/kaist-dev.jsonl > /tmp/klem-audit-kaist.jsonl
./target/debug/examples/evaluate gsd data/corpora/gsd/ko_gsd-ud-dev.conllu \
  data/baselines/gsd-dev.jsonl > /tmp/klem-audit-gsd.jsonl
python3 tools/audit-inventory.py --dictionary data/dictionaries/krdict/krdict.db \
  --report /tmp/klem-audit-kaist.jsonl --report /tmp/klem-audit-gsd.jsonl \
  > /tmp/klem-inventory.json
```

The tool uses Python's standard library and opens the database read-only. It
verifies each report's corpus hash, case population, IDs, and match count. Its
full output contains every inventoried entry and every remaining miss, rather
than only the examples retained in the compact report. No dataset is fetched,
no baseline is overwritten, and the runtime does not load this report.

## Dictionary versus source tables

| KRDict POS | Entries (homonyms separate) | Literal mentions in the relevant source section |
| --- | ---: | ---: |
| Ending (어미) | 504 | 142 |
| Particle (조사) | 157 | 53 |
| Auxiliary verb (보조 동사) | 40 | 16 |
| Auxiliary adjective (보조 형용사) | 14 | 5 |

The last column is a **triage hint**, not implemented coverage. The script
compares hyphen-trimmed headwords against string literals in `endings()` and
`particles()`, and auxiliary stems against `aux_allowed()`. For example, -ㄴ
is implemented through an attached-coda boundary despite having no literal ㄴ
table entry. Prefinals and contracted particles live elsewhere. Conversely,
the table mentions 만 but does not yet license the sentence-final 만 reading.
An auxiliary stem can occur in the table with only some connectors licensed.
Dictionary homonyms must be reviewed separately; spelling overlap proves
neither attachment support nor the correct sense.

The full inventory is a review queue. Prefix/suffix entries (505 in this
snapshot), dialectal forms, and multiword grammar expressions are outside this
first table comparison; derivational gaps remain COV-020/022. Headwords and
source IDs are from the National Institute of Korean Language's KRDict,
[CC BY-SA 2.0 KR](https://creativecommons.org/licenses/by-sa/2.0/kr/).

## Corpus triage and selected fixes

Before COV-016 there were 393 KAIST and 246 GSD development misses; afterward
there are **378 and 242**, respectively. These comparisons used fresh reports
from the COV-012 engine and then the COV-016 engine. All 19 gains are listed in
the compact report. Previously matched groups/component sets remain covered;
the four-partition check also passes all 66,570 frozen cases. Frozen baselines
and their older aggregate measurements are unchanged.

The script groups misses by the *annotated* trailing ending/particle sequence,
using OrigLemma when supplied, and marks auxiliary-tagged rows. It does not
infer a cause from the surface suffix. A signature can mix missing rules,
spelling/annotation issues, and lexical segmentation differences. Examples:

| Observation | Disposition |
| --- | --- |
| 보듯이, 나타나듯이, 했듯이 | Confirmed missing literal -듯/-듯이; COV-016 implemented. |
| 합니다만/있습니다만 style | Separate post-ending 만 from nominal restrictive 만; COV-018. KRDict [86555](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86555) documents the former. |
| 지+는, 지+도, 고+도, 면서+도 | Additional post-ending particle licenses; COV-018. Counts are token occurrences, not numbers of valid rules. |
| 한다면, 절약하려는, 배우자는 | Missing/review-needed ending families, not arbitrary suffix removal; COV-017. |
| 어디까지나 | Still misses 어디; until a chain rule is reviewed, retain its whole-word dictionary option; COV-018. |
| 번져나갔다, 늘어났다 | Review auxiliary 나가다/나다 and their connectors; COV-019. Do not split all compound verbs. |
| 사회주의라고 → 사회주의 | Annotation treats 라고 as a particle, while an existing copular alternative has an extra 이다 component. Representation/quotation-particle review, COV-018. |
| 부드러우면서도 → 부드러우다 | Includes a questionable lexical lemma as well as a particle gap. Do not require that lemma without review. |
| GSD 파워블로거 → 파워블 + 거, 지진희는 → 지진 + 희다 | Segmentation/annotation review; not automatically promoted to grammar requirements. |
| 神을, mile로, numeric/alphanumeric tokens | Tokenization/pronunciation/coverage boundaries under COV-014. |

Two complete KAIST development sentences now provide offline regression coverage
for both saved 보듯이 IDs. Tests separately assert exact morpheme kinds, order,
and forbidden boundary recoveries. The other new matches are recorded as gains,
not independent judgments of every candidate. The test partitions were used
only for regression comparison in this batch, not for selecting new rules.

## Remaining review

COV-017 through COV-022 split the former broad backlog into separately scoped
work. COV-013 stays partial until each dictionary entry and remaining corpus
family receives a reviewed disposition. Independent Korean-language review,
adjective/verb attachment distinctions, additional homonyms, and judgment of
unannotated alternatives remain open. Source-backed narrow rules should be
implemented with positive and negative paths; automatic inventory differences
must not become required linguistic judgments.

## Reviewed quotation representations (COV-018d/017j)

The [quoted-definition comparison](quoted-definition-evaluation.json) gives
stable-ID dispositions for eight remaining development cases ending in 라는.
KAIST 근대라는, 사회주의라는 and 민주주의라는 use noun + jcm annotations;
the engine already recovers noun + 이다 + 라는, consistent with the cited NIKL
and KRDict descriptions. These are representation differences, not evidence for
an otherwise unsourced standalone 라는 particle. They remain measured misses;
no adapter or baseline is changed to conceal the difference.

대안인가라는, 달아줘라는 and GSD 빨라진다라는 require further quotation and
attachment review under COV-018/020. COV-020b resolves the two standalone 라는
tokens with a conditional omitted-copula candidate and adds the explicit 이라는
Copula-role alternative. The [fragment comparison](copula-fragment-evaluation.json)
records both stable IDs and the unchanged corpus bytes. The quoted context is
neither inferred nor joined to the fragment. Other fragment forms, the full
715-entry inventory and remaining corpus families are still open.

## Necessity/intention representation (COV-017k)

The [obligation comparison](obligation-evaluation.json) records canonical 어야겠
as the KRDict-listed expression before a final ending. KAIST 말해야겠다 and
이야기해야겠다 and GSD 먹어야겠네요 now match. GSD dev-s361/10 와야겠다
and dev-s475/7 세척해야겠지요 include an implicit 하다 in their lemma groups;
their annotations and measured misses remain unchanged. The report includes
the actual bundled alternatives instead of treating the two cases as evidence
for a missing explicit auxiliary. General modal/ending and left-predicate
auxiliary constraints remain COV-017/019 work, including the other inherited
connectors after the new bundle.

COV-017l subsequently reviewed 해야겠더라 and 먹었더라, retaining the
retrospective reading while excluding incompatible command recoveries. See
[the prefinal-license comparison](prefinal-license-evaluation.json).
Broader modal-before-auxiliary combinations remain unjudged; only the new
고 있다/계시다 boundary was constrained in COV-017k.

## Polite reporting inventory review (COV-017m)

[The reporting comparison](reporting-evaluation.json) records attachment
dispositions for four entries from this ending inventory (81377, 81389, 81393,
76427), plus five related grammar-expression entries (86633, 86635, 86636,
86638, 81412). Present allomorphs, factual/copular and command senses are
represented without inserting implicit 하다. The source notes, ordered paths,
prefinal exclusions and dictionary links have regression coverage; unknown
lexical head classes and contextual senses remain unjudged.

Fresh development reports now have **145 KAIST and 169 GSD misses**. These
counts supersede the initial triage counts for current work; the original
inventory report and frozen corpus baselines stay unchanged. Every-entry
review of the 715-item inventory and remaining corpus families is still open.

## Enumerative copula inventory review (COV-020d)

[The connective -요 comparison](copula-yo-evaluation.json) reviews ending 86117
separately from polite particle 86116 and terminal -오. Five complete KAIST
sentences validate connective uses; two sentence-final gold-group matches are
explicitly incidental and do not validate a spelling substitution. The current
measured misses are **138 KAIST and 169 GSD**. Other inventory entries and
contextual sense judgments remain open.

## Causal ending inventory review (COV-017n)

[The causal comparison](causal-evaluation.json) records source-listed attachment
for -기에 (84811) and -길래 (73011), including prefinal differences and the
separate 기 + 에 nominalization analysis. Two complete GSD sentences recover
추천하길래 and 뽑길래. Current measured development misses are **138 KAIST and
167 GSD**, without lost gold groups or component recoveries. Nine entries now
have scoped dispositions in the persistent review ledger; the broader inventory,
omitted copulas, shortened 하다 forms and contextual judgments remain open.

## Expressive auxiliary 하다 review (COV-019d)

[The left-class comparison](auxiliary-left-hada-evaluation.json) records the
adjective selection of auxiliary 하다 sense 9, source 62888. Known auxiliary
verbs and represented copulas are excluded at 어 하다; inherited negative
classes and internal particles are checked. Other 하다 senses and unclassified
lexical heads remain. The nine-sense entry has a scoped disposition specifically
for this boundary, not certification of all its senses. This brings the review
ledger to ten scoped entries, with 705 still without a disposition. Corpus
recovery remains **138 KAIST / 167 GSD misses**; the 75 removed hypotheses in
32 audited surfaces are listed individually, with independent review pending.

## Quoted-alternative expressions (COV-017o)

[The expression comparison](quoted-alternatives-evaluation.json) records
individual source dispositions for ten 문법‧표현 / 품사 없음 entries. They cover
present, declarative, copular/factual, command and proposal alternatives through
eight canonical bundles. These sources are outside the four POS classes in the
715-entry queue, so that queue still has ten scoped reviews and 705 entries
without a disposition; expression reviews are not counted as ordinary endings.

Four newly recovered development groups leave **135 KAIST and 166 GSD misses**.
The 해방시키다 headword is absent from the pinned dictionary even though the
unfiltered rule recovers it. The connective-clause case 위해서라거나 remains
open under COV-020. The report preserves both distinctions, records all additions
across 74 audited surfaces, and leaves historical baselines unchanged.

## Enumerative particles and choice ending (COV-018e/017p)

[The comparison](enumerative-particle-evaluation.json) records six individual
source dispositions: particles 70330, 85861, 86046, 86518 and endings 82342/85037.
The existing present-ending entry receives a scoped review of known
adjective/copula class restrictions after honorific 시. Two
related particle spellings absent from the pinned dictionary use explicit source
mappings backed by NIKL's form tables. Full nominal particles, short
nominal/adverbial forms, final-ending + 든가 and literal -든가 remain distinct.
The review ledger now has sixteen scoped entries and 699 without a disposition;
these scoped reviews do not certify every possible attachment or contextual use.

Development misses remain **135 KAIST and 166 GSD** with no lost gold groups or
component recoveries. Three separately selected KAIST training tokens gain their
annotated groups: 것이라든가, 않든가 and 취미라든가. Complete byte-identical
sentences preserve those regressions; they are not a held-out score. All candidate
changes across 78 audited surfaces are retained in the report, with unjudged
lexical hypotheses and remaining particle/clause restrictions explicit.

The final comparison lists 500 added analyses and three removed known-class
violations individually. The latter are 학생이신다, 먹고싶으신다 and
학생다우신다; their composed 든가 paths are excluded too. Existing unclassified
lexical hypotheses remain, and broader present-ending restrictions need review.

## Destination and recipient particle review (COV-018f)

[The comparison](destination-particle-evaluation.json) records scoped attachment
reviews for twelve particles: 41693, 41695, 70037, 70051, 73013, 73014, 80293,
83879, 83880, 86550, 86573 and 86577. It retains every sense of those sources and
separately records the seven deictic location/direction entries used before
emphatic 다/다가. The inventory ledger now has **28 scoped reviews and 687
entries without a disposition**. Semantic recipient eligibility, contextual
senses, further adverbial bases and particle stacks remain open.

Two KAIST and one GSD development groups now recover: 강에다, 노동자보고 and
거기에다. Current development misses are **133 KAIST and 165 GSD**, without
lost gold groups or component recoveries. The report preserves all 121 added
analyses across 66 audited surfaces and removes none. All thirty stress
fingerprints remain unchanged. Bundled and component paths are alternatives;
matching corpus gold does not certify every candidate or resolve sense choice.


## Enumerative 다/이다 particle review (COV-018g)

[The comparison](enumerative-da-evaluation.json) records separate scoped reviews
of enumerative 다 (85738) and 이다 (86118). Vowel/consonant nominal attachment,
nominalizations, bounded suffixes and foreign pronunciation conditions are
implemented; no prior case phrase or predicate ending is stripped for this use.
Identical component paths can merge the enumerative and emphatic provenance;
labels retain both sources rather than claiming a contextual choice.

The ledger now has **30 scoped reviews and 685 entries without a disposition**.
Development misses remain **133 KAIST and 165 GSD**, with no lost groups or
component sets. Three changed stress snapshots gain reviewed nominal hypotheses;
all prior candidates and hashes remain. Independent Korean-language review,
lexical/sense suitability and further combinations remain open.


## Further omitted copulas and connective 은 (COV-020e/018h)

[The comparison](omitted-connective-evaluation.json) retains fourteen dictionary
source projections and NIKL omission guidance. Twelve POS-scoped entries receive
manual dispositions; the two grammar-expression entries remain outside the
715-entry POS queue. The inventory now has **42 scoped reviews and 673 entries
without a disposition**. Each disposition covers the implemented copula or
connective-particle attachment, not all senses or combinations.

Development misses are **127 KAIST and 162 GSD**. Nine grouped gains include an
incidental match to an apparent place-name annotation error; they do not imply
nine linguistically improved analyses. All corpus annotations remain unchanged.
Four stress snapshots gain explicitly unjudged nominal/copula hypotheses, with
prior candidates and hashes retained. Omitted honorific prefinals, auxiliary
left-class eligibility, internal 는 before 싶다, and broader copula bases remain
visible gaps. The absence of 엘리트주의 in the pinned dictionary is recorded
separately from successful raw morphology recovery.


## Honorific copula omission (COV-020f)

[The comparison](honorific-copula-evaluation.json) records NIKL's explicit
선수셨다 example and scoped reviews of 시/으시 (80330/80329) and 세요/으세요
(86558/86609). Restoration before honorific 시 preserves the existing tense stack
and known copula ending restrictions. The restored stem remains copula-only;
short 세요 stays bundled. The inventory now has **46 scoped reviews and 669
entries without a disposition**.

Development misses remain **127 KAIST and 162 GSD**, without lost gold groups or
component sets. Three selected corpus sentences preserve lexical verb readings;
none is relabeled as a copula. The report records 72 added analyses on 66 surfaces
and one changed stress fingerprint with prior candidates and hashes retained.
Unknown nominal hypotheses and contextual honorific suitability remain unjudged.
Other prefinal omissions and broader auxiliary restrictions remain open.


## Contrastive desire link review (COV-019e)

Three new scoped dispositions cover 싶다, 는 and contracted ㄴ at the
고 + 는 + 싶다 boundary. The persistent queue now contains **49 scoped
entries and 666 without a disposition**. The previously reviewed -고 source
retains its earlier scope; its auxiliary-connector sense is also preserved in
[the new comparison](desire-topic-evaluation.json). A direct spaced example
from 좀 is retained separately, outside the queue's grammar-POS scope.
These dispositions do not certify all senses, particle combinations or auxiliary
left classes. The new tests expose a further 어 있다 left-class question,
recorded explicitly in the report rather than asserted as a forbidden judgment.


## Continuative left-class review (COV-019f)

Two new scoped reviews cover auxiliary 있다 and 계시다 at their 어/고
boundaries. The queue has **51 scoped entries and 664 without a disposition**.
Six specific expression entries, outside the queue's grammar-POS scope, are
preserved in [the comparison](continuative-class-evaluation.json). Their explicit
verb-attachment notes supplement the broader 있다 note. This closes the known
adjective/copula issue from COV-019e/020e, while retaining unknown lexical heads
and known verb paths. Lexical-subset, transitivity and semantic conditions remain
unreviewed; these dispositions are not full-entry or contextual certification.


## Seo connective and particle review (COV-017q/018i)

Seven new scoped dispositions cover 고서, the three 어서야 allomorph sources,
emphatic 야, 부터 and 보다. The queue now has **58 scoped entries and 657
without a disposition**. The [comparison](seo-connective-evaluation.json) records
nine new KAIST development grouped matches, all previous gold/candidates retained,
and unchanged stress fingerprints. Broader particle attachments, 어서야
prefinal licenses and contextual class/sense decisions remain open.


## Modal/retrospective copula omission (COV-020g)

Eight grammar entries now have scoped dispositions for omitted copula attachment,
with three additional expression sources attributed separately. The queue now
contains **66 scoped entries and 649 without a disposition**. The source catalog
is unchanged. [The comparison](prefinal-copula-evaluation.json) records three
new development matches, all thirty unchanged stress fingerprints, and explicit
remaining attachment gaps. This is not full-entry linguistic certification.


## Retrospective following-ending licenses (COV-017r)

[The review](retrospective-license-evaluation.json) covers 46 source entries.
Twenty grammar entries gain scoped dispositions and twelve existing dispositions
retain their previous evidence while adding this attachment audit. Fourteen
expression entries remain separately attributed outside the grammar-POS queue.
The queue now contains **86 scoped entries and 629 without a disposition**.
The exact-path regressions distinguish rejected bundles from unreviewed
alternatives, including 더 + 나 + 요. Broader following-ending and lexical/sense
licenses, independent Korean review and fresh passages remain open.


## Retrospective nominalization and connectives (COV-017s)

[The review](retrospective-connective-evaluation.json) records 37 grammar and
expression sources. 29 entries gain scoped dispositions and 6 existing
entries retain their previous scope and evidence while adding this boundary
review. The queue now has **115 scoped entries and 600 without a disposition**.
Short 며/면서/므로 receive explicit source links in their existing canonical
labels. The earlier unjudged 더 + 나 + 요 and nominalizing 기 paths are now
rejected with separate exact-path judgments. Other followers and lexical/sense
constraints remain open; this does not certify full coverage of any entry.


## Retrospective adnominal and question alternatives (COV-017t)

[The review](retrospective-adnominal-evaluation.json) records 32 KRDict entries
and five NIKL references about segmentation. 22 grammar entries gain scoped
dispositions and 4 existing entries add evidence without discarding their
previous scope. The queue now contains **137 scoped entries and 578 without a disposition**.
The review distinguishes the present/prospective exclusions from retained
retrospective adnominal components, and adds the dictionary bundles 던가/던지.
Nine short-allomorph sources and two bundle sources receive catalog links.
Independent Korean review and other attachment/class conditions remain open.


## Omitted-copula question forms (COV-020h)

[The source review](question-copula-evaluation.json) covers seven dictionary
entries plus NIKL's copula-omission explanation. Six existing grammar dispositions
add the question-boundary evidence while retaining their earlier reviews; the
short ㄹ까요 expression is attributed outside the grammar-POS queue. The queue
remains at **137 scoped entries and 578 without a disposition**. This batch
recovers the GSD 뭔지/뭔가 gold groups and adds a dictionary check for the single
new unverified nominal stress hypothesis. Broader pronoun normalization and
particle-marked copula bases still need review.
