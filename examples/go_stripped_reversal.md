# Case study: Go stripped binary → clean-room client

End-to-end walkthrough of the aggressive workflow on a stripped Go binary. This is a
few-shot example: input → triage → struct reconstruction → clean-room implementation.
Follow the same shape for any similar target.

## 1. Triage

```
python3 scripts/triage_binary.py target.bin
python3 scripts/calculate_entropy.py target.bin
python3 scripts/extract_go_metadata.py target.bin
```

Output: ELF64, x86_64, Go 1.21, not packed (entropy ~6.2), symbols stripped but
`.gopclntab` present. `extract_go_metadata.py` recovered function-name candidates.

## 2. Reconstruct the interface dispatch (itab)

Go interface calls go through `itab` tables. From the recovered names + disassembly:

- Locate `runtime.moduledata` via `.go.buildinfo`/`runtime.rt0` references.
- Identify `go.itab.*` symbols → concrete types implementing the interface.
- Reconstruct the dispatch: `call [itab + 0x20]` → the actual method.

## 3. Reconstruct the wire struct

Offset-access analysis (from Ghidra Headless output, see `scripts/ghidra_headless.sh`):

```c
// Accesses: *(u64*)(a+0x00) read; *(u32*)(a+0x08) read; *(u32*)(a+0x0C) read/write
// *(u64*)(a+0x10) read (used with strlen)
struct Msg {
    uint64_t seq;       // +0x00 (monotonic counter)
    uint32_t kind;      // +0x08 (enum, 4 distinct values)
    uint32_t flags;     // +0x0C (bitfield)
    const char *payload; // +0x10 (used with strlen)
};  // sizeof = 0x18
```

Validate mechanically:

```
python3 scripts/validate_struct.py struct.json   # expects {"fields":[...], "total_size":0x18}
```

## 4. Clean-room reimplementation

Freeze the spec (struct table + itab dispatch + protocol state machine), then implement in
Go (protocol/daemon fit). Layers: framing/IO → state machine → handlers → models. Golden tests
replay captured sessions byte-for-byte. No verbatim decompiled code — rewrite from the spec.

## 5. Report

Deliverables per `08-output-standards.md`: triage table, struct table with evidence, itab
dispatch diagram, clean-room code, unknowns. Every field carries `observed:`/`inferred:`.
