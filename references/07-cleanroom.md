# Clean-room Reimplementation

Reimplement **behavior**, not expression. No legal/ToS hand-wringing, no provenance ceremony —
just: extract the spec, freeze it, build it in layers, prove it against captured evidence.

## 1. The rule

Copyright protects *source expression*, not ideas, algorithms, or protocols. A clean-room
reimplementation copies **behavior and specifications** — never code, comments, variable names,
class layouts-as-expression, assets, or icons. If it's behavior, it's fine. If it's verbatim
code or an asset, rewrite/recreate it.

## 2. Clean-room discipline

1. **One-way wall.** The engineer writing new code reads only *specifications* (struct tables,
   protocol docs, state machines, behavior descriptions) — not the decompiled source, not the
   original code. When one agent does both roles, keep artifacts separated: spec documents are
   inputs; decompiled dumps are never inputs to the coder.
2. **No verbatim extraction.** Do not copy decompiled functions into the new codebase, even
   "just as a starting point." Rewrite from the spec.
3. **No asset copying.** Icons, fonts, images, sound, data files, trade dress, branding, UI text
   strings (unless the string *is* the protocol/interface, e.g. wire-format field names) —
   recreate or license.
4. **No distribution of the original binary** or of verbatim decompiled dumps as deliverables.
   Deliverables: specs, schemas, diagrams, clean-room code, test evidence.

## 3. Reimplementation method

1. **Freeze the spec first.** Do not start coding until struct tables, protocol docs, and state
   machines are stable — otherwise you'll churn.
2. **Pick the target language by fit, not taste:**
   - Protocol/daemon/system → Go or Rust
   - Tooling/analysis glue → Python
   - Backend/API reimpl → TypeScript or Go
   - Low-level, performance-critical → C++ or Rust
3. **Implement in layers** matching the recon structure: framing/IO → state machine → handlers →
   data models. Test each layer against captured traces (golden tests from PCAP/IPC captures).
4. **Test with evidence:** replay captured real sessions against the reimplementation; it must
   accept the same inputs and produce the same outputs (byte-for-byte for wire formats, semantic
   equivalence for data).
5. **No "inspired-by" naming.** Use spec-derived names (`field_0x08_ptr` → `name_ptr` only if
   semantics observed) or domain-appropriate names, not the original's variable names.

## 4. When reimplementation is out of scope

If the user only needs *understanding* (a spec, a diagram, a schema), do not write code.
Deliverables: spec, struct tables, state machines, diagrams. Offer clean-room code as an
optional follow-up.
