//! Modern Hangul arithmetic. Compatibility jamo are never silently normalized.
pub(crate) const V_A: u32 = 0;
pub(crate) const V_EO: u32 = 4;

pub(crate) fn split(c: char) -> Option<(u32, u32, u32)> {
    let n = (c as u32).checked_sub(0xac00)?;
    (n < 11172).then_some((n / 588, n / 28 % 21, n % 28))
}

pub(crate) fn compose(l: u32, v: u32, t: u32) -> char {
    char::from_u32(0xac00 + l * 588 + v * 28 + t).expect("valid Hangul indices")
}

pub(crate) fn last(s: &str) -> Option<(u32, u32, u32)> {
    split(s.chars().next_back()?)
}

pub(crate) fn replace_last(s: &str, v: u32, t: u32) -> Option<String> {
    let (l, _, _) = last(s)?;
    let mut out = s[..s.len() - 3].to_owned();
    out.push(compose(l, v, t));
    Some(out)
}

pub(crate) fn coda(s: &str) -> Option<u32> {
    last(s).map(|(_, _, t)| t)
}

pub(crate) fn has_hangul(s: &str) -> bool {
    s.chars().any(|c| split(c).is_some())
}

pub(crate) fn bright(s: &str) -> bool {
    last(s).is_some_and(|(_, v, _)| v == 0 || v == 8)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn every_modern_syllable_round_trips() {
        for n in 0xac00..=0xd7a3 {
            let c = char::from_u32(n).unwrap();
            let (l, v, t) = split(c).unwrap();
            assert_eq!(compose(l, v, t), c);
        }
        assert_eq!(split('a'), None);
        assert_eq!(split('ㄱ'), None);
    }
}
