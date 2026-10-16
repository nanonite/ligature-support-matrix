# Workspace-root Nix flake snapshot

The parent workspace (`/home/goya/storage/full-ligature-port-workspace`) is not a Git repository. This directory preserves the exact flake inputs used for the Date-Creusot verifier environment so the pilot repository can reproduce them. The flake and lock are byte-for-byte copies captured on 2026-10-16.

- `flake.nix` SHA-256: `7f631c89297f25fcbbef7e860d6c931539e7236142b5dba7cf148459e3d4ab07`
- `flake.lock` SHA-256: `a1945f624d7bff521a1742b5cf85b0a94dd44989fcd4c23d29100340cbf45137`
- Creusot input revision: `553a8b732697ae8b8f2b66a64600b0d39e086f9f`
- Root nixpkgs input revision: `b77b3de8775677f84492abe84635f87b0e153f0f`

From the pilot repository root, enter the pinned shell with:

```sh
nix develop path:analysis/verification/workspace-root-flake#date-creusot
```

The snapshot is an input record, not a second edited flake. If the verifier environment changes, update the owning root flake first and then replace this documented snapshot through a reviewed change.
