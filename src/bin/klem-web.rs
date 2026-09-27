//! Local HTTP adapter for the SolidJS sentence explorer.
use klem::dictionary::{
    Compatibility, Dictionary, DictionarySession, EntrySummary, Result, SqliteDictionary,
};
use klem::{Lemmatizer, MorphemeKind, TokenKind, Tokenizer};
use serde::Deserialize;
use serde_json::{Value, json};
use std::{
    collections::{BTreeMap, BTreeSet},
    env, fs,
    io::Read,
    path::{Component, Path, PathBuf},
    time::Instant,
};
use tiny_http::{Header, Method, Request, Response, Server, StatusCode};

const MAX_TEXT_BYTES: usize = 8_000;
const MAX_WORD_CHARS: usize = 64;
const MAX_BODY_BYTES: u64 = 32_768;
#[path = "klem-web/grammar_labels.rs"]
mod grammar_labels;
const HELP: &str = "klem-web — local Korean sentence explorer\n\nUsage: klem-web [--port 8080] [--assets web/dist] [--dictionary path.db]\n\nOpen http://127.0.0.1:8080 in your browser. Binds only to loopback.\nWithout --dictionary, the app shows rule candidates without dictionary matches.\nBuild assets first with cd web && npm ci && npm run build, or use nix run .#web.\n";

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct AnalyzeRequest {
    text: String,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct EntryRequest {
    id: String,
}

fn validate_text(text: &str) -> std::result::Result<(), &'static str> {
    if text.trim().is_empty() {
        return Err("Paste a sentence to analyze.");
    }
    if text.len() > MAX_TEXT_BYTES {
        return Err(
            "This sentence is too long. Use up to 8,000 UTF-8 bytes, or use the CLI for larger works.",
        );
    }
    if Tokenizer::new(text)
        .any(|(_, kind, word)| kind == TokenKind::Word && word.chars().count() > MAX_WORD_CHARS)
    {
        return Err(
            "A word is too long. The sentence viewer supports up to 64 characters per word; use the CLI for longer words.",
        );
    }
    Ok(())
}

fn analyze(text: &str, dictionary: Option<&SqliteDictionary>) -> Result<Value> {
    validate_text(text)?;
    let start = Instant::now();
    let engine = Lemmatizer::new();
    let mut lookups = dictionary.map(|d| DictionarySession::new(d, 4 * 1024 * 1024));
    let mut rules = BTreeMap::new();
    let mut records = Vec::new();
    let mut breakdowns = Vec::new();
    let mut glosses: BTreeMap<String, Option<String>> = BTreeMap::new();
    let mut grammar: BTreeMap<String, Vec<EntrySummary>> = BTreeMap::new();
    for token in engine.analyze_text(text) {
        let annotation = if let (Some(a), Some(d)) = (&token.analysis, &mut lookups) {
            Some(d.annotate(a)?)
        } else {
            None
        };
        // Short hints for compatible homonyms. Full senses remain available on demand;
        // neither dictionary order nor POS compatibility chooses a contextual sense.
        if let (Some(annotation), Some(db)) = (&annotation, dictionary) {
            let supported: BTreeSet<_> = annotation
                .readings
                .iter()
                .flat_map(|r| &r.lemmas)
                .flat_map(|l| &l.entries)
                .filter(|e| e.status != Compatibility::Incompatible)
                .map(|e| e.id.as_str())
                .collect();
            for matches in &annotation.lemmas {
                for entry in matches.entries.iter().filter(|e| {
                    e.pos_compatibility != Compatibility::Incompatible
                        || supported.contains(e.entry.id.as_str())
                }) {
                    if glosses.contains_key(&entry.entry.id) {
                        continue;
                    }
                    let gloss = db.entry(&entry.entry.id)?.and_then(|e| {
                        e.senses
                            .into_iter()
                            .flat_map(|s| s.translations)
                            .find(|t| t.language == "영어" && !t.lemma.is_empty())
                            .map(|t| t.lemma)
                    });
                    glosses.insert(entry.entry.id.clone(), gloss);
                }
            }
        }
        breakdowns.push(
            token
                .analysis
                .as_ref()
                .map(|a| a.analyses.iter().map(|a| a.breakdown()).collect::<Vec<_>>()),
        );
        if let Some(analysis) = &token.analysis {
            for a in &analysis.analyses {
                if let Some(lookups) = &mut lookups {
                    for m in &a.morphemes {
                        let headword = match m.kind {
                            MorphemeKind::Particle => m.form.clone(),
                            MorphemeKind::Ending | MorphemeKind::Suffix => format!("-{}", m.form),
                            MorphemeKind::Prefinal => format!("-{}-", m.form),
                        };
                        if !grammar.contains_key(&headword) {
                            grammar.insert(
                                headword.clone(),
                                grammar_labels::lookup(lookups, m.kind, &headword)?,
                            );
                        }
                    }
                }
                for rule in &a.rules {
                    rules.insert(
                        rule.clone(),
                        klem::rule_explanation(rule).unwrap_or("No explanation available."),
                    );
                }
            }
        }
        let mut record = serde_json::to_value(token)?;
        record["dictionary"] = serde_json::to_value(annotation)?;
        records.push(record);
    }
    Ok(
        json!({"records":records, "rules":rules, "breakdowns":breakdowns, "glosses":glosses, "grammar":grammar, "elapsed_ms":start.elapsed().as_secs_f64()*1000.0}),
    )
}

