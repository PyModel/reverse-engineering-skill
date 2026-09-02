# Ghidra post-script for headless batch decompilation.
# Run via scripts/ghidra_headless.sh. Args: "<symbol-regex>|<output-dir>"
# Decompiles matching functions and writes C pseudocode + disassembly to files.
# @category Analysis

import re, os
from ghidra.util.task import ConsoleTaskMonitor
from ghidra.app.decompiler import DecompInterface

args = getScriptArgs()
symbol_re = ".*"
out_dir = "."

if args:
    if len(args) == 1 and "|" in args[0]:
        parts = args[0].split("|", 1)
        symbol_re = parts[0] if parts[0] else ".*"
        out_dir = parts[1] if parts[1] else "."
    else:
        symbol_re = args[0] if args[0] else ".*"
        if len(args) > 1:
            out_dir = args[1]

if not os.path.exists(out_dir):
    os.makedirs(out_dir)

monitor = ConsoleTaskMonitor()
listing = currentProgram.getListing()
fm = currentProgram.getFunctionManager()
pattern = re.compile(symbol_re)

decomp = DecompInterface()
decomp.openProgram(currentProgram)

count = 0
for func in fm.getFunctions(True):
    name = func.getName()
    if not pattern.match(name):
        continue
    # Decompiled C
    res = decomp.decompileFunction(func, 30, monitor)
    code = res.getDecompiledFunction().getC() if (res and res.getDecompiledFunction()) else "// Decompilation failed or timed out"
    # Disassembly
    body = func.getBody()
    dis = []
    addr = body.getMinAddress()
    while addr is not None and addr.compareTo(body.getMaxAddress()) <= 0:
        cu = listing.getCodeUnitAt(addr)
        if cu is not None:
            dis.append(cu.toString())
        addr = addr.add(1 if cu is None else cu.getLength())
    safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
    out = os.path.join(out_dir, safe_name + ".c")
    with open(out, "w") as f:
        f.write("// function: " + name + " @ " + hex(func.getEntryPoint().getOffset()) + "\n")
        f.write(code + "\n\n// disassembly:\n" + "\n".join(dis) + "\n")
    count += 1

print("decompiled {} functions to {}".format(count, out_dir))
