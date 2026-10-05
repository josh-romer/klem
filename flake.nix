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
                ./tools/hada_nominal_preservation.rs
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
                ./tools/gam_question_audit.py
                ./tools/gam_question_regressions.py
                ./tools/gam_question_compare.py
                ./tools/gam_question_corpora.py
                ./tools/gam_question_runtime.py
                ./tools/gam_question_queue.py
                ./tools/gam_question_implementation.py
                ./tools/emphatic_ending_audit.py
                ./tools/emphatic_ending_regressions.py
                ./tools/emphatic_ending_corpora.py
                ./tools/emphatic_ending_diagnostics.py
                ./tools/emphatic_ending_compare.py
                ./tools/emphatic_ending_runtime.py
                ./tools/emphatic_ending_queue.py
                ./tools/doeda_role_audit.py
                ./tools/doeda_role_regressions.py
                ./tools/doeda_role_diagnostics.py
                ./tools/doeda_role_historical.py
                ./tools/doeda_role_stress.py
                ./tools/doeda_role_corpora.py
                ./tools/doeda_role_compare.py
                ./tools/doeda_role_runtime.py
                ./tools/doeda_role_browser.py
                ./tools/doeda_complement_audit.py
                ./tools/doeda_complement_regressions.py
                ./tools/doeda_complement_diagnostics.py
                ./tools/doeda_complement_package.py
                ./tools/doeda_complement_compare.py
                ./tools/doeda_complement_corpora.py
                ./tools/test_doeda_complement_corpora.py
                ./tools/doeda_noun_suffix_discovery.py
                ./tools/doeda_suffix_audit.py
                ./tools/doeda_suffix_regressions.py
                ./tools/doeda_suffix_diagnostics.py
                ./tools/doeda_suffix_package.py
                ./tools/doeda_suffix_compare.py
                ./tools/doeda_suffix_corpora.py
                ./tools/doeda_suffix_performance.py
                ./tools/test_doeda_suffix_regressions.py
                ./tools/test_doeda_suffix_diagnostics.py
                ./tools/test_doeda_suffix_package.py
                ./tools/test_doeda_suffix_compare.py
                ./tools/test_doeda_suffix_corpora.py
                ./tools/test_doeda_suffix_performance.py
                ./tools/doeda_native_audit.py
                ./tools/doeda_native_preflight.py
                ./tools/doeda_native_implementation.py
                ./tools/doeda_native_regressions.py
                ./tools/doeda_native_diagnostics.py
                ./tools/doeda_native_runtime.py
                ./tools/doeda_native_package.py
                ./tools/doeda_native_compare.py
                ./tools/doeda_native_corpora.py
                ./tools/doeda_native_performance.py
                ./tools/test_doeda_native_audit.py
                ./tools/test_doeda_native_diagnostics.py
                ./tools/test_doeda_native_package.py
                ./tools/test_doeda_native_compare.py
                ./tools/test_doeda_native_corpora.py
                ./tools/test_doeda_native_performance.py
                ./tools/doeda_identity_audit.py
                ./tools/doeda_identity_implementation.py
                ./tools/doeda_identity_diagnostics.py
                ./tools/doeda_identity_runtime.py
                ./tools/doeda_identity_package.py
                ./tools/doeda_identity_observations.py
                ./tools/doeda_identity_corpora.py
                ./tools/doeda_identity_performance.py
                ./tools/test_doeda_identity_release.py
                ./tools/test_doeda_identity.py
                ./src/doeda_identity.rs
                ./src/doeda_originless_forms.rs
                ./tools/doeda_originless_audit.py
                ./tools/doeda_originless_implementation.py
                ./tools/doeda_originless_diagnostics.py
                ./tools/test_doeda_originless.py
                ./tools/doeda_originless_runtime.py
                ./tools/doeda_originless_package.py
                ./tools/doeda_originless_observations.py
                ./tools/doeda_originless_corpora.py
                ./tools/doeda_originless_performance.py
                ./tools/test_doeda_originless_release.py
                ./tools/doeda_partial_origins.py
                ./tools/well_doeda_audit.py
                ./tools/test_well_doeda_audit.py
                ./tools/well_doeda_broad.py
                ./tools/well_doeda_corpora.py
                ./tools/well_doeda_runtime.py
                ./tools/well_doeda_release.py
                ./tools/well_doeda_performance.py
                ./tools/test_well_doeda_release.py
                ./tools/nominal_si_audit.py
                ./tools/nominal_si_broad.py
                ./tools/nominal_si_corpora.py
                ./tools/nominal_si_runtime.py
                ./tools/test_nominal_si_audit.py
                ./tools/test_nominal_si_runtime.py
                ./tools/nominal_si_release.py
                ./tools/nominal_si_performance.py
                ./tools/test_nominal_si_release.py
                ./tools/nominal_hwa_audit.py
                ./tools/test_nominal_hwa_audit.py
                ./tools/nominal_hwa_broad.py
                ./tools/nominal_hwa_corpora.py
                ./tools/nominal_hwa_runtime.py
                ./tools/test_nominal_hwa_runtime.py
                ./tools/nominal_hwa_release.py
                ./tools/nominal_hwa_performance.py
                ./tools/test_nominal_hwa_release.py
                ./tools/nominal_hwa_hada_release.py
                ./tools/nominal_hwa_hada_performance.py
                ./tools/test_nominal_hwa_hada_release.py
                ./tools/nominal_hwa_hada_broad.py
                ./tools/nominal_hwa_hada_corpora.py
                ./tools/test_nominal_hwa_hada_corpora.py
                ./tools/nominal_hwa_hada_audit.py
                ./tools/test_nominal_hwa_hada_audit.py
                ./tools/nominal_hwa_hada_runtime.py
                ./tools/test_nominal_hwa_hada_runtime.py
                ./tools/nominal_si_hada_release.py
                ./tools/nominal_si_hada_performance.py
                ./tools/test_nominal_si_hada_release.py
                ./tools/hada_nominal_release.py
                ./tools/hada_nominal_performance.py
                ./tools/test_hada_nominal_release.py
                ./tools/hada_nominal_broad.py
                ./tools/hada_nominal_corpora.py
                ./tools/test_hada_nominal_release_audits.py
                ./tools/hada_nominal_runtime.py
                ./tools/test_hada_nominal_runtime.py
                ./web/tests/hada-nominal.mjs
                ./tools/hada_nominal_audit.py
                ./tools/test_hada_nominal_audit.py
                ./tools/hada_remaining_audit.py
                ./tools/test_hada_remaining_audit.py
                ./web/src/hada-sources.json
                ./tools/hada_remaining_context.py
                ./tools/hada_remaining_runtime.py
                ./tools/test_hada_remaining_runtime.py
                ./web/tests/hada-remaining.mjs
                ./web/tests/hada-remaining-scoped.mjs
                ./web/src/breakdown.ts
                ./tools/hada_remaining_scoped_runtime.py
                ./tools/test_hada_remaining_scoped_runtime.py
                ./tools/hada_remaining_broad.py
                ./tools/hada_remaining_corpora.py
                ./tools/test_hada_remaining_release_audits.py
                ./tools/hada_remaining_release.py
                ./tools/hada_remaining_performance.py
                ./tools/test_hada_remaining_release.py
                ./tools/ssik_audit.py
                ./tools/ssik_comparison.py
                ./tools/ssik_runtime.py
                ./tools/ssik_corpora.py
                ./tools/ssik_broad.py
                ./tools/ssik_morphology.py
                ./tools/ssik_release.py
                ./tools/ssik_performance.py
                ./tools/fresh_passage_audit.py
                ./web/tests/ssik.mjs
                ./tools/nominal_si_hada_audit.py
                ./tools/test_nominal_si_hada_audit.py
                ./tools/nominal_si_hada_runtime.py
                ./tools/test_nominal_si_hada_runtime.py
                ./tools/nominal_si_hada_broad.py
                ./tools/nominal_si_hada_corpora.py
                ./tools/test_nominal_si_hada_corpora.py
                ./web/tests/nominal-si-hada.mjs
                ./src/hada_suffix.rs
                ./web/tests/nominal-hwa-hada.mjs
                ./web/tests/nominal-hwa.mjs
                ./src/nominal_hwa.rs
                ./src/nominal_si.rs
                ./web/tests/nominal-si.mjs
                ./web/tests/well-doeda.mjs
                ./tools/doeda_partial_origin_diagnostics.py
                ./tools/test_doeda_partial_origins.py
                ./tools/test_doeda_partial_origin_diagnostics.py
                ./tools/doeda_partial_origin_runtime.py
                ./tools/doeda_partial_origin_package.py
                ./tools/doeda_partial_origin_observations.py
                ./tools/doeda_partial_origin_corpora.py
                ./tools/doeda_partial_origin_performance.py
                ./tools/test_doeda_partial_origin_release.py
                ./web/tests/doeda-originless.mjs
                ./web/tests/doeda-identity.mjs
                ./src/doeda_native_forms.rs
                ./web/tests/doeda-native.mjs
                ./web/tests/doeda-complement.mjs
                ./web/tests/doeda-suffix.mjs
                ./src/engine.rs ./src/grammar.rs
                ./web/tests/gam-question.mjs
                ./web/tests/emphatic-ending.mjs
                ./web/tests/doeda-role.mjs
                ./examples/audit_adjectival_allomorph.rs
                ./web/tests/adjectival-allomorph.mjs
                ./tools/adjectival_allomorph.rs
                ./tools/hada_nominal_preservation.rs
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
            python tools/gam_question_audit.py --verify
            python tools/gam_question_regressions.py --verify
            python tools/gam_question_compare.py --verify
            python tools/gam_question_corpora.py --verify
            python tools/gam_question_queue.py --verify
            python tools/gam_question_implementation.py --verify
            python tools/emphatic_ending_audit.py --verify
            python tools/emphatic_ending_regressions.py --verify
            python tools/emphatic_ending_corpora.py --verify
            python tools/emphatic_ending_diagnostics.py --verify
            python tools/emphatic_ending_compare.py --verify
            python tools/emphatic_ending_runtime.py --verify
            python tools/emphatic_ending_queue.py --verify
            python tools/doeda_role_audit.py --verify
            python tools/doeda_role_regressions.py --verify
            python tools/doeda_role_diagnostics.py --verify
            python tools/doeda_role_historical.py --verify
            python tools/doeda_role_stress.py --verify
            python tools/doeda_role_corpora.py --verify
            python tools/doeda_role_compare.py --verify
            python tools/doeda_role_runtime.py --verify
            python tools/doeda_role_browser.py --verify
            python tools/doeda_complement_audit.py --verify
            python tools/doeda_complement_regressions.py --verify
            python tools/doeda_complement_diagnostics.py --verify
            python tools/doeda_complement_package.py --verify
            python tools/doeda_complement_compare.py --verify
            python tools/doeda_complement_corpora.py --verify
            python -m unittest discover -s tools -p 'test_doeda_complement_corpora.py'
            python tools/doeda_noun_suffix_discovery.py --verify
            python tools/doeda_suffix_audit.py --verify
            python tools/doeda_suffix_regressions.py --verify
            python tools/doeda_suffix_diagnostics.py --verify
            python tools/doeda_suffix_package.py --verify
            python tools/doeda_suffix_compare.py --verify
            python tools/doeda_suffix_corpora.py --verify
            python tools/doeda_suffix_performance.py --verify
            python -m unittest discover -s tools -p 'test_doeda_suffix_*.py'
            python tools/doeda_native_audit.py --verify
            python tools/doeda_native_preflight.py --verify
            python tools/doeda_native_implementation.py --verify
            python tools/doeda_native_regressions.py --verify
            python tools/doeda_native_diagnostics.py --verify
            python tools/doeda_native_package.py --verify
            python tools/doeda_native_compare.py --verify
            python tools/doeda_native_corpora.py --verify
            python tools/doeda_native_performance.py --verify
            python -m unittest discover -s tools -p 'test_doeda_native_*.py'
            python tools/doeda_identity_audit.py --verify
            python tools/doeda_identity_implementation.py --verify
            python tools/doeda_identity_diagnostics.py --verify
            python -m unittest discover -s tools -p 'test_doeda_identity.py'
            python tools/doeda_identity_package.py --verify
            python tools/doeda_identity_observations.py --verify
            python tools/doeda_identity_corpora.py --verify
            python tools/doeda_identity_performance.py --verify
            python -m unittest discover -s tools -p 'test_doeda_identity_release.py'
            python tools/doeda_originless_audit.py --verify
            python tools/doeda_originless_implementation.py --verify
            python tools/doeda_originless_diagnostics.py --verify
            python -m unittest discover -s tools -p 'test_doeda_originless.py'
            python tools/doeda_originless_package.py --verify
            python tools/doeda_originless_observations.py --verify
            python tools/doeda_originless_corpora.py --verify
            python tools/doeda_originless_performance.py --verify
            python -m unittest discover -s tools -p 'test_doeda_originless_release.py'
            python tools/doeda_partial_origins.py --verify
            python tools/doeda_partial_origin_diagnostics.py --verify
            python -m unittest discover -s tools -p 'test_doeda_partial_origins.py'
            python -m unittest discover -s tools -p 'test_doeda_partial_origin_diagnostics.py'
            python tools/doeda_partial_origin_package.py --verify
            python tools/doeda_partial_origin_observations.py --verify
            python tools/doeda_partial_origin_corpora.py --verify
            python tools/doeda_partial_origin_performance.py --verify
            python -m unittest discover -s tools -p 'test_doeda_partial_origin_release.py'
            python tools/well_doeda_audit.py --verify
            python tools/well_doeda_audit.py --verify --comparison docs/well-doeda-diagnostics.json.gz
            python tools/well_doeda_broad.py --verify
            python tools/well_doeda_corpora.py --verify
            python tools/well_doeda_runtime.py --verify
            python -m unittest discover -s tools -p 'test_well_doeda_audit.py'
            python tools/well_doeda_release.py --verify
            python tools/well_doeda_broad.py --verify --report docs/well-doeda-packaged-observations.json.gz
            python tools/well_doeda_corpora.py --verify --report docs/well-doeda-packaged-corpora.json.gz
            python tools/well_doeda_performance.py --verify
            python -m unittest discover -s tools -p 'test_well_doeda_release.py'
            python tools/nominal_si_audit.py --verify --comparison docs/nominal-si-diagnostics.json.gz
            python tools/nominal_si_broad.py --verify
            python tools/nominal_si_corpora.py --verify
            python tools/nominal_si_runtime.py --verify
            python -m unittest discover -s tools -p 'test_nominal_si_audit.py'
            python -m unittest discover -s tools -p 'test_nominal_si_runtime.py'
            python tools/nominal_si_release.py --verify
            python tools/nominal_si_broad.py --verify --report docs/nominal-si-packaged-observations.json.gz
            python tools/nominal_si_corpora.py --verify --report docs/nominal-si-packaged-corpora.json.gz
            python tools/nominal_si_performance.py --verify
            python -m unittest discover -s tools -p 'test_nominal_si_release.py'
            python tools/nominal_hwa_audit.py --verify --comparison docs/nominal-hwa-diagnostics.json.gz
            python -m unittest discover -s tools -p 'test_nominal_hwa_audit.py'
            python tools/nominal_hwa_broad.py --verify
            python tools/nominal_hwa_corpora.py --verify
            python tools/nominal_hwa_runtime.py --verify
            python -m unittest discover -s tools -p 'test_nominal_hwa_runtime.py'
            python tools/nominal_hwa_release.py --verify
            python tools/nominal_hwa_broad.py --verify --report docs/nominal-hwa-packaged-observations.json.gz
            python tools/nominal_hwa_corpora.py --verify --report docs/nominal-hwa-packaged-corpora.json.gz
            python tools/nominal_hwa_performance.py --verify
            python -m unittest discover -s tools -p 'test_nominal_hwa_release.py'
            python tools/nominal_hwa_hada_audit.py --verify --comparison docs/nominal-hwa-hada-diagnostics.json.gz
            python -m unittest discover -s tools -p 'test_nominal_hwa_hada_audit.py'
            python tools/nominal_hwa_hada_runtime.py --verify
            python -m unittest discover -s tools -p 'test_nominal_hwa_hada_runtime.py'
            python tools/nominal_hwa_hada_broad.py --verify
            python tools/nominal_hwa_hada_corpora.py --verify
            python -m unittest discover -s tools -p 'test_nominal_hwa_hada_corpora.py'
            python tools/nominal_hwa_hada_release.py --verify
            python tools/nominal_hwa_hada_broad.py --verify --report docs/nominal-hwa-hada-packaged-observations.json.gz
            python tools/nominal_hwa_hada_corpora.py --verify --report docs/nominal-hwa-hada-packaged-corpora.json.gz
            python tools/nominal_hwa_hada_performance.py --verify
            python -m unittest discover -s tools -p 'test_nominal_hwa_hada_release.py'
            python tools/nominal_si_hada_audit.py --verify --comparison docs/nominal-si-hada-diagnostics.json.gz
            python tools/hada_nominal_audit.py --verify
            python -m unittest discover -s tools -p 'test_hada_nominal_audit.py'
            python tools/hada_remaining_audit.py --verify
            python -m unittest discover -s tools -p 'test_hada_remaining_audit.py'
            python tools/hada_remaining_context.py --verify
            python tools/hada_remaining_runtime.py --verify
            python tools/hada_remaining_scoped_runtime.py --verify
            python -m unittest discover -s tools -p 'test_hada_remaining_scoped_runtime.py'
            python -m unittest discover -s tools -p 'test_hada_remaining_runtime.py'
            python tools/hada_remaining_broad.py --verify
            python tools/hada_remaining_corpora.py --verify
            python -m unittest discover -s tools -p 'test_hada_remaining_release_audits.py'
            python tools/hada_remaining_release.py --verify
            python tools/hada_remaining_broad.py --verify --report docs/hada-remaining-packaged-observations.json.gz
            python tools/hada_remaining_corpora.py --verify --report docs/hada-remaining-packaged-corpora.json.gz
            python tools/hada_remaining_performance.py --verify
            python -m unittest discover -s tools -p 'test_hada_remaining_release.py'
            python tools/hada_nominal_runtime.py --verify
            python -m unittest discover -s tools -p 'test_hada_nominal_runtime.py'
            python tools/hada_nominal_broad.py --verify
            python tools/hada_nominal_corpora.py --verify
            python -m unittest discover -s tools -p 'test_hada_nominal_release_audits.py'
            python tools/hada_nominal_release.py --verify
            python tools/hada_nominal_broad.py --verify --report docs/hada-nominal-packaged-observations.json.gz
            python tools/hada_nominal_corpora.py --verify --report docs/hada-nominal-packaged-corpora.json.gz
            python tools/hada_nominal_performance.py --verify
            python -m unittest discover -s tools -p 'test_hada_nominal_release.py'
            python -m unittest discover -s tools -p 'test_nominal_si_hada_audit.py'
            python tools/nominal_si_hada_runtime.py --verify
            python -m unittest discover -s tools -p 'test_nominal_si_hada_runtime.py'
            python tools/nominal_si_hada_broad.py --verify
            python tools/nominal_si_hada_corpora.py --verify
            python -m unittest discover -s tools -p 'test_nominal_si_hada_corpora.py'
            python tools/nominal_si_hada_release.py --verify
            python tools/nominal_si_hada_broad.py --verify --report docs/nominal-si-hada-packaged-observations.json.gz
            python tools/nominal_si_hada_corpora.py --verify --report docs/nominal-si-hada-packaged-corpora.json.gz
            python tools/nominal_si_hada_performance.py --verify
            python -m unittest discover -s tools -p 'test_nominal_si_hada_release.py'
            python tools/future_question_additional.py --verify
            python tools/future_question_queue.py --verify
            python tools/caution_ending_queue.py --verify
            python tools/review_inventory.py --verify
            python tools/ssik_audit.py
            python tools/ssik_comparison.py
            python tools/ssik_runtime.py
            python tools/ssik_corpora.py --verify
            python tools/ssik_broad.py --verify
            python tools/ssik_morphology.py
            python tools/ssik_broad.py --verify --report docs/ssik-packaged-observations.json.gz
            python tools/ssik_corpora.py --verify --report docs/ssik-packaged-corpora.json.gz
            python tools/ssik_release.py --verify
            python tools/ssik_performance.py --verify
            python tools/fresh_passage_audit.py
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
