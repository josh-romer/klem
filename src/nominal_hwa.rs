//! KRDict 88499: source-listed noun + -화 formations and separately recorded passives.
use crate::{Lemma, LemmaKind, Morpheme, MorphemeKind, doeda_identity::OriginSource};
pub(crate) const RULE: &str = "suffix.nominal.hwa";
pub(crate) fn nominal(head: &str) -> Option<&'static str> {
    match head {
        "가속화" => Some("가속"),
        "가시화" => Some("가시"),
        "개념화" => Some("개념"),
        "개방화" => Some("개방"),
        "개별화" => Some("개별"),
        "객관화" => Some("객관"),
        "격식화" => Some("격식"),
        "내면화" => Some("내면"),
        "내실화" => Some("내실"),
        "노령화" => Some("노령"),
        "민영화" => Some("민영"),
        "민주화" => Some("민주"),
        "보편화" => Some("보편"),
        "상품화" => Some("상품"),
        "생활화" => Some("생활"),
        "온난화" => Some("온난"),
        "이론화" => Some("이론"),
        "이상화" => Some("이상"),
        "일반화" => Some("일반"),
        "일상화" => Some("일상"),
        "제도화" => Some("제도"),
        "조직화" => Some("조직"),
        "최소화" => Some("최소"),
        "토착화" => Some("토착"),
        "특수화" => Some("특수"),
        "표준화" => Some("표준"),
        "합리화" => Some("합리"),
        "황폐화" => Some("황폐"),
        _ => None,
    }
}
pub(crate) fn passive(head: &str) -> Option<&'static str> {
    match head {
        "가속화되다" => Some("가속"),
        "가시화되다" => Some("가시"),
        "개방화되다" => Some("개방"),
        "객관화되다" => Some("객관"),
        "내면화되다" => Some("내면"),
        "민영화되다" => Some("민영"),
        "민주화되다" => Some("민주"),
        "보편화되다" => Some("보편"),
        "상품화되다" => Some("상품"),
        "생활화되다" => Some("생활"),
        "이론화되다" => Some("이론"),
        "이상화되다" => Some("이상"),
        "일반화되다" => Some("일반"),
        "일상화되다" => Some("일상"),
        "제도화되다" => Some("제도"),
        "조직화되다" => Some("조직"),
        "토착화되다" => Some("토착"),
        "특수화되다" => Some("특수"),
        "표준화되다" => Some("표준"),
        "합리화되다" => Some("합리"),
        "황폐화되다" => Some("황폐"),
        _ => None,
    }
}
pub(crate) fn owner(lemma: &Lemma, rules: &[String], morphs: &[Morpheme]) -> bool {
    morphs
        .first()
        .is_some_and(|m| m.kind == MorphemeKind::Suffix && m.form == "화")
        && lemma.kind == LemmaKind::Nominal
        && matches!(
            lemma.text.as_str(),
            "가속"
                | "가시"
                | "개념"
                | "개방"
                | "개별"
                | "객관"
                | "격식"
                | "내면"
                | "내실"
                | "노령"
                | "민영"
                | "민주"
                | "보편"
                | "상품"
                | "생활"
                | "온난"
                | "이론"
                | "이상"
                | "일반"
                | "일상"
                | "제도"
                | "조직"
                | "최소"
                | "토착"
                | "특수"
                | "표준"
                | "합리"
                | "황폐"
        )
        && rules.iter().any(|r| r == RULE)
}
pub(crate) fn passive_owner(lemma: &Lemma, rules: &[String], morphs: &[Morpheme]) -> bool {
    owner(lemma, rules, morphs)
        && matches!(
            lemma.text.as_str(),
            "가속"
                | "가시"
                | "개방"
                | "객관"
                | "내면"
                | "민영"
                | "민주"
                | "보편"
                | "상품"
                | "생활"
                | "이론"
                | "이상"
                | "일반"
                | "일상"
                | "제도"
                | "조직"
                | "토착"
                | "특수"
                | "표준"
                | "합리"
                | "황폐"
        )
        && rules.iter().any(|r| r == "suffix.verb.doeda")
        && morphs
            .get(1)
            .is_some_and(|m| m.kind == MorphemeKind::Suffix && m.form == "되다")
}
pub(crate) fn identity(base: &str) -> Option<&'static OriginSource> {
    SOURCES.iter().find(|source| source.base == base)
}
const SOURCES: &[OriginSource] = &[
    OriginSource {
        base: "가속",
        expected_origins: &["加速"],
        whole_entries: &["krdict:14635"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "가시",
        expected_origins: &["可視"],
        whole_entries: &["krdict:14682"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "개방",
        expected_origins: &["開放"],
        whole_entries: &["krdict:23472"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "객관",
        expected_origins: &["客觀"],
        whole_entries: &["krdict:22451"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "내면",
        expected_origins: &["內面"],
        whole_entries: &["krdict:39525"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "민영",
        expected_origins: &["民營"],
        whole_entries: &["krdict:89328"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "민주",
        expected_origins: &["民主"],
        whole_entries: &["krdict:57393"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "보편",
        expected_origins: &["普遍"],
        whole_entries: &["krdict:59639"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "상품",
        expected_origins: &["商品"],
        whole_entries: &["krdict:83323"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "생활",
        expected_origins: &["生活"],
        whole_entries: &["krdict:62829"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "이론",
        expected_origins: &["理論"],
        whole_entries: &["krdict:71744"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "이상",
        expected_origins: &["理想"],
        whole_entries: &["krdict:72007"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "일반",
        expected_origins: &["一般"],
        whole_entries: &["krdict:72723"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "일상",
        expected_origins: &["日常"],
        whole_entries: &["krdict:72809"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "제도",
        expected_origins: &["制度"],
        whole_entries: &["krdict:75536"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "조직",
        expected_origins: &["組織"],
        whole_entries: &["krdict:75937"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "토착",
        expected_origins: &["土着"],
        whole_entries: &["krdict:81113"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "특수",
        expected_origins: &["特殊"],
        whole_entries: &["krdict:83016"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "표준",
        expected_origins: &["標準"],
        whole_entries: &["krdict:84229"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "합리",
        expected_origins: &["合理"],
        whole_entries: &["krdict:85522"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "황폐",
        expected_origins: &["荒廢"],
        whole_entries: &["krdict:87801"],
        whole_origins_complete: true,
    },
];

/// Nominal whole heads provide their own identity evidence, independently of passives.
pub(crate) fn nominal_identity(base: &str) -> Option<&'static OriginSource> {
    NOMINAL_SOURCES.iter().find(|source| source.base == base)
}

/// KRDict 68612 explicitly records 溫暖/溫煖; nominal 68615 uses 溫暖化.
/// This one attributed alternative is not a normalization of unrelated origins.
pub(crate) fn recorded_nominal_variant(source: &OriginSource, origin: &str) -> bool {
    source.base == "온난"
        && source.whole_entries == ["krdict:68615"]
        && source.expected_origins == ["溫暖"]
        && origin == "溫暖/溫煖"
}
const NOMINAL_SOURCES: &[OriginSource] = &[
    OriginSource {
        base: "가속",
        expected_origins: &["加速"],
        whole_entries: &["krdict:14634"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "가시",
        expected_origins: &["可視"],
        whole_entries: &["krdict:14680"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "개방",
        expected_origins: &["開放"],
        whole_entries: &["krdict:23468"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "객관",
        expected_origins: &["客觀"],
        whole_entries: &["krdict:22448"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "격식",
        expected_origins: &["格式"],
        whole_entries: &["krdict:33040"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "내면",
        expected_origins: &["內面"],
        whole_entries: &["krdict:39524"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "내실",
        expected_origins: &["內實"],
        whole_entries: &["krdict:19549"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "노령",
        expected_origins: &["老齡"],
        whole_entries: &["krdict:24156"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "민영",
        expected_origins: &["民營"],
        whole_entries: &["krdict:56493"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "민주",
        expected_origins: &["民主"],
        whole_entries: &["krdict:15778"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "보편",
        expected_origins: &["普遍"],
        whole_entries: &["krdict:59638"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "상품",
        expected_origins: &["商品"],
        whole_entries: &["krdict:83322"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "생활",
        expected_origins: &["生活"],
        whole_entries: &["krdict:62825"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "온난",
        expected_origins: &["溫暖"],
        whole_entries: &["krdict:68615"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "이론",
        expected_origins: &["理論"],
        whole_entries: &["krdict:71743"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "이상",
        expected_origins: &["理想"],
        whole_entries: &["krdict:72006"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "일반",
        expected_origins: &["一般"],
        whole_entries: &["krdict:72722"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "일상",
        expected_origins: &["日常"],
        whole_entries: &["krdict:72808"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "제도",
        expected_origins: &["制度"],
        whole_entries: &["krdict:75533"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "조직",
        expected_origins: &["組織"],
        whole_entries: &["krdict:75936"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "최소",
        expected_origins: &["最小", "最少"],
        whole_entries: &["krdict:79467", "krdict:79469"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "토착",
        expected_origins: &["土着"],
        whole_entries: &["krdict:81111"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "특수",
        expected_origins: &["特殊"],
        whole_entries: &["krdict:83015"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "표준",
        expected_origins: &["標準"],
        whole_entries: &["krdict:84227"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "합리",
        expected_origins: &["合理"],
        whole_entries: &["krdict:85521"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "황폐",
        expected_origins: &["荒廢"],
        whole_entries: &["krdict:87800"],
        whole_origins_complete: true,
    },
];