fn header(name: &str, value: &str) -> Header {
    Header::from_bytes(name, value).expect("valid fixed HTTP header")
}
fn respond(request: Request, code: u16, mime: &str, body: Vec<u8>) {
    let response = Response::from_data(body).with_status_code(StatusCode(code))
        .with_header(header("Content-Type", mime))
        .with_header(header("Cache-Control", "no-store"))
        .with_header(header("X-Content-Type-Options", "nosniff"))
        .with_header(header("Referrer-Policy", "no-referrer"))
        .with_header(header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'"));
    if let Err(e) = request.respond(response) {
        eprintln!("klem-web: response failed: {e}");
    }
}
fn json_response(request: Request, code: u16, value: Value) {
    respond(
        request,
        code,
        "application/json; charset=utf-8",
        serde_json::to_vec(&value).expect("serializable JSON"),
    );
}
fn fail(request: Request, code: u16, message: &str) {
    json_response(request, code, json!({"error":message}));
}

fn asset(root: &Path, url: &str) -> Option<(Vec<u8>, &'static str)> {
    let relative = if url == "/" {
        "index.html"
    } else {
        url.strip_prefix('/')?
    };
    if relative.is_empty()
        || !Path::new(relative)
            .components()
            .all(|c| matches!(c, Component::Normal(_)))
    {
        return None;
    }
    let path = root.join(relative).canonicalize().ok()?;
    if !path.starts_with(root) {
        return None;
    }
    let mime = match path.extension()?.to_str()? {
        "html" => "text/html; charset=utf-8",
        "js" => "text/javascript; charset=utf-8",
        "css" => "text/css; charset=utf-8",
        "svg" => "image/svg+xml",
        "woff2" => "font/woff2",
        "txt" => "text/plain; charset=utf-8",
        _ => return None,
    };
    Some((fs::read(path).ok()?, mime))
}

fn handle(mut request: Request, root: &Path, dictionary: Option<&SqliteDictionary>, port: u16) {
    let allowed = [format!("127.0.0.1:{port}"), format!("localhost:{port}")];
    let host = request
        .headers()
        .iter()
        .find(|h| h.field.equiv("Host"))
        .map(|h| h.value.as_str());
    if !host.is_some_and(|h| allowed.iter().any(|a| a == h)) {
        fail(request, 403, "Use the local app address.");
        return;
    }
    // Vite proxies API calls with changeOrigin in development. Production is
    // same-origin; rejecting other origins also prevents browser DNS rebinding.
    if let Some(origin) = request.headers().iter().find(|h| h.field.equiv("Origin"))
        && !allowed
            .iter()
            .any(|a| origin.value.as_str() == format!("http://{a}"))
    {
        fail(request, 403, "Cross-origin requests are not supported.");
        return;
    }
    let url = request.url().split('?').next().unwrap_or("/").to_owned();
    if request.method() == &Method::Get && url == "/api/status" {
        json_response(
            request,
            200,
            json!({"version":env!("CARGO_PKG_VERSION"),
            "dictionary":dictionary.map(|d| json!({"metadata":d.metadata(), "fingerprint":d.fingerprint()})),
            "limits":{"text_bytes":MAX_TEXT_BYTES,"word_chars":MAX_WORD_CHARS}}),
        );
        return;
    }
    if request.method() == &Method::Get && !url.starts_with("/api/") {
        if let Some((body, mime)) = asset(root, &url) {
            respond(request, 200, mime, body);
        } else {
            fail(request, 404, "Page not found.");
        }
        return;
    }
    if !matches!(url.as_str(), "/api/analyze" | "/api/entry") {
        fail(request, 404, "Endpoint not found.");
        return;
    }
    if request.method() != &Method::Post {
        fail(request, 405, "Use POST for this endpoint.");
        return;
    }
    let json_type = request.headers().iter().any(|h| {
        h.field.equiv("Content-Type")
            && h.value
                .as_str()
                .split(';')
                .next()
                .is_some_and(|v| v.trim().eq_ignore_ascii_case("application/json"))
    });
    if !json_type {
        fail(request, 415, "Send application/json.");
        return;
    }
    if request
        .body_length()
        .is_some_and(|n| n > MAX_BODY_BYTES as usize)
    {
        fail(request, 413, "Request is too large.");
        return;
    }
    let mut body = Vec::new();
    if request
        .as_reader()
        .take(MAX_BODY_BYTES + 1)
        .read_to_end(&mut body)
        .is_err()
    {
        fail(request, 400, "Could not read the request.");
        return;
    }
    if body.len() > MAX_BODY_BYTES as usize {
        fail(request, 413, "Request is too large.");
        return;
    }
    if url == "/api/analyze" {
        let Ok(input) = serde_json::from_slice::<AnalyzeRequest>(&body) else {
            fail(request, 400, "Expected a JSON object with a text string.");
            return;
        };
        if let Err(message) = validate_text(&input.text) {
            fail(request, 422, message);
            return;
        }
        match analyze(&input.text, dictionary) {
            Ok(value) => json_response(request, 200, value),
            Err(e) => {
                eprintln!("klem-web: {e}");
                fail(
                    request,
                    500,
                    "Analysis failed. See the server log for details.",
                );
            }
        }
    } else {
        let Ok(input) = serde_json::from_slice::<EntryRequest>(&body) else {
            fail(request, 400, "Expected a JSON object with an entry ID.");
            return;
        };
        let Some(dictionary) = dictionary else {
            fail(request, 409, "No dictionary is connected.");
            return;
        };
        match dictionary.entry(&input.id) {
            Ok(Some(entry)) => json_response(request, 200, json!({"entry":entry})),
            Ok(None) => fail(request, 404, "Dictionary entry not found."),
            Err(e) => {
                eprintln!("klem-web: {e}");
                fail(request, 500, "Dictionary lookup failed.");
            }
        }
    }
}

fn run() -> Result<()> {
    let mut args = env::args().skip(1);
    let mut port: u16 = 8080;
    let mut assets = env::var_os("KLEM_WEB_ASSETS")
        .map(PathBuf::from)
        .unwrap_or_else(|| "web/dist".into());
    let mut dictionary_path = None;
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--help" | "-h" => {
                print!("{HELP}");
                return Ok(());
            }
            "--port" => port = args.next().ok_or("--port needs a number")?.parse()?,
            "--assets" => assets = args.next().ok_or("--assets needs a directory")?.into(),
            "--dictionary" => {
                dictionary_path = Some(args.next().ok_or("--dictionary needs a database")?)
            }
            _ => return Err(format!("unknown argument: {arg}\n{HELP}").into()),
        }
    }
    let assets = assets.canonicalize().map_err(|e| {
        format!("Cannot open frontend assets: {e}. Build web/ first or use nix run .#web.")
    })?;
    if !assets.join("index.html").is_file() {
        return Err("frontend index.html is missing; run npm run build in web/".into());
    }
    let dictionary = dictionary_path.map(SqliteDictionary::open).transpose()?;
    let server = Server::http(("127.0.0.1", port))?;
    let actual_port = server
        .server_addr()
        .to_ip()
        .ok_or("missing TCP address")?
        .port();
    eprintln!("klem-web: http://127.0.0.1:{actual_port}");
    for request in server.incoming_requests() {
        handle(request, &assets, dictionary.as_ref(), actual_port);
    }
    Ok(())
}
fn main() {
    if let Err(error) = run() {
        eprintln!("klem-web: {error}");
        std::process::exit(1);
    }
}

