# Output Standards — Deliverables Template

## Per-answer standards (apply everywhere)

- **Precision:** reference exact memory offsets, registers, and instructions where relevant.
  Use `path:line` for source refs, `0x...` for offsets, `file:section+offset` for binary locations.
- **Clarity:** translate complex assembly/decompilation artifacts into clean, readable code and
  structural diagrams (Mermaid or ASCII).
- **Completeness:** all extracted data structures include field names, estimated types, and byte
  offsets. Mark inferred (not observed) items as `inferred` / `TBD (unverified)`.

## Final deliverable package

```
1. Executive summary (what the target is, what it does, key interfaces)
2. Triage table (container, arch, toolchain, runtime, packing, obfuscation, symbols, entry,
   surface, first hypotheses)
3. Architecture summary (component interaction, Mermaid diagram or ASCII)
4. Data structure tables (field, offset, size, type, endianness, evidence)
5. Protocol / IPC specification (framing, handshake, message schema, state machine diagram,
   sequence diagram)
6. Deobfuscation log (hooks, patches, address, original→patched bytes, why)
7. Clean-room reimplementation (per layer, with golden tests) — optional
8. Asset/config extraction inventory (offset, size, encoding, decoded dump)
9. Research appendix (web-sourced facts, URLs, confidence, conflicts)
10. Unknowns & open questions (untested paths, unresolved symbols)
```

## Struct table format

```text
Field            Offset  Size  Type          Endianness  Evidence
magic            0x00    4     u8[4]         -           constant in all captures
version          0x04    2     u16           LE          varies 1..3, monotonic
payload_len      0x06    4     u32           LE          == remaining bytes
flags            0x0A    1     bitfield u8   -           4 distinct values seen
reserved         0x0B    5     -             -           always zero
payload          0x10    var   byte[]        -           zlib (magic 78 9C)
```

## Protocol message table format

```text
Name        Dir   Code   Fields (in order)                      Notes
HANDSHAKE   C→S   0x01   ver:u16, nonce:u32, cipher:u8          first msg
HANDSHAKE_OK S→C  0x81   session:u32, cipher:u8, key:u32[4]     reply
AUTH        C→S   0x02   hmac:u8[32]                            HMAC-SHA256
DATA        C→S   0x10   seq:u32, len:u32, payload:byte[len]    zlib
ACK         S→C   0x90   seq:u32                                reply to DATA
ERROR       S→C   0xF0   code:u32, msg:u8[len]                  any state
```

## Evidence labeling convention

- `observed:` — read directly from the binary/capture (offset, instruction, packet, string).
  Ground truth.
- `inferred:` — deduced from access patterns/allocator sizes/ABI rules; state the reasoning.
- `proposed:` — name you invented for readability; not from the target.
- `web:` — from online docs; cite URL and confidence.

## Tone rules

- Lead with impact: "What does this program do, and what can I now build?"
- No filler: "appears to perhaps maybe" → "does X, evidenced by Y".
- Every claim carries its evidence label.
- Separate the *spec* (what it does) from the *how-I-know* (evidence).
