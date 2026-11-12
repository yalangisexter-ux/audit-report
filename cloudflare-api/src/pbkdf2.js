// Pure JavaScript PBKDF2-HMAC-SHA256 implementation
// Necessary because Cloudflare Workers runtime (workerd) hard-caps PBKDF2 at 100,000 iterations,
// while desktop/app.py databases use 200,000 iterations for password verification.

const K = new Int32Array(64);
let primeCandidate = 2, kCount = 0;
while (kCount < 64) {
  let isPrime = true;
  for (let d = 2; d * d <= primeCandidate; d++) {
    if (primeCandidate % d === 0) { isPrime = false; break; }
  }
  if (isPrime) {
    const frac = Math.cbrt(primeCandidate) % 1;
    K[kCount++] = (frac * 0x100000000) | 0;
  }
  primeCandidate++;
}

const H_INIT = new Int32Array([
  0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
  0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
]);

function rotr(x, n) {
  return (x >>> n) | (x << (32 - n));
}

function sha256Compress(h, w) {
  for (let i = 16; i < 64; i++) {
    const s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >>> 3);
    const s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >>> 10);
    w[i] = (w[i - 16] + s0 + w[i - 7] + s1) | 0;
  }
  let a = h[0], b = h[1], c = h[2], d = h[3];
  let e = h[4], f = h[5], g = h[6], hv = h[7];
  for (let i = 0; i < 64; i++) {
    const s1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
    const ch = (e & f) ^ ((~e) & g);
    const temp1 = (hv + s1 + ch + K[i] + w[i]) | 0;
    const s0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
    const maj = (a & b) ^ (a & c) ^ (b & c);
    const temp2 = (s0 + maj) | 0;
    hv = g; g = f; f = e; e = (d + temp1) | 0;
    d = c; c = b; b = a; a = (temp1 + temp2) | 0;
  }
  h[0] = (h[0] + a) | 0; h[1] = (h[1] + b) | 0;
  h[2] = (h[2] + c) | 0; h[3] = (h[3] + d) | 0;
  h[4] = (h[4] + e) | 0; h[5] = (h[5] + f) | 0;
  h[6] = (h[6] + g) | 0; h[7] = (h[7] + hv) | 0;
}

export function computePbkdf2Sha256(passwordStr, saltStr, iterations = 200000) {
  const enc = new TextEncoder();
  const password = enc.encode(passwordStr);
  const salt = enc.encode(saltStr);

  const keyPad = new Uint8Array(64);
  if (password.length > 64) {
    // Hash key if > 64 bytes
    const h = new Int32Array(H_INIT);
    const w = new Int32Array(64);
    for (let i = 0; i < password.length; i++) {
      w[i >> 2] |= password[i] << (24 - (i & 3) * 8);
    }
    w[password.length >> 2] |= 0x80 << (24 - (password.length & 3) * 8);
    w[15] = password.length * 8;
    sha256Compress(h, w);
    for (let i = 0; i < 8; i++) {
      keyPad[i * 4] = (h[i] >>> 24) & 0xff;
      keyPad[i * 4 + 1] = (h[i] >>> 16) & 0xff;
      keyPad[i * 4 + 2] = (h[i] >>> 8) & 0xff;
      keyPad[i * 4 + 3] = h[i] & 0xff;
    }
  } else {
    keyPad.set(password);
  }

  // Precompute inner state (H_INIT after ipad block)
  const ipadH = new Int32Array(H_INIT);
  const ipadW = new Int32Array(64);
  for (let i = 0; i < 16; i++) {
    const b0 = keyPad[i * 4] ^ 0x36;
    const b1 = keyPad[i * 4 + 1] ^ 0x36;
    const b2 = keyPad[i * 4 + 2] ^ 0x36;
    const b3 = keyPad[i * 4 + 3] ^ 0x36;
    ipadW[i] = (b0 << 24) | (b1 << 16) | (b2 << 8) | b3;
  }
  sha256Compress(ipadH, ipadW);

  // Precompute outer state (H_INIT after opad block)
  const opadH = new Int32Array(H_INIT);
  const opadW = new Int32Array(64);
  for (let i = 0; i < 16; i++) {
    const b0 = keyPad[i * 4] ^ 0x5c;
    const b1 = keyPad[i * 4 + 1] ^ 0x5c;
    const b2 = keyPad[i * 4 + 2] ^ 0x5c;
    const b3 = keyPad[i * 4 + 3] ^ 0x5c;
    opadW[i] = (b0 << 24) | (b1 << 16) | (b2 << 8) | b3;
  }
  sha256Compress(opadH, opadW);

  // Compute U1: HMAC(password, salt || [0,0,0,1])
  const saltBuf = new Uint8Array(salt.length + 4);
  saltBuf.set(salt, 0);
  saltBuf[salt.length + 3] = 1;

  const innerMsgLen = 64 + saltBuf.length;
  const innerH = new Int32Array(ipadH);
  const innerW = new Int32Array(64);
  for (let i = 0; i < saltBuf.length; i++) {
    innerW[i >> 2] |= saltBuf[i] << (24 - (i & 3) * 8);
  }
  innerW[saltBuf.length >> 2] |= 0x80 << (24 - (saltBuf.length & 3) * 8);
  innerW[15] = innerMsgLen * 8;
  sha256Compress(innerH, innerW);

  const outerH = new Int32Array(opadH);
  const outerW = new Int32Array(64);
  for (let i = 0; i < 8; i++) outerW[i] = innerH[i];
  outerW[8] = 0x80000000;
  outerW[15] = (64 + 32) * 8; // 768 bits
  sha256Compress(outerH, outerW);

  // Accumulated XOR result T
  const t = new Int32Array(outerH);
  const currentU = new Int32Array(outerH);

  // Reusable working arrays for iterations 2..N
  const inWorkH = new Int32Array(8);
  const outWorkH = new Int32Array(8);
  const inWorkW = new Int32Array(64);
  inWorkW[8] = 0x80000000;
  inWorkW[15] = 768; // (64 + 32) * 8
  const outWorkW = new Int32Array(64);
  outWorkW[8] = 0x80000000;
  outWorkW[15] = 768;

  for (let iter = 1; iter < iterations; iter++) {
    // Step A: inner hash with currentU
    inWorkH.set(ipadH);
    for (let j = 0; j < 8; j++) inWorkW[j] = currentU[j];
    sha256Compress(inWorkH, inWorkW);

    // Step B: outer hash with inner result
    outWorkH.set(opadH);
    for (let j = 0; j < 8; j++) outWorkW[j] = inWorkH[j];
    sha256Compress(outWorkH, outWorkW);

    for (let j = 0; j < 8; j++) {
      currentU[j] = outWorkH[j];
      t[j] ^= outWorkH[j];
    }
  }

  let hex = "";
  for (let j = 0; j < 8; j++) {
    hex += (t[j] >>> 0).toString(16).padStart(8, "0");
  }
  return hex;
}
