#!/usr/bin/env python3
"""Validates a reconstructed struct table: no overlapping offsets, sane alignment.

Usage: python3 scripts/validate_struct.py <struct.json>
Expects JSON: {"fields": [{"name": ..., "offset": int, "size": int, ...}], "total_size": int}
Prints padding gaps and errors. Exit code 1 on overlap/size violations.
"""
import sys, json, os


def to_int(val, field_name="value"):
    if val is None:
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        try:
            return int(val, 0)
        except ValueError:
            raise ValueError(f"Invalid integer/hex value '{val}' for {field_name}")
    raise TypeError(f"Expected int or hex string for {field_name}, got {type(val).__name__}")


def validate_layout(fields, total_size=None):
    current = 0
    errors = []
    
    parsed_fields = []
    for idx, f in enumerate(fields):
        name = f.get("name", f"field_{idx}")
        try:
            off = to_int(f.get("offset"), f"'{name}' offset")
            size = to_int(f.get("size"), f"'{name}' size")
        except (ValueError, TypeError) as e:
            errors.append(str(e))
            continue

        if off is None or size is None:
            errors.append(f"Missing offset or size for '{name}'")
            continue
        if off < 0:
            errors.append(f"Negative offset {hex(off)} for '{name}'")
        if size <= 0:
            errors.append(f"Non-positive size {size} for '{name}'")

        parsed_fields.append({"name": name, "offset": off, "size": size})

    parsed_total_size = None
    if total_size is not None:
        try:
            parsed_total_size = to_int(total_size, "total_size")
        except (ValueError, TypeError) as e:
            errors.append(str(e))

    for f in sorted(parsed_fields, key=lambda x: x["offset"]):
        off = f["offset"]
        size = f["size"]
        if off < current:
            errors.append(f"Overlap at {hex(off)} for '{f['name']}' (current end {hex(current)})")
        elif off > current:
            print(f"Padding: {off - current} bytes before '{f['name']}' at {hex(current)}")
        current = off + size

    if parsed_total_size is not None:
        if current > parsed_total_size:
            errors.append(f"Fields exceed total size ({hex(current)} > {hex(parsed_total_size)})")
        elif current < parsed_total_size:
            print(f"Trailing padding: {parsed_total_size - current} bytes at {hex(current)} (up to total size {hex(parsed_total_size)})")

    return errors


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: python3 scripts/validate_struct.py <struct.json>")
        print("JSON format: {\"fields\": [{\"name\": \"...\", \"offset\": 0x0, \"size\": 4}], \"total_size\": 0x18}")
        sys.exit(0 if len(sys.argv) >= 2 else 1)

    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"Error: file '{path}' not found", file=sys.stderr)
        sys.exit(1)

    try:
        with open(path) as f:
            doc = json.load(f)
    except Exception as e:
        print(f"Error parsing JSON from '{path}': {e}", file=sys.stderr)
        sys.exit(1)

    errors = validate_layout(doc.get("fields", []), doc.get("total_size"))
    for e in errors:
        print(f"ERROR: {e}")
    print("OK: layout valid" if not errors else f"FAILED: {len(errors)} error(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
