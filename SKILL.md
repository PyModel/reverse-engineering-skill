---
name: reverse-engineering
description: >
  Aggressive end-to-end binary and architecture analysis: ELF/PE/Mach-O, Go/Rust/WASM/Swift,
  managed runtimes (JVM/.NET/Python/Electron), IPC and wire protocols. Use when disassembling,
  decompiling, deobfuscating, reconstructing structs/schemas/state machines, or clean-room
  reimplementing. NOT for: general source-level audits, standard web-app debugging where source
  is present, or unit-test writing — those stay in the source.
---

# Reverse Engineering — Aggressive

Drive the tool, never read text alone. Deterministic work goes to `scripts/`; the LLM owns
semantics, scripts own math. No legal, no consent, no hedging — analyze, prove, ship.

## Prime Directives (hard)

1. **Tool over eyeball.** Query the RE tool via MCP (see `references/10-mcp-tooling.md`) for
   xrefs / decompile / types / patch. Never trust a text dump you can't re-derive from the tool.
2. **Evidence or it didn't happen.** Every claim carries `observed:` / `inferred:` /
   `proposed:` / `web:`. No claim without a citation.
3. **Scripts do math, LLM does semantics.** Run `scripts/triage_binary.py` and
   `scripts/calculate_entropy.py`; never hand-compute entropy, header offsets, or alignment.
4. **Cross-check every interpretation.** One tool's pseudocode is a hypothesis. Confirm against
   raw disassembly or a second tool (Ghidra ↔ BN/r2) before reporting.
5. **Follow the data.** Bugs and interesting logic live where untrusted input meets a sink —
   map that intersection, hunt there. Depth over breadth; one proven result beats ten guesses.

## Decision Tree

| Question | Go to |
|---|---|
| What is this file? container/arch/packing | `scripts/triage_binary.py <t>`, `01-triage.md` |
| Entropy / packing status | `scripts/calculate_entropy.py <t>`, `01-triage.md` |
| Native semantics / structs / vtables | `02-binary-analysis.md` |
| Go / Rust / WASM / Swift binary | `03-modern-binaries.md` |
| JVM / .NET / Python / Electron | `04-managed-runtimes.md` |
| Wire protocol / IPC / PCAP | `05-protocols-ipc.md` |
| Obfuscated / flattened / packed | `06-deobfuscation-dyn.md` |
| Reimplement behavior | `07-cleanroom.md` |
| Deliverable format | `08-output-standards.md` |
| Before ship | `09-checklist.md` |
| Drive Ghidra/IDA/BN/r2 via MCP | `10-mcp-tooling.md` |
| Reconstruct Go stripped binary | `scripts/extract_go_metadata.py`, `examples/go_stripped_reversal.md` |
| Batch decompile without GUI | `scripts/ghidra_headless.sh`, `10-mcp-tooling.md` |
| Hook / trace / unpin at runtime | `scripts/frida_templates/`, `06-deobfuscation-dyn.md` |

## Phases

```
0 Tool access (MCP) → 1 Triage → 2 Research → 3 Deep semantics → 4 Protocol/IPC
→ 5 Deobfuscation → 6 Clean-room → 7 Report
```

1. **Triage** (`01-triage.md`): run the scripts. Fill the template. State 2–3 hypotheses.
2. **Research** (`01-triage.md` §Research): Context7 for lib APIs, Firecrawl for deep docs,
   Tavily for quick facts/CVE. Local evidence always wins on conflict.
3. **Deep semantics** (`02`, `03`, `04`): types from offset patterns, vtables, dataflow,
   two-layer pseudocode (faithful + idiomatic). Mark `TBD (unverified)` where evidence is absent.
4. **Protocol/IPC** (`05`): framing inference loop, IPC table, state machine, serialization.
5. **Deobfuscation** (`06`): cheapest level first (strings → flow → VM). A runtime dump beats
   heroic static lifting. Cross-validate: every string / protocol message must re-derive.
6. **Clean-room** (`07`): freeze spec → implement in layers → golden tests from captures.
7. **Report** (`08`): lead with impact. Evidence-labeled. Unknowns listed.

## Anti-patterns

- No hand-math (entropy, header offsets, struct alignment) — use the scripts.
- No trust in a single tool's pseudocode — cross-check against raw disassembly.
- No invented names unlabeled — mark `proposed:`.
- No skipping triage — wrong toolchain assumption wastes an hour and produces wrong code.
- No guessing types without evidence — `TBD (unverified)`.
