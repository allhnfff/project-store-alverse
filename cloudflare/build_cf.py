"""Rakit worker.js Cloudflare untuk AL STORE dari sumber toko yang sama (store/src.html).
Hasil: cloudflare/worker.js (satu file, tinggal tempel di editor dashboard Cloudflare)."""
import base64, glob, io, json, os, pathlib, re
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = (ROOT / "store/src.html").read_text()
DATA = json.loads((ROOT / "store/data.json").read_text())
ASSET_DIR = ROOT / "store/logos"
OG = ROOT / "assets/og.png"

# ---------- potong sumber jadi bagian-bagian ----------
def between(s, a, b):
    i = s.index(a) + len(a); return s[i:s.index(b, i)]
css = between(SRC, '<style id="app-css">', "</style>")
shell = between(SRC, '<template id="app-shell">', "</template>")
appjs = between(SRC, '<script id="app-js">', "</script>")
head_extra = SRC[SRC.index("<meta name=\"claude:viewport-fit-sides\""):SRC.index('<style id="app-css">')]
head_extra = head_extra.replace('<meta name="claude:viewport-fit-sides" content="cover">\n', "")

# tombol Keluar di kepala halaman admin
shell = shell.replace(
    '<a class="btn btn-secondary" href="#"><svg class="ic" aria-hidden="true"><use href="#i-store"/></svg>Lihat toko</a>',
    '<span style="display:flex;gap:8px;flex-wrap:wrap"><a class="btn btn-secondary" href="#"><svg class="ic" aria-hidden="true"><use href="#i-store"/></svg>Lihat toko</a><a class="btn btn-ghost" href="/logout">Keluar</a></span>', 1)
assert "/logout" in shell
appjs = appjs.replace("File terlalu besar. Maksimal 20 MB (SVG 2 MB).", "File terlalu besar. Maksimal 2 MB.")

RESET = (":root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}"
         "body{margin:0;font:14px system-ui,-apple-system,sans-serif}img{max-width:100%}[hidden]{display:none!important}")

# Penghubung: meniru runtime claude.ai (user/artifact/assets) memakai API worker ini,
# jadi kode toko & admin tidak perlu diubah.
SHIM = r"""
(() => {
  const me = fetch("/api/me", { credentials: "same-origin", cache: "no-store" }).then((r) => r.ok ? r.json() : { admin: false }).catch(() => ({ admin: false }));
  const fail = (status) => { const e = new Error("gagal"); e.code = status === 401 || status === 403 ? "not_writer" : status === 413 ? "too_large" : status === 415 ? "unsupported_type" : status === 429 ? "rate_limited" : status === 400 ? "invalid_content" : "upstream_error"; return e; };
  window.claude = { use: async (name) => {
    const m = await me;
    if (name === "user") return { canEdit: async () => !!m.admin };
    if (!m.admin) throw Object.assign(new Error("bukan admin"), { code: "not_granted" });
    if (name === "artifact") return { publish: async (html) => {
      const k = '<script type="application/json" id="store-data">';
      const i = html.indexOf(k), j = html.indexOf("<\/script>", i);
      const body = html.slice(i + k.length, j);
      const r = await fetch("/api/data", { method: "POST", credentials: "same-origin", headers: { "content-type": "application/json" }, body });
      if (!r.ok) throw fail(r.status);
      setTimeout(() => location.reload(), 400);
      return { ok: true };
    } };
    if (name === "assets") return { upload: async (file) => {
      const r = await fetch("/api/logo", { method: "POST", credentials: "same-origin", headers: { "content-type": file.type || "application/octet-stream" }, body: file });
      if (!r.ok) throw fail(r.status);
      return r.json();
    } };
    throw Object.assign(new Error("tidak tersedia"), { code: "not_declared" });
  } };
})();
"""

PAGE = ("<!doctype html><html lang=\"id\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\">"
        "<title>AL STORE</title>"
        "<meta name=\"description\" content=\"Langganan aplikasi premium dan jasa desain. Lihat paket dan harga, pesan lewat WhatsApp.\">"
        "<meta name=\"theme-color\" content=\"#000000\"><link rel=\"icon\" href=\"/favicon.png\">"
        "<meta property=\"og:type\" content=\"website\"><meta property=\"og:site_name\" content=\"AL STORE\"><meta property=\"og:title\" content=\"AL STORE\">"
        "<meta property=\"og:description\" content=\"Aplikasi premium & jasa desain. Lihat paket dan harga, pesan lewat WhatsApp.\">"
        "<meta property=\"og:image\" content=\"__ORIGIN__/og.png\"><meta property=\"og:image:width\" content=\"1200\"><meta property=\"og:image:height\" content=\"630\">"
        "<meta name=\"twitter:card\" content=\"summary_large_image\">"
        "<style>" + RESET + "</style></head><body>\n" + head_extra
        + '<style id="app-css">' + css + "</style>\n"
        + '<template id="app-shell">' + shell + "</template>\n"
        + '<div id="app"></div>\n'
        + '<script type="application/json" id="store-data">__DATA__</script>\n'
        + "<script>" + SHIM + "</script>\n"
        + '<script id="app-js">' + appjs + "</script></body></html>")

# ---------- logo bawaan (diperkecil supaya file worker ringan) ----------
logos = {}
for f in glob.glob(str(ASSET_DIR / "*")):
    name = os.path.basename(f); aid = name.split(".")[0]
    if not re.fullmatch(r"[0-9a-f]{32}", aid): continue
    im = Image.open(f)
    im = im.convert("RGBA")
    size = 256 if aid == DATA["store"]["logoAsset"] else 128
    im.thumbnail((size, size), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, "WEBP", quality=86, method=6)
    logos[aid] = ["image/webp", base64.b64encode(buf.getvalue()).decode()]
used = {p["logoAsset"] for p in DATA["products"] if p.get("logoAsset")} | {DATA["store"]["logoAsset"]}
missing = used - set(logos)
assert not missing, missing
logos = {k: v for k, v in logos.items() if k in used}
fav = Image.open(io.BytesIO(base64.b64decode(logos[DATA["store"]["logoAsset"]][1]))).convert("RGBA")
fav.thumbnail((64, 64)); fb = io.BytesIO(); fav.save(fb, "PNG")
EXTRA = {"og.png": ["image/png", base64.b64encode(OG.read_bytes()).decode()],
         "favicon.png": ["image/png", base64.b64encode(fb.getvalue()).decode()]}

worker = (ROOT / "cloudflare/worker.template.js").read_text()
worker = (worker
  .replace("/*__PAGE__*/\"\"", json.dumps(PAGE))
  .replace("/*__DEFAULT_DATA__*/{}", json.dumps(DATA, ensure_ascii=False))
  .replace("/*__LOGOS__*/{}", json.dumps(logos))
  .replace("/*__FILES__*/{}", json.dumps(EXTRA)))
assert "/*__" not in worker
(ROOT / "cloudflare/worker.js").write_text(worker)
print("worker.js", len(worker.encode()), "bytes;", len(logos), "logo")
