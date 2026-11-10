import json, re, pathlib
from playwright.sync_api import sync_playwright
from shot import install_routes, ROOT

results = []
def check(name, ok, info=""):
    results.append((name, bool(ok), info))

def lum(hex_):
    h = hex_.lstrip("#"); r, g, b = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
def cr(a, b):
    la, lb = sorted([lum(a), lum(b)], reverse=True); return (la + .05) / (lb + .05)

with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome")
    ctx = b.new_context(viewport={"width": 1440, "height": 900}, permissions=["clipboard-read", "clipboard-write"])

    # --- 1. Data integrity: compare product arrays (old vs new, ignoring added `cat`)
    def products_of(file):
        pg = ctx.new_page(); install_routes(pg); pg.goto((ROOT / file).as_uri()); pg.wait_for_timeout(300)
        data = pg.evaluate("products.map(({cat, ...r}) => r)")
        pg.close(); return data
    old, new = products_of("original.html"), products_of("index.html")
    check("33 produk, data identik dengan versi lama (judul, deskripsi, logo, paket, harga)", old == new and len(new) == 33, f"{len(old)} vs {len(new)}")

    pg = ctx.new_page(); install_routes(pg)
    errors = []; pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto((ROOT / "index.html").as_uri()); pg.wait_for_timeout(500)

    check("Semua kartu dirender", pg.locator("#grid .product").count() == 33)
    # all packages visible across modals
    total_pkgs = sum(len(x["prices"]) for x in new)
    shown = 0
    for i in range(1, 34):
        pg.evaluate(f"openDetail({i})"); shown += pg.locator("#dPackages .pkg").count(); pg.evaluate("closeDetail()")
    check("Semua paket tampil di detail", shown == total_pkgs, f"{shown}/{total_pkgs}")

    # --- 2. Search / filter / sort
    pg.fill("#q", "netflix"); check("Cari 'netflix' -> 1 hasil", pg.locator("#grid .product").count() == 1)
    pg.fill("#q", "musik"); check("Cari 'musik' (nama kategori) -> Spotify & Apple Music", pg.locator("#grid .product").count() == 2)
    pg.fill("#q", "zzzz"); check("Pencarian kosong menampilkan empty state + tautan tanya admin",
        pg.locator("#empty").is_visible() and "6283168725825" in pg.get_attribute("#askAdmin", "href"))
    pg.click("#resetFilters"); check("Reset kembali ke 33", pg.locator("#grid .product").count() == 33)
    pg.click('[data-cat="music"]'); check("Chip Musik -> 2", pg.locator("#grid .product").count() == 2)
    pg.click('[data-cat="streaming"]'); n_stream = pg.locator("#grid .product").count()
    vis_in_stream = pg.evaluate("[...document.querySelectorAll('#grid .product-name')].some(e=>e.textContent==='Vision Premium')")
    check("Vision Premium masuk Streaming (dulu salah ke AI)", vis_in_stream, f"streaming={n_stream}")
    pg.click('[data-cat="all"]')
    pg.select_option("#sort", "low")
    first = pg.locator("#grid .product-name").first.text_content()
    check("Urut termurah: Getcontact (Rp1.000) pertama", first == "Getcontact Premium", first)
    pg.select_option("#sort", "high")
    first = pg.locator("#grid .product-name").first.text_content()
    check("Urut termahal (berdasar harga mulai): ChatGPT Rp28.000 pertama", first == "ChatGPT Premium", first)
    pg.select_option("#sort", "az"); check("A–Z", pg.locator("#grid .product-name").first.text_content() == "Alight Motion")
    pg.select_option("#sort", "reco")
    check("Harga ganjil dinormalkan", pg.evaluate("[parsePrice('18..000').text, parsePrice('  18.000').text, parsePrice('1000').text, parsePrice('35.000/bln').text]") == ["Rp18.000", "Rp18.000", "Rp1.000", "Rp35.000/bln"])

    # --- 3. Links
    hrefs = pg.evaluate("[...document.querySelectorAll('#contactList a')].map(a=>a.href)")
    check("Kontak: admin, order admin, bot LIST, grup, IG, Telegram", hrefs == [
        "https://wa.me/6285841218112", "https://wa.me/6283168725825", "https://wa.me/6287897294851?text=LIST",
        "https://chat.whatsapp.com/C9h8uAhCujyF5Wa4d3XzmS", "https://www.instagram.com/alveersse", "https://t.me/lylyst0ree"], hrefs)
    check("Chat admin header -> nomor order admin", pg.get_attribute("#navAdmin", "href") == "https://wa.me/6283168725825")
    check("Bar bawah: Chat admin -> admin order, Order bot -> LIST",
          pg.get_attribute("#barAdmin", "href") == "https://wa.me/6283168725825" and pg.get_attribute("#barBot", "href") == "https://wa.me/6287897294851?text=LIST")
    check("Nama toko AL STORE, tidak ada sisa H&T", "H&T" not in pg.content() and pg.title().startswith("AL STORE"))
    check("Tidak ada em dash di teks halaman", "\u2014" not in pg.evaluate("document.body.innerText + document.title"))

    # --- 4. Modal via keyboard
    card = pg.locator("#grid .product").first
    card.focus(); pg.keyboard.press("Enter"); pg.wait_for_timeout(250)
    check("Enter membuka modal", pg.evaluate("document.getElementById('detail').open"))
    check("Fokus pindah ke judul modal", pg.evaluate("document.activeElement.id") == "dName")
    href0 = pg.get_attribute("#dOrderAdmin", "href")
    check("Pesan admin default sama dengan versi lama", "(tulis%20paket)" in href0 and "6283168725825" in href0)
    pg.locator("#dPackages .pkg").nth(1).click()
    href1 = pg.get_attribute("#dOrderAdmin", "href")
    from urllib.parse import unquote
    check("Pilih paket -> pesan admin berisi paket", "Paket yang saya pilih: 3 Bulan (Rp13.000)." in unquote(href1), unquote(href1))
    check("Bot di modal -> LIST", pg.get_attribute("#dOrderBot", "href") == "https://wa.me/6287897294851?text=LIST")
    pg.click("#dCopy"); pg.wait_for_timeout(150)
    clip = pg.evaluate("navigator.clipboard.readText()")
    check("Salin teks order", clip.startswith("Halo, saya mau order Canva Pro. Paket yang saya pilih: 3 Bulan"), clip)
    # Tab stays inside modal
    inside = True
    for _ in range(12):
        pg.keyboard.press("Tab")
        inside &= pg.evaluate("document.getElementById('detail').contains(document.activeElement) || document.activeElement===document.body")
    check("Tab tidak keluar ke halaman di belakang modal", inside)
    pg.keyboard.press("Escape"); pg.wait_for_timeout(150)
    check("Escape menutup modal", not pg.evaluate("document.getElementById('detail').open"))
    check("Fokus kembali ke kartu pemicu", pg.evaluate("document.activeElement.classList.contains('product') && document.activeElement.dataset.id") == card.get_attribute("data-id"))
    # backdrop click
    pg.locator("#grid .product").nth(2).click(); pg.wait_for_timeout(200)
    pg.mouse.click(10, 10); pg.wait_for_timeout(150)
    check("Klik area gelap menutup modal", not pg.evaluate("document.getElementById('detail').open"))

    # copy number
    pg.click("[data-copy]"); pg.wait_for_timeout(150)
    check("Salin nomor admin order", pg.evaluate("navigator.clipboard.readText()") == "+6283168725825")

    # --- 5. Image fallback (CDN logos blocked in sandbox -> should become initials after load attempt)
    pg.evaluate("window.scrollTo(0, document.body.scrollHeight)"); pg.wait_for_timeout(1500)
    pg.evaluate("window.scrollTo(0, 0)"); pg.wait_for_timeout(300)
    imgs_left = pg.evaluate("document.querySelectorAll('#grid img').length")
    fallbacks = pg.evaluate("document.querySelectorAll('#grid .tile-fallback').length")
    check("Gambar gagal -> inisial produk", fallbacks == 33 and imgs_left == 0, f"fallback={fallbacks}, img tersisa={imgs_left}")
    check("logo.png termuat di header & hero", pg.evaluate("[document.getElementById('brandLogo')?.naturalWidth, document.getElementById('heroLogo').naturalWidth]") == [512, 512])
    check("Tidak ada error JavaScript", not errors, errors)
    pg.close()

    # --- 6. Responsive: overflow + mobile menu + modal sheet
    for w in (360, 390, 430, 768, 1024, 1440):
        pg = ctx.new_page(); pg.set_viewport_size({"width": w, "height": 800}); install_routes(pg)
        pg.goto((ROOT / "index.html").as_uri()); pg.wait_for_timeout(300)
        sw = pg.evaluate("document.documentElement.scrollWidth")
        pg.evaluate("openDetail(27)"); pg.wait_for_timeout(300)  # Vidio, 5 packages
        box = pg.locator("#detail").bounding_box()
        fits = box["y"] >= 0 and box["y"] + box["height"] <= 800 + 1 and box["width"] <= w
        act = pg.locator("#dOrderAdmin").bounding_box()
        if w in (360, 1440):
            pg.screenshot(path=str(ROOT / f"modal-{w}.png"))
        pg.evaluate("closeDetail()")
        if w <= 768:
            bar = pg.locator(".action-bar").is_visible()
            pg.click("#menuToggle"); menu_ok = bar and pg.locator("#mobileMenu").is_visible() and pg.get_attribute("#menuToggle", "aria-expanded") == "true"
            pg.keyboard.press("Escape"); menu_ok &= pg.locator("#mobileMenu").is_hidden()
        else:
            menu_ok = pg.locator(".nav").is_visible() and pg.locator(".action-bar").is_hidden()
        check(f"{w}px: tanpa overflow horizontal, modal muat layar & tombol order terlihat, navigasi OK",
              sw <= w and fits and act["y"] + act["height"] <= 800 and menu_ok, f"scrollWidth={sw} modal={box} menu={menu_ok}")
        pg.close()
    b.close()

