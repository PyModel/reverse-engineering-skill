#!/usr/bin/env python3
"""Go pclntab locator + best-effort function-name extraction for stripped Go binaries.

Usage: python3 scripts/extract_go_metadata.py <target>
Locates .gopclntab (which survives stripping), checks the magic, and attempts to
parse the function-name table. On uncertain magic, prints a GoReSym hint rather
than guessing. For authoritative reconstruction use GoReSym
(https://github.com/mandiant/GoReSym).
"""
import sys, os, subprocess, struct, re


KNOWN_MAGICS = {
    0xFFFFFFFB: "Go 1.2 - 1.15",
    0xFFFFFFFA: "Go 1.16 - 1.17",
    0xFFFFFFF0: "Go 1.18 - 1.19",
    0xFFFFFFF1: "Go 1.20+",
}


def find_pclntab(target: str, data: bytes):
    # 1. Try ELF section headers via readelf
    try:
        out = subprocess.run(
            ["readelf", "-S", "-W", target],
            capture_output=True, text=True, timeout=30
        ).stdout
        for line in out.splitlines():
            # [Nr] Name Type Address Off Size ...
            m = re.search(r"\[\s*\d+\]\s+\.gopclntab\s+\S+\s+[0-9a-fA-F]+\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)", line)
            if m:
                return int(m.group(1), 16), int(m.group(2), 16)
    except Exception:
        pass

    # 2. Try Mach-O sections via otool
    try:
        out = subprocess.run(
            ["otool", "-l", target],
            capture_output=True, text=True, timeout=30
        ).stdout
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
                if cur_sect in ("__gopclntab", ".gopclntab"):
                    return cur_offset, cur_size
                cur_sect, cur_offset, cur_size = None, None, None
    except Exception:
        pass

    # 3. Direct binary search for known pclntab magic headers
    for magic_bytes in (b"\xf1\xff\xff\xff", b"\xf0\xff\xff\xff", b"\xfa\xff\xff\xff", b"\xfb\xff\xff\xff"):
        pos = 0
        while True:
            idx = data.find(magic_bytes, pos)
            if idx == -1:
                break
            # Validate pclntab header: bytes 4-5 are zero padding, byte 7 is pointer size (4 or 8)
            if idx + 8 <= len(data):
                pad = data[idx + 4: idx + 6]
                ptr_size = data[idx + 7]
                if pad == b"\x00\x00" and ptr_size in (4, 8):
                    return idx, len(data) - idx
            pos = idx + 4

    return None, None


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: python3 scripts/extract_go_metadata.py <target_binary>")
        sys.exit(0 if len(sys.argv) >= 2 else 1)

    target = sys.argv[1]
    if not os.path.exists(target):
        print(f"Error: target file '{target}' not found", file=sys.stderr)
        sys.exit(1)

    with open(target, "rb") as f:
        data = f.read()

    off, size = find_pclntab(target, data)
    if off is None:
        print("No .gopclntab section or signature found. Use GoReSym (github.com/mandiant/GoReSym).")
        return

    blob = data[off: off + size]
    if len(blob) < 8:
        print(f"Error: .gopclntab at @0x{off:x} is too short ({len(blob)} bytes)")
        return

    magic = struct.unpack("<I", blob[:4])[0]
    ver_label = KNOWN_MAGICS.get(magic, "unknown")
    print(f"gopclntab @0x{off:x} size={size} magic=0x{magic:08x} ({ver_label})")

    if magic not in KNOWN_MAGICS:
        print("Magic not recognized -> use GoReSym (github.com/mandiant/GoReSym) for full recovery.")
        return

    quantum = blob[6]
    ptr_size = blob[7]
    print(f"quantum={quantum} ptrSize={ptr_size}")

    # Extract NUL-terminated candidate printable strings
    names = []
    i = 16
    limit = min(len(blob), 2 * 1024 * 1024)
    while i < limit:
        if blob[i] == 0:
            i += 1
            continue
        end = blob.find(b"\x00", i)
        if end < 0:
            break
        if end - i > 250:
            i = end + 1
            continue
        s = blob[i:end]
        if len(s) >= 4 and all(32 <= c < 127 for c in s) and s[:1] not in b"()":
            try:
                decoded = s.decode("utf-8")
                if "." in decoded or "/" in decoded:
                    names.append(decoded)
            except UnicodeDecodeError:
                pass
            i = end + 1
        else:
            i += 1

    print(f"Extracted {len(names)} candidate symbol names (first 20):")
    for n in names[:20]:
        print(f"  {n}")
    print("Tip: pipe through `go tool nm`/GoReSym for authoritative symbol recovery.")


if __name__ == "__main__":
    main()
