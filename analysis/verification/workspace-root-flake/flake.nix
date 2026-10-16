{
  description = "ligature verifier development shells";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs?rev=b77b3de8775677f84492abe84635f87b0e153f0f";
    creusot.url = "github:creusot-rs/creusot?rev=553a8b732697ae8b8f2b66a64600b0d39e086f9f";
  };

  outputs =
    {
      self,
      nixpkgs,
      creusot,
    }:
    let
      systems = [ "x86_64-linux" ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
    in
    {
      devShells = forAllSystems (
        system:
        let
          pkgs = import nixpkgs {
            inherit system;
            config.allowUnfreePredicate = pkg: nixpkgs.lib.getName pkg == "alt-ergo";
          };

          verusVersion = "0.2026.05.24.ecee80a";
          verusZip = pkgs.fetchzip {
            url = "https://github.com/verus-lang/verus/releases/download/release/${verusVersion}/verus-${verusVersion}-x86-linux.zip";
            hash = "sha256-Gd9tG4zmCnJs0QOepx7Lg/dFYjTvYW3n9EZhpzhY10U=";
          };
          verus = pkgs.runCommand "verus-tools" { nativeBuildInputs = [ pkgs.makeWrapper ]; } ''
            mkdir -p $out/bin
            makeWrapper ${verusZip}/verus $out/bin/verus \
              --prefix PATH : ${pkgs.lib.makeBinPath [ pkgs.rustup ]}
            makeWrapper ${verusZip}/cargo-verus $out/bin/cargo-verus \
              --prefix PATH : ${pkgs.lib.makeBinPath [ pkgs.rustup ]}
          '';

          python = pkgs.python3.withPackages (ps: [
            ps.jsonschema
            ps.pyyaml
          ]);

          commonPackages = with pkgs; [
            cargo-nextest
            cargo-llvm-cov
            git
            graphviz
            pkg-config
            rustup
            python
            cmake
            gcc
            clang
            gdb
            lldb
            uv
          ];

          kaniShellHook = ''
            export CARGO_HOME="''${CARGO_HOME:-$HOME/.cargo}"
            export KANI_HOME="''${KANI_HOME:-''${XDG_CACHE_HOME:-$HOME/.cache}/kani}"
            export PATH="$CARGO_HOME/bin:$PATH"

            rustup toolchain install 1.95.0 --profile minimal --component clippy --component rustfmt
            rustup toolchain install nightly-2026-04-21 --profile minimal --component rust-src

            if ! command -v cargo-kani >/dev/null 2>&1; then
              cargo install --locked kani-verifier
            fi

            if command -v cargo-kani >/dev/null 2>&1 && ! find "$KANI_HOME" -maxdepth 3 -path "$KANI_HOME/kani-*/bin/kani-compiler" -type f -print -quit 2>/dev/null | grep -q .; then
              cargo kani setup
            fi
          '';

          rdbShellHook = ''
            if [ -x "$HOME/.cargo/bin/rdb" ]; then
              export PATH="$HOME/.cargo/bin:$PATH"
            else
              echo "warning: ~/.cargo/bin/rdb is missing; rdb is not on PATH" >&2
            fi
          '';

          # Chainlink #714: creusot's "free" variant bundles alt-ergo-free 2.4.3.
          # Its --version output ("2.4.3-free", no leading 'v') is rejected by
          # creusot-setup's detect_altergo_version → strip_prefix("v") check
          # (creusot-setup/src/tools.rs). Replace it with our project nixpkgs
          # alt-ergo 2.6.x whose --version starts with "v".
          creusotPackage = pkgs.symlinkJoin {
            name = "creusot-wrapped";
            paths = [ creusot.packages.${system}.free ];
            nativeBuildInputs = [ pkgs.makeWrapper ];
            postBuild = ''
              rm $out/bin/alt-ergo
              ln -s ${pkgs.alt-ergo}/bin/alt-ergo $out/bin/alt-ergo

              # Re-wrap so CREUSOT_DATA_HOME points to this patched derivation;
              # otherwise paths.bin() still resolves to the unpatched store path.
              rm $out/bin/cargo-creusot
              makeWrapper $out/bin/.cargo-creusot-wrapped_ $out/bin/cargo-creusot \
                --set CREUSOT_DATA_HOME "$out"
            '';
          };

          proverPackages =
            with pkgs;
            [
              why3
              z3
              cvc5
            ]
            ++ pkgs.lib.optionals (builtins.hasAttr "alt-ergo" pkgs) [ pkgs.alt-ergo ];
        in
        {
          date-creusot = pkgs.mkShell {
            packages = commonPackages ++ [ creusotPackage ] ++ proverPackages;
            shellHook =
              rdbShellHook
              + kaniShellHook
              + ''
                echo "date-creusot: Creusot, Why3, Z3, cvc5, Alt-Ergo, Kani, and Rust"
              '';
          };

          swisstable-verus = pkgs.mkShell {
            packages = commonPackages ++ [
              verus
              pkgs.z3
            ];
            shellHook =
              rdbShellHook
              + kaniShellHook
              + ''
                rustup component add miri --toolchain nightly-2026-04-21
                echo "swisstable-verus: Verus, Z3, Kani, Miri, and Rust"
              '';
          };

          crypto-mixed = pkgs.mkShell {
            packages =
              commonPackages
              ++ [
                creusotPackage
                verus
              ]
              ++ proverPackages;
            shellHook =
              rdbShellHook
              + kaniShellHook
              + ''
                echo "crypto-mixed: Creusot, Verus, Why3, Z3, cvc5, Alt-Ergo, Kani, and Rust"
              '';
          };

          default = pkgs.mkShell {
            packages =
              commonPackages
              ++ [
                creusotPackage
                verus
              ]
              ++ proverPackages;
            shellHook =
              rdbShellHook
              + kaniShellHook
              + ''
                rustup component add miri --toolchain nightly-2026-04-21
                echo "default: Creusot, Verus, Why3, Z3, cvc5, Alt-Ergo, Kani, Miri, and Rust"
              '';
          };
        }
      );

      formatter = forAllSystems (
        system:
        let
          pkgs = import nixpkgs { inherit system; };
        in
        pkgs.nixfmt-rfc-style
      );
    };
}
