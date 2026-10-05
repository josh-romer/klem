# Fresh literary passage review

This review uses the original text of 현진건's *운수 좋은 날* from
[Korean Wikisource revision 457472](https://ko.wikisource.org/w/index.php?oldid=457472&title=%EC%9A%B4%EC%88%98_%EC%A2%8B%EC%9D%80_%EB%82%A0).
The [source record](fresh-unsu-source.json) retains attribution, publisher-page
URLs and hashes, and the license notices observed at capture time. The narrative
fragment is retained exactly; original spelling, punctuation, dialogue and spacing
are preserved. Publisher navigation is not included in the offline fragment.

The separate work contains 82 paragraphs and 2,660 word records. Before observing
CLI output, four uniformly spaced paragraphs were selected: indices 0, 27, 54 and
81. This provides narrative and dialogue samples outside the repeatedly used
regression corpora and pinned novel. It does not establish coverage for other
works, historical Korean, dialects or arbitrary contemporary text.

The captured executable and assets are the COV-022t Nix outputs committed in
`52bd71e`, before the new -씩 implementation. The [CLI capture](fresh-unsu-cli.json.gz)
preserves twelve Unicode/cache/filter streams, all original candidates and ordered
reading assessments, and all earlier dictionary-entry fields. The 45 added
readings across the three modes invert to source-backed -하다 whole-head parents;
they are not new contextual gold judgments.

| Dictionary filter | Word records without candidates |
| --- | ---: |
| Raw | 0 |
| Headword matches | 276 |
| Compatible matches | 291 |

The [individual review queue](fresh-unsu-review.json) gives each of the 291
compatible-filter misses a stable ID, original byte span and surrounding context.
For 276 records there is no complete dictionary-matched candidate; 15 have a
headword-matched candidate excluded by compatibility. These observations separate
filter behavior from contextual correctness. They do not distinguish every
missing dictionary headword from a missing morphological path.

Frequent misses include 첨지는 (27 occurrences), 첨지의 (11), 오라질 (10), and
인력거를 (five). Raw 인력거를 does offer 인력거 + 를, with no dictionary entry for
that lemma in the pinned snapshot. 잔씩 offers only the original unchanged word;
the missing 잔 + 씩 path is tracked as **COV-022u**, with its own preserved source
and baseline. Names, historical spelling, dictionary breadth and derivation gaps
must be reviewed separately; these counts are not a precision or recall score.

The [browser capture](fresh-unsu-browser.json.gz) preserves eight NFC/NFD renders,
24 exact CLI/export comparisons, input preservation and desktop/mobile captures.
[Screenshots](fresh-unsu-screenshots/) retain the actual reader-visible defaults.
Fourteen display observations are tracked individually in the review queue:
dictionary hints can be misleading in context even when alternatives are present.
Examples include 먹지를 displayed as 먹지 (“carbon paper”) + 를, 오고 initially
displayed through the nominal 오 + copula reading, and 김 displayed with “steam.”
The observed defaults are recorded, not converted into independently reviewed
gold labels or a contextual ranking rule.

[Actual alternative-selection checks](fresh-unsu-options.json) confirm that both
먹지를 occurrences can be switched to 먹다 + 지 + 를 in NFC and NFD, rendering
먹 + 지 + 를. The noun alternative remains available. Thus the candidate exists;
the initial choice and dictionary sense remain separate reading decisions.

Run `python3 tools/fresh_passage_audit.py` for the offline evidence check. It checks
the retained narrative extraction, deterministic selection, every CLI byte span,
cache/Unicode parity, preservation, source parents, miss IDs/contexts, browser
exports, selectable candidate records and screenshot hashes. The original full
publisher pages are represented by their capture hashes and URLs, not replayed
offline. Contextual ranking, sense disambiguation and independent Korean-language
review remain open or deferred under the release boundaries.
