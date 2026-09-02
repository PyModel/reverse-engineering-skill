// ssl_unpin.js — universal TLS certificate pinning bypass for Android/iOS/macOS.
// Usage: frida -n <target> -l ssl_unpin.js
// Covers OpenSSL, BoringSSL, iOS/macOS Security framework, and Android Conscrypt.

const log = (s) => console.log("[ssl] " + s);

// --- 1. OpenSSL Native Hooks ---
function hook_openssl_verify(name) {
  const p = Module.findExportByName(null, name);
  if (!p) return;
  Interceptor.attach(p, {
    onEnter(args) {
      log(`${name} ctx=${args[0]} mode=${args[1]} -> forcing SSL_VERIFY_NONE (0)`);
      args[1] = ptr(0); // SSL_VERIFY_NONE = 0
      args[2] = NULL;   // Clear custom verify callback
    },
  });
}
for (const fn of ["SSL_CTX_set_verify", "SSL_set_verify"]) {
  hook_openssl_verify(fn);
}

// OpenSSL cert verify callback hook
const ssl_cert_cb = Module.findExportByName(null, "SSL_CTX_set_cert_verify_cb");
if (ssl_cert_cb) {
  const always_ok_cb = new NativeCallback((store_ctx, arg) => 1, "int", ["pointer", "pointer"]);
  Interceptor.replace(ssl_cert_cb, new NativeCallback((ctx, cb, arg) => {
    const orig = new NativeFunction(ssl_cert_cb, "void", ["pointer", "pointer", "pointer"]);
    orig(ctx, always_ok_cb, NULL);
    log("SSL_CTX_set_cert_verify_cb -> replaced with always-ok callback");
  }, "void", ["pointer", "pointer", "pointer"]));
}

// --- 2. BoringSSL (Android / iOS / macOS) ---
// enum ssl_verify_result_t { ssl_verify_ok = 0, ssl_verify_invalid = 1, ssl_verify_retry = 2 };
const boring_custom_cb = new NativeCallback((ssl, out_alert) => 0, "int", ["pointer", "pointer"]);
for (const name of ["SSL_CTX_set_custom_verify", "SSL_set_custom_verify"]) {
  const p = Module.findExportByName(null, name);
  if (p) {
    Interceptor.replace(p, new NativeCallback((ssl_or_ctx, mode, cb) => {
      const orig = new NativeFunction(p, "void", ["pointer", "int", "pointer"]);
      orig(ssl_or_ctx, 0, boring_custom_cb);
      log(`${name} -> replaced custom verify with always-ok callback`);
    }, "void", ["pointer", "int", "pointer"]));
  }
}

// --- 3. iOS / macOS: Security Framework ---
// Modern: OSStatus SecTrustEvaluateWithError(SecTrustRef trust, CFErrorRef *error) (iOS 12+, macOS 10.15+)
const stewe = Module.findExportByName(null, "SecTrustEvaluateWithError");
if (stewe) {
  Interceptor.replace(stewe, new NativeCallback((trust, error) => {
    log("SecTrustEvaluateWithError -> forced true (trusted)");
    if (error && !error.isNull()) {
      error.writePointer(NULL);
    }
    return 1; // true
  }, "int", ["pointer", "pointer"]));
}

// Legacy: OSStatus SecTrustEvaluate(SecTrustRef trust, SecTrustResultType *result)
const ste = Module.findExportByName(null, "SecTrustEvaluate");
if (ste) {
  Interceptor.attach(ste, {
    onEnter(args) { this.res = args[1]; },
    onLeave(retval) {
      if (this.res && !this.res.isNull()) {
        this.res.writeU32(1); // kSecTrustResultProceed = 1
        log("SecTrustEvaluate -> forced kSecTrustResultProceed");
      }
    },
  });
}

// --- 4. Android Conscrypt / Java TrustManager ---
if (typeof Java !== "undefined" && Java.available) {
  Java.perform(() => {
    try {
      const TrustManagerImpl = Java.use("com.android.org.conscrypt.TrustManagerImpl");
      TrustManagerImpl.checkTrustedRecursive.implementation = function() {
        log("Android Conscrypt checkTrustedRecursive -> bypassed");
        return Java.use("java.util.ArrayList").$new();
      };
    } catch (e) {}

    try {
      const CertificatePinner = Java.use("okhttp3.CertificatePinner");
      CertificatePinner.check.overload("java.lang.String", "java.util.List").implementation = function() {
        log("OkHttp3 CertificatePinner.check -> bypassed");
      };
    } catch (e) {}
  });
}

log("ssl unpinning hooks installed");
