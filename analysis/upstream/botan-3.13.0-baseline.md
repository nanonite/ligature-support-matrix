# Botan 3.13.0 upstream baseline

Chainlink #41 pins the P3 upstream source and captures its native test baseline.

## Source pin

- Repository: [randombit/botan](https://github.com/randombit/botan)
- Release tag: `3.13.0`
- Commit: `2a81eef56c96c237e590c27f9a75e60317c9c700`
- Commit subject: `Update for 3.13.0 release`
- Checkout: `crypto-mixed/upstream/botan` (detached at the pinned release; clean)
- Machine-readable pin: [`../../upstream/upstream-pin.json`](../../upstream/upstream-pin.json)

## Build and tests

The issue text requests CMake, but this Botan release has no `CMakeLists.txt`.
Its upstream build guide documents `configure.py`, which generates a Makefile;
the upstream native path was used instead.

Environment: Linux x86_64, Python 3.12.3, GCC/G++ 13.3.0, GNU Make 4.3.
The generated build directory is outside the source checkout at
`/tmp/crypto-mixed-botan-3.13.0-build`.

Configure command (from `crypto-mixed/upstream/botan`):

```sh
python3 configure.py --with-build-dir=/tmp/crypto-mixed-botan-3.13.0-build
```

Build and full upstream test command (from the same directory):

```sh
LD_LIBRARY_PATH=/tmp/crypto-mixed-botan-3.13.0-build \
  make -f /tmp/crypto-mixed-botan-3.13.0-build/Makefile -j8 check
```

Successful output:

```text
ChaCha20Poly1305 ran 336450 tests in 295.37 msec all ok
Poly1305 ran 6624 tests in 2.86 msec all ok
ChaCha(20) ran 7560 tests in 4.78 msec all ok
FFI ChaCha20Poly1305 ran 64 tests in 0.30 msec all ok
Tests complete ran 4124473 tests in 35.37 sec all tests ok
```

The full successful pass list is in
[`botan-3.13.0-make-check-success.log`](botan-3.13.0-make-check-success.log).
The configure transcript is in
[`botan-3.13.0-configure.log`](botan-3.13.0-configure.log); the combined
attempt transcript, including the initial test-runner loader setup issue, is
[`botan-3.13.0-make-check.log`](botan-3.13.0-make-check.log). The successful
run used `LD_LIBRARY_PATH` to expose the out-of-tree Botan shared library to
the test runner. GCC emitted non-fatal `-Wstringop-overread` and
`-Wstringop-overflow` warnings in upstream test code; the build and full test
run completed successfully.

This is the upstream baseline only. No Rust port or Ligature project
initialization was performed for this issue.
