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
                ./examples
                ./tools/corpus.rs
                ./tools/validity.rs
                ./README.md
                ./LICENSE-MIT
                ./LICENSE-APACHE
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

      checks = forAllSystems (system: {
        inherit (self.packages.${system}) klem web-assets;
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
