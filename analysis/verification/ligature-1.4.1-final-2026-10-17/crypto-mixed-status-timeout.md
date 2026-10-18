# crypto-mixed status timeout

With the final installed Ligature 1.4.1 binary (`sha256:973b883b3f4d19e60950ce6b9f0247828459d60fadd05f0d6e29d17d19c31ab8`), `python3 -I tools/ligature/ligature.pyz --workspace <crypto-mixed> status --json` did not complete within 180 seconds. The same pilot passed `sha256sum -c`, `version --verify`, sanctioned migration, and `doctor`; its installation manifest and all 18 managed-resource hashes match. The timeout is an observed command-performance limitation, not an installation or adjudicator-pin failure.
