# Phase 3 — Deep Semantic Analysis (Native Binaries)

## 0. Drive the tool, not the text

For any GUI-free or batch work, use Ghidra Headless instead of a GUI — see
`scripts/ghidra_headless.sh` and `references/10-mcp-tooling.md`. Extract decompiled pseudocode
for specific symbols into workspace files, then reason over it. Never eyeball a hex dump when
the tool can decompile.

```bash
./scripts/ghidra_headless.sh <project_dir> <project> <target> \
  --script decompile_functions.py --symbols 'main|sub_1400.*' --out ./decompiled/
```

## 1. Assembly idioms → meaning (translation table)

### x86_64
| Idiom | Meaning |
|-------|---------|
| `mov rax, [rbp+var]; cmp; jcc` with const | opaque predicate (obfuscation) |
| `lea rax, [rip+0x...]` | PC-relative data/function address (PIC) |
| `xor eax, eax; sete al` | `return (a == b)` — compare idiom |
| `movsxd rax, ecx` | sign-extend 32→64 (int → size_t) |
| `cmp rax, rdx; ja` | unsigned compare (pointer/size arithmetic) |
| `test rax, rax; js` | signed test (negative check on int, not pointer) |
| `rdtsc` / `QueryPerformanceCounter` | timing/anti-debug check |
| `cpuid` / `rdrand` | feature check / RNG |
| `mov rax, fs:[0x30]` | PEB access (Windows) — anti-analysis |
| `syscall` / `int 0x80` / `sysenter` | direct syscalls (often obfuscation/hiding) |
| `call qword ptr [rax+0x18]` | vtable / dispatch-table call |
| `lea rax, [rbp-0x40]; mov rcx, 0x10; call memcpy@plt` | stack buffer copy (note size) |
| `sub rsp, 0x100; lea rax, [rsp+...]` | alloca-like, variable stack frame |
| `movaps [rsp+...], xmm` | SSE struct copy / ABI spill area |
| `endbr64` | CFI/CET — legitimate control flow, not obfuscation |

### ARM64
| Idiom | Meaning |
|-------|---------|
| `adrp x0, ...; add x0, x0, #lo` | PC-relative address |
| `cset/csel/ccmp` | conditional-select idiom (branchless compare) |
| `ldp/stp x29, x30, [sp, -N]` | prologue with frame pointer + return addr |
| `dmb ish` / `ldaxr/stlxr` | memory barrier / atomic ops |
| `mrs x8, NZCV` / `msr` | flags/feature register access |
| `svc #0` | syscall |
| `br x8` (register branch) | indirect/dispatch (obfuscation or vtable) |
| `stur/ldur` (unprefixed) | misaligned or negative-offset access — note it |

### MIPS / RISC-V
- Delayed load/branch slots (MIPS): decompilers misplace them — verify.
- `lui/addiu` pairs: 32-bit constant materialization.
- RISC-V: `auipc/addi` PC-relative pairs; `fence`/`fence.i` barriers; `jalr` register dispatch.

## 2. Type reconstruction from access patterns

Method (works with or without symbols):
1. **Collect accesses** to a buffer/register: `[rax+0x00]`, `[rax+0x08]`, `[rax+0x0C]`,
   `[rax+0x10]` … with sizes (byte/half/word/qword).
2. **Bucket by size & alignment:** qword at `0x00` and `0x08` → two pointers or an int64+ptr;
   dword at `0x0C` → 32-bit field; byte at `0x0F` → bool/flag or packed data.
3. **Apply ABI rules:** x86_64 SysV: struct ≤16 bytes passed in registers (`rdx:rax`, `rcx:rdx`);
   Windows: `.data`-relativism, `sret` for >8-byte structs; ARM64: composite args passed via
   `x8` (indirect) if >16 bytes.
