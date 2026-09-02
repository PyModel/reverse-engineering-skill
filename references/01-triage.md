# Phase 1 — Triage & Surface Analysis

Know *what* you're looking at before reading disassembly. Wrong toolchain assumptions produce
wrong decompilation and wrong conclusions. **Run the scripts first** — do not hand-calculate.

## 0. Automate the mechanical part

```bash
python3 scripts/triage_binary.py <target>          # magic, arch, entropy, compiler hints
python3 scripts/calculate_entropy.py <target>      # section-by-section Shannon entropy
```

The scripts output the container/arch/toolchain/entropy fields — paste them into the triage
template and spend your reasoning on semantics, not on parsing headers.

## 1. Container identification

| Signal | Meaning |
|--------|---------|
| File magic `7F 45 4C 46` | ELF (check e_machine: `3E`=x86_64, `B7`=ARM64, `08`=MIPS, `F3`=RISC-V) |
| File magic `4D 5A` | PE/COFF (check machine in optional header; `BSJB` in headers = .NET assembly) |
| File magic `CF FA ED FE` / `FE ED FA CF` | Mach-O 64-bit (LE / BE); universal fat if `CA FE BA BE`/`CA FE BA BF` |
| File magic `CE FA ED FE` / `FE ED FA CE` | Mach-O 32-bit (LE / BE) |
| File magic `CA FE BA BE` (major ver ≥ 45) | Java `.class` bytecode |
| `PK \x03\x04` zip | Jar/APK/IPA/docx-like — unpack first |
| `64 65 78 0A` (`dex\n`) | Android DEX → Jadx |
| `00 61 73 6D` (`\x00asm`) | WebAssembly → wasm2wat / wasm-decomp |
| `04 00 00 00` + `{"files":` | ASAR (Electron archive) → `npx asar extract` |
| `#!` shebang | Script → analyze source directly |
| `V8 bytecode` (cachedData) | Node/Electron snapshot → v8 disassembler |
| PyInstaller (`MEI`/`pyi`), Nuitka, Cython, `.pyc` | Python-family → managed-runtimes ref |

Quick commands:
```bash
file <target>; xxd -l 64 <target>; md5sum <target>
strings -n 6 <target> | head -100        # early strings: paths, URLs, tool hints
readelf -h / objdump -f / otool -h       # arch, endian, entry
```

## 2. Toolchain fingerprinting

Compiler identification from artifacts (idiosyncrasies, not exact science):
- **MSVC:** `__chkstk`, `@@` decoration, `call __security_check_cookie`, SEH flow, `GS` cookie.
- **GCC/Clang:** `__stack_chk_fail`, `endbr64` (CFI), `sub rsp, 0x...` prologue, `.comment` version.
- **Rust:** panic machinery (`core::panicking`), `Option<T>`/`Result<T>` niche layouts,
  `#[no_mangle]`, v0 mangling (`_R...`).
- **Go:** `runtime.*` symbols, goroutine machinery, `go.itab.*`, `runtime.moduledata`,
  string/slice header idioms.
- **D/Ada/OCaml:** exception/runtime idioms — note them, don't fight them.
- **Build systems:** `.comment`, `Build ID`, `.go.buildinfo`, rustc PDB paths, PDB/`debug` sections.

## 3. Packing / obfuscation status

- **Packed:** high entropy sections, few imports, `UPX!`/`VMProtect`/`Themida`/`.aspack`/`.nsp`
  section names, `Entropy > 7.0` per section, stub-like small code section.
- **Obfuscated (in-place):** normal imports but odd control flow (flattening → dispatcher
  variable; opaque predicates → `cmp`/`jcc` with constant operands; string blobs → XOR/RC4
  decryptors; VM handlers).
- **Anti-analysis:** anti-debug (`IsDebuggerPresent`, `ptrace`, `0x1F` after `int3`), anti-VM
  (cpuid, timing, MAC prefixes), self-CRC, `NtSetInformationThread(ThreadHideFromDebugger)`,
  TLS callbacks, `LD_PRELOAD` checks. Neutralize before deep analysis — see deobfuscation ref.

## 4. Symbol & import surface

- Exports/imports: `nm`, `readelf --dyn-syms`, `dumpbin /exports`, `objdump -T`, `jtool`,
  `nm -gU` (Mach-O).
- Import-table reconstruction for packed PEs (solve after unpacking).
- Note forwarded imports, delay-load DLLs, `dlsym`/`GetProcAddress` dynamic resolution
  (obfuscation vector — see deobfuscation ref).
- RTTI: `Microsoft::RTP` classes, `.rdata` vtable strings, `std::` symbols — strong C++
  signal; try class reconstruction from vtable layout.

## 5. Entry points & first-pass surface

- ELF: `e_entry`, `init_array`/`preinit_array`, constructors; PE: `AddressOfNew... Code`
  entry + TLS callbacks; Mach-O: `LC_MAIN`, `__mod_init_func`.
- Note the "real" main — unpackers often fake the entry; the real main is reached after unpack.
- Strings triage: error messages, file paths, URLs, protocol keywords, log format strings,
  license markers, embedded resource names. Group them — they seed Phase 3 hypotheses.

## 6. Research (Phase 2 — as needed)

Unfamiliar format/toolchain/packer/protocol? Look it up — but **local evidence decides**;
research only fills gaps, never overrides the binary.

| Need | Tool |
|---|---|
| Library/framework/tool API (angr, Miasm, Ghidra scripting API) | **context7** |
| Official spec / RFC / ISA / ABI doc, full page | **firecrawl scrape** |
| Quick facts / known-CVE / tool existence | **tavily search** |
| Docs-site crawl for offline reference | **firecrawl crawl** |

Rules: query with specific nouns (tool/format/packer names, quoted error strings). Prefer
primary sources (official docs, spec papers). 2–3 searches max per question — if unresolved,
switch to local brute-force. Cite URL + confidence + `web:` label. On conflict, **local wins**.

## Triage output template (produce before anything else)

```
Container:    ELF64 / PE64 / Mach-O / Jar / .NET / ASAR / pyc / WASM
Arch:         x86_64 / ARM64 / MIPS / RISC-V / MSIL / JVM / WASM
Toolchain:    GCC 13 (Ubuntu) / MSVC 2022 / rustc 1.7x / go 1.2x / MSIL (Roslyn)
Runtime:      glibc 2.36 / .NET 8 / Node 20 / Android 13
Packing:      none / UPX / VMProtect / custom (entropy: <list>)
Obfuscation:  none / flattening / string-enc / anti-debug / VM
Symbols:      full / partial / stripped (note what's left)
Entry:        0x... (main at ...; note init/TLS)
Surface:      <N> exports, <N> imports, <M> notable strings
First hypotheses: <2-3 bullet guesses about what this program does>
```

Only proceed to Phase 3 with this table filled.
