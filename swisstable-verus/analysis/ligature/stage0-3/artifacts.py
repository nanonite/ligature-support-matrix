#!/usr/bin/env python3
"""Stage 0-3 artifact definitions and driver for chainlink #28 (p2-swisstable-verus).

One file is the single source of truth for every artifact drafted here: the
prompt variables fed to `ligature.pyz draft`, and the JSON-only response fed
back on stdin. Nothing is written into a protected path by this script --
every artifact reaches the filesystem only through `ligature.pyz draft`
(which stages `<target>.json.draft`) or, for Stage 0 evidence only,
`ligature.pyz promote-evidence`.

Run modes:

  --emit <dir>     write every `<kind>__<id>.json` body and `<kind>__<id>.cmd`
                   command line into <dir>, and run nothing. Auditable record
                   of exactly what was sent to the binary.
  --root <dir>     run the recorded command lines against that workspace root
                   and tee the combined transcript to <root>/<transcript>.

Constraint-id discipline: every `<Concept>.C<nnn>` referenced by a boundary
contract, an interaction's `reliances`, or a bridge's `callee_requirement` /
`bridge_logic.conclusion.obligation_id` is checked against the constraint ids
actually declared by CONCEPTS below, and the script refuses to emit anything if
one dangles. That is the check the operator has to repeat by eye, so it is
mechanised here rather than trusted.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys

PILOT = "swisstable-verus"
DESCRIPTOR_MODE = "port"
DESCRIPTOR_REPO = "https://github.com/abseil/abseil-cpp"
UPSTREAM_COMMIT = "2065f4ded0558c6f89fee67c8e5228feb4eb960e"
TARGET_TRIPLE = "x86_64-unknown-linux-gnu"
CRATE = "rust/swisstable-verus-core"
VERIFIER = "verus"

# Real digests of the pinned upstream files (sha256sum, tag 20260817.0).
HASH_RAW_HASH_SET_H = "sha256:811f35e12e768f3bc155ce919684d923e3d8995e87de74c21496305c0c586e2c"
HASH_RAW_HASH_SET_CC = "sha256:69db6b95c6f945ad001fd4d85672f08cb38a7f23c7cc8adf49fba90a407d369c"
HASH_CTRL_BYTES_H = "sha256:fd40300b487870c6bbff3e0fe2b8a61d526cb82bc0d5050fe464ea06b0c1a95d"
HASH_UPSTREAM_PIN = "sha256:c243a10dcd03f6fdf4b12d7020681004f4fd40acdf760e4778b29f1a463dbdf8"

NO_REENTRY = {"prior_artifact": "", "finding": ""}


def origin(symbol: str, path: str, content_hash: str, line_hint: str) -> dict:
    return {
        "repository": DESCRIPTOR_REPO,
        "commit": UPSTREAM_COMMIT,
        "symbol": symbol,
        "path": path,
        "content_hash": content_hash,
        "line_hint": line_hint,
    }


def evidence(eid, kind, claim, origin_, disposition, lifecycle, confidence="high"):
    return {
        "schema_version": "1.0",
        "id": eid,
        "kind": kind,
        "claim": claim,
        "origin": origin_,
        "semantic_disposition": disposition,
        "lifecycle": lifecycle,
        "confidence": confidence,
        # mode: port + the claim originates in the C++ source being ported -> P.
        "mode": "P" if DESCRIPTOR_MODE == "port" else "R",
    }


# --------------------------------------------------------------------------
# Stage 0 -- evidence records (workspace-level `evidence/`, promoted mechanically)
# --------------------------------------------------------------------------
EVIDENCE = [
    evidence(
        "E-001",
        "source-artifact",
        "The SwissTable slot index is taken from the low bits of the user hash (H1 is the "
        "identity) and the same hash's 7 most significant bits are stored in the full "
        "slot's control byte (H2 = hash >> (sizeof(size_t)*8 - 7)), so a port that "
        "changes the hash function must change both the probe start offset and the "
        "control-byte tag together.",
        origin("absl::container_internal::H1 / H2", "absl/container/internal/raw_hash_set.h",
               HASH_RAW_HASH_SET_H, "831-837"),
        "required", "accepted"),
    evidence(
        "E-002",
        "source-artifact",
        "A control byte is one of exactly four shapes -- empty (-128, high bit set), "
        "deleted (-2, high bit set), sentinel (-1, all bits set), or full (high bit "
        "clear, low 7 bits the slot's H2) -- and a byte counts as empty-or-deleted "
        "exactly when it compares less than the sentinel, which is the single test the "
        "probe, erase and iterator paths all share.",
        origin("absl::container_internal::ctrl_t / IsEmptyOrDeleted",
               "absl/container/internal/hashtable_control_bytes.h", HASH_CTRL_BYTES_H, "166-232"),
        "required", "accepted"),
    evidence(
        "E-003",
        "source-artifact",
        "The probe sequence is a quadratic triple-step recurrence, not a linear stride: "
        "next() adds Width to a running probe index and then adds that index to the "
        "offset before masking with capacity-1, so after k advances the offset is "
        "h1 + Width*k*(k+1)/2 masked by capacity-1.",
        origin("absl::container_internal::probe_seq::next",
               "absl/container/internal/raw_hash_set.h", HASH_RAW_HASH_SET_H, "1773-1797"),
        "required", "accepted"),
    evidence(
        "E-004",
        "source-artifact",
        "The insert-slot search stops at the first group containing any empty OR deleted "
        "byte, not the first empty byte, and upstream states in its own NOTE that this "
        "must keep working on tables holding both states at once -- which is the steady "
        "state after any erase.",
        origin("absl::container_internal::probe_till_first_non_full_group",
               "absl/container/internal/raw_hash_set.cc", HASH_RAW_HASH_SET_CC, "171-206"),
        "required", "accepted"),
    evidence(
        "E-005",
        "source-artifact",
        "Erasing a slot from a large table writes kDeleted when that slot was full at "
        "some point in the table's life and kEmpty when it has never been full, and the "
        "distinction is recorded in the growth-info word rather than inferred from the "
        "control byte -- so a port that always writes one of the two either leaks "
        "capacity or breaks probe chains.",
        origin("absl::container_internal::EraseMetaOnlyLarge",
               "absl/container/internal/raw_hash_set.cc", HASH_RAW_HASH_SET_CC, "868-885"),
        "required", "accepted"),
    evidence(
        "E-006",
        "source-artifact",
        "Rehash reclaims tombstones in one pass by rewriting every empty byte as empty "
        "and every full byte as deleted, then re-inserting; the sequence is an "
        "optimisation, not a correctness requirement, and a port that drops it only "
        "loses the reclaimed capacity.",
        origin("absl::container_internal::ConvertDeletedToEmptyAndFullToDeleted",
               "absl/container/internal/raw_hash_set.cc", HASH_RAW_HASH_SET_CC, "434-444"),
        "incidental", "accepted"),
    evidence(
        "E-007",
        "source-artifact",
        "Iteration walks the control array in ascending index, skipping empty and "
        "deleted bytes and stopping at the sentinel, so the order in which two live "
        "elements are enumerated is a function of their slot layout.",
        origin("absl::container_internal::raw_hash_set::iterator::operator++ / skip_empty_or_deleted",
               "absl/container/internal/raw_hash_set.h", HASH_RAW_HASH_SET_H, "2399-2456"),
        "incidental", "accepted"),
    evidence(
        "E-008",
        "comment",
        "The per-table hash seed exists precisely to randomise iteration order -- its "
        "own documentation says it is mixed into H1 to randomise iteration order per "
        "table and is needed to ensure non-determinism of that order -- so no iteration "
        "order is an observable property of the map.",
        origin("absl::container_internal::PerTableSeed (class documentation)",
               "absl/container/internal/raw_hash_set.h", HASH_RAW_HASH_SET_H, "597-599"),
        "required", "accepted"),
    evidence(
        "E-009",
        "source-artifact",
        "Every rehash calls generate_new_seed on the table's common fields before "
        "re-inserting the surviving elements, so the salt that E-008 relies on to "
        "randomise iteration order changes on every resize as well as at construction.",
        origin("absl::container_internal::ResizeAllocatedTableWithSeedChange",
               "absl/container/internal/raw_hash_set.cc", HASH_RAW_HASH_SET_CC, "2104-2133"),
        "required", "accepted"),
    evidence(
        "E-010",
        "source-artifact",
        "The SIMD group is a separate implementation selected at compile time "
        "(GroupSse2Impl under ABSL_INTERNAL_HAVE_SSE2, with a portable Group "
        "otherwise) that computes the same full/empty-or-deleted masks as 128-bit "
        "lane compares; whether that half is ported, scope-cut, or given to a second "
        "verifier is chainlink #36's open decision, not this record's.",
        origin("absl::container_internal::GroupSse2Impl",
               "absl/container/internal/hashtable_control_bytes.h", HASH_CTRL_BYTES_H, "277-330"),
        "incidental", "deferred"),
    evidence(
        "E-011",
        "requirement",
        "The differential oracle cannot compare hash values across languages, so both "
        "sides must be driven with one injected hash function; until chainlink #37 "
        "builds that shared driver no oracle case may assert on a hash-derived value.",
        origin("plan.md P2 subset, 'Hash values are not comparable across languages'",
               "upstream/upstream-pin.json", HASH_UPSTREAM_PIN, "1-45"),
        "required", "deferred"),
]

# --------------------------------------------------------------------------
# Stage 3 -- concept specs (`<crate>/specs/<snake>.json.draft`)
# --------------------------------------------------------------------------
def q(english, sig, witness=False):
    return {"english": english, "rust_sig": sig, "pure": True, "witness_required": witness}


def cmd(english, sig):
    return {"english": english, "rust_sig": sig}


def con(cid, english, logic, kind, applies_to):
    return {"english": english, "logic": logic, "kind": kind, "source": "hand",
            "applies_to": applies_to, "id": cid}


def adv(scenario, violates, resolution):
    return {"scenario": scenario, "violates": violates, "resolution": resolution}


def ref(kind, path, notes=""):
    r = {"kind": kind, "citation_or_path": path}
    if notes:
        r["notes"] = notes
    return r


CONCEPTS = {
    "HashMix": {
        "cluster": "hashing",
        "source_material": "raw_hash_set.h:831-837 (H1, H2) and raw_hash_set.h:597-599 (PerTableSeed)",
        "spec": {
            "schema_version": "1.0",
            "concept": "HashMix",
            "kind": "struct",
            "cluster": "hashing",
            "english_description": "A 64-bit user hash value split into the probe offset and the seven-bit control-byte tag that identify one slot.",
            "verifier": VERIFIER,
            "queries": [
                q("give the probe start offset", "fn h1(&self) -> u64"),
                q("give the seven-bit control byte tag", "fn h2(&self) -> u8", witness=True),
            ],
            "commands": [
                cmd("take the hash value to split", "fn from_hash(&mut self, hash: u64)"),
            ],
            "constraints": [
                con("C001", "A query is observed only after from_hash has supplied a hash.",
                    "self.supplied", "precondition", ["h1", "h2"]),
                con("C002", "h1 is the supplied hash unchanged.",
                    "self.hash == self.supplied_hash", "postcondition", ["h1"]),
                con("C003", "h2 is the seven most significant bits of the supplied hash.",
                    "self.h2 as u64 == self.supplied_hash >> 57", "postcondition", ["h2"]),
                con("C004", "No query observes any field other than the supplied hash.",
                    "self.hash == self.supplied_hash", "invariant", ["h1", "h2"]),
            ],
            "adversary_table": [
                adv("a hash whose seven most significant bits are all zero, so h2 is 0 and a full slot's control byte reads as 0",
                    "C003", "preserve reference behaviour: 0 is a legal h2 and a legal control byte"),
                adv("two distinct hashes that agree on the top seven bits but differ below",
                    "C003", "preserve reference behaviour: they collide in the group mask exactly as upstream does"),
            ],
            "source_references": [
                ref("reference-implementation", "absl/container/internal/raw_hash_set.h", "H1 and H2"),
                ref("reference-implementation", "absl/container/internal/raw_hash_set.h", "PerTableSeed is mixed into H1 upstream and is out of this concept"),
            ],
        },
    },
    "ControlBytes": {
        "cluster": "control-bytes",
        "source_material": "hashtable_control_bytes.h:166-232 (ctrl_t encoding, IsEmpty/IsDeleted/IsEmptyOrDeleted)",
        "spec": {
            "schema_version": "1.0",
            "concept": "ControlBytes",
            "kind": "struct",
            "cluster": "control-bytes",
            "english_description": "The array of one control byte per slot recording empty, deleted, sentinel, or full-with-tag, and the tests and writes over it.",
            "verifier": VERIFIER,
            "queries": [
                q("tell whether this slot is empty", "fn is_empty(&self, slot: usize) -> bool"),
                q("tell whether this slot is deleted", "fn is_dead(&self, slot: usize) -> bool"),
                q("tell whether this slot is full", "fn is_full(&self, slot: usize) -> bool"),
                q("tell whether this slot is empty or deleted", "fn is_empty_or_deleted(&self, slot: usize) -> bool"),
                q("count the empty slots in this group", "fn count_empty(&self, base: usize) -> usize", witness=True),
            ],
            "commands": [
                cmd("mark the slot full with its tag", "fn set_full(&mut self, slot: usize, h2: u8)"),
                cmd("mark the slot deleted", "fn set_dead(&mut self, slot: usize)"),
                cmd("mark the slot empty", "fn set_empty(&mut self, slot: usize)"),
                cmd("reclaim every deleted slot as empty and every full slot as deleted", "fn clear_dead(&mut self)"),
            ],
            "constraints": [
                con("C001", "Every control byte holds one of empty, deleted, the sentinel, or a full byte whose low seven bits are its slot tag.",
                    "self.byte(slot) == EMPTY || self.byte(slot) == DELETED || self.byte(slot) == SENTINEL || self.byte(slot) >= 0",
                    "invariant", ["is_empty", "is_dead", "is_full", "is_empty_or_deleted"]),
                con("C002", "The byte at index capacity is the sentinel and no slot index equals capacity.",
                    "self.capacity < self.byte_len && self.byte(self.capacity) == SENTINEL",
                    "invariant", ["is_empty_or_deleted"]),
                con("C003", "A slot is marked deleted only while it is currently full.",
                    "self.is_full(slot)", "precondition", ["set_dead"]),
                con("C004", "After a slot is marked deleted it reads as empty or deleted and every other slot is unchanged.",
                    "self.is_empty_or_deleted(slot) && self.bytes_unchanged_except(slot)",
                    "postcondition", ["set_dead"]),
                con("C005", "Reclaiming deleted slots runs over a control array that ends in the sentinel.",
                    "self.byte(self.capacity) == SENTINEL", "precondition", ["clear_dead"]),
                con("C006", "Reclaiming deleted slots turns every full byte into a deleted byte, keeps every empty byte empty, and never turns a deleted byte into an empty one.",
                    "self.all_full_are_deleted() && self.all_empty_stay_empty() && !self.any_deleted_became_empty()",
                    "postcondition", ["clear_dead"]),
                con("C007", "The tag read back from a full slot is the tag that was written into it.",
                    "self.tag(slot) == self.written_tag(slot)", "invariant", ["is_full"]),
                con("C008", "After a slot is marked empty it reads as empty and every other slot is unchanged.",
                    "self.is_empty(slot) && self.bytes_unchanged_except(slot)",
                    "postcondition", ["set_empty"]),
            ],
            "adversary_table": [
                adv("marking a slot that is already deleted, as a double erase would",
                    "C003", "reject: the precondition is not established, so the call is not made"),
                adv("reclaiming deleted slots on a control array with no sentinel at index capacity",
                    "C005", "reject: the rehash precondition is not established"),
                adv("a slot whose tag byte is zero, which is a full slot and not an empty one",
                    "C001", "preserve reference behaviour: the high bit, not the value, distinguishes full from empty"),
            ],
            "source_references": [
                ref("reference-implementation", "absl/container/internal/hashtable_control_bytes.h", "ctrl_t encoding and the scalar predicates"),
            ],
        },
    },
    "ProbeSeq": {
        "cluster": "probing",
        "source_material": "raw_hash_set.h:1773-1797 (probe_seq), raw_hash_set.cc:1800-1810 (probe_h1 / probe)",
        "spec": {
            "schema_version": "1.0",
            "concept": "ProbeSeq",
            "kind": "struct",
            "cluster": "probing",
            "english_description": "The bounded triple-step probe sequence that walks a table from a start offset to every slot exactly once.",
            "verifier": VERIFIER,
            "queries": [
                q("give the current slot index", "fn offset(&self) -> usize"),
                q("give the zero-based probe index", "fn index(&self) -> usize"),
                q("give the slot index some steps ahead", "fn offset_at(&self, i: usize) -> usize"),
            ],
            "commands": [
                cmd("build a sequence from a capacity mask and a start hash",
                    "fn from_capacity_and_h1(&mut self, capacity_mask: usize, h1: u64)"),
                cmd("advance to the next probe position", "fn advance(&mut self)"),
            ],
            "constraints": [
                con("C001", "The capacity mask is two to the n minus one for at least four bits, "
                    "both when the sequence is built and whenever a slot offset is read from it.",
                    "self.capacity_mask + 1 == (1 << self.capacity_bits) && self.capacity_bits >= 4",
                    "precondition", ["from_capacity_and_h1", "offset", "offset_at"]),
                con("C002", "The current slot index is always strictly less than the capacity.",
                    "self.offset_ < self.capacity_mask + 1", "invariant", ["offset", "offset_at"]),
                con("C003", "The probe index is a multiple of the group width and never exceeds the capacity.",
                    "self.index_ % 16 == 0 && self.index_ <= self.capacity_mask + 1", "invariant", ["index"]),
                con("C004", "After advancing, the new slot index is the old one plus the new probe index, masked by the capacity.",
                    "self.offset_ == (self.prev_offset_ + self.index_) & self.capacity_mask",
                    "postcondition", ["advance"]),
            ],
            "adversary_table": [
                adv("a capacity that is not two to the n minus one, so the mask is not a whole number of slots",
                    "C001", "reject: no probe sequence is built for such a capacity"),
                adv("advancing on a table with no non-full slot left, which would wrap forever",
                    "C003", "reject: the caller's loop is required to establish a non-full slot exists"),
            ],
            "source_references": [
                ref("reference-implementation", "absl/container/internal/raw_hash_set.h", "probe_seq"),
            ],
        },
    },
    "GroupProbe": {
        "cluster": "probing",
        "source_material": "hashtable_control_bytes.h:277-330 (GroupSse2Impl mask queries) and the portable Group; raw_hash_set.cc:175-187",
        "spec": {
            "schema_version": "1.0",
            "concept": "GroupProbe",
            "kind": "struct",
            "cluster": "probing",
            "english_description": "A sixteen-slot window over a table's control bytes that answers which slots hold a tag, which are full, and which are free to reuse.",
            "verifier": VERIFIER,
            "queries": [
                q("give the slots of this group that are full with the given tag", "fn match_full(&self, h2: u8) -> u16", witness=True),
                q("give the slots of this group that are empty or deleted", "fn match_empty_or_deleted(&self) -> u16"),
                q("count the empty slots of this group", "fn count_empty(&self) -> usize"),
            ],
            "commands": [
                cmd("load the group from the control bytes at a slot index", "fn load(&mut self, slot: usize)"),
            ],
            "constraints": [
                con("C001", "A group's sixteen control bytes lie wholly inside the table's "
                    "control array: that window must be established when the group is "
                    "loaded and still hold whenever a mask is read from it.",
                    "self.base + 16 <= self.capacity", "precondition",
                    ["load", "match_full", "match_empty_or_deleted"]),
                con("C002", "Matching a tag sets a group's bit for a slot exactly when that slot is full and its tag is the given value.",
                    "self.bit_i_match(h2) == (self.ctrl(i) >= 0 && self.ctrl(i) as u8 == h2)",
                    "postcondition", ["match_full"]),
                con("C003", "The empty-or-deleted mask sets a group's bit for a slot exactly when that slot is empty or deleted.",
                    "self.bit_i_free() == (self.ctrl(i) == EMPTY || self.ctrl(i) == DELETED)",
                    "postcondition", ["match_empty_or_deleted"]),
                con("C004", "A group never covers the sentinel byte at index capacity.",
                    "self.base + 16 <= self.capacity", "invariant", ["load", "match_full", "match_empty_or_deleted"]),
                con("C005", "Every group's answer is a function of its own sixteen control bytes and of nothing else.",
                    "self.result_depends_only_on(self.ctrl_window)", "invariant", ["match_full", "match_empty_or_deleted", "count_empty"]),
            ],
            "adversary_table": [
                adv("a group whose window would include the sentinel at index capacity",
                    "C001", "reject: the group is not loaded"),
                adv("a table holding both deleted and empty slots in one group, the steady state after an erase",
                    "C003", "preserve reference behaviour: both states set the free bit"),
                adv("a small table whose capacity is below the group width, where the trailing control bytes are padding",
                    "C004", "reject: only the first capacity bytes after the sentinel are real slots"),
            ],
            "source_references": [
                ref("reference-implementation", "absl/container/internal/hashtable_control_bytes.h", "GroupSse2Impl; the portable Group computes the same masks"),
                ref("issue", "chainlink #36", "SIMD reach is this pilot's open decision, not this concept's"),
            ],
        },
    },
    "RawTable": {
        "cluster": "table",
        "source_material": "raw_hash_set.cc:171-235 (find_first_non_full), 868-885 (EraseMetaOnlyLarge), 2104-2133 (ResizeAllocatedTableWithSeedChange); raw_hash_set.h:825-838 (H1/H2)",
        "spec": {
            "schema_version": "1.0",
            "concept": "RawTable",
            "kind": "struct",
            "cluster": "table",
            "english_description": "The open-addressed slot array with its control bytes, holding the table's elements and serving lookup, insertion, erase and rehash.",
            "verifier": VERIFIER,
            "queries": [
                q("give the number of live elements", "fn len(&self) -> usize"),
                q("give the number of slots", "fn capacity(&self) -> usize"),
                q("tell whether the table has no free slot left", "fn is_full(&self) -> bool"),
            ],
            "commands": [
                cmd("find the slot holding a hash or report that it is absent", "fn find(&mut self, hash: u64) -> Option<usize>"),
                cmd("find or open a slot for a hash", "fn insert(&mut self, hash: u64) -> (usize, bool)"),
                cmd("erase the element in a slot", "fn erase(&mut self, slot: usize)"),
                cmd("rehash into a new capacity", "fn resize(&mut self, new_capacity: usize)"),
            ],
            "constraints": [
                con("C001", "The capacity is always two to the n minus one and the sentinel sits at index capacity.",
                    "self.capacity_ + 1 == (1 << self.capacity_bits) && self.ctrl(self.capacity_) == SENTINEL",
                    "invariant", ["capacity", "find", "insert", "erase", "resize"]),
                con("C002", "The number of live elements never exceeds the number of full control bytes.",
                    "self.len_ <= self.count_full_ctrl()", "invariant", ["len", "insert", "erase"]),
                con("C003", "Inserting is called only when the table has at least one empty or deleted slot.",
                    "self.count_empty_or_deleted() > 0", "precondition", ["insert"]),
                con("C004", "After a successful insertion the element count rises by one and the new slot reads as full.",
                    "self.len_ == self.prev_len_ + 1 && self.is_full_ctrl(self.inserted_slot)",
                    "postcondition", ["insert"]),
                con("C005", "After an erase the element count falls by one and the erased slot reads as empty or deleted.",
                    "self.len_ == self.prev_len_ - 1 && self.is_empty_or_deleted_ctrl(self.erased_slot)",
                    "postcondition", ["erase"]),
                con("C006", "A slot reported by a lookup is full and its tag is the top seven bits of the supplied hash.",
                    "self.is_full_ctrl(slot) && self.tag_ctrl(slot) == (hash >> 57) as u8",
                    "postcondition", ["find"]),
                con("C007", "A rehash keeps every live element and the multiset of stored hashes.",
                    "self.stored_hashes_after() == self.stored_hashes_before() && self.len_ == self.prev_len_",
                    "postcondition", ["resize"]),
            ],
            "adversary_table": [
                adv("looking up a hash whose key was erased, leaving only a tombstone",
                    "C006", "report absent, and do not read the tombstoned slot as an element"),
                adv("inserting into a table with no empty or deleted slot left",
                    "C003", "reject: the caller must resize first"),
                adv("rehashing while a slot marked deleted still holds a stale tag",
                    "C007", "preserve reference behaviour: the reclaimed capacity is reused, not leaked"),
            ],
            "source_references": [
                ref("reference-implementation", "absl/container/internal/raw_hash_set.cc", "find_first_non_full, EraseMetaOnlyLarge, ResizeAllocatedTableWithSeedChange"),
                ref("reference-implementation", "absl/container/internal/raw_hash_set.h", "CommonFields, capacity invariants"),
            ],
            "depends_on": [
                {"crate": "swisstable-verus-core", "concept": "ControlBytes",
                 "reason": "every slot-state test the table makes is a read of the control byte array, and the never-full flag erase needs is kept beside it"},
                {"crate": "swisstable-verus-core", "concept": "ProbeSeq",
                 "reason": "lookup and insertion walk the table through a probe sequence whose masking assumes this table's capacity shape"},
                {"crate": "swisstable-verus-core", "concept": "GroupProbe",
                 "reason": "the table reads sixteen control bytes at a time through a group, so every per-slot answer is only as good as the group's window"},
            ],
        },
    },
    "SwissTable": {
        "cluster": "api",
        "source_material": "raw_hash_set.h public surface (erase/insert/reserve/clear); raw_hash_set.h:597-599 on the per-table seed",
        "spec": {
            "schema_version": "1.0",
            "concept": "SwissTable",
            "kind": "struct",
            "cluster": "api",
            "english_description": "The key-value container users of the port call, mapping keys to values on top of the open-addressed table.",
            "verifier": VERIFIER,
            "queries": [
                q("give the number of live entries", "fn len(&self) -> usize"),
                q("tell whether a key is present", "fn contains(&self, key: &K) -> bool"),
            ],
            "commands": [
                cmd("insert or replace an entry", "fn insert(&mut self, key: K, value: V) -> bool"),
                cmd("remove an entry", "fn erase(&mut self, key: &K) -> bool"),
                cmd("reserve room for more entries", "fn reserve(&mut self, additional: usize)"),
                cmd("drop every entry", "fn clear(&mut self)"),
            ],
            "constraints": [
                con("C001", "The container's observable contents are exactly the live key-value pairs held in its table.",
                    "self.contents() == self.table_contents()", "invariant", ["len", "contains"]),
                con("C002", "A true insert return means the key was newly added and a false return means an existing key's value was replaced.",
                    "self.inserted_new == !self.replaced_existing", "postcondition", ["insert"]),
                con("C003", "A true erase return means the key was present and is now absent, and a false return means it was already absent.",
                    "self.erase_return == self.was_present && !self.contains_after()",
                    "postcondition", ["erase"]),
                con("C004", "Two containers holding the same key-value pairs enumerate them in no guaranteed order.",
                    "self.order_is_unspecified()", "invariant", ["len", "contains"]),
            ],
            "adversary_table": [
                adv("inserting a key that is already present with a different value",
                    "C002", "preserve reference behaviour: replace the value, keep the entry count, return false"),
                adv("erasing a key that was never present",
                    "C003", "return false and leave every other entry untouched"),
                adv("an oracle comparing two maps entry by entry in enumeration order",
                    "C004", "reject the comparison: compare contents, never order"),
            ],
            "source_references": [
                ref("reference-implementation", "absl/container/internal/raw_hash_set.h", "raw_hash_set public surface"),
                ref("reference-implementation", "absl/container/internal/raw_hash_set.h", "PerTableSeed exists to randomise iteration order"),
            ],
            "depends_on": [
                {"crate": "swisstable-verus-core", "concept": "RawTable",
                 "reason": "every observable operation of this container is a slot operation on the table below it"},
            ],
        },
    },
    "TableIterator": {
        "cluster": "iteration",
        "source_material": "raw_hash_set.h:2399-2456 (iterator::operator++, skip_empty_or_deleted) and 2395-2397 (operator* requires a full slot)",
        "spec": {
            "schema_version": "1.0",
            "concept": "TableIterator",
            "kind": "struct",
            "cluster": "iteration",
            "english_description": "A cursor over a table's slots that visits only full slots, in ascending control-array index, and stops at the sentinel.",
            "verifier": VERIFIER,
            "queries": [
                q("tell whether the cursor has run past the last element", "fn is_end(&self) -> bool"),
                q("give the control index the cursor rests on", "fn offset(&self) -> usize"),
            ],
            "commands": [
                cmd("advance to the next full slot or to the end", "fn advance(&mut self)"),
                cmd("move a default cursor onto the first full slot", "fn rewind_to_full(&mut self)"),
            ],
            "constraints": [
                con("C001", "A cursor that is not at the end never rests on an empty or deleted slot.",
                    "self.is_end() || self.ctrl(self.offset_) >= 0", "invariant", ["is_end", "offset"]),
                con("C002", "After advancing, the cursor rests on a full slot or reports the end.",
                    "self.is_end() || self.ctrl(self.offset_) >= 0", "postcondition", ["advance"]),
                con("C003", "The control index never passes the sentinel at index capacity.",
                    "self.offset_ <= self.capacity", "invariant", ["offset", "advance"]),
                con("C004", "The order in which a cursor visits elements follows slot layout and is not part of the container's contract.",
                    "self.order_is_unspecified()", "invariant", ["advance", "rewind_to_full"]),
            ],
            "adversary_table": [
                adv("advancing a cursor that already sits on a deleted slot, which a stale cursor would",
                    "C001", "reject: the cursor is repaired before use, never trusted where it is"),
                adv("a cursor stopped by the sentinel rather than by running off the control array",
                    "C003", "preserve reference behaviour: the sentinel byte is the stop condition"),
            ],
            "source_references": [
                ref("reference-implementation", "absl/container/internal/raw_hash_set.h", "iterator and skip_empty_or_deleted"),
            ],
            "depends_on": [
                {"crate": "swisstable-verus-core", "concept": "ControlBytes",
                 "reason": "the cursor decides where to stop purely by reading the control byte under it, so the stop condition is the byte encoding"},
            ],
        },
    },
}

# --------------------------------------------------------------------------
# Stage 3 -- interactions (`<crate>/specs/_interactions/<id>.json.draft`)
# --------------------------------------------------------------------------
def inter(iid, caller, callee, edge_class, rationale, obligation, evidence_links=None,
          requirement="required", claims=("postcondition-holds",), minimum_scope=None):
    derived = "boundary-required"
    if not ({"cross-verifier", "cross-crate-public-api", "stateful",
             "error-panic-boundary", "ownership-transfer", "numeric-domain-boundary"}
            & set(edge_class)):
        derived = "inform" if ({"pure-data-type-reference", "import-only"} & set(edge_class)) else "ignore"
    body = {
        "schema_version": "1.0",
        "interaction_id": iid,
        "caller": {"concept": caller[0], "method": caller[1]},
        "callee": {"concept": callee[0], "method": callee[1]},
        "edge_class": edge_class,
        # computed from edge_class by the template's own rule, never hand-picked
        "eligibility": derived,
        "rationale": rationale,
        "protocol_class": "pairwise",
        "realization": {
            "requirement": requirement,
            "config_scope": {"target": TARGET_TRIPLE, "features": ["default"], "cfg": []},
        },
    }
    if evidence_links:
        body["evidence_links"] = evidence_links
    if derived == "boundary-required":
        body["reliances"] = [{
            "obligation_id": obligation,
            "required_assurance": {
                "required_claims": list(claims),
                "accepted_evidence_kinds": ["verus-deductive-check"],
                "minimum_scope": minimum_scope or {"input_domain": "any capacity of the form two to the n minus one"},
                "trust_policy": {"assumptions_allowed": []},
            },
        }]
    return body


INTERACTIONS = [
    inter("raw_table_find_to_group_probe_match_full",
          ("RawTable", "find"), ("GroupProbe", "match_full"),
          ["stateful"],
          "The table's key-equality decision is only sound if the group reports a slot as full "
          "exactly when that slot's own control byte is full with the tag derived from the hash "
          "the table passed in.",
          "GroupProbe.C002", ["E-001", "E-002"]),
    inter("raw_table_find_to_group_probe_match_empty_or_deleted",
          ("RawTable", "find"), ("GroupProbe", "match_empty_or_deleted"),
          ["stateful"],
          "Insert-slot search must stop at the first group holding any deleted byte as well as "
          "any empty one, or the table stops reusing capacity and, worse, never terminates its "
          "probe on a table that has only tombstones left.",
          "GroupProbe.C003", ["E-004"]),
    inter("raw_table_find_to_probe_seq_offset",
          ("RawTable", "find"), ("ProbeSeq", "offset"),
          ["numeric-domain-boundary"],
          "The probe start offset is the hash masked by the table's capacity; if the callee is "
          "handed a capacity that is not two to the n minus one the mask stops being a whole "
          "number of slots and every later read leaves the control array.",
          "ProbeSeq.C002", ["E-001", "E-003"]),
    inter("raw_table_find_to_probe_seq_advance",
          ("RawTable", "find"), ("ProbeSeq", "advance"),
          ["numeric-domain-boundary"],
          "The lookup loop's only termination argument is that the running probe index stays "
          "within the capacity, which is a property of the recurrence the callee owns rather "
          "than of anything the caller checks.",
          "ProbeSeq.C004", ["E-003"]),
    inter("raw_table_find_to_control_bytes_is_empty_or_deleted",
          ("RawTable", "find"), ("ControlBytes", "is_empty_or_deleted"),
          ["stateful"],
          "The fast path of the probe loop decides the whole lookup on one byte test, and that "
          "test has to mean exactly 'this slot is free to reuse', which is the byte encoding's "
          "own definition and not the caller's.",
          "ControlBytes.C001", ["E-002"]),
    inter("raw_table_find_to_hash_mix_h2",
          ("RawTable", "find"), ("HashMix", "h2"),
          ["pure-data-type-reference"],
          "The seven-bit tag the table stores alongside a full slot is whatever the mixer "
          "returns for the hash it was handed; the table stores and compares the value rather "
          "than depending on how it was produced.",
          None, ["E-001"]),
    inter("raw_table_erase_to_control_bytes_set_dead",
          ("RawTable", "erase"), ("ControlBytes", "set_dead"),
          ["stateful"],
          "Marking a slot deleted is only safe on a slot that is currently full: doing it on an "
          "already-deleted byte is what breaks a probe chain, and the byte array is what "
          "decides which of the two the caller is looking at.",
          "ControlBytes.C004", ["E-002", "E-005"]),
    inter("raw_table_erase_to_control_bytes_set_empty",
          ("RawTable", "erase"), ("ControlBytes", "set_empty"),
          ["stateful"],
          "Erasing a slot that was never full reclaims it as empty rather than leaving a "
          "tombstone; choosing wrongly in either direction either leaks capacity or breaks the "
          "probe chain, and the distinction is the control byte's own state.",
          "ControlBytes.C008", ["E-005"]),
    inter("raw_table_resize_to_control_bytes_clear_dead",
          ("RawTable", "resize"), ("ControlBytes", "clear_dead"),
          ["stateful"],
          "Reclaim-on-rehash rewrites the whole control array in one pass, turning full bytes "
          "into deleted ones and leaving empty bytes empty; the table's capacity accounting "
          "depends on that exact rewrite and nothing else.",
          "ControlBytes.C006", ["E-006"],
          claims=("callee-precondition-established",)),
    inter("raw_table_resize_to_probe_seq_offset",
          ("RawTable", "resize"), ("ProbeSeq", "offset"),
          ["numeric-domain-boundary"],
          "Re-insertion probes with the NEW capacity's mask while carrying an offset read from "
          "the OLD table, so the caller must not reuse a stale offset as a probe position.",
          "ProbeSeq.C002", ["E-003"],
          claims=("callee-precondition-established",)),
    inter("swiss_table_insert_to_raw_table_insert",
          ("SwissTable", "insert"), ("RawTable", "insert"),
          ["stateful"],
          "The container reports 'newly added' versus 'replaced' from what the table returns, "
          "so the container's own observable postcondition rests on the table distinguishing "
          "those two cases.",
          "RawTable.C004", ["E-005"]),
    inter("swiss_table_erase_to_raw_table_erase",
          ("SwissTable", "erase"), ("RawTable", "erase"),
          ["stateful"],
          "The container's erase return value is exactly the table's pre-erase occupancy test, "
          "so a stale tombstone that still answers 'present' would make erase report true for "
          "a key that is gone.",
          "RawTable.C005", ["E-005"]),
    inter("swiss_table_erase_to_control_bytes_set_dead",
          ("SwissTable", "erase"), ("ControlBytes", "set_dead"),
          ["stateful"],
          "The user-visible removal of a key bottoms out in writing one control byte, which is "
          "the only thing that stops a later lookup from finding the element again.",
          "ControlBytes.C004", ["E-002", "E-005"]),
    inter("table_iterator_advance_to_control_bytes_is_empty_or_deleted",
          ("TableIterator", "advance"), ("ControlBytes", "is_empty_or_deleted"),
          ["stateful"],
          "The cursor's step is defined by skipping bytes that are empty or deleted; it would "
          "stop on a tombstone, or run past the sentinel, if that byte test meant something "
          "other than it does.",
          "ControlBytes.C001", ["E-002", "E-007"]),
    inter("swiss_table_reserve_to_raw_table_resize",
          ("SwissTable", "reserve"), ("RawTable", "resize"),
          ["stateful"],
          "Reserve is only a promise about capacity, and it is kept by the table's own capacity "
          "invariant after a rehash rather than by anything the container records.",
          "RawTable.C001", ["E-006"],
          requirement="optional"),
]

# --------------------------------------------------------------------------
# Stage 3 -- boundary contracts (`<crate>/specs/_boundaries/<id>.json.draft`)
# --------------------------------------------------------------------------
def snake(pascal):
    out = []
    for i, ch in enumerate(pascal):
        if ch.isupper() and i > 0:
            out.append("_")
        out.append(ch.lower())
    return "".join(out)


# Interaction id -> the callee PRECONDITION constraint a bridge discharges at that call
# site. Each one names a `kind: precondition` constraint declared by the callee concept.
PRECONDITION_FOR = {
    "raw_table_find_to_group_probe_match_full": "GroupProbe.C001",
    "raw_table_find_to_group_probe_match_empty_or_deleted": "GroupProbe.C001",
    "raw_table_find_to_probe_seq_offset": "ProbeSeq.C001",
    "raw_table_erase_to_control_bytes_set_dead": "ControlBytes.C003",
    "raw_table_resize_to_control_bytes_clear_dead": "ControlBytes.C005",
    "swiss_table_insert_to_raw_table_insert": "RawTable.C003",
}

BOUNDARIES = []
for i in INTERACTIONS:
    if i["eligibility"] != "boundary-required":
        continue
    c, k = i["caller"], i["callee"]
    bid = f"{snake(c['concept'])}_{c['method']}__to__{snake(k['concept'])}_{k['method']}"
    guarantees = [i["reliances"][0]["obligation_id"]]
    # The boundary template says a callee PRECONDITION belongs in a bridge, not here;
    # the bridge template then requires callee_requirement to be one of this
    # boundary's own callee_guarantees. Both rules are satisfiable only by listing the
    # precondition alongside the postcondition, which is what `extra` below does for
    # the edges that have a bridge. Flagged for the operator in README.md.
    extra = PRECONDITION_FOR.get(i["interaction_id"])
    if extra and extra not in guarantees:
        guarantees.append(extra)
    BOUNDARIES.append({
        "schema_version": "1.0",
        "boundary_id": bid,
        "caller": {"concept": c["concept"], "method": c["method"]},
        "callee": {"concept": k["concept"], "method": k["method"]},
        "callee_guarantees": guarantees,
        "_interaction_id": i["interaction_id"],
    })

# --------------------------------------------------------------------------
# Stage 3 -- bridges (`<crate>/specs/_bridges/<id>.json.draft`)
# --------------------------------------------------------------------------
VERUS_ASSURANCE = [{"obligation_id": None}]


def bridge(bid, boundary_id, callee_requirement, facts, local_facts, target_expr,
           bindings, premises):
    body = {
        "schema_version": "1.0",
        "bridge_id": bid,
        "boundary_id": boundary_id,
        "callee_requirement": callee_requirement,
        "available_contract_facts": facts,
        "required_local_facts": local_facts,
        "target_expression": target_expr,
        "protocol_class": "pairwise",
        "bridge_logic": {
            "bindings": bindings,
            "premises": premises,
            "conclusion": {"obligation_id": callee_requirement},
        },
    }
    return body


BRIDGES = [
    bridge("BR-GROUPPROBE-WINDOW-001", "raw_table_find__to__group_probe_match_full",
           "GroupProbe.C001",
           [{"obligation_id": "RawTable.C001", "role": "invariant"},
            {"obligation_id": "RawTable.C004", "role": "caller-precondition"}],
           [{"fact_id": "group_base", "expression": "base"},
            {"fact_id": "group_width", "expression": "GROUP_WIDTH"}],
           "GroupProbe::load(base).match_full(h2)",
           {"self": "RawTable", "base": "usize", "h2": "u8", "GROUP_WIDTH": "usize"},
           ["self.capacity() == capacity_mask + 1",
            "base % GROUP_WIDTH == 0",
            "capacity_mask + 1 >= GROUP_WIDTH",
            "base + GROUP_WIDTH <= capacity_mask + 1"]),
    bridge("BR-GROUPPROBE-FREE-WINDOW-001", "raw_table_find__to__group_probe_match_empty_or_deleted",
           "GroupProbe.C001",
           [{"obligation_id": "RawTable.C001", "role": "invariant"},
            {"obligation_id": "RawTable.C004", "role": "caller-precondition"}],
           [{"fact_id": "group_base", "expression": "seq.offset()"},
            {"fact_id": "group_width", "expression": "GROUP_WIDTH"}],
           "GroupProbe::load(seq.offset()).match_empty_or_deleted()",
           {"self": "RawTable", "seq": "ProbeSeq", "GROUP_WIDTH": "usize"},
           ["self.capacity() == capacity_mask + 1",
            "self.capacity() >= GROUP_WIDTH",
            "seq.offset() + GROUP_WIDTH <= self.capacity()"]),
    bridge("BR-PROBESEQ-MASK-001", "raw_table_find__to__probe_seq_offset",
           "ProbeSeq.C001",
           [{"obligation_id": "RawTable.C001", "role": "invariant"},
            {"obligation_id": "RawTable.C004", "role": "caller-precondition"}],
           [{"fact_id": "capacity_bits", "expression": "self.capacity_bits()"},
            {"fact_id": "capacity_mask", "expression": "self.capacity_mask()"}],
           "ProbeSeq::from_capacity_and_h1(self.capacity_mask(), h1).offset()",
           {"self": "RawTable", "h1": "u64", "capacity_mask": "usize", "capacity_bits": "usize"},
           ["capacity_mask + 1 == (1usize << capacity_bits)",
            "capacity_bits >= 4",
            "self.capacity() == capacity_mask + 1"]),
    bridge("BR-CONTROLBYTES-SETDEAD-001", "raw_table_erase__to__control_bytes_set_dead",
           "ControlBytes.C003",
           [{"obligation_id": "RawTable.C006", "role": "prior-callee-postcondition"},
            {"obligation_id": "RawTable.C001", "role": "invariant"}],
           [{"fact_id": "slot", "expression": "slot"}],
           "ControlBytes::set_dead(slot)",
           {"self": "RawTable", "slot": "usize"},
           ["slot < self.capacity()",
            "self.is_full_ctrl(slot)"]),
    bridge("BR-CONTROLBYTES-CLEARDEAD-001", "raw_table_resize__to__control_bytes_clear_dead",
           "ControlBytes.C005",
           [{"obligation_id": "RawTable.C001", "role": "invariant"},
            {"obligation_id": "RawTable.C007", "role": "caller-precondition"}],
           [{"fact_id": "new_capacity", "expression": "new_capacity"}],
           "ControlBytes::clear_dead()",
           {"self": "RawTable", "new_capacity": "usize"},
           ["self.ctrl(self.capacity()) == SENTINEL",
            "new_capacity == (1usize << self.capacity_bits()) - 1",
            "self.capacity() == self.ctrl_len() - 1"]),
    bridge("BR-RAWINSERT-NONFULL-001", "swiss_table_insert__to__raw_table_insert",
           "RawTable.C003",
           [{"obligation_id": "RawTable.C001", "role": "invariant"},
            {"obligation_id": "RawTable.C004", "role": "prior-callee-postcondition"}],
           [{"fact_id": "free_slot_count", "expression": "self.count_empty_or_deleted()"}],
           "RawTable::insert(hash)",
           {"self": "RawTable", "hash": "u64"},
           ["self.capacity() >= GROUP_WIDTH",
            "free_slot_count > 0",
            "self.len_ <= self.count_full_ctrl()"]),
]

# --------------------------------------------------------------------------
# Stage 3 -- witness specs (`<crate>/specs/_witnesses/<concept>.<query>.json.draft`)
# --------------------------------------------------------------------------
PLACEHOLDER_HASH = "sha256:" + "0" * 64
RENDERER = "group_bitmask"


def witness(wid, concept, query, fixture_id, region, distribution, description):
    return {
        "schema_version": "1.0",
        "witness_id": wid,
        "concept": concept,
        "query": query,
        "fixture": {"fixture_id": fixture_id, "seed": 0, "description": description},
        "renderer": RENDERER,
        "expectation": {"renderer": RENDERER, "coverage_region": region,
                        "value_distribution": distribution, "fixture_family": fixture_id},
        "determinism": {"value_hash": PLACEHOLDER_HASH,
                        "claim": "byte-identical-across-runs",
                        "platforms": [TARGET_TRIPLE]},
        "output": {"path": f"docs/witnesses/{snake(concept)}.{query}.svg",
                   "render_hash": PLACEHOLDER_HASH, "renderer_actual": RENDERER},
    }


WITNESSES = [
    witness("W-GROUPPROBE-MATCHFULL-001", "GroupProbe", "match_full", "FX-GROUP-MATCH-16",
            "full-grid", "must-vary",
            "One sixteen-slot control group covering every combination of empty, deleted, "
            "sentinel and each of the 128 tag values at least once."),
    witness("W-CONTROLBYTES-COUNTEMPTY-001", "ControlBytes", "count_empty", "FX-CTRL-EMPTY-DENSITY",
            "full-grid", "must-vary",
            "One control group swept over every empty-slot density from zero to sixteen, so "
            "the empty count is a genuinely varying measurement rather than a constant."),
]

# --------------------------------------------------------------------------
# Stage 3 -- evidence conflict resolution (workspace-level `specs/_conflicts/`)
# --------------------------------------------------------------------------
CONFLICTS = [
    {
        "schema_version": "1.0",
        "conflict_id": "EC-1",
        "evidence": ["E-007", "E-008"],
        "status": "resolved",
        "resolution": {
            "selected_authority": "E-008",
            "disposition_of_other": "incidental",
            "rationale": (
                "E-007 and E-008 are both true and disagree about what they add up to. E-007 is "
                "the implementation fact: within one table, slots are visited in ascending "
                "control index. E-008 is the intent: the per-table seed is mixed into H1 "
                "specifically to randomise that order, so no enumeration order survives a "
                "different seed. E-008 wins because it is the authority that decides what a "
                "caller may rely on -- E-007 only describes one table's layout. The resolution "
                "binds the port and the oracle: iteration order is not an observable property, "
                "so no concept constraint may require an order and no oracle case may compare "
                "one. TableIterator.C004 and SwissTable.C004 are written from E-008, and "
                "chainlink #37 owns the oracle-side half of the same decision."),
        },
    },
]

# --------------------------------------------------------------------------
# Constraint-id integrity check
# --------------------------------------------------------------------------
def declared_constraint_ids():
    ids = {}
    for name, c in CONCEPTS.items():
        ids[name] = {x["id"]: x["kind"] for x in c["spec"]["constraints"]}
    return ids


def declared_members():
    """Query and command names each concept actually declares.

    A constraint's `applies_to` is a reference to one of these, and G2+ checks it
    against the boundary's callee method -- so an `applies_to` naming something the
    concept never declares, or a member the callee does not have, is a real error the
    binary reports as a hard `G2+/error`, not a cosmetic slip. See proof 5.
    """
    out = {}
    for name, c in CONCEPTS.items():
        members = set()
        for q in c["spec"].get("queries", []):
            members.add(q["rust_sig"].split("(")[0][3:])
        for cmd in c["spec"].get("commands", []):
            members.add(cmd["rust_sig"].split("(")[0][3:])
        out[name] = members
    return out


def check_applies_to(problems):
    """Every `applies_to` must resolve, and must cover the method that relies on it."""
    members = declared_members()
    applies = {n: {c["id"]: c.get("applies_to", []) for c in v["spec"]["constraints"]}
               for n, v in CONCEPTS.items()}

    for name, c in CONCEPTS.items():
        for con_ in c["spec"]["constraints"]:
            for a in con_.get("applies_to", []):
                if a not in members[name]:
                    problems.append(
                        f"concept {name}: constraint {con_['id']} applies_to {a!r}, which is not "
                        f"a declared query or command of {name} (declared: {sorted(members[name])})")

    for i in INTERACTIONS:
        callee = i["callee"]["method"]
        for r in i.get("reliances", []):
            concept, cid = r["obligation_id"].split(".", 1)
            at = applies.get(concept, {}).get(cid, [])
            if callee not in at:
                problems.append(
                    f"{i['interaction_id']}: relies {r['obligation_id']} applies_to {at}, which "
                    f"does not include this interaction's callee method {callee!r}")

    for b in BOUNDARIES:
        callee = b["callee"]["method"]
        for g in b["callee_guarantees"]:
            concept, cid = g.split(".", 1)
            at = applies.get(concept, {}).get(cid, [])
            if callee not in at:
                problems.append(
                    f"boundary {b['boundary_id']}: callee_guarantee {g} applies_to {at}, which "
                    f"does not include this boundary's callee method {callee!r} "
                    f"(G2+/error once specs_search_root resolves -- see proof 5)")


def check_constraint_ids():
    ids = declared_constraint_ids()
    problems = []
    # Every `applies_to` must name a declared member AND cover the relying method;
    # a boundary that misses the second is a hard G2+/error, not a cosmetic slip.
    check_applies_to(problems)
    # Every origin.content_hash is recomputed against the real pinned file, so an
    # evidence record can never claim a digest the checkout does not have. The
    # checkout is identified relative to THIS file, so the check reads the pilot's
    # own upstream tree whether the run root is the pilot or a scratch copy. A tree
    # with no upstream checkout at all (the proofs' rsync copies exclude it) is
    # reported as unverifiable rather than failed.
    pilot = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))))
    have_upstream = os.path.isdir(os.path.join(pilot, "upstream", "abseil-cpp"))
    if have_upstream:
        print("origin-hash check: recomputing every evidence content_hash against "
              f"{pilot}/upstream/abseil-cpp")
    else:
        print("origin-hash check: SKIPPED -- no upstream/abseil-cpp in this tree "
              "(the proofs' scratch copies exclude it; run from the pilot root to check)")
    print(f"constraint-id integrity: checking {len(EVIDENCE)} evidence, "
          f"{len(CONCEPTS)} concept, {len(INTERACTIONS)} interaction, "
          f"{len(BOUNDARIES)} boundary, {len(BRIDGES)} bridge, {len(WITNESSES)} witness, "
          f"{len(CONFLICTS)} conflict records")
    for e in EVIDENCE:
        rel = e["origin"]["path"]
        full = os.path.join(pilot, "upstream", "abseil-cpp", rel)
        if not os.path.isfile(full):
            full = os.path.join(pilot, rel)
        if not have_upstream:
            continue
        if not os.path.isfile(full):
            problems.append(f"{e['id']}: origin.path {rel} does not resolve to a file in this pilot")
            continue
        import hashlib
        digest = "sha256:" + hashlib.sha256(open(full, "rb").read()).hexdigest()
        if digest != e["origin"]["content_hash"]:
            problems.append(f"{e['id']}: content_hash {e['origin']['content_hash']} != real {digest} ({rel})")
        lo, _, hi = e["origin"]["line_hint"].partition("-")
        lines = sum(1 for _ in open(full, errors="replace"))
        if hi and int(hi) > lines:
            problems.append(f"{e['id']}: line_hint end {hi} past end of {rel} ({lines} lines)")
    for i in INTERACTIONS:
        for r in i.get("reliances", []):
            oid = r["obligation_id"]
            if "." not in oid:
                problems.append(f"{i['interaction_id']}: obligation_id {oid} is not <Concept>.<id>")
                continue
            concept, cid = oid.split(".", 1)
            if concept not in ids:
                problems.append(f"{i['interaction_id']}: unknown concept {concept} in {oid}")
            elif cid not in ids[concept]:
                problems.append(f"{i['interaction_id']}: {oid} is not declared by {concept}")
    for b in BOUNDARIES:
        for g in b["callee_guarantees"]:
            concept, cid = g.split(".", 1)
            if concept not in ids:
                problems.append(f"boundary {b['boundary_id']}: unknown concept {concept} in {g}")
            elif cid not in ids[concept]:
                problems.append(f"boundary {b['boundary_id']}: {g} is not declared by {concept}")
    boundary_ids = {b["boundary_id"] for b in BOUNDARIES}
    applies_of = {n: {c["id"]: c.get("applies_to", []) for c in v["spec"]["constraints"]}
                  for n, v in CONCEPTS.items()}
    for b in BRIDGES:
        if b["boundary_id"] not in boundary_ids:
            problems.append(f"bridge {b['bridge_id']}: boundary_id {b['boundary_id']} has no boundary contract")
        owner = next((x for x in BOUNDARIES if x["boundary_id"] == b["boundary_id"]), None)
        if owner and b["callee_requirement"] not in owner["callee_guarantees"]:
            problems.append(f"bridge {b['bridge_id']}: callee_requirement {b['callee_requirement']} is not a callee_guarantee of {owner['boundary_id']}")
        if b["bridge_logic"]["conclusion"]["obligation_id"] != b["callee_requirement"]:
            problems.append(f"bridge {b['bridge_id']}: conclusion != callee_requirement")
        concept, cid = b["callee_requirement"].split(".", 1)
        if concept in ids and ids[concept].get(cid) != "precondition":
            problems.append(f"bridge {b['bridge_id']}: {b['callee_requirement']} is a {ids[concept].get(cid)}, not a precondition")
        # The bridge discharges the precondition AT THIS boundary's callee, so its
        # applies_to has to cover that callee method too -- otherwise fixing the
        # boundary drags the bridge out with it (see proof 5).
        if owner and concept in applies_of and owner["callee"]["method"] not in applies_of[concept].get(cid, []):
            problems.append(
                f"bridge {b['bridge_id']}: callee_requirement {b['callee_requirement']} applies_to "
                f"{applies_of[concept].get(cid)}, which does not include "
                f"{owner['boundary_id']}'s callee method {owner['callee']['method']!r}")
        for f in b["available_contract_facts"]:
            concept, cid = f["obligation_id"].split(".", 1)
            if concept not in ids or cid not in ids.get(concept, {}):
                problems.append(f"bridge {b['bridge_id']}: fact {f['obligation_id']} is not declared")
    concept_queries = {n: {q_["rust_sig"].split("(")[0][3:] for q_ in c["spec"]["queries"]}
                       for n, c in CONCEPTS.items()}
    for w in WITNESSES:
        if w["concept"] not in concept_queries:
            problems.append(f"witness {w['witness_id']}: unknown concept {w['concept']}")
        elif w["query"] not in concept_queries[w["concept"]]:
            problems.append(f"witness {w['witness_id']}: {w['query']} is not a query of {w['concept']}")
        elif w["path"] if False else False:
            pass
        if w["output"]["path"] != f"docs/witnesses/{snake(w['concept'])}.{w['query']}.svg":
            problems.append(f"witness {w['witness_id']}: output.path does not match the required shape")
    ev_ids = {e["id"] for e in EVIDENCE}
    for i in INTERACTIONS:
        for e in i.get("evidence_links", []):
            if e not in ev_ids:
                problems.append(f"{i['interaction_id']}: evidence_link {e} does not exist")
    for c in CONFLICTS:
        for e in c["evidence"]:
            if e not in ev_ids:
                problems.append(f"{c['conflict_id']}: evidence {e} does not exist")
        if c["resolution"]["selected_authority"] not in c["evidence"]:
            problems.append(f"{c['conflict_id']}: selected_authority is not in its own evidence list")
    return problems


# --------------------------------------------------------------------------
# Artifact assembly: (target path, template, stage, vars, body)
# --------------------------------------------------------------------------
def build():
    artifacts = []
    for e in EVIDENCE:
        artifacts.append({
            "kind": "evidence",
            "target": f"evidence/{e['id']}.json",
            "stage": "0",
            "template": "evidence-intake",
            "vars": {
                "source_material": (
                    f"{e['origin']['path']}:{e['origin']['line_hint']} "
                    f"({e['origin']['symbol']}) at pinned commit {UPSTREAM_COMMIT}, tag 20260817.0. "
                    f"The claim below is the proposition that record supports; origin is the "
                    f"bytes it was read from."),
                "project_descriptor": (
                    "mode=port, closure_kind=deductive, verifier_policy.default=verus, "
                    f"port_source.repository={DESCRIPTOR_REPO}. mode: port and the claim "
                    f"originates in the C++ source being ported, so this record is mode P."),
                **NO_REENTRY,
            },
            "body": e,
        })

    for name, c in CONCEPTS.items():
        artifacts.append({
            "kind": "concept",
            "target": f"{CRATE}/specs/{snake(name)}.json",
            "stage": "3",
            "template": "concept-to-code",
            "vars": {
                "concept": name,
                "cluster": c["cluster"],
                "verifier": VERIFIER,
                "source_material": c["source_material"],
                **NO_REENTRY,
            },
            "body": c["spec"],
        })

    inter_by_id = {i["interaction_id"]: i for i in INTERACTIONS}
    for i in INTERACTIONS:
        caller, callee = i["caller"], i["callee"]
        artifacts.append({
            "kind": "interaction",
            "target": f"{CRATE}/specs/_interactions/{i['interaction_id']}.json",
            "stage": "3",
            "template": "interaction-drafting",
            "vars": {
                "interaction_id": i["interaction_id"],
                "caller_concept": caller["concept"],
                "caller_method": caller["method"],
                "callee_concept": callee["concept"],
                "callee_method": callee["method"],
                "caller_spec": json.dumps(CONCEPTS[caller["concept"]]["spec"], indent=2),
                "callee_spec": json.dumps(CONCEPTS[callee["concept"]]["spec"], indent=2),
                "target_triple": TARGET_TRIPLE,
                **NO_REENTRY,
            },
            "body": i,
        })

    for b in BOUNDARIES:
        caller, callee = b["caller"], b["callee"]
        owner = inter_by_id[b["_interaction_id"]]
        artifacts.append({
            "kind": "boundary",
            "target": f"{CRATE}/specs/_boundaries/{b['boundary_id']}.json",
            "stage": "3",
            "template": "boundary-drafting",
            "vars": {
                "caller_concept": caller["concept"],
                "caller_method": caller["method"],
                "callee_concept": callee["concept"],
                "callee_method": callee["method"],
                "caller_concept_snake": snake(caller["concept"]),
                "callee_concept_snake": snake(callee["concept"]),
                "caller_spec": json.dumps(CONCEPTS[caller["concept"]]["spec"], indent=2),
                "callee_spec": json.dumps(CONCEPTS[callee["concept"]]["spec"], indent=2),
                "reliance_policy": (
                    "docs/reliance-policy.md, unmodified. Resolution rule applied: a callee "
                    "postcondition or invariant the caller's correctness depends on goes into "
                    "callee_guarantees as <CalleeConcept>.<constraint id>; a callee precondition "
                    "the caller must establish is a bridge, and no A*-shaped adversary case is "
                    "ever listed as a guarantee. Every id below is one this run declares in the "
                    "callee's own concept spec -- see analysis/ligature/stage0-3/artifacts.py."),
                **NO_REENTRY,
            },
            "body": {k: v for k, v in b.items() if not k.startswith("_")},
        })
        del owner

    for b in BRIDGES:
        owner = next(x for x in BOUNDARIES if x["boundary_id"] == b["boundary_id"])
        caller_concept, callee_concept = owner["caller"]["concept"], owner["callee"]["concept"]
        artifacts.append({
            "kind": "bridge",
            "target": f"{CRATE}/specs/_bridges/{b['bridge_id']}.json",
            "stage": "3",
            "template": "bridge-drafting",
            "vars": {
                "bridge_id": b["bridge_id"],
                "boundary_id": b["boundary_id"],
                "callee_requirement": b["callee_requirement"],
                "caller_spec": json.dumps(CONCEPTS[caller_concept]["spec"], indent=2),
                "callee_spec": json.dumps(CONCEPTS[callee_concept]["spec"], indent=2),
                "boundary_contract": json.dumps({k: v for k, v in owner.items() if not k.startswith("_")}, indent=2),
                **NO_REENTRY,
            },
            "body": b,
        })

    for w in WITNESSES:
        artifacts.append({
            "kind": "witness",
            "target": f"{CRATE}/specs/_witnesses/{snake(w['concept'])}.{w['query']}.json",
            "stage": "3",
            "template": "witness-drafting",
            "vars": {
                "witness_id": w["witness_id"],
                "concept": w["concept"],
                "query": w["query"],
                "concept_spec": json.dumps(CONCEPTS[w["concept"]]["spec"], indent=2),
                **NO_REENTRY,
            },
            "body": w,
        })

    for c in CONFLICTS:
        involved = [e for e in EVIDENCE if e["id"] in c["evidence"]]
        artifacts.append({
            "kind": "conflict",
            "target": f"specs/_conflicts/{c['conflict_id']}.json",
            "stage": "3",
            "template": "conflict-resolution-drafting",
            "vars": {
                "conflict_id": c["conflict_id"],
                "evidence_records": json.dumps(involved, indent=2),
                **NO_REENTRY,
            },
            "body": c,
        })

    return artifacts


def cmdline(a):
    cmd = ["python3", "tools/ligature/ligature.pyz", "draft", a["stage"], a["template"], a["target"]]
    for k, v in a["vars"].items():
        cmd += ["--var", f"{k}={v}"]
    return cmd


def run_one(a, root=None):
    """Stage exactly one artifact with `ligature.pyz draft`. Returns the exit code."""
    root = root or os.getcwd()
    cmd = ["python3", "tools/ligature/ligature.pyz", "draft", a["stage"], a["template"], a["target"]]
    for k, v in a["vars"].items():
        cmd += ["--var", f"{k}={v}"]
    proc = subprocess.run(cmd, cwd=root, input=json.dumps(a["body"], indent=2),
                          capture_output=True, text=True)
    for line in (proc.stdout + proc.stderr).strip().splitlines()[-2:]:
        print("   ", line)
    return proc.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit")
    ap.add_argument("--root")
    ap.add_argument("--transcript", default="analysis/ligature/stage0-3/drafting.txt")
    ap.add_argument("--only", default=None, help="comma-separated artifact kinds")
    args = ap.parse_args()

    problems = check_constraint_ids()
    if problems:
        print("ARTIFACT INTEGRITY FAILURE:", file=sys.stderr)
        for p in problems:
            print("  -", p, file=sys.stderr)
        return 2

    artifacts = build()
    if args.only:
        keep = set(args.only.split(","))
        artifacts = [a for a in artifacts if a["kind"] in keep]

    if args.emit:
        os.makedirs(args.emit, exist_ok=True)
        for a in artifacts:
            stem = re_sub(a["target"].replace("/", "__")[:-5])
            with open(os.path.join(args.emit, stem + ".json"), "w") as fh:
                json.dump(a["body"], fh, indent=2)
                fh.write("\n")
            with open(os.path.join(args.emit, stem + ".cmd"), "w") as fh:
                fh.write(" ".join(shlex.quote(c) for c in cmdline(a)) + " < " + stem + ".json\n")
        print(f"emitted {len(artifacts)} artifact bodies + command lines to {args.emit}")
        return 0

    if not args.root:
        ap.error("need --emit or --root")

    lines = []
    def emit(s=""):
        print(s)
        lines.append(s)

    emit(f"# Stage 0-3 drafting transcript -- chainlink #28, pilot {PILOT}")
    emit(f"# root: {args.root}")
    emit("# generated by analysis/ligature/stage0-3/artifacts.py")
    emit()
    counts = {}
    for a in artifacts:
        counts[a["kind"]] = counts.get(a["kind"], 0) + 1
    emit("# artifact counts: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    emit("# constraint-id integrity: PASS (every <Concept>.C<nnn> above is declared by that")
    emit("#   concept's own spec in this file, and every bridge's callee_requirement is a")
    emit("#   callee precondition listed in its boundary's callee_guarantees)")
    emit()

    failures = 0
    for a in artifacts:
        proc_rc = run_one(a, args.root)
        status = "OK" if proc_rc == 0 else f"FAIL exit={proc_rc}"
        if proc_rc != 0:
            failures += 1
        emit(f"### {a['kind']}: {a['target']}")
        emit(f"$ {' '.join(shlex.quote(c) for c in cmdline(a)[:6])} ... [{len(a['vars'])} --var] < body.json")
        emit(f"    -> {status}")
        emit()

    emit(f"# {len(artifacts) - failures}/{len(artifacts)} drafts staged cleanly; {failures} failed")

    if args.transcript:
        dest = os.path.join(args.root, args.transcript)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w") as fh:
            fh.write("\n".join(lines) + "\n")
    return 1 if failures else 0


def re_sub(s):
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in s)


if __name__ == "__main__":
    sys.exit(main())