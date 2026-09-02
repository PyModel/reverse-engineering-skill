# Deobfuscation & Dynamic Analysis

Neutralize at the cheapest level first — strings → flow → VM. A runtime dump beats heroic static
lifting. Keep a log of every hook/patch: address, original bytes, patched bytes, why
(reproducibility). After deobfuscation, the decompiled output must **re-derive every observed
string and every observed IPC/protocol message** — anything unexplained means incomplete work.

## 1. Obfuscation taxonomy (identify first, then neutralize)

| Strategy | Signature | Neutralization |
|----------|-----------|----------------|
| Control-flow flattening | dispatcher variable, `switch` in loop, all blocks route through one point | symbolic execution (angr, Miasm), deobfuscator (deflat, D-810), manual dispatcher trace |
| Opaque predicates | `cmp`/`jcc` with constant operands, `push/pop` pairs, dead branches | constant folding, algebraic simplification, SMT (Z3), dead-code elimination |
| MBA expressions | mixed boolean-arithmetic (`x ^ (x>>7) + ...`) — arithmetic disguised as logic | **msynth** (oracle-based MBA simplification) or stochastic program synthesis |
| String encryption | XOR/RC4/AES decryptor called at use site; blobs in `.rodata` | find decryptor, extract keys, batch-decrypt all call sites; hook at runtime to dump plaintext |
| Dynamic symbol resolution | `dlsym`/`GetProcAddress` with encrypted names, custom hash→func tables | hook the resolver, log (name, address) pairs; reconstruct the table |
| Packers | high entropy, few imports, stub section, `UPX`/`Themida`/`VMProtect`/`.aspack` | unpack statically (UPX -d) or dynamically (run + dump memory, rebuild IAT) |
| VM-based (VMProtect, Themida, custom VM) | dispatcher loop, handler table, bytecode blob | identify VM handlers, reconstruct bytecode ISA, write a lifter (handler → IR) |
| Bytecode-level (R8/ProGuard, ConfuserEx, Dotfuscator) | minified names, control-flow mangling, reflection | deobfuscators (de4dot, R8 mapping files), string-decrypt helper trace |
| Anti-debug / anti-VM | `IsDebuggerPresent`, `ptrace(0x1F)`, `cpuid`, timing (`rdtsc`), MAC prefixes | patch checks, hide breakpoints, set registers/flags, run in bare VM, hook at runtime |

## 2. Practical neutralization playbook

### Static-first (when possible)
1. Diff against a *clean* build if you have one (same toolchain, unobfuscated build of the same
   version) — the diff reveals the obfuscation delta.
2. Recover names from: RTTI/typeinfo, error strings, log format strings, resource names,
   `.pdb`/`dwarf`/export table leftovers, `mapping.txt` (R8), source-map files, `.class`/metadata.
3. Symbolize: rename only what you can justify (`proposed:` vs `observed:`).

### Triaging where to look (aggressive)
- **`obfuscation_detection`** (Binary Ninja plugin): portfolio of lightweight heuristics (CFG
  complexity, flattening/state-machine patterns, uncommon instruction sequences,
  overlapping/disaligned instructions, entropy/RC4 markers, loop patterns) surfaces top-ranked
  hotspots — use it to triage large binaries instead of eyeballing every function.
- **`obfuscation_analysis`** (Binary Ninja plugin): MBA simplification in the decompiler view,
  corrupted-function detection/removal, recursive decompiler-level inlining for propagation and
  cleanup across call boundaries.

### SMT / symbolic execution (control-flow flattening + opaque predicates)
- **angr** for CFF: identify the dispatcher variable, build a clean CFG from the state machine
  (the classic `angr_notes` approach works on unpatched binaries via the hard-coded jump table).
- **Z3** for opaque predicates: encode `cmp`/`jcc` conditions, ask the solver which branch is
  always-taken/always-false, then constant-fold and eliminate dead branches.
- **Miasm** for OLLVM-style flattening: MODeflattener-style static approach; use
  `miasm` symbolic/simplification passes to lift flattened handlers into an IR.

### Dynamic-assisted (when static fails)
- Run in a **sandbox VM** with no network (or consented network), hook
  `dlsym`/`GetProcAddress`/string decryptors, dump:
  - decrypted strings at decryptor return
  - resolved function addresses + names
  - memory snapshot at rest points (before/after unpacking)
- Rebuild: unpacked memory → valid PE/ELF (fix section headers, imports) or dump to a decompiler
  as a "memory region" file.
- VM handlers: single-step the dispatcher, log `bytecode ptr`, handler address, and side
  effects; after N iterations you'll have the ISA table.

### Frida harnesses (drop-in, see `scripts/frida_templates/`)
- `hook_crypto.js` — intercept common cipher/HMAC calls (AES, RC4, HMAC, OpenSSL/BoringSSL).
- `trace_ipc.js` — sockets, named pipes, Mach ports; log framing bytes pre/post transform.
- `ssl_unpin.js` — universal Android/iOS TLS unpinning (SSL_CTX, SecTrustEvaluate, BoringSSL).

### LLM-assisted deobfuscation (2025+ research)
- General LLMs can deobfuscate assembly-level CFF and MBA without fine-tuning (arXiv 2505.19887).
  Use the model to *reason* about flattened handlers and opaque predicates — but verify the
  resulting control flow against a symbolic-execution pass or SMT solver before trusting it.
- LLM4Decompile-class models refine Ghidra pseudocode (variable names, types) — auxiliary, not a
  decompiler replacement.

### Bytecode-level
- R8/ProGuard: check for `mapping.txt` (often shipped by accident) — full name recovery.
- ConfuserEx: runtime constant resolution — trace with dnSpy debugger or run in a sandbox and
  hook the constant resolver.
- String decryptors: usually one function with a key constant — find it, script all call sites,
  batch-decrypt, then rename symbols.

## 3. Embedded asset & config extraction

- Look in: `.rodata`/`.rdata`, resource sections (`.rsrc`, `resources.arsc`, `PE resources`),
  appended-data (after last section), steganographic "extra" bytes, `__DATA` blobs,
  zip/protobuf inside binaries.
- Extract: config tables (JSON/XML/INI/protobuf/custom TLV), license keys, feature flags,
  endpoint URLs, embedded certificates, key derivation constants, hardcoded passwords.
- **Deliverable:** each asset with offset, size, encoding, and a decoded dump.

## 4. Obfuscation-resistant workflow

1. Never fight the obfuscator in the decompiler first — neutralize at the level that's cheapest.
2. Keep a *log* of every hook/patch applied: address, original bytes, patched bytes, why.
   The report must include it (reproducibility).
3. Prefer runtime dumps over heroic static analysis when a packer is involved — one memory dump
   replaces hours of lifting.
4. Cross-validate: after deobfuscation, the decompiled output should re-derive every observed
   string and every observed IPC/protocol message. Anything unexplained means incomplete work.
