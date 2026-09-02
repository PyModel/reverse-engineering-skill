// hook_crypto.js — intercept common cipher/HMAC calls and log keys/plaintext/ciphertext.
// Usage: frida -n <target> -l hook_crypto.js  (or frida-trace for quick wins)
// Covers OpenSSL/BoringSSL AES, RC4, HMAC, and EVP wrappers.

const log = (s) => console.log("[crypto] " + s);

const hexPreview = (ptr, len) => {
  if (!ptr || ptr.isNull() || len <= 0) return "";
  try {
    const n = Math.min(len, 32);
    const buf = ptr.readByteArray(n);
    if (!buf) return "";
    return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, "0")).join(" ");
  } catch (e) {
    return "<unreadable>";
  }
};

// OpenSSL / BoringSSL EVP encrypt/decrypt/cipher
// Signature: int EVP_*Update(EVP_CIPHER_CTX *ctx, unsigned char *out, int *outl, const unsigned char *in, int inl)
function hook_evp(name) {
  const p = Module.findExportByName(null, name);
  if (!p) return;
  Interceptor.attach(p, {
    onEnter(args) {
      this.ctx = args[0];
      this.out = args[1];
      this.outl = args[2];
      this.in = args[3];
      this.in_len = args[4].toInt32();
      log(`${name} ctx=${this.ctx} in_len=${this.in_len} in_preview=[${hexPreview(this.in, this.in_len)}]`);
    },
    onLeave(retval) {
      if (retval.toInt32() === 1 && this.outl && !this.outl.isNull()) {
        const out_len = this.outl.readInt();
        log(`${name} -> success out_len=${out_len} out_preview=[${hexPreview(this.out, out_len)}]`);
      } else {
        log(`${name} -> ret=${retval}`);
      }
    },
  });
}

for (const fn of ["EVP_EncryptUpdate", "EVP_DecryptUpdate", "EVP_CipherUpdate"]) {
  hook_evp(fn);
}

// HMAC / hash — log data length
// Signature: int HMAC_Update(HMAC_CTX *ctx, const unsigned char *data, size_t len)
// Signature: int EVP_DigestUpdate(EVP_MD_CTX *ctx, const void *d, size_t cnt)
for (const name of ["HMAC_Update", "EVP_DigestUpdate"]) {
  const p = Module.findExportByName(null, name);
  if (!p) continue;
  Interceptor.attach(p, {
    onEnter(args) {
      const len = args[2].toInt32();
      log(`${name} ctx=${args[0]} data_len=${len} data_preview=[${hexPreview(args[1], len)}]`);
    },
  });
}

// RC4 key setup vs processing
// Signature: void RC4_set_key(RC4_KEY *key, int len, const unsigned char *data)
const rc4_set_key = Module.findExportByName(null, "RC4_set_key");
if (rc4_set_key) {
  Interceptor.attach(rc4_set_key, {
    onEnter(args) {
      const key_len = args[1].toInt32();
      log(`RC4_set_key key_len=${key_len} key=[${hexPreview(args[2], key_len)}]`);
    },
  });
}

// Signature: void RC4(RC4_KEY *key, size_t len, const unsigned char *indata, unsigned char *outdata)
const rc4 = Module.findExportByName(null, "RC4");
if (rc4) {
  Interceptor.attach(rc4, {
    onEnter(args) {
      const len = args[1].toInt32();
      log(`RC4 data_len=${len} in=[${hexPreview(args[2], len)}]`);
    },
  });
}

// AES key setup
// Signature: int AES_set_encrypt_key(const unsigned char *userKey, const int bits, AES_KEY *key)
for (const name of ["AES_set_encrypt_key", "AES_set_decrypt_key"]) {
  const p = Module.findExportByName(null, name);
  if (!p) continue;
  Interceptor.attach(p, {
    onEnter(args) {
      const bits = args[1].toInt32();
      log(`${name} bits=${bits} key=[${hexPreview(args[0], Math.floor(bits / 8))}]`);
    },
  });
}

log("crypto hooks installed");