#[cfg(test)]
mod tests {
    #[test]
    fn expression_lookup_is_limited_to_reviewed_ids_headwords_and_kinds() {
        use super::*;
        for (headword, id) in [
            ("-으려는", "krdict:86717"),
            ("-자는", "krdict:83896"),
            ("-냐는", "krdict:86030"),
            ("-잖아", "krdict:86756"),
            ("-잖아요", "krdict:86757"),
            ("-느냐는", "krdict:86031"),
            ("-으냐는", "krdict:86032"),
        ] {
            let mut entry = EntrySummary {
                id: id.into(),
                headword: headword.into(),
                homonym: "0".into(),
                pos: "품사 없음".into(),
            };
            assert!(grammar_labels::entry_matches(
                MorphemeKind::Ending,
                headword,
                &entry
            ));
            for kind in [
                MorphemeKind::Suffix,
                MorphemeKind::Particle,
                MorphemeKind::Prefinal,
            ] {
                assert!(!grammar_labels::entry_matches(kind, headword, &entry));
            }
            assert!(!grammar_labels::entry_matches(
                MorphemeKind::Ending,
                "-는다면",
                &entry
            ));
            entry.id = "krdict:68841".into();
            assert!(!grammar_labels::entry_matches(
                MorphemeKind::Ending,
                headword,
                &entry
            ));
            entry.id = id.into();
            entry.headword = "다른표현".into();
            assert!(!grammar_labels::entry_matches(
                MorphemeKind::Ending,
                headword,
                &entry
            ));
            entry.headword = headword.into();
            entry.pos = "명사".into();
            assert!(!grammar_labels::entry_matches(
                MorphemeKind::Ending,
                headword,
                &entry
            ));
        }
    }

    use super::*;
    #[test]
    fn api_preserves_all_records_and_original_byte_offsets() {
        let text = "가까워 먹어봤어요.\n🙂";
        let result = analyze(text, None).unwrap();
        let records = result["records"].as_array().unwrap();
        let expected: Vec<_> = Lemmatizer::new().analyze_text(text).collect();
        assert_eq!(records.len(), expected.len());
        for (actual, expected) in records.iter().zip(expected) {
            let mut actual = actual.clone();
            assert!(
                actual
                    .as_object_mut()
                    .unwrap()
                    .remove("dictionary")
                    .unwrap()
                    .is_null()
            );
            assert_eq!(actual, serde_json::to_value(expected).unwrap());
        }
        assert!(!result["rules"].as_object().unwrap().is_empty());
    }
    #[test]
    fn sentence_limits_reject_whole_requests_without_truncating() {
        for text in [" ".to_owned(), "가".repeat(65), "가 ".repeat(2001)] {
            assert!(validate_text(&text).is_err());
        }
        assert!(validate_text(&"가".repeat(64)).is_ok());
        assert!(validate_text("안녕하세요.").is_ok());
    }
}
