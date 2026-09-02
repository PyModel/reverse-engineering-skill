# Phase 0 — Tool Access: Driving the RE Tool via MCP

The 2025/2026 workflow is agent-native: the model **drives the RE tool directly through an MCP
server** — decompile, xref, types, patch — instead of reading text the human analyst would
have produced. Never eyeball a hex dump when the tool can answer for you.

## 1. Pick the server

| Tool | Server | Notes |
|------|--------|-------|
| Ghidra | **GhidraMCP** (~5.4k stars, most comprehensive) | GUI + multi-client |
| Ghidra (headless/CI) | **ghidra-headless-mcp** | containerized, GUI-free — best for headless harnesses |
| Ghidra (AI-first) | **ReVa** (reverse-engineering-assistant) | tool-driven + chain-of-reasoning |
| IDA Pro | **ida-pro-mcp** | 20+ tools, automated install |
| Binary Ninja | **binary-ninja-mcp** / binja-lattice-mcp | BN API; lattice = security-focused |
| Binary Ninja (headless) | **binary-ninja-headless-mcp** | containerized, GUI-free |
| radare2 | **radare2-mcp** (official) | 26+ tools, STDIO transport |
| Cutter/Rizin | **CutterMCP** | modern GUI integration |
| Android (Jadx/APK) | **Jadx-MCP**, apktool-mcp-server | mobile RE |
| x64dbg (Windows) | **x64dbgMCP** | 40+ SDK tools |

## 2. ReVa's philosophy — adopt it

ReVa deliberately exposes **many small, well-defined tools** to the model (like a human analyst
uses a small set of RE tools) combined with **chain-of-reasoning**, to limit context rot and
reduce hallucination on long tasks. Do NOT ask the tool for "decompile everything and explain" —
instead:

- Ask for a single function's disassembly + decompiled output + its xrefs/imports.
- Pull strings/API usage/symbols as *context* for that function only.
- Rename/types only what you can justify; write comments back to the database.
- Keep each query small and bounded; chain reasoning across queries.

This is the "small tools" pattern that the serious labs (e.g. SentinelOne's multi-agent malware
pipeline across radare2/Ghidra/BN/IDA) rely on to catch hallucinated meaning.

## 3. Headless for automation

- **ghidra-headless-mcp** / **binary-ninja-headless-mcp** run cleanly in containerized or
  GUI-free workflows — ideal for CI and headless coding-agent harnesses.
- For batch decompilation without an interactive session, use `scripts/ghidra_headless.sh`
  (wraps `analyzeHeadless` with `-import`, `-postScript`, `-deleteProject`).

## 4. Dynamic / network MCP

| Need | Server |
|---|---|
| Live instrumentation | **frida-mcp** |
| Network/PCAP analysis | **WireMCP** (Wireshark), Burp Suite MCP, ZAP-MCP |
| Debugger stepping | **GDB MCP**, **LLDB** (native MCP as of June 2025) |
| Windows debugging | **x64dbgMCP** |

## 5. Known gaps — fall back to CLI

No MCP server exists yet for: packers/unpackers (UPX, PEiD, Detect-It-Easy), fuzzing (AFL++,
libFuzzer), WinDbg, malware sandboxes (Cuckoo/CAPE), file-format tools (binwalk, ExifTool). When
you hit these, use the CLI directly and feed the output back as context — don't wait for a
server that doesn't exist.

## 6. Guardrail

Prefer **local evidence over web claims** — the binary is ground truth. Web research fills gaps
(see `01-triage.md` §Research); it never overrides what the tool shows you.
