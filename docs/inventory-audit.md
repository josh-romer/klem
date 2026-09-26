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

The [manual ledger](inventory-reviews.json) contains ten scoped reviews:
-듯/-듯이 (COV-016), four informative ending entries (COV-017m), and connective
-요 (COV-020d), causal -기에/-길래 (COV-017n), and the expressive 어 하다
sense of auxiliary 하다 (COV-019d). Their source notes were
inspected individually; each review
records its supported scope, remaining limits, checklist item, named Rust tests,
evaluation evidence, and source-specific candidate judgments. Independent
Korean-language review is pending. The other **705 entries are unreviewed in
this ledger**, which does not imply they are unimplemented.

The queue links **214 entries to the teaching catalog**, **75 to source-citing
candidate judgments**, and all **54 auxiliaries to the earlier attachment
inventory**. These are evidence navigation aids, not coverage certifications.
In particular, a source citation can support one narrow forbidden path without
establishing the rest of an entry's attachment behavior.

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
