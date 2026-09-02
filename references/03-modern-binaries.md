# Modern Binaries — Go, Rust, WASM, Swift

Modern compiled languages are *not* legacy C. Their ABI, symbol layout, and idiom sets are
distinct — wrong assumptions waste time. These sections are aggressive: reconstruct the
metadata, don't fight the runtime.

## 1. Go (1.20+)

Go binaries statically link the runtime — stripped builds are 10–50 MB. `strip` removes
`.symtab`, but **`.gopclntab` survives** and holds function names, package paths, filenames,
and line numbers.

- **Automate:** run `scripts/extract_go_metadata.py <target>` to locate `.gopclntab` and pull
  the function-name table. For authoritative reconstruction, use **GoReSym**
  (github.com/mandiant/GoReSym) — it recovers full func metadata from pclntab.
- **Reconstruct:**
  - `runtime.moduledata` — the runtime module table; locate it via the `runtime.types` /
    `runtime.pclntab` pointers in `.go.buildinfo` or from `runtime.rt0` references.
  - `itab` (interface dispatch) — `go.itab.*` symbols; interface calls go through
    `*(itab+0x18)` type info + `*(itab+0x20)` function pointer. Reconstruct interface dispatch
    tables to recover which concrete type actually implements a call.
  - String/slice headers — Go strings are `(ptr,len)`, slices `(ptr,len,cap)`; the ABI passes
    them as register pairs/triples, never as a single pointer. A 16-byte "string" field is a
    header, not a fixed buffer.
- **Idioms:** `runtime.*` symbols, goroutine machinery (`runtime.newproc`, `runtime.morestack`),
  `runtime.convT64` (interface boxing), no stack-prologue variation, `runtime.duffzero`
  (zero-fill loops).
- **Note:** Go 1.21+ ABI (`go:funcabi`) and register-based calling conventions differ from
  older Go — verify against the specific Go version before assuming SysV-style arg passing.

## 2. Rust

- **v0 mangling (`_R...`)** — modern rustc uses the v0 scheme; parse `_R` symbols directly.
  Demangling: `rustfilt`/`rustc-demangle` (or `c++filt -s rust` where supported).
- **Niche optimizations** — `Option<T>`/`Result<T>` reuse niche values, not extra space:
  - `Option<NonNull<T>>` occupies exactly one pointer; the `None` niche is `0x0`.
  - `Option<&T>` is one pointer (niche = null). `Option<Box<T>>` is one pointer (niche = 0).
  - `Option<NonZeroU32>` is 4 bytes with 0 as the niche — do not infer a separate tag field.
  - `Result<T,E>` may use a niche from `E` — an enum tag is not always a separate discriminant.
- **Panic machinery** — `core::panicking::panic_bounds_check`/`panic_index` reveal array sizes
  and boundary constraints: the panic call site carries the index, length, and often the
  offending value in registers/stack. Use these to infer array lengths and bounds.
- **Layouts:** `#[repr(C)]` = C layout; `#[repr(Rust)]` (default) = unspecified — field order
  and padding are *not* guaranteed. Reconstruct from actual offsets, never assume declaration
  order. `#[repr(transparent)]`/`#[repr(align)]`/`#[repr(packed)]` change alignment — run
  `scripts/validate_struct.py` against the target ABI.
- **Idioms:** `core::iter::Iterator` calls, `core::fmt::Arguments` (format strings), drop glue
  (`core::ptr::drop_in_place`), `#[no_mangle]`/`#[export_name]` for FFI symbols.

## 3. WASM / WASI

- **Tooling:** `wasm2wat` → readable IR; `wasm-decomp` → C-like output; `wasmer`/`wasmtime` for
  dynamic tracing with instrumented imports.
- **Recovery:** extract the module's imports/exports table first — it names the ABI boundary
  (host functions, memory, globals). Reconstruct memory model: linear memory, `__heap_base`,
  `__data_end`, stack pointer global (`__stack_pointer`). Recover functions from the `name`
  custom section if present (usually stripped — infer from call graph instead).
- **WASI:** identify the ABI via `wasi_snapshot_preview1` imports; map fd/errno conventions.
- **Idioms:** `call_indirect` (function pointers/table dispatch), `br_table` (switch), `memory
  grow/copy/fill`, `i32.div_s` (signed division — Rust/LLVM emits explicit checks).

## 4. Swift / Objective-C

- **Swift mangling:** `$s...` demangled via `swift demangle`/`swiftc-demangle`; reconstruct
  module/type/function names from mangled symbols (do not guess from hex).
- **Protocol witness tables** — Swift uses witness tables (like vtables) for protocol
  conformance; a call through a protocol is `call [witness_table + offset]`. Reconstruct the
  witness table to recover which concrete type implements a protocol requirement.
- **Objective-C interop:** `objc_msgSend` dispatch, class/selector tables in `__objc_classlist`
  / `__objc_selrefs`; recover class names and method selectors from the metadata sections —
  names are preserved, use them.
