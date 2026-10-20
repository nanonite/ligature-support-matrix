#!/usr/bin/env bash
# Build the pinned Botan subset and the oracle driver outside the pilot root.
#
# Run from the crypto-mixed pilot root inside the flake shell:
#   nix develop path:/home/goya/storage/full-ligature-port-workspace#crypto-mixed -c oracle/build_upstream.sh
#
# Botan 3.13.0 ships configure.py, not CMake, so the library is a minimized
# static build of exactly the modules the port covers (scalar providers only;
# --minimized-build skips the auto-loaded SIMD providers). The driver itself is
# built with CMake against that library. Nothing is written into upstream/.
set -euo pipefail

pilot_root="$(cd "$(dirname "$0")/.." && pwd)"
build_root="${CRYPTO_MIXED_ORACLE_BUILD:-/tmp/crypto-mixed-oracle-build}"
botan_build="$build_root/botan"
driver_build="$build_root/driver"
expected_commit="2a81eef56c96c237e590c27f9a75e60317c9c700"

actual_commit="$(git -C "$pilot_root/upstream/botan" rev-parse HEAD)"
if [ "$actual_commit" != "$expected_commit" ]; then
  echo "upstream/botan is at $actual_commit, expected $expected_commit" >&2
  exit 1
fi
if [ -n "$(git -C "$pilot_root/upstream/botan" status --porcelain)" ]; then
  echo "upstream/botan has local modifications" >&2
  exit 1
fi

mkdir -p "$build_root"
(
  cd "$pilot_root/upstream/botan"
  python3 configure.py \
    --minimized-build \
    --enable-modules=chacha20poly1305,chacha,poly1305 \
    --disable-shared-library \
    --without-documentation \
    --cc=clang \
    --cc-bin="${CXX:-clang++}" \
    --with-build-dir="$botan_build"
  # The generated Makefile names sources relative to the checkout.
  make -f "$botan_build/Makefile" -j"$(nproc)" libs
)

cmake -S "$pilot_root/oracle" -B "$driver_build" \
  -DCMAKE_BUILD_TYPE=Release \
  -DBOTAN_BUILD_DIR="$botan_build"
cmake --build "$driver_build" --target oracle_driver -j"$(nproc)"

if [ -n "$(git -C "$pilot_root/upstream/botan" status --porcelain)" ]; then
  echo "the build modified upstream/botan" >&2
  exit 1
fi
echo "oracle driver: $driver_build/oracle_driver"
