#!/usr/bin/env bash
# Build the pinned abseil-cpp upstream and capture its CTest results.
#
# Reproduces the configure/build/test invocation upstream uses in its own CMake
# CI (ci/linux_gcc-latest_libstdcxx_cmake.sh), pinned to a release GoogleTest
# tarball so a re-run cannot silently pick up a different googletest.
#
# Run from the pilot root, inside the pilot Nix shell:
#   nix develop <workspace>/#swisstable-verus -c bash analysis/upstream/build-upstream.sh
set -euo pipefail

# `nix develop` puts its scratch dir under $TMPDIR, and the nix cc-wrapper
# (clang-wrapper/gcc-wrapper) refers to a generated response file by an absolute
# @path into that dir. If $TMPDIR disappears while a long build is still running
# (e.g. a sandbox that cleans up per-command temp dirs), every later compile
# dies with:
#   clang++: error: no such file or directory: '@.../cc-params.XXXXXX'
# Give nix develop a TMPDIR that outlives the build.
export TMPDIR="${NIX_BUILD_TMPDIR:-/tmp/opencode/nix-shell-tmp}"
mkdir -p "${TMPDIR}"

BUILD_DIR="${BUILD_DIR:-/tmp/opencode/swisstable-verus-abseil-build}"
BUILD_TYPE="${BUILD_TYPE:-Debug}"
CXX_STANDARD="${CXX_STANDARD:-17}"
JOBS="${JOBS:-$(nproc)}"

# Keep in sync with ci/cmake_common.sh in the pinned upstream checkout.
ABSL_GOOGLETEST_VERSION="1.17.0"
ABSL_GOOGLETEST_DOWNLOAD_URL="https://github.com/google/googletest/releases/download/v${ABSL_GOOGLETEST_VERSION}/googletest-${ABSL_GOOGLETEST_VERSION}.tar.gz"

SRC_DIR="upstream/abseil-cpp"
if [ ! -d "${SRC_DIR}" ]; then echo "missing ${SRC_DIR}" >&2; exit 2; fi

GENERATOR=()
if command -v ninja >/dev/null 2>&1; then GENERATOR=(-G Ninja); fi

echo "== configure =="
cmake "${GENERATOR[@]}" -S "${SRC_DIR}" -B "${BUILD_DIR}" \
  -DABSL_GOOGLETEST_DOWNLOAD_URL="${ABSL_GOOGLETEST_DOWNLOAD_URL}" \
  -DABSL_BUILD_TESTING=ON \
  -DBUILD_SHARED_LIBS=OFF \
  -DCMAKE_BUILD_TYPE="${BUILD_TYPE}" \
  -DCMAKE_CXX_STANDARD="${CXX_STANDARD}"

echo "== build =="
cmake --build "${BUILD_DIR}" -j "${JOBS}"

echo "== ctest =="
# Upstream CI exports TZDIR for the cctz zoneinfo test; mirror that.
TZDIR="$(cd "${SRC_DIR}" && pwd)/absl/time/internal/cctz/testdata/zoneinfo" \
  ctest --test-dir "${BUILD_DIR}" -j "${JOBS}" --output-on-failure
