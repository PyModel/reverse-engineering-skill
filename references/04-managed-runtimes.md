# Managed Runtimes — Bytecode, Bundles, and Script Runtimes

Managed targets give you more than native binaries: metadata, class names, and (until
obfuscated) real source-level structure. **Always prefer bytecode-level analysis over blind
disassembly.** Verify decompiled output at IL/bytecode level for any branch-heavy or
exception-heavy region — decompilers are lossy there. Record tool version in the report.

## 1. JVM (Java / Kotlin / Scala)

**Tooling:** CFR, Procyon, Jadx (APKs), FernFlower, javap, `dex2jar` for Android, `smali/baksmali`
for raw DEX.

Workflow:
1. Unpack container: `.jar`/`.war`/`.apk`/`.aab`/`.dex`/`.kotlin_metadata`.
2. Decompile class-by-class with CFR/Procyon; cross-check with `javap -c -v` for bytecode-level
   questions (decompilers hide edge cases).
3. Android specifics: `resources.arsc` (string/table assets), `AndroidManifest` (permissions,
   exported components), NDK `.so` (go to native ref), Kotlin `metadata` (reconstruct data
   classes, sealed hierarchies, extension fns).
4. Android via MCP: `Jadx-MCP`/`jadx-mcp-server` + `apktool-mcp-server` let the agent drive
   Jadx/APK tools directly — see `references/10-mcp-tooling.md`.
5. Obfuscation: ProGuard/R8 (name minification, inlining, access modification), Kotlin
   obfuscators, commercial (DexGuard, StringCare). Neutralize: rename maps (`mapping.txt`),
   string-decryption helpers, R8 inlining undo via pattern search.

Class hierarchy reconstruction:
- Read `InnerClasses`/`NestHost` attributes; superclass chain from `super_class`; interfaces
  from `interfaces[]`.
- Kotlin: `@Metadata` holds sealed/companion/data/suspend info — parse it (or via Jadx plugin).

## 2. .NET / CLR (C# / F# / VB)

**Tooling:** ILSpy, dnSpy/Hex editor, dotPeek, de4dot, `ILDasm`, `Mono.Cecil`, `PeVerify`.

Workflow:
1. Detect: `BSJ`/`BM`+`CE` header, `CLR` header in PE, `mscorlib` reference.
2. Load in ILSpy/dnSpy: decompile assembly-by-assembly; dump full metadata (types, methods,
   fields, `[Obfuscation]` attributes, `Reflection` targets).
3. IL-level analysis with `ILDasm /adv` when decompiled C# is ambiguous (e.g. `ldc.i4 0x7FFFFFFF`
   vs `sizeof(int)*` idioms, `try/filter` blocks).
4. Obfuscation: de4dot for common protectors (ConfuserEx, .NET Reactor, Dotfuscator,
   SmartAssembly); ConfuserEx may need runtime-resolved constants — run in a sandbox or trace
   with dnSpy debugger.
5. Reconstruct: class hierarchies from metadata (cheap!), interfaces, generics, attributes,
   P/Invoke (`[DllImport]`) → native interop list.

## 3. V8 / Node.js / Electron

**Electron app:**
- `app.asar` → `npx asar extract app.asar out/` — read JS directly if not minified/obfuscated.
- Webpack/Vite/rollup bundles: source maps (`app.js.map`) if shipped — `npx source-map-explorer`
  or `sourcemap` lib to recover original files, variable names, TS types.
- No source maps: JS-beautifier + module-name inference from `__webpack_require__` module IDs,
  `exports` shapes, and string constants.

**V8 bytecode / snapshot:**
- `--print-bytecode` (dev builds), `v8-disassembler`, `node --print-code` for JIT-compiled code,
  `snapshot_blob` parsing for startup snapshots.
- `cachedData` in Electron/Node: `v8::ScriptCompiler` cached-data → reconstruct via `v8` source
  flag or `node --expose-internals` tooling (check Node version — flags move around).

## 4. Python

**Version-gate the decompiler — this matters:**

| Python version | Tool |
|---|---|
| ≤ 3.8 | `uncompyle6` |
| 3.9 | `decompyle3` |
| 3.10–3.12 | `pycdc` (compile from source; latest only) |
| newer than tools support | `marshal` + `dis` fallback (works on any version) |

- `.pyc` → decompile → source; **verify with `dis` opcode disassembly** (decompilers lose
  edge-case semantics). The `marshal`+`dis` path reads the code object and its strings directly
  on any version — it never fails on version skew.
- PyInstaller: `pyi-archive_viewer` → extract `pyz` → individual `.pyc` (check magic).
- Nuitka: compiled to C — go to native ref, but note `Nuitka` markers in strings.
- Cython: compiled to C with Python-API calls — recover semantics by tracing `Py*` call sites.
- Obfuscated `.pyc` (custom opcodes, xor'd strings): fix opcode table or use an `uncompyle6`
  fork; string-decrypt helpers are usually a single function — find and trace it.

## 5. Other runtimes (quick pointers)

- **Lua:** `luadec`/`unluac` (bytecode → source); game scripts, embedded configs; watch for JIT.
- **Dart / Flutter (AOT):** `blutter`/`darter` for snapshot parsing; reconstruct classes from
  snapshot metadata.
- **Go (compiled):** `go tool nm`, `objdump` + Go symbol table, `redress` for struct
  reconstruction; interface/`itab` layout is well-documented (see modern-binaries ref).
- **Rust (compiled):** `rustfilt` demangling + generic ABI knowledge (see modern-binaries ref).
- **WASM:** `wasm2wat` → readable IR; `wasm-decomp` → C-like output; `wasmer`/`wasmtime` for
  dynamic tracing with instrumented imports (see modern-binaries ref).

## 6. Cross-runtime rules

- Always prefer **metadata + strings + resource tables** over raw code when available — names
  for free.
- Verify decompiled output at IL/bytecode level for branch-heavy or exception-heavy regions.
- Record tool version in the report — decompiler version changes output shape.
