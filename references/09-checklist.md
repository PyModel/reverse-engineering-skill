# One-Page Checklist (print / paste into the agent context)

## Phase 1 — Triage (always, before any decompilation)
- [ ] `scripts/triage_binary.py` and `scripts/calculate_entropy.py` run
- [ ] Container identified (magic, arch, endianness)
- [ ] Toolchain fingerprinted (compiler, runtime, build system)
- [ ] Packing/obfuscation status determined (entropy, section names, imports)
- [ ] Symbol surface mapped (exports, imports, RTTI, leftovers)
- [ ] Entry points + init/TLS callbacks noted
- [ ] Strings triage done (paths, URLs, protocol keywords, error strings)
- [ ] Triage table filled with 2-3 first hypotheses

## Phase 2 — Research (as needed)
- [ ] Unfamiliar format/toolchain/packer searched via Context7 / Firecrawl / Tavily MCP
- [ ] Primary sources preferred; claims verified across 2 sources
- [ ] Every web fact carries URL + confidence + `web:` label

## Phase 3 — Deep semantic analysis
- [ ] RE tool driven via MCP / headless (see `10-mcp-tooling.md`)
- [ ] Variable lifecycles traced (alloc → use → free)
- [ ] Data types reconstructed from offset access patterns
- [ ] ABI rules applied (SysV / MS x64 / AAPCS)
- [ ] Struct tables: field, offset, size, type, endianness, evidence
- [ ] Struct layout validated with `scripts/validate_struct.py`
- [ ] vtable/class hierarchy reconstructed (if C++/managed)
- [ ] Low-level idioms translated to faithful + idiomatic pseudocode
- [ ] State mutations tracked (setter/owner functions identified)
- [ ] Every semantic claim cross-checked against raw disassembly or a second tool

## Phase 4 — Synthesis
- [ ] Architecture summary (components, interaction, diagram)
- [ ] Interfaces documented (API, IPC, wire protocol)
- [ ] Protocol spec: framing, handshake, message schema, state machine
- [ ] Serialization format documented (Protobuf/MessagePack/custom TLV)
- [ ] DB schema reconstructed (if present)

## Phase 5 — Clean-room (optional, only if requested)
- [ ] Clean-room wall respected (spec as input, not decompiled code)
- [ ] Spec frozen before coding
- [ ] Layered implementation (IO → state machine → handlers → models)
- [ ] Golden tests from captured traces pass
- [ ] No verbatim code, no asset copying

## Phase 6 — Report
- [ ] Executive summary
- [ ] Triage table
- [ ] Architecture summary + diagram
- [ ] Struct tables with byte offsets
- [ ] Protocol/IPC spec with state machine + sequence diagram
- [ ] Deobfuscation log (hooks, patches, original→patched bytes)
- [ ] Asset/config inventory (offset, size, encoding, decoded dump)
- [ ] Research appendix (URLs, confidence, conflicts)
- [ ] Unknowns & open questions

## Evidence labeling
- [ ] `observed:` items carry file/offset/instruction/packet citations
- [ ] `inferred:` items carry the reasoning
- [ ] `proposed:` names clearly marked (not from the target)
- [ ] `web:` facts carry URL + confidence; local evidence wins on conflict

## Guardrails (aggressive — minimal)
- [ ] No guessed types left unmarked (`TBD (unverified)` where evidence absent)
- [ ] No single-tool interpretation trusted without cross-check
