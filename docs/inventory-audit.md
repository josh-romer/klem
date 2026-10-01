# Grammar inventory triage (COV-013)

Measured 2026-09-26 against the local September 2026 KRDict snapshot and pinned
UD 2.15 **development** partitions. [The compact report](inventory-audit.json)
records input/source hashes, inventory counts, stable IDs for the 19 new matches,
and examples from the largest remaining annotation signatures. This is an
initial inventory pass, not completion of the linguistic audit.

## Persistent entry review queue

This queue covers entries tagged 어미, 조사, 보조 동사 or 보조 형용사.
Grammar expressions tagged 품사 없음 are reviewed in the ending-family
checklist and their source reports, without inflating these 715-entry counts.
For example, [COV-017aq](dajiman-evaluation.json) covers ten such entries.

The [current queue](inventory-review-queue.json) contains all 715 source entries,
with separate IDs/POS for homonyms, every sense's definition and attachment
notes, patterns, and up to two source example groups per sense. The full source
example count is retained. Source text is from the National Institute of Korean
Language's Korean Basic Dictionary, September 2026 export, under
[CC BY-SA 2.0 KR](https://creativecommons.org/licenses/by-sa/2.0/kr/).
The generated queue is an attributed selection of that data under the same
license; the Python tooling retains the repository's code license.

The [manual ledger](inventory-reviews.json) currently contains **386 scoped
reviews**, **one observed gap with unresolved acceptability** (마다), and
**328 entries
unreviewed in this ledger**. This does not imply
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


COV-017u adds a scoped review of auxiliary 놓다 (72578): the Article 35
놓아 → 놔 spelling preserves its verb, adjective and copular left contexts.
The [comparison](noh-contraction-evaluation.json) and three explicit role
judgments support this disposition; other contextual/lexical restrictions are
still open. The queue now contains **138 scoped entries and 577 without a disposition**.
Lexical 놓다, compound verbs and 놔두다/놓아두다 are attributed separately
outside the grammar-POS queue. No new canonical grammar label is needed.


COV-017v adds four scoped grammar-POS dispositions (75148, 75175, 75191, 75476)
for the informative 다네 family, preserving reported-expression homonyms,
prefinal/allomorph constraints, auxiliary roles and reviewed 요/도 composition.
The related 다는데 and retrospective expressions are attributed separately;
expression POS is outside this 715-entry queue. The [review](report-ne-evaluation.json)
accounts for 954 added candidates on 186 surfaces and five recovered development
groups, with no lost candidates or changed previous provenance. The inventory
now contains **142 scoped entries and 573 without a disposition**. Unknown
lexical classes, broader honorific judgments and contextual senses remain open.


COV-017w adds scoped dispositions for 되/으되 (80289, 80291), separating literal
stem attachment from existential/past/modal full-form selection. The queue now
contains **144 scoped entries and 571 without a disposition**. The
[review](doe-evaluation.json) records 132 candidate additions on 67 surfaces,
two development gains and unchanged historical stress fingerprints. Short
existential spellings remain explicitly unjudged under a named followup;
scoped disposition is not full-entry certification.


COV-018j adds scoped dispositions for 치고, 치고는 and 치고서
(73015/83882/73016). The queue now contains **147 scoped entries and 568
without a disposition**. Noun/plural attachment, bundled/component alternatives,
reviewed topic/polite composition and exact forbidden boundary paths have
source-linked judgments. [The comparison](chigo-evaluation.json) records 113
added candidates on 70 surfaces, one GSD development gain and thirty unchanged
stress fingerprints. Other outer particles and nominalization semantics remain
unjudged; 교수님 has a separately tracked dictionary gap.


COV-018k adds five scoped dispositions for 까지, 가, 를, 에 and 로 and
extends the earlier 부터 review without removing its connector evidence.
Direct dictionary examples support five range/case pairs. COV-018l separately
records 마다 as an observed implementation gap with unresolved linguistic
acceptability; its complete corpus sentence is evidence rather than a required
or forbidden judgment. The queue now contains **152 scoped entries, one gap
and 562 unreviewed**. [The comparison](range-case-evaluation.json) records 84
candidate additions on 65 surfaces and two provenance-only changes, with
one KAIST gain and unchanged stress fingerprints. Other case combinations,
contextual restrictions and independent review remain open.


COV-018m adds scoped dispositions for 토록, 마냥, 만치 and 만큼
(86121/80341/80343/80342). Their noun/particle/어서 licenses remain separate
from the bound-noun and adverb homonyms; lexical alternatives and shortened
하다 predicate paths are retained. [The comparison](extent-evaluation.json)
records 123 additions on 81 surfaces, no removals/provenance changes, one KAIST
gain and thirty unchanged stress fingerprints. The inventory now has **156
scoped entries, one observed gap and 558 unreviewed**. Semantic subclasses,
other connectors and further particle combinations remain open.


## Approximation suffix scope (COV-020i)

The [source/candidate review](approximation-evaluation.json) adds noun-attached
-쯤 and its reviewed nominal composition. The grammar catalog has 278 forms,
350 source IDs and 351 fixture entries. Suffix POS is outside this queue's
four grammar POS categories; its 715 entries remain **156 scoped, one observed
gap and 558 unreviewed**. Do not count the new suffix label as an additional
review of those entries. Remaining suffix order, nominalized/particle bases,
semantic classes and independent Korean review are explicit followups.


## Quoted/confirmatory myeo family review (COV-017x)

The [review](report-myeo-evaluation.json) retains all 34 source entries behind
18 new canonical labels, distinguishing ending and expression homonyms. Fourteen
ending entries receive scoped dispositions with same-source ledger citations.
The 715-entry queue is now **170 scoped, one observed gap and 544 unreviewed**;
the expression POS entries do not inflate that queue's reviewed count.

The review preserves source-attested auxiliary stative plain-다 forms and
separates present, factual/copular, command, proposal and question licenses.
Generic retrospective question compounds remain unjudged. Source examples also
expose older auxiliary report restrictions in COV-019g. Other quoted endings,
lexical/existential classes, further particles and independent Korean review
remain open. Labels, source matches and passing tests are not full-entry
linguistic certification.


## Stative auxiliary reports (COV-019g)

[The review](stative-report-evaluation.json) distinguishes source-attested
plain-다 reports from the auxiliary's verbal POS and reviews the direct bare
있다 declarative paradigm. It preserves 계신다 and inherited negative readings,
checks resets through later dynamic auxiliaries, and removes only the reviewed
bare auxiliary 있는다 paths. The 178-surface comparison records 96 additions and
50 removals with unchanged development recall and all thirty stress fingerprints.
COV-019h retains prefinal/existential question/adnominal work; the full
먹고는있다네 internal-particle path remains an unjudged missing observation.

The existing 62595 and 61346 scoped dispositions gain this evidence without
replacing their earlier left-class judgments. Counts remain 170 scoped, one
observed gap and 544 unreviewed across the 715-entry queue. All 166 new cases
have stable exact-role judgments: 108 required and 58 forbidden. This is a
reviewed inflection scope, not contextual sense selection or a precision estimate.


## Shared present declaratives (COV-017y / partial COV-019h)

[The review](present-license-evaluation.json) unifies prefinal and known-class
licenses for eleven canonical families. It closes older 는다/는다고/는다는
past/modal/retrospective gaps, including auxiliary chains, and known
adjective/copula honorific loopholes. Unknown lexical hypotheses remain separate.
The 343-surface comparison accounts for 306 removals and no additions or changed
provenance. Existing corpus gold and all thirty stress fingerprints remain.

Nine missing source homonyms are now linked; the catalog has 296 forms, 393
source IDs and 394 grammar fixture entries. The persistent grammar-POS queue gains
nine scoped reviews and updates nine prior dispositions, preserving their older
evidence. Counts are now 179 scoped, one observed gap and 535 unreviewed across
715 entries. There are 338 new cases (169 required and 171 forbidden). The broader
existential honorific, adnominal and question review remains open: a naturalness
preference or contextual temporal correction is insufficient for a blanket ban.


### Surprise and quoted -니 families (COV-017z)

Nine canonical families now distinguish surprise/statement, factual/copular,
command, proposal, retrospective and question readings. Eight components and
24 source IDs are new; existing 다니 retains its bare-verbal surprise readings.
Full/short forms and expression homonyms are mapped explicitly. Seven new scoped
dispositions and two updates leave **186 scoped, one observed gap and 528
unreviewed** in the 715-entry queue. The expression entries remain attributed
outside the grammar-POS queue; neither a catalog link nor a matching dictionary
headword certifies an ending's lexical sense/class.

The [review](report-ni-evaluation.json) retains 163 probe surfaces with 727 added
candidates, no removals and 106 provenance-only changes to existing 다니 paths.
Three development gold groups are newly recovered, with no lost groups or
component sets; misses are 104 KAIST and 150 GSD. All 30 stress fingerprints are
unchanged. Exact role judgments cover 109 required and 54 forbidden paths.
The new COV-017aa item tracks lexical-class hypotheses that survive headword
filtering. Generic retrospective questions, existential paradigms and
particle-marked copula bases remain explicitly unjudged followups, not passed
coverage claims. Independent Korean-language review is still pending.


### Short quoted modifiers and change/conditionals (COV-017ab)

Eight new components distinguish quoted 단/는단/잔/냔/느냔/으냔 and the
change/conditional 단/다간/다가는 homonyms. Ten explicit source IDs preserve
full/attached and expression readings, while excluding noun suffix -단 (73350).
The generic question source explicitly supports 누구냔 with omitted 이다.
Three new scoped ending reviews leave **189 scoped, one observed gap and 525
unreviewed** among the 715 grammar-POS entries. Seven expression entries remain
separately attributed outside that POS queue.

The [review](short-clause-evaluation.json) records 151 surfaces and 599 added
candidates, with no removed candidates or changed existing provenance. Two
KAIST gold groups newly match; misses are 102 KAIST / 150 GSD, with no losses.
All 30 stress fingerprints are unchanged. Exact role judgments cover 92 required
and 50 forbidden paths. A separate probe records all 17 converted development
surfaces ending in the new spellings: 16 gain hypotheses while retaining their
original readings, including noun-context 세단 and 판단. This does not certify
contextual correctness. Further particles, omitted copulas, shortening,
existential questions and lexical classes remain explicit followups; independent
Korean-language review is still pending.

### Prayer final-ending dispositions (COV-017ay)

Four new scoped dispositions cover KRDict 78535/80927 소서/으소서 and
86109/86110 only as evidence for the modern 옵소서/으옵소서 final bundle.
Complete native senses, notes and examples are retained. General polite
prefinals, including source example 읽으옵고, remain COV-017az. The
[candidate evaluation](soseo-evaluation.json) and
[draft corrections](soseo-draft-corrections.json) distinguish source tokens,
structural inference and unjudged outputs. The queue now contains 330 scoped,
384 unreviewed and one observed gap across 715 entries, with 382 catalog-linked
and 370 cited entries. Scoped dispositions are not whole-entry coverage or
independent linguistic certification.

### Basic polite-prefinal dispositions (COV-017az, in progress)

Two new scoped dispositions cover KRDict 86107/86108, while 86109/86110's
existing final-bundle dispositions now also record the basic polite paradigm.
Both boundaries select (으)오/(으)옵; tense/modal order, spelling ownership and
auxiliary/답다 composition remain explicit. The ten native tokens include
읽으옵고 and all three 오리다 examples, with a separately represented final
리다 bundle. Missing primary KRDict grammar entries can have primary-reference
teaching labels without fabricated dictionary matches.

The [evaluation](polite-evaluation.json) records 133 judgments (93 required,
40 forbidden), 48 complete native entries, 808 additions and no removals across
8,990 probes. Of those additions, 716 remain unjudged. One frozen corpus partial
gain in a proper-name context is preserved as an annotation disagreement, not
a correctness claim. The compatible-filter novel gains 336 hypotheses across
204 records with no removals; these passage additions remain unjudged. The
current queue has **332 scoped, 382 unreviewed and one observed gap**, with
384 catalog-linked and 372 cited entries. The distinct 사오/사옵 and 삽 paradigms
now have 130 further structural judgments and five primary examples; their
source links are external references because the primary entries are absent
from the pinned KRDict. See [humble evaluation](humble-evaluation.json).
Across 9,115 probes, this batch adds 231 candidates and removes none; 139
additions remain unjudged. Four frozen corpus partitions retain identical gold
recovery and case reports, with seven added, unjudged hypotheses individually
recorded. The 179,112-record novel adds four hypotheses at one token under each
dictionary filter, with no removals. Release medians are approximately 1.6 seconds
and peak memory stays below 30 MiB in the recorded samples. Rust, browser/native
dictionary and x86_64-linux Nix checks pass; these checks do not establish
contextual precision or completion of the broader row.
General 옵시/으옵시/사옵시, modern 자옵 lexical restrictions, broader ending licenses and
independent Korean-language review remain open under the original COV-017az
scope. See the [primary-source audit](polite-source-audit.json).

The COV-017ba bare-promise audit reviews KRDict 78483/78496 against every
native example group, exact boundary/owner regressions, a preserved KAIST
annotation and the novel occurrence 맡음세. The queue now has 336 scoped,
378 unreviewed and one observed gap across 715 entries, with 386 catalog-linked
and 375 judgment-cited entries. These counts describe dispositions and links,
not a precision estimate. Prefinal combinations remain explicitly unknown;
see [the individual review](eumse-evaluation.json). COV-018l's public-source
retrieval recheck still leaves 마다 + 에 unresolved.

The COV-017bb background-connective audit reviews KRDict 87110–87113 against
all senses and 24 complete native example groups, plus exact boundary/prefinal/
owner regressions and optional per-entry class filtering. All six pinned corpus
files contain only lexical 이른바 among ending-shaped hits; no annotated ending
target is claimed. The queue now has 340 scoped, 374 unreviewed and one gap
across 715 entries, with 390 catalog-linked and 379 judgment-cited entries.
Bound noun composition, wider paradigms, negative inheritance and independent
Korean/contextual review remain unresolved. See [individual evidence](background-ba-evaluation.json).

The COV-017bc comparison/reason audit reviews seven native ending entries
80839/85722/85723/85725/85726/85727/85728 and separately preserves the exact
85824 expression (품사 없음) outside the queue. All eight entries' senses and
34 complete example groups remain intact; optional per-entry policy preserves
unknown source-disagreement, prefinal and auxiliary-role readings. Five selected
annotated tokens become grouped matches, while four quoted listing observations
remain distinct open COV-017bd work. The queue now has 347 scoped, 367 unreviewed
and one gap across 715 entries, with 397 catalog-linked and 386 judgment-cited
entries. Contextual correctness and independent Korean-language review remain
open. See [individual evidence](neuni-evaluation.json).

The COV-017bd quoted-listing audit reviews eight native ending entries
86068/86069/86911/86079/86080/86070/88983/88987 and separately preserves exact
expressions 88986/86074 (품사 없음) outside the queue. All ten entries' 11 senses
and 49 complete example groups remain intact; per-entry class policy keeps
homonyms, unknown auxiliary roles and unlisted polite markers independent. Four
training groups become matches; all four frozen dev/test reports remain identical.
The original missing-space input remains explicit COV-020p work. The queue now
has 355 scoped, 359 unreviewed and one gap across 715 entries, with 405 catalog-
linked and 393 judgment-cited entries. See [individual evidence](quoted-neuni-evaluation.json).

COV-017be adds two exact comparative expressions, KRDict 85729/85731. Their
complete native entries, two senses and all eight example groups are reviewed
outside the 715-entry queue because their POS is 품사 없음 and lexical unit
문법‧표현. The queue remains 355 scoped / 359 unreviewed / one gap, with
405 linked and 393 judgment-cited entries. The catalog now has 455 canonical
forms and 636 unique source identities; the native label fixture has 682 entries.
The [manifest](../tests/fixtures/neuni-comparison-sources.json) preserves 43
complete native entries and source hashes, while the [evaluation](neuni-comparison-evaluation.json)
tracks 48 required / ten forbidden raw and eight retained / four excluded policy
paths. No broad expression fallback or general 보다 follower license is added.

The COV-017be complete comparison retains 148 added hypotheses at 55 of 10,479
surfaces without removals: 45 required, four dictionary conflicts and 99 unjudged.
Both full novel filters preserve all 179,112 records byte for byte, as do all four
frozen corpus reports; neither dataset has an exact target occurrence. Full
Rust/stress, pinned corpus, lint/format, browser/frontend and x86_64 Linux Nix
checks pass. The packaged preview has complete-dictionary CLI/HTTP/asset parity.

COV-020p implements separate opt-in spacing hypotheses for the original native
86079 example 결혼을하라느니. This representation reuses reviewed word endings/
particles and does not add grammar source IDs or inventory dispositions. The
715-entry queue remains 355 scoped / 359 unreviewed / one gap, with 405 catalog-
linked and 393 judgment-cited entries; the catalog remains 455 canonical forms.
Twenty stable component/segmentation judgments are tracked separately because
independent words must not become a single lemma/auxiliary analysis. Source
identity, native hashes and scope are retained in [the manifest](../tests/fixtures/spacing-sources.json)
and [audit](spacing-source-audit.json); additional output partitions remain unjudged.

COV-020p now has six focused spacing/source/Unicode/limit/search-stress tests,
full Rust/stress and pinned corpus gates, lint/format, frontend/browser, final
x86_64 Linux Nix checks and a refreshed complete-dictionary packaged preview.
No morphology/catalog review totals changed. All 10,514 raw comparisons, four
frozen reports and both default novel streams remain unchanged. Every opt-in
novel hypothesis is retained with an unjudged status and reconstructable original
span/context in [the individual observation record](spacing-novel-observations.json).

COV-017bf reviews six native ending entries (81040/81045/81050/81056/76460/76475)
and six polite expressions with separate canonical 요 composition. Full native
entries preserve all 106 original groups and 105 direct token targets; the
remaining malformed 끝난던걸요 group is an explicit unjudged observation.
The catalog has 459 canonical forms / 642 source identities and the native
label fixture has 688 entries. The [source audit](geol-source-audit.json) and
[evaluation](geol-evaluation.json) preserve all new raw paths, four exact
annotated training tokens and eight changed novel occurrences per filter.
Independent Korean review and full contextual/sense coverage remain pending.

Six scoped COV-017bf ending dispositions bring the queue to 361 scoped / 353
unreviewed / one gap across 715 entries, with 411 catalog-linked and 399
judgment-cited entries. Polite expressions retain their native 품사 없음
identities outside this queue. This is scoped evidence, not full-entry or
independent linguistic certification.

The completed COV-017bf batch preserves every prior raw candidate, all four
frozen reports and all optional novel spacing hypotheses. Source-spelling
uncertainty is retained explicitly, and all ten new novel paths at eight
occurrences per filter remain unjudged. Full runtime/build checks and the
refreshed Nix preview pass; broader parent checklist items remain open.

COV-017bg audits twenty native ending entries (including four zero-example
arrow redirects) and eight polite expressions. The full fixture contains
175 entries and preserves all 127 original groups/direct token targets.
Native 92511 retains exact headword 로구만; canonical 구먼 normalization is
tolerant rather than normative. The 더구나 note/example contradiction and
lexical-versus-auxiliary 있다 distinctions are recorded in the
[source audit](exclamation-source-audit.json). Six original training tokens
gain lemma recovery, while full dev/test case rows and recall are unchanged.
Broader polite, quoted-contraction and contextual-sense work remains open.

Nineteen new scoped COV-017bg dispositions and the extended 81572 review bring
the queue to 380 scoped / 334 unreviewed / one gap across 715 entries, with
428 catalog-linked and 418 judgment-cited identities. The catalog has
473 canonical forms / 660 source IDs and the native label fixture has 706
entries. Optional novel spacing alternatives change at three occurrences
(5,555 to 5,556 total); their contexts and unjudged readings remain visible.

The COV-017bg runtime/build gates and refreshed packaged preview pass. The
next explicit gap is quoted declarative exclamation contractions (COV-017bh);
base ending coverage does not imply that their quoted bundles are generated.
The full inventory audit and independent Korean-language review remain open.

## Full literal -다가 source regressions (2026-10-01)

The [native source audit](daga-native-source-audit.json) reviews all four senses
and 15 original example groups of entry 85740. Nineteen stable target-occurrence
judgments preserve literal -다가 paths, including alternating constructions,
past predicates, and bare adjectives. Lexical/transfer and 들다/듣다 alternatives
remain available; these cases do not select an intended contextual sense.
The [evaluation](daga-native-evaluation.json) records source integrity, both
dictionary filters, CLI/library word/text parity, ordered components, preview
and packaged API checks, 620 Rust tests, full pinned corpus checks, and Nix
CLI/web verification. Application binaries and production frontend bytes are
unchanged. The queue now has 383 scoped dispositions, 331 unreviewed entries
and one unresolved gap. Broader attachments and independent Korean review
remain open.

## Native intention/concession source regressions (2026-10-01)

All original groups of -자면 (80338) and -나마/-으나마 (80167/80164) now
have stable target cases, attributed full native fixtures, and scoped inventory
dispositions. The [source audit](native-conditionals-source-audit.json) retains
14 groups and 14 target occurrences; [three tests](../tests/native_conditionals.rs)
protect source turns, roles, normalization, lexical homonyms, both dictionary
filters and ordered CLI word/text exports. 조금이나마 preserves copular ending
and nominal/adverbial particle alternatives without choosing the intended sense.
The [evaluation](native-conditionals-evaluation.json) records the unchanged
application binary, 623 Rust tests, full pinned corpus checks and preview API
parity, Nix CLI/web builds and packaged API/asset checks. The refreshed preview
uses the verified package. The queue has 386 scoped dispositions, 328 unreviewed entries and one
unresolved gap. Contextual senses, wider attachments and independent Korean
review remain open.

## Finite opaque adverb roots (2026-10-01)

COV-022c adds 천천/분연 + 히 with the explicit `Root` role, plus a separately
inferred 천천하다 lookup alternative. Four full native entries retain five
senses and 84 original groups; 40 target occurrences and two complete training
sentences preserve source spelling and whole lexical adverbs. Both 분연히
homonyms remain. Missing dictionary heads remain unknown.

The [source audit](opaque-adverb-source-audit.json) and
[evaluation](opaque-adverb-evaluation.json) record 61 new required judgments,
two forbidden modern-spelling paths, no removed candidates across 12,060
probes, and 114 unjudged additions. All frozen corpus outcomes and filtered
novel output (with and without spacing suggestions) remain unchanged. Two
raw novel occurrences gain four unmatched derivational alternatives, whose
contextual senses remain unjudged.

These adverb and suffix entries lie outside the 715-entry ending, particle and
auxiliary queue. Its dispositions remain 386 scoped / 328 unreviewed / one
gap, with 429 catalog-linked and 418 judgment-cited entries. Wider COV-022
classes and independent Korean-language review remain open. Nix CLI/web
builds, flake checks and the refreshed packaged preview pass; both filters and
all three browser export modes match the CLI. The release novel check retains
179,112 records, with approximately 1.6-second median runs per filter on this
host. These observations do not certify every generated analysis.

## Native noun-forming -이 (2026-10-01)

COV-022d separates all eight native sense-1 predicate-base noun formations
from adverbial -이, retaining whole lexical nouns, causative predicates and
homonyms. The full fixture preserves 33 source entries and all three noun
suffix senses/44 original groups; four lexical gold targets remain unchanged
in three complete training sentences. Five tests track source identity, rule
constraints, exact dictionary/CLI exports, ordered components and spacing roles.

The [source audit](nominal-i-source-audit.json) and
[evaluation](nominal-i-evaluation.json) record 127 new required judgments and
24 boundary exclusions. All 12,212 probe inputs retain every prior candidate
under raw/headword/compatible modes; each adds 280 paths, 34 unjudged. Full
frozen corpus outcomes are unchanged. These noun and suffix entries remain
outside the 715-entry ending/particle/auxiliary queue; its counts remain 386
scoped / 328 unreviewed / one gap. Wider noun suffix senses, nonlexical repeated
base classification and independent Korean review remain open. All 632 Rust
tests, Nix CLI/web builds and flake checks, and refreshed packaged-preview gates
pass. Novel output retains all 179,112 records, adds 41 candidates at 39
occurrences without removals, and retains existing dictionary readings. One
spacing segment gains a noun path; boundaries and search limits remain unchanged.
All new contextual novel paths remain unjudged. Packaged/debug output hashes
match in all five modes. Three interleaved local release runs per filter give
after medians of 1.61/1.59 seconds; these observations do not certify grammar
coverage or universal throughput.

## Remaining native noun-forming -이 discovery (2026-10-01)

COV-022e expands the remaining COV-022 work into 36 individually identified
native examples: six sense-2 compound formations and thirty sense-3
noun/root/sound-or-manner bases. The [report](nominal-i-remaining-audit.json)
retains full original example groups, exact dictionary head/POS probes, and
all 108 bare-word CLI outputs under raw and both filter modes. None currently
contains `suffix.nominal.i`. This describes a derivational coverage gap, not
a missing whole-word lookup or a certification of proposed segmentations.

The six-file literal-prefix scan finds fourteen rows in fourteen complete
KAIST training sentences and none in the other five partitions. Original
lexical gold remains unchanged. `떠돌이` and `미닫이` are explicit unresolved
class/boundary examples under the compound sense's general attachment note;
missing base heads and guessed related predicates are not promoted to gold.
No source candidate judgment, frozen baseline or runtime path changes.

Reproduce with the CLI path and source revision recorded in the report:

```sh
python3 tools/audit_nominal_i.py --cli /path/to/built/klem \
  --revision a2f6c19f5ae3b6290134c01b01df0c58c4485933 > /tmp/nominal-i-remaining-audit.json
```

The CLI and pinned dictionary/corpus hashes must match the report for historical
reproduction. The 715-entry ending/particle/auxiliary review queue is unchanged;
these noun and suffix entries lie outside its POS scope.
