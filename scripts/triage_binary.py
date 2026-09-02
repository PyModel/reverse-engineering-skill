#!/usr/bin/env python3
"""Fast triage: container, architecture, entropy, compiler hints.

Usage: python3 scripts/triage_binary.py <target>
Prints a triage-ready report. Mechanical only — no external tooling required.
"""
import sys, math, os, re, subprocess


def shannon_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = [0.0] * 256
    for b in data:
        counts[b] += 1
    total = len(data)
    entropy = 0.0
    for c in counts:
        if c:
            p = c / total
            entropy -= p * math.log2(p)
    return entropy


def magic(data: bytes) -> str:
    if len(data) < 4:
        return "empty/too small"
    if data[:4] == b"\x7fELF":
        is_64 = data[4] == 2
        endian = "little" if data[5] == 1 else "big"
        order = "<H" if endian == "little" else ">H"
        import struct
        machine = struct.unpack(order, data[18:20])[0] if len(data) >= 20 else 0
        arch_map = {0x03: "x86", 0x3E: "x86_64", 0x28: "ARM", 0xB7: "ARM64", 0x08: "MIPS", 0xF3: "RISC-V"}
        arch = arch_map.get(machine, f"machine={hex(machine)}")
        bit_str = "ELF64" if is_64 else "ELF32"
        return f"{bit_str} ({arch}, {endian}-endian)"
    if data[:2] == b"MZ":
        if b"BSJB" in data[:4096]:
            return "PE/COFF (.NET assembly / CLR header detected)"
        return "PE/COFF"
    # Mach-O headers
    if data[:4] in (b"\xCF\xFA\xED\xFE", b"\xFE\xED\xFA\xCF"):
        cputype = int.from_bytes(data[4:8], "little" if data[:4] == b"\xCF\xFA\xED\xFE" else "big")
        cpu_map = {0x01000007: "x86_64", 0x0100000C: "ARM64"}
        return f"Mach-O 64-bit ({cpu_map.get(cputype, hex(cputype))})"
    if data[:4] in (b"\xCE\xFA\xED\xFE", b"\xFE\xED\xFA\xCE"):
        return "Mach-O 32-bit"
    if data[:4] in (b"\xCA\xFE\xBA\xBE", b"\xBE\xBA\xFE\xFE"):
        # Disambiguate Java .class vs Mach-O universal fat binary
        major = int.from_bytes(data[6:8], "big")
        if major >= 45 and major <= 70:
            return f"Java .class bytecode (v{major})"
        return "Mach-O (fat/universal)"
    if data[:4] == b"\xCA\xFE\xBA\xBF":
        return "Mach-O 64-bit (fat/universal)"
    if data[:2] == b"PK":
        return "ZIP (jar/apk/ipa/docx-like) — unpack first"
    if data[:4] == b"\x00asm":
        return "WebAssembly (.wasm)"
    if data[:4] == b"\x04\x00\x00\x00" and b'"files"' in data[:1024]:
        return "ASAR (Electron archive) — asar extract"
    if data[:4] == b"BSJB":
        return ".NET metadata stream — ILSpy/dnSpy"
    if data[:4] == b"dex\n":
        return "Android DEX — Jadx"
    if data[:2] == b"#!":
        return "Script (shebang)"
    return f"unknown magic {data[:4].hex()}"


def compiler_hints(target: str) -> str:
    try:
        out = subprocess.run(
            ["strings", "-n", "6", target], capture_output=True, text=True, timeout=30
        ).stdout
    except Exception:
        return "strings unavailable"
    hints = []
    for kw, label in [
        (r"gcc|clang", "GCC/Clang"),
        (r"rustc|core::panicking", "Rust"),
        (r"runtime\.|go\.buildinfo|go\.itab", "Go"),
        (r"msvc|__security_check_cookie|__chkstk", "MSVC"),
        (r"upx", "UPX-packed"),
        (r"vmprotect|themida", "VM-packed"),
        (r"\.net|mscorlib", ".NET"),
        (r"cpython", "Python"),
        (r"swift", "Swift"),
    ]:
        if re.search(kw, out, re.IGNORECASE):
            hints.append(label)
    return ", ".join(hints) if hints else "none detected (check symbols/sections manually)"


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: python3 scripts/triage_binary.py <target_binary>")
        sys.exit(0 if len(sys.argv) >= 2 else 1)

    target = sys.argv[1]
    if not os.path.exists(target):
        print(f"Error: target file '{target}' not found", file=sys.stderr)
        sys.exit(1)

    with open(target, "rb") as f:
        header = f.read(4096)
    
    with open(target, "rb") as f:
        full_data = f.read()
    ent = shannon_entropy(full_data)

    print(f"File:        {target} ({os.path.getsize(target):,} bytes)")
    print(f"Container:   {magic(header)}")
    print(f"Entropy:     {ent:.2f} bits/byte ({'packed/obfuscated' if ent > 7.0 else 'normal'})")
    print(f"Compiler:    {compiler_hints(target)}")
    print(f"Suggested:   triage template in references/01-triage.md")


if __name__ == "__main__":
    main()