4. **Guess semantics:** pointer followed by `call [rax+0x08]` → object with vtable;
   `[rax+0x08]` used with `strcmp` → string pointer; dword at fixed offset incremented in a
   loop → counter/length; qword at offset 0 set from `malloc`/`operator new` return → embedded
   pointer field.
5. **Name conservatively:** `field_0x00_ptr`, `field_0x08_count` — rename only when semantics
   are *observed*, not assumed.
6. **Cross-check with allocator sizes:** `malloc(0x2C)` → struct ≤0x2C bytes;
   `operator new(0x30)` → C++ class ≤0x30 bytes (incl. vtable ptr at 0x00).
7. **Validate mechanically:** run `scripts/validate_struct.py` on your struct table to catch
   overlapping offsets and ABI alignment mistakes before reporting.

Example reconstruction:
```c
// Accesses: *(u32*)(rax+0x00) read/write; *(u64*)(rax+0x08) read;
// *(u32*)(rax+0x10) read; call *(u64*)(rax+0x18)
struct Obj {
    uint32_t id;          // +0x00
    /* pad */             // +0x04
    const char *name;     // +0x08 (used with strlen/strcmp)
    uint32_t flags;       // +0x10
    /* pad */             // +0x14
    void (*fn)(Obj*);     // +0x18 (called indirectly)
};  // sizeof = 0x20
```

## 3. vtable / class hierarchy reconstruction

- Find vtable: array of function pointers in `.data.rel.ro` (ELF) / `.rdata` (PE) /
  `__data` (Mach-O), referenced by `lea` at object offset 0.
- Reconstruct: slot 0 = dtor (often), slots 1..N = virtuals; count via `call [vtbl+idx]` sites.
- Cross-vtable: two vtables sharing slots → common base class. Diff slots to infer
  override/extension.
- RTTI (MSVC): `CompleteObjectLocator` → type descriptor → class name string.
  Itanium ABI: `_ZTI` structures → typeinfo with name.

## 4. Dataflow / lifecycle analysis

- Track: allocation → use → free. Note double-free, UAF, leak (also useful for security review).
- String lifecycles: `strlen` result stored → length field; concatenation patterns → string
  class (SSO on MSVC: buffer at offset 0x20, capacity 0xF — a strong MSVC `std::string` marker).
- State mutations: fields written in only one function → that function is a setter (state
  owner). Fields read in many → hot config/status.
- Serialization boundaries: `memcpy`/`fwrite`/`send` with struct-sized lengths → wire format
  (go to protocol ref).

## 5. Idiom translation to clean pseudocode

Always produce *two* layers:
1. **Faithful pseudocode** — matches decompiled output, with register/offset comments preserved.
2. **Idiomatic rewrite** — modern, readable equivalent (C++/Rust/Go/TS pseudocode), preserving
   behavior, not instruction-level noise.

```c
// Faithful (from decompiler):
u32 result; u32 tmp = *(u32*)(a+0x10) ^ 0xDEADBEEF;
result = ((tmp << 0x1D) | (tmp >> 0x3)) ^ *(u32*)(a+0x14);

// Idiomatic:
u32 h = (rotl(field->key ^ 0xDEADBEEF, 29)) ^ field->salt;
```

## 6. Cross-check before reporting

- One tool's pseudocode is a hypothesis, not a fact. Re-verify the semantic claim against raw
  disassembly, or run the same function through a second tool (Ghidra ↔ Binary Ninja / r2).
- If two tools disagree on control flow or types, trust the one whose output re-derives the
  observed strings and API calls — and note the disagreement.

## 7. What to do with uncertainty

- Mark unknowns: `field_0x24 /* purpose TBD */`, `sub_14000...`.
- Never invent names without labeling them `proposed:` (vs `observed:` from strings/symbols/RTTI).
- Record *why* you inferred a type ("size 0x2C from malloc site at 0x4012A0, 5 dword accesses
  at +0x00/+0x04/+0x08/+0x10/+0x28") — the evidence line is part of the deliverable.
