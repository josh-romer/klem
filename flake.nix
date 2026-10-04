{
  description = "A rule-based Korean lemmatizer: Rust library, CLI, and development environment";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";

  outputs = { self, nixpkgs, ... }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "aarch64-darwin"
      ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
      manifest = builtins.fromTOML (builtins.readFile ./Cargo.toml);
    in
    {
      packages = forAllSystems (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          klem = pkgs.rustPlatform.buildRustPackage {
            pname = manifest.package.name;
            version = manifest.package.version;

            # Keep build outputs, downloaded corpora, and local caches out of the source.
            src = pkgs.lib.fileset.toSource {
              root = ./.;
              fileset = pkgs.lib.fileset.unions [
                ./Cargo.toml
                ./Cargo.lock
                ./src
                ./tests
                ./docs/adverb-root-inventory.json
                ./docs/question-case-source-preflight.json
                ./docs/question-clause-additive-preflight.json
                ./docs/continuation-left-source-preflight.json
                ./docs/continuation-inflection-source-preflight.json
                ./docs/continuation-gold-residual-preflight.json
                ./examples
                ./tools/corpus.rs
                ./tools/validity.rs
                ./tools/adjectival_allomorph.rs
                ./README.md
                ./LICENSE-MIT
                ./LICENSE-APACHE
                ./web/src/grammar-labels.json
              ];
            };

            cargoLock.lockFile = ./Cargo.lock;
            buildFeatures = [ "web" ];
            checkFeatures = [ "web" ];
            doCheck = true;

            meta = {
              description = manifest.package.description;
              license = with pkgs.lib.licenses; [ mit asl20 ];
              mainProgram = "klem";
              platforms = systems;
            };
          };
          web-assets = pkgs.buildNpmPackage {
            pname = "klem-web-assets";
            version = manifest.package.version;
            src = pkgs.lib.fileset.toSource {
              root = ./web;
              fileset = pkgs.lib.fileset.unions [
                ./web/package.json ./web/package-lock.json ./web/index.html
                ./web/tsconfig.json ./web/vite.config.ts ./web/src ./web/public
              ];
            };
            npmDepsHash = "sha256-TPUi4+ekXlwgRQDE9CVwvENqwIgQIi1LOvRGiPDiyDg=";
            installPhase = ''
              runHook preInstall
              mkdir -p $out/share/klem-web
              cp -r dist/. $out/share/klem-web/
              runHook postInstall
            '';
          };
          web = pkgs.writeShellApplication {
            name = "klem-web";
            text = ''
              exec ${klem}/bin/klem-web --assets ${web-assets}/share/klem-web "$@"
            '';
          };
        in
        {
          inherit klem web web-assets;
          default = klem;
        });

      apps = forAllSystems (system:
        let
          app = {
            type = "app";
            program = nixpkgs.lib.getExe self.packages.${system}.klem;
            meta.description = manifest.package.description;
          };
        in
        {
          klem = app;
          default = app;
          web = {
            type = "app";
            program = nixpkgs.lib.getExe self.packages.${system}.web;
            meta.description = "Local SolidJS Korean sentence explorer";
          };
        });

      checks = forAllSystems (system:
        let pkgs = nixpkgs.legacyPackages.${system};
        in {
          inherit (self.packages.${system}) klem web-assets;
          inventory-review = pkgs.runCommand "klem-inventory-review" {
            nativeBuildInputs = [ pkgs.python3 ];
            src = pkgs.lib.fileset.toSource {
              root = ./.;
              fileset = pkgs.lib.fileset.unions [
                ./tools/review_inventory.py ./tools/test_review_inventory.py
                ./tools/excluded_paradigm_audit.py
                ./tools/excluded_paradigm_queue.py
                ./tools/question_topic_audit.py
                ./tools/question_topic_queue.py
                ./tools/question_additive_audit.py
                ./tools/question_additive_queue.py
                ./tools/continuation_left_audit.py
                ./tools/continuation_left_compare.py
                ./tools/continuation_left_queue.py
                ./tools/continuation_left_broad_queue.py
                ./tools/continuation_left_corpus_audit.py
                ./tools/continuation_residual_audit.py
                ./tools/continuation_inflection_audit.py
                ./tools/continuation_inflection_additional.py
                ./tools/continuation_inflection_review.py
                ./tools/continuation_inflection_compare.py
                ./tools/continuation_inflection_queue.py
                ./tools/bare_noun_spacing_audit.py
                ./tools/bare_noun_spacing_additional.py
                ./tools/bare_noun_spacing_compare.py
                ./tools/bare_noun_spacing_runtime.py
                ./tools/bare_noun_spacing_queue.py
                ./tools/lexical_nada_audit.py
                ./tools/lexical_nada_review.py
                ./tools/lexical_nada_fixtures.py
                ./tools/lexical_nada_dependencies.py
                ./tools/lexical_nada_priority.py
                ./tools/lexical_nada_compare.py
                ./tools/lexical_nada_runtime.py
                ./tools/lexical_nada_queue.py
                ./tools/lexical_nada_country_tree_review.py
                ./tools/lexical_nada_listed_review.py
                ./tools/lexical_nada_listed_fixtures.py
                ./tools/lexical_nada_listed_compare.py
                ./tools/lexical_nada_listed_runtime.py
                ./tools/lexical_nada_listed_additional.py
                ./tools/lexical_nada_listed_queue.py
                ./tools/rya_boundary_audit.py
                ./tools/rya_boundary_regressions.py
                ./tools/rya_boundary_compare.py
                ./tools/rya_boundary_runtime.py
                ./tools/rya_boundary_queue.py
                ./tools/rya_copula_audit.py
                ./tools/rya_copula_compare.py
                ./tools/rya_copula_runtime.py
                ./tools/rya_copula_queue.py
                ./tools/caution_ending_audit.py
                ./tools/caution_ending_compare.py
                ./tools/caution_ending_runtime.py
                ./tools/caution_ending_queue.py
                ./tools/future_question_audit.py
                ./tools/future_question_compare.py
                ./tools/future_question_additional.py
                ./tools/future_question_runtime.py
                ./tools/future_question_queue.py
                ./tools/reported_retrospective_audit.py
                ./tools/reported_retrospective_corrections.py
                ./tools/reported_retrospective_compare.py
                ./tools/reported_retrospective_additional.py
                ./tools/reported_retrospective_queue.py
                ./tools/reported_retrospective_runtime.py
                ./tools/adjectival_allomorph_audit.py
                ./tools/adjectival_allomorph_corrections.py
                ./tools/adjectival_allomorph_policy.py
                ./tools/adjectival_allomorph_checkpoint.py
                ./tools/adjectival_allomorph_corpora.py
                ./tools/adjectival_allomorph_compare.py
                ./tools/adjectival_allomorph_runtime.py
                ./tools/adjectival_allomorph_browser.py
                ./examples/audit_adjectival_allomorph.rs
                ./web/tests/adjectival-allomorph.mjs
                ./tools/adjectival_allomorph.rs
                ./tools/native_lmf.py ./tools/test_native_lmf.py
                ./docs ./tests ./web/src/grammar-labels.json
                ./web/tests/browser.mjs
                ./web/tests/question-topic.mjs
                ./web/tests/question-additive.mjs
                ./web/tests/continuation-left.mjs
                ./web/tests/continuation-inflection.mjs
                ./web/tests/bare-noun-spacing.mjs
                ./web/tests/lexical-nada.mjs
                ./web/tests/lexical-nada-listed.mjs
                ./web/tests/rya-boundary.mjs
                ./web/tests/rya-copula.mjs
                ./web/tests/caution-ending.mjs
                ./web/tests/future-question.mjs
                ./web/tests/reported-retrospective.mjs
              ];
            };
          } ''
            cd "$src"
            export PYTHONDONTWRITEBYTECODE=1
            python -m unittest discover -s tools -p 'test_review_inventory.py'
            python -m unittest discover -s tools -p 'test_native_lmf.py'
            python tools/excluded_paradigm_audit.py --verify
            python tools/excluded_paradigm_queue.py --verify
            python tools/question_topic_audit.py --verify
            python tools/question_topic_queue.py --verify
            python tools/question_additive_audit.py --verify
            python tools/question_additive_queue.py --verify
            python tools/continuation_left_audit.py --verify
            python tools/continuation_left_queue.py --verify
            python tools/continuation_left_broad_queue.py --verify
            python tools/continuation_left_corpus_audit.py --verify
            python tools/continuation_residual_audit.py --verify
            python tools/continuation_inflection_audit.py --verify
            python tools/continuation_inflection_additional.py --verify
            python tools/continuation_inflection_review.py --verify
            python tools/continuation_inflection_queue.py --verify
            python tools/bare_noun_spacing_audit.py --verify
            python tools/bare_noun_spacing_additional.py --verify
            python tools/bare_noun_spacing_queue.py --verify
            python tools/lexical_nada_audit.py --verify
            python tools/lexical_nada_review.py --verify
            python tools/lexical_nada_fixtures.py --verify
            python tools/lexical_nada_dependencies.py --verify
            python tools/lexical_nada_priority.py --verify
            python tools/lexical_nada_queue.py --verify
            python tools/lexical_nada_country_tree_review.py --verify
            python tools/lexical_nada_listed_review.py --verify
            python tools/lexical_nada_listed_fixtures.py --verify
            python tools/lexical_nada_listed_queue.py --verify
            python tools/rya_boundary_audit.py --verify
            python tools/rya_boundary_regressions.py --verify
            python tools/rya_boundary_queue.py --verify
            python tools/rya_copula_audit.py --verify
            python tools/rya_copula_queue.py --verify
            python tools/caution_ending_audit.py --verify
            python tools/future_question_audit.py --verify
            python tools/reported_retrospective_queue.py --verify
            python tools/adjectival_allomorph_audit.py --verify
            python tools/adjectival_allomorph_corrections.py --verify
            python tools/adjectival_allomorph_policy.py --verify
            python tools/adjectival_allomorph_checkpoint.py --verify
            python tools/adjectival_allomorph_corpora.py --verify
            python tools/adjectival_allomorph_compare.py --verify
            python tools/adjectival_allomorph_runtime.py --verify
            python tools/adjectival_allomorph_browser.py --verify
            python tools/future_question_additional.py --verify
            python tools/future_question_queue.py --verify
            python tools/caution_ending_queue.py --verify
            python tools/review_inventory.py --verify
            touch "$out"
          '';
        });

      devShells = forAllSystems (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          default = pkgs.mkShell {
            packages = with pkgs; [
              cargo
              rustc
              rustfmt
              clippy
              rust-analyzer
              nodejs
              python3 # Offline grammar/corpus inventory audit.
            ];

            RUST_SRC_PATH = "${pkgs.rustPlatform.rustLibSrc}";
          };
        });
    };
}
