// trace_ipc.js — intercept IPC boundary calls (sockets, pipes, Mach ports) and
// log framing bytes before/after transformation. Use to reconstruct wire framing.
// Usage: frida -n <target> -l trace_ipc.js

const log = (s) => console.log("[ipc] " + s);

const hex = (buf) => {
  if (!buf) return "";
  try {
    return Array.from(new Uint8Array(buf))
      .map(b => b.toString(16).padStart(2, "0"))
      .join(" ");
  } catch (e) {
    return "<unreadable>";
  }
};

// Sockets / IPC: send / sendto / write
for (const name of ["send", "sendto", "write"]) {
  const p = Module.findExportByName(null, name);
  if (!p) continue;
  Interceptor.attach(p, {
    onEnter(args) {
      this.len = args[2].toInt32();
      this.buf = args[1];
      this.fd = args[0].toInt32();
    },
    onLeave(retval) {
      const written = retval.toInt32();
      if (written > 0 && this.buf && !this.buf.isNull()) {
        try {
          const preview = this.buf.readByteArray(Math.min(written, 32));
          log(`${name} fd=${this.fd} bytes=${written} preview=[${hex(preview)}]`);
        } catch (e) {}
      }
    },
  });
}

// Sockets / IPC: recv / recvfrom / read
for (const name of ["recv", "recvfrom", "read"]) {
  const p = Module.findExportByName(null, name);
  if (!p) continue;
  Interceptor.attach(p, {
    onEnter(args) {
      this.len = args[2].toInt32();
      this.buf = args[1];
      this.fd = args[0].toInt32();
    },
    onLeave(retval) {
      const readBytes = retval.toInt32();
      if (readBytes > 0 && this.buf && !this.buf.isNull()) {
        try {
          const preview = this.buf.readByteArray(Math.min(readBytes, 32));
          log(`${name} fd=${this.fd} bytes=${readBytes} preview=[${hex(preview)}]`);
        } catch (e) {}
      }
    },
  });
}

// Named pipes / FIFOs: open/mkfifo
for (const name of ["open", "mkfifo"]) {
  const p = Module.findExportByName(null, name);
  if (!p) continue;
  Interceptor.attach(p, {
    onEnter(args) {
      if (args[0] && !args[0].isNull()) {
        try {
          log(`${name} path=${args[0].readUtf8String()}`);
        } catch (e) {}
      }
    },
  });
}

// macOS Mach ports: log MIG message size on mach_msg
const mach = Module.findExportByName(null, "mach_msg");
if (mach) {
  Interceptor.attach(mach, {
    onEnter(args) {
      const size = args[1].toInt32();
      log(`mach_msg size=${size}`);
    },
  });
}

// Windows named pipes: CreateFileW with pipe names
const cfw = Module.findExportByName(null, "CreateFileW");
if (cfw) {
  Interceptor.attach(cfw, {
    onEnter(args) {
      if (args[0] && !args[0].isNull()) {
        try {
          const path = args[0].readUtf16String();
          if (path && path.includes("\\\\.\\pipe\\")) {
            log(`CreateFileW pipe=${path}`);
          }
        } catch (e) {}
      }
    },
  });
}

log("ipc hooks installed");