# --- 7. Contrast (WCAG AA 4.5:1 normal text) from the CSS tokens
css = (ROOT / "index.html").read_text()
tok = dict(re.findall(r"--color-(bg|surface|text|muted|border|accent|on-accent):\s*(#[0-9A-Fa-f]{6})", css.split("/* --- Alternatif")[0]))
def mix(a, b, t):  # t of a into b
    ha, hb = a.lstrip("#"), b.lstrip("#")
    return "#" + "".join(f"{round(int(ha[i:i+2],16)*t + int(hb[i:i+2],16)*(1-t)):02x}" for i in (0,2,4))
sunken = mix(tok["text"], tok["surface"], .04); soft = mix(tok["accent"], tok["surface"], .09)
hover = mix(tok["accent"], tok["text"], .80)
pairs = {
    "teks / latar": (tok["text"], tok["bg"]), "teks sekunder / latar": (tok["muted"], tok["bg"]),
    "teks sekunder / surface": (tok["muted"], tok["surface"]), "teks sekunder / sunken": (tok["muted"], sunken),
    "aksen / surface (tautan, harga)": (tok["accent"], tok["surface"]), "aksen / latar": (tok["accent"], tok["bg"]),
    "aksen / accent-soft (label, inisial)": (tok["accent"], soft), "putih / tombol aksen": (tok["on-accent"], tok["accent"]),
    "putih / tombol hover": (tok["on-accent"], hover),
}
for k, (a, c) in pairs.items():
    r = cr(a, c); check(f"Kontras {k}: {r:.2f}:1", r >= 4.5)
r = cr(mix("#FFFFFF", "#000000", .72), "#000000"); check(f"Kontras teks sekunder di area hitam: {r:.2f}:1", r >= 4.5)
r = cr(mix(tok["text"], tok["border"], .42), tok["surface"])
check(f"Kontras garis input/chip (border-strong): {r:.2f}:1 (UI ≥3:1)", r >= 3)

for name, ok, info in results:
    print(("PASS " if ok else "FAIL ") + name + (f"  [{info}]" if (not ok and info) else ""))
print(sum(o for _, o, _ in results), "/", len(results))
