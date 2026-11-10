// AL STORE: toko + panel admin dalam satu Cloudflare Worker.
// Butuh dua pengaturan di dashboard Cloudflare:
//   1. Binding KV bernama  DATA            (namespace: alstore-data)
//   2. Secret bernama      ADMIN_PASSWORD  (kata sandi admin, dibuat sendiri oleh pemilik)

const PAGE = /*__PAGE__*/"";
const DEFAULT_DATA = /*__DEFAULT_DATA__*/{};
const DEFAULT_LOGOS = /*__LOGOS__*/{};
const FILES = /*__FILES__*/{};

const SESSION_DAYS = 7;
const MAX_DATA = 512 * 1024;
const MAX_LOGO = 2 * 1024 * 1024;
const LOGO_TYPES = ["image/png", "image/jpeg", "image/webp", "image/svg+xml"];

const enc = new TextEncoder();
const b64 = (s) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));
const html = (body, status = 200, extra = {}) => new Response(body, { status, headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store", ...extra } });
const json = (obj, status = 200, extra = {}) => new Response(JSON.stringify(obj), { status, headers: { "content-type": "application/json", "cache-control": "no-store", ...extra } });

async function hmac(key, msg) {
  const k = await crypto.subtle.importKey("raw", enc.encode(key), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", k, enc.encode(msg));
  return [...new Uint8Array(sig)].map((b) => b.toString(16).padStart(2, "0")).join("");
}
function sameText(a, b) {
  const x = enc.encode(String(a)), y = enc.encode(String(b));
  let d = x.length ^ y.length;
  for (let i = 0; i < Math.max(x.length, y.length); i++) d |= (x[i] || 0) ^ (y[i] || 0);
  return d === 0;
}
function cookie(req, name) {
  const m = (req.headers.get("cookie") || "").match(new RegExp("(?:^|;\\s*)" + name + "=([^;]+)"));
  return m ? m[1] : "";
}
async function isAdmin(req, env) {
  if (!env.ADMIN_PASSWORD) return false;
  const [exp, sig] = cookie(req, "alstore_admin").split(".");
  if (!exp || !sig || Number(exp) < Date.now()) return false;
  return sameText(sig, await hmac(env.ADMIN_PASSWORD, "alstore:" + exp));
}
// Tolak permintaan tulis dari situs lain.
function sameOrigin(req, url) {
  const o = req.headers.get("origin");
  return !o || o === url.origin;
}

async function loadData(env, fresh) {
  if (env.DATA) {
    const d = await env.DATA.get("data", fresh ? { type: "json" } : { type: "json", cacheTtl: 60 });
    if (d) return d;
  }
  return DEFAULT_DATA;
}
function validData(d) {
  return d && typeof d === "object" && d.store && typeof d.store.name === "string" && d.contact && Array.isArray(d.products) && Array.isArray(d.faq) && Array.isArray(d.testimoni)
    && d.products.every((p) => p && typeof p.id === "string" && typeof p.title === "string" && Array.isArray(p.prices));
}

const LOGIN = (msg, origin) => `<!doctype html><html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Masuk admin | AL STORE</title><meta name="robots" content="noindex"><link rel="icon" href="/favicon.png">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,100..900&display=swap">
<style>
:root{color-scheme:light}*{box-sizing:border-box}
body{margin:0;min-height:100vh;min-height:100dvh;display:grid;place-items:center;padding:24px 16px;background:#000;color:#fff;font:15px/1.5 "Archivo",system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}
main{width:100%;max-width:380px}
.mark{display:flex;align-items:center;gap:12px;margin-bottom:28px}
.mark img{width:44px;height:44px}
.mark b{font-stretch:125%;font-weight:800;font-size:20px;letter-spacing:.02em}
h1{margin:0 0 4px;font-size:24px;font-stretch:112%;font-weight:800}
p{margin:0 0 20px;color:#B8B8B8}
label{display:block;font-weight:700;font-size:14px;margin-bottom:6px}
input{width:100%;min-height:48px;padding:10px 12px;border:1px solid #8a8a8a;border-radius:4px;background:#111;color:#fff;font:inherit;font-size:16px}
input:focus-visible{outline:2px solid #fff;outline-offset:2px;border-color:#fff}
button{margin-top:14px;width:100%;min-height:48px;border:0;border-radius:4px;background:#fff;color:#000;font:inherit;font-weight:800;cursor:pointer}
button:hover{background:#dcdcdc}button:focus-visible{outline:2px solid #fff;outline-offset:3px}
.err{margin:12px 0 0;color:#FFB4AB;font-weight:700;font-size:14px}
a{color:#fff}.back{display:inline-block;margin-top:20px;font-size:14px}
</style></head><body><main>
<div class="mark"><img src="/logo/${DEFAULT_DATA.store.logoAsset}" alt="" width="44" height="44"><b>AL STORE</b></div>
<h1>Masuk admin</h1><p>Kelola produk, harga, dan info toko.</p>
<form method="post" action="/admin">
<label for="pw">Kata sandi admin</label>
<input id="pw" name="password" type="password" autocomplete="current-password" required autofocus>
<button type="submit">Masuk</button>
${msg ? `<p class="err" role="alert">${msg}</p>` : ""}
</form>
<a class="back" href="/">Kembali ke toko</a>
</main></body></html>`;

export default {
  async fetch(req, env, ctx) {
    const url = new URL(req.url);
    const path = url.pathname;

    // ---------- halaman toko ----------
    if (path === "/" || path === "/index.html") {
      if (req.method !== "GET" && req.method !== "HEAD") return new Response("Method not allowed", { status: 405 });
      const admin = await isAdmin(req, env);
      const data = await loadData(env, admin);
      const body = PAGE.replace("__ORIGIN__", url.origin).replace("__DATA__", () => JSON.stringify(data).replace(/</g, "\\u003c"));
      return html(body, 200, { "x-content-type-options": "nosniff", "referrer-policy": "strict-origin-when-cross-origin" });
    }

    // ---------- file tetap ----------
    if (FILES[path.slice(1)]) {
      const [type, data] = FILES[path.slice(1)];
      return new Response(b64(data), { headers: { "content-type": type, "cache-control": "public, max-age=86400" } });
    }

    // ---------- logo (unggahan admin di KV, lalu logo bawaan) ----------
    const lm = path.match(/^\/(?:logo|_blob)\/([0-9a-f]{32})$/i);
    if (lm) {
      const id = lm[1].toLowerCase();
      const cache = caches.default;
      const hit = await cache.match(req);
      if (hit) return hit;
      let res = null;
      if (env.DATA) {
        const { value, metadata } = await env.DATA.getWithMetadata("logo:" + id, { type: "arrayBuffer" });
        if (value) res = new Response(value, { headers: { "content-type": (metadata && metadata.type) || "image/png" } });
      }
      if (!res && DEFAULT_LOGOS[id]) res = new Response(b64(DEFAULT_LOGOS[id][1]), { headers: { "content-type": DEFAULT_LOGOS[id][0] } });
      if (!res) return new Response("Not found", { status: 404 });
      res.headers.set("cache-control", "public, max-age=31536000, immutable");
      res.headers.set("x-content-type-options", "nosniff");
      res.headers.set("content-security-policy", "default-src 'none'; style-src 'unsafe-inline'; sandbox");
      ctx.waitUntil(cache.put(req, res.clone()));
      return res;
    }

    // ---------- masuk / keluar admin ----------
    if (path === "/admin") {
      if (!env.ADMIN_PASSWORD) return html(LOGIN("Kata sandi admin belum diatur di pengaturan Cloudflare (secret ADMIN_PASSWORD)."), 503);
      if (req.method === "GET") {
        if (await isAdmin(req, env)) return Response.redirect(url.origin + "/#kelola", 303);
        return html(LOGIN(""));
      }
      if (req.method === "POST") {
        if (!sameOrigin(req, url)) return html(LOGIN("Permintaan ditolak."), 403);
        const form = await req.formData();
        const pw = String(form.get("password") || "");
        if (!sameText(pw, env.ADMIN_PASSWORD)) {
          await new Promise((r) => setTimeout(r, 900));
          return html(LOGIN("Kata sandi salah."), 401);
        }
        const exp = Date.now() + SESSION_DAYS * 864e5;
        const sig = await hmac(env.ADMIN_PASSWORD, "alstore:" + exp);
        return new Response(null, { status: 303, headers: {
          location: "/#kelola",
          "set-cookie": `alstore_admin=${exp}.${sig}; Path=/; Max-Age=${SESSION_DAYS * 86400}; HttpOnly; Secure; SameSite=Strict`,
          "cache-control": "no-store" } });
      }
      return new Response("Method not allowed", { status: 405 });
    }
    if (path === "/logout") {
      return new Response(null, { status: 303, headers: { location: "/", "set-cookie": "alstore_admin=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Strict", "cache-control": "no-store" } });
    }

    // ---------- API admin ----------
    if (path === "/api/me") return json({ admin: await isAdmin(req, env) });

    if (path === "/api/data" && req.method === "POST") {
      if (!(await isAdmin(req, env)) || !sameOrigin(req, url)) return json({ error: "unauthorized" }, 401);
      if (!env.DATA) return json({ error: "storage_missing" }, 500);
      const text = await req.text();
      if (text.length > MAX_DATA) return json({ error: "too_large" }, 413);
      let d; try { d = JSON.parse(text); } catch (_) { return json({ error: "invalid" }, 400); }
      if (!validData(d)) return json({ error: "invalid" }, 400);
      await env.DATA.put("data", JSON.stringify(d));
      return json({ ok: true });
    }

    if (path === "/api/logo" && req.method === "POST") {
      if (!(await isAdmin(req, env)) || !sameOrigin(req, url)) return json({ error: "unauthorized" }, 401);
      if (!env.DATA) return json({ error: "storage_missing" }, 500);
      const type = (req.headers.get("content-type") || "").split(";")[0].trim().toLowerCase();
      if (!LOGO_TYPES.includes(type)) return json({ error: "unsupported_type" }, 415);
      const buf = await req.arrayBuffer();
      if (!buf.byteLength) return json({ error: "empty" }, 400);
      if (buf.byteLength > MAX_LOGO) return json({ error: "too_large" }, 413);
      const id = crypto.randomUUID().replace(/-/g, "");
      await env.DATA.put("logo:" + id, buf, { metadata: { type } });
      return json({ id });
    }

    return new Response("Halaman tidak ditemukan", { status: 404, headers: { "content-type": "text/plain; charset=utf-8" } });
  }
};
