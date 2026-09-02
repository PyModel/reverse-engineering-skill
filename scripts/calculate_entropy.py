#!/usr/bin/env python3
"""Section-by-section Shannon entropy for packing/obfuscation detection.

Usage: python3 scripts/calculate_entropy.py <target>
If the target is ELF and readelf is available, computes per-section entropy;
otherwise falls back to whole-file block entropy. Entropy > 7.0 per section is
a strong packing/obfuscation signal.
"""
import sys, math, os, subprocess


def shannon(data: bytes) -> float:
    if not data:
        return 0.0
    counts = [0.0] * 256
    for b in data:
        counts[b] += 1
    total = len(data)
    ent = 0.0
    for c in counts:
        if c:
            p = c / total
            ent -= p * math.log2(p)
    return ent


def elf_sections(target: str):
    try:
        out = subprocess.run(
            ["readelf", "-S", "-W", target], capture_output=True, text=True, timeout=30
        ).stdout
    except Exception:
        return []
    sections = []
    for line in out.splitlines():
        m = re_search(line)
        if m:
            sections.append((m[0], int(m[1], 16), int(m[2], 16)))
    return sections


def macho_sections(target: str):
    try:
        out = subprocess.run(
            ["otool", "-l", target], capture_output=True, text=True, timeout=30
        ).stdout
    except Exception:
        return []
    import re
    sections = []
    cur_sect = None
    cur_offset = None
    cur_size = None
    for line in out.splitlines():
        line = line.strip()
        m_sect = re.match(r"^sectname\s+(\S+)", line)
        if m_sect:
            cur_sect = m_sect.group(1)
            continue
        m_size = re.match(r"^size\s+0x([0-9a-fA-F]+)", line)
        if m_size and cur_sect:
            cur_size = int(m_size.group(1), 16)
            continue
        m_off = re.match(r"^offset\s+(\d+)", line)
        if m_off and cur_sect and cur_size is not None:
            cur_offset = int(m_off.group(1))
            sections.append((cur_sect, cur_offset, cur_size))
            cur_sect, cur_offset, cur_size = None, None, None
    return sections


def re_search(line):
    import re
    # name, offset, size
    m = re.search(r"\[\s*\d+\]\s+(\S+)\s+\S+\s+[0-9a-fA-F]+\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)", line)
    return m.groups() if m else None


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: python3 scripts/calculate_entropy.py <target_binary>")
        sys.exit(0 if len(sys.argv) >= 2 else 1)

    target = sys.argv[1]
    if not os.path.exists(target):
        print(f"Error: target file '{target}' not found", file=sys.stderr)
        sys.exit(1)

    with open(target, "rb") as f:
        data = f.read()

    sections = elf_sections(target)
    format_type = "ELF"
    if not sections:
        sections = macho_sections(target)
        format_type = "Mach-O"

    if sections:
        print(f"Per-section entropy ({format_type}):")
        flagged = []
        for name, off, size in sections:
            if size == 0 or off + size > len(data):
                continue
            block = data[off: off + size]
            e = shannon(block)
            flag = "  <-- high" if e > 7.0 else ""
            if e > 7.0:
                flagged.append(name)
            print(f"  {name:<24} size={size:>10}  entropy={e:.2f}{flag}")
        print(f"High-entropy sections: {', '.join(flagged) if flagged else 'none'}")
    else:
        print("No ELF/Mach-O section table (or tools unavailable). Whole-file block entropy:")
        step = 4096
        blocks = []
        for i in range(0, len(data), step):
            block = data[i:i + step]
            e = shannon(block)
            blocks.append((i, len(block), e))
        
        # If file is large, show high entropy blocks and distribution instead of thousands of lines
        if len(blocks) > 32:
            high_blocks = [b for b in blocks if b[2] > 7.0]
            print(f"  Total 4KB blocks: {len(blocks)} ({len(high_blocks)} high entropy > 7.0)")
            print("  First 8 blocks:")
            for i, sz, e in blocks[:8]:
                flag = "  <-- high" if e > 7.0 else ""
                print(f"    @0x{i:08x} size={sz:>5} entropy={e:.2f}{flag}")
            if high_blocks:
                print(f"  High entropy blocks (first 10 of {len(high_blocks)}):")
                for i, sz, e in high_blocks[:10]:
                    print(f"    @0x{i:08x} size={sz:>5} entropy={e:.2f}  <-- high")
        else:
            for i, sz, e in blocks:
                flag = "  <-- high" if e > 7.0 else ""
                print(f"  @0x{i:08x} size={sz:>5} entropy={e:.2f}{flag}")

    print(f"Overall entropy: {shannon(data):.2f} bits/byte")


if __name__ == "__main__":
    main()
