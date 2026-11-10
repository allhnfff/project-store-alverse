"""Local harness: wraps the artifact page in the publish skeleton, stubs the claude.ai
runtime (user/artifact/assets) and walks the admin flow end to end."""
import pathlib, json, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from playwright.sync_api import sync_playwright
from shot import install_routes

HERE = pathlib.Path(__file__).parent
RESET = ":root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0;font:14px system-ui,sans-serif}img{max-width:100%}[hidden]{display:none!important}"
def wrap(content):
    return ('<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1,viewport-fit=cover"><style>'
            + RESET + '</style></head><body>' + content + '</body></html>')

STUB = """
window.__published = [];
window.claude = { use: async (n) => {
  await new Promise(r => setTimeout(r, 30));
  if (n === 'user') return { canEdit: async () => true };
  if (n === 'artifact') return { publish: async (html) => { window.__published.push(html); return { version: 'v' + window.__published.length }; } };
  if (n === 'assets') return { upload: async (f) => ({ id: '0123456789abcdef0123456789abcdef', url: '/_blob/0123456789abcdef0123456789abcdef', sizeBytes: f.size, contentType: f.type }) };
  return null; } };
"""
results = []
def check(name, ok, info=""):
    results.append((name, bool(ok), info))

page_src = (HERE / "al-store.html").read_text()
(HERE / "_wrapped.html").write_text(wrap(page_src))

with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome")
    ctx = b.new_context(viewport={"width": 1280, "height": 900}, permissions=["clipboard-read", "clipboard-write"])

    # 1. Buyer view, no runtime
    pg = ctx.new_page(); install_routes(pg); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto((HERE / "_wrapped.html").as_uri() + "#kelola"); pg.wait_for_timeout(500)
    check("Pembeli: 33 produk tampil per kategori", pg.locator("#groups .product").count() == 33 and pg.locator("#grid .product").count() == 0)
    check("Pembeli: etalase andalan berisi 4 produk", pg.locator("#rail .feature").count() == 4, pg.locator("#rail .feature").count())
    check("Pembeli: bagian atas = nama toko + 2 baris tagline", pg.inner_text("#heroTitle") == "AL STORE" and pg.inner_text("#heroLine1") == "Aplikasi premium & jasa desain." and pg.inner_text("#heroLine2") == "Pesan lewat WhatsApp.")
    pg.fill("#q", "netflix"); pg.wait_for_timeout(100)
    check("Pembeli: pencarian jadi daftar biasa", pg.locator("#grid .product").count() == 1 and pg.locator("#showcase").is_hidden() and pg.locator("#groups").is_hidden())
    pg.fill("#q", ""); pg.click('#chips [data-cat="music"]'); pg.wait_for_timeout(100)
    check("Pembeli: filter kategori Musik", pg.locator("#grid .product").count() == 2 and pg.locator("#showcase").is_hidden())
    pg.click('#chips [data-cat="all"]'); pg.wait_for_timeout(100)
    check("Pembeli: kembali ke tampilan etalase", pg.locator("#rail .feature").count() == 4)
    check("Pembeli: tombol Kelola toko tidak muncul, #kelola tetap toko", pg.locator("#adminLink").is_hidden() and pg.locator("#adminView").is_hidden())
    check("Pembeli: judul halaman AL STORE", pg.title() == "AL STORE")
    pg.locator("#rail .feature").first.click(); pg.wait_for_timeout(200)
    pg.locator("#dPackages .pkg").nth(1).click()
    check("Pembeli: pesan order berisi paket", "3 Bulan (Rp13.000)" in pg.evaluate("decodeURIComponent(document.getElementById('dOrderAdmin').href)"))
    pg.keyboard.press("Escape")
    check("Pembeli: tanpa error JS", not errs, errs)
    pg.close()

    # 2. Admin flow with stubbed runtime
    pg = ctx.new_page(); install_routes(pg); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.add_init_script(STUB)
    pg.goto((HERE / "_wrapped.html").as_uri()); pg.wait_for_timeout(600)
    check("Admin: tombol Kelola toko muncul untuk editor", pg.locator("#adminLink").is_visible())
    pg.click("#adminLink"); pg.wait_for_timeout(300)
    check("Admin: daftar 33 produk", pg.locator("#alist .arow").count() == 33)
    check("Admin: tombol terbit nonaktif saat belum ada perubahan", pg.locator("#publishBtn").is_disabled())
    pg.screenshot(path=str(HERE / "shot-admin-desktop.png"))

    # edit Canva Pro price and name
    pg.locator('.arow[data-id="p1"] .btn-edit').click(); pg.wait_for_timeout(250)
    check("Editor: terbuka dengan data Canva Pro", pg.input_value("#e-title") == "Canva Pro")
    pg.fill("#pk-0-p", "7.500"); pg.wait_for_timeout(50)
    check("Editor: pratinjau harga", "Rp7.500" in pg.locator('#e-pkgs .rep-row[data-i="0"] [data-out]').inner_text())
    pg.fill("#pk-1-p", "abc")
    check("Editor: harga salah ditandai", pg.get_attribute("#pk-1-p", "aria-invalid") == "true")
    pg.click("#eSave"); pg.wait_for_timeout(150)
    check("Editor: tidak tersimpan saat harga salah", pg.evaluate("document.getElementById('editor').open") and pg.locator("#e-pkgs-err").is_visible())
    pg.fill("#pk-1-p", "14.000")
    pg.click("#e-addPkg"); pg.fill("#pk-4-n", "2 Tahun"); pg.fill("#pk-4-p", "25.000")
    pg.set_input_files("#e-file", files=[{"name": "logo.png", "mimeType": "image/png", "buffer": (HERE.parent / "logo.png").read_bytes()}]); pg.wait_for_timeout(200)
    check("Editor: unggah logo masuk ke produk", "terunggah" in pg.inner_text("#e-logoStatus"))
    pg.click("#eSave"); pg.wait_for_timeout(200)
    check("Editor: tertutup setelah simpan, fokus kembali ke Edit", (not pg.evaluate("document.getElementById('editor').open")) and pg.evaluate("document.activeElement.classList.contains('btn-edit')"))
    check("Admin: tombol terbit aktif setelah ada perubahan", pg.locator("#publishBtn").is_enabled())

    # add product
    pg.click("#addProduct"); pg.wait_for_timeout(200)
    pg.fill("#e-title", "Disney+ Hotstar"); pg.fill("#e-desc", "Film Disney & Marvel"); pg.select_option("#e-cat", "streaming")
    pg.fill("#pk-0-n", "1 Bulan Sharing"); pg.fill("#pk-0-p", "12.000")
    pg.click("#eSave"); pg.wait_for_timeout(200)
    check("Admin: produk baru di urutan pertama", pg.locator("#alist .arow b").first.inner_text() == "Disney+ Hotstar")
    # hide one, reorder, delete one
    pg.locator('.arow[data-id="p2"] input[data-act="show"]').uncheck(); pg.wait_for_timeout(100)
    pg.locator('.arow[data-id="p3"] button[data-act="up"]').click(); pg.wait_for_timeout(100)
    pg.locator('.arow[data-id="p4"] button[data-act="ask-delete"]').click(); pg.wait_for_timeout(100)
    check("Admin: hapus minta konfirmasi di baris", pg.locator(".arow-confirm").is_visible())
    pg.locator('.arow[data-id="p4"] button[data-act="delete"]').click(); pg.wait_for_timeout(100)
    check("Admin: produk terhapus dari draf", pg.locator('.arow[data-id="p4"]').count() == 0 and pg.locator("#alist .arow").count() == 33)

    # store settings
    pg.click('.seg button[data-tab="toko"]'); pg.wait_for_timeout(100)
    pg.fill("#f-tagline", "Langganan aplikasi & jasa desain")
    pg.fill("#f-waBot", "62 878-9729-4851x")
    check("Toko: nomor WA dibersihkan jadi angka", pg.input_value("#f-waBot") == "6287897294851")
    pg.fill("#f-igLabel", "@alveersse.store")
    # faq
    pg.click('.seg button[data-tab="faq"]'); pg.wait_for_timeout(100)
    pg.click("#addTesti"); pg.fill("#testi-0-0", "Cepat diproses, aman."); pg.fill("#testi-0-1", "Contoh Pembeli")
    pg.locator('#faqRep .rep-row[data-i="4"] [data-rep="del"]').click()
    check("FAQ: tersisa 4 pertanyaan", pg.locator("#faqRep .rep-row").count() == 4)

    # invalid URL blocks publish
    pg.click('.seg button[data-tab="toko"]'); pg.fill("#f-tg", "t.me/salah"); pg.click("#publishBtn"); pg.wait_for_timeout(150)
    check("Terbit: ditolak bila link tidak diawali https://", "https://" in pg.inner_text("#saveStatus") and pg.evaluate("window.__published.length") == 0)
    pg.fill("#f-tg", "https://t.me/lylyst0ree")

    # preview in store view
    pg.click('#adminView a[href="#"]'); pg.wait_for_timeout(250)
    check("Pratinjau: banner tampil & produk baru ada", pg.locator("#previewBanner").is_visible() and pg.locator("#groups .product-name").first.inner_text() == "Disney+ Hotstar")
    check("Pratinjau: produk disembunyikan (Jasa Design) tidak tampil", "Jasa Design" not in pg.inner_text("#groups"))
    pg.goto(pg.url.split("#")[0] + "#kelola"); pg.wait_for_timeout(600)
    check("Draf: tersimpan di browser saat halaman dimuat ulang", pg.locator("#alist .arow b").first.inner_text() == "Disney+ Hotstar" and pg.locator("#publishBtn").is_enabled())

    pg.click("#publishBtn"); pg.wait_for_timeout(300)
    pub = pg.evaluate("window.__published")
    check("Terbit: satu dokumen dikirim", len(pub) == 1)
    html = pub[0] if pub else ""
    check("Terbit: dokumen diawali doctype & berisi data", html.startswith("<!doctype html>") and "Disney+ Hotstar" in html and "7.500" in html)
    check("Terbit: draf lokal dibersihkan", pg.evaluate("localStorage.getItem('alstore-draft-v1')") is None)
    check("Admin: tanpa error JS", not errs, errs)
    pg.close()

    # 3. Load the published document as a fresh buyer and as editor again (round trip)
    (HERE / "_published.html").write_text(html)
    pg = ctx.new_page(); install_routes(pg); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto((HERE / "_published.html").as_uri()); pg.wait_for_timeout(500)
    names = pg.locator("#groups .product-name").all_inner_texts()
    check("Versi terbit: 32 produk tampil (1 disembunyikan)", len(names) == 32, len(names))
    check("Versi terbit: urutan diatur admin, CapCut terhapus, Jasa Design tersembunyi", names[:4] == ["Disney+ Hotstar", "YouTube Premium", "Netflix Premium", "Dramabox"] and "CapCut Premium" not in names and "Jasa Design" not in names, names[:4])
    check("Versi terbit: harga Canva baru", "Rp7.500" in pg.inner_text("#rail"))
    check("Versi terbit: testimoni & IG baru", "Cepat diproses" in pg.inner_text("#testimonials") and "@alveersse.store" in pg.inner_text("#contactList"))
    check("Versi terbit: link bot pakai nomor bersih", pg.get_attribute("#barBot", "href").startswith("https://wa.me/6287897294851"))
    check("Versi terbit: tanpa error JS", not errs, errs)
    pg.close()

    pg = ctx.new_page(); install_routes(pg); pg.add_init_script(STUB)
    pg.goto((HERE / "_published.html").as_uri() + "#kelola"); pg.wait_for_timeout(600)
    pg.click('.seg button[data-tab="toko"]'); pg.fill("#f-name", "AL STORE ID"); pg.click("#publishBtn"); pg.wait_for_timeout(300)
    html2 = pg.evaluate("window.__published[0]")
    a, b2 = html.split('<script type="application/json"')[0], html2.split('<script type="application/json"')[0]
    check("Terbit ulang: struktur halaman stabil (hanya judul & data berubah)", a.replace("<title>AL STORE</title>", "") == b2.replace("<title>AL STORE ID</title>", ""))
    pg.close()

    # 4. Mobile admin screenshots
    m = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, reduced_motion="reduce")
    pg = m.new_page(); install_routes(pg); pg.add_init_script(STUB)
    pg.goto((HERE / "_wrapped.html").as_uri() + "#kelola"); pg.wait_for_timeout(700)
    check("HP admin: tanpa scroll samping", pg.evaluate("document.documentElement.scrollWidth") <= 390)
    pg.screenshot(path=str(HERE / "shot-admin-m1.png"))
    pg.locator('.arow[data-id="p5"] .btn-edit').click(); pg.wait_for_timeout(300)
    pg.screenshot(path=str(HERE / "shot-admin-m2.png"))
    pg.keyboard.press("Escape"); pg.wait_for_timeout(100)
    pg.click('.seg button[data-tab="toko"]'); pg.wait_for_timeout(100)
    pg.screenshot(path=str(HERE / "shot-admin-m3.png"))
    sw = pg.evaluate("document.documentElement.scrollWidth")
    check("HP admin (form toko): tanpa scroll samping", sw <= 390, sw)
    pg.goto((HERE / "_wrapped.html").as_uri()); pg.wait_for_timeout(500)
    pg.screenshot(path=str(HERE / "shot-store-m.png"))
    b.close()

for n, ok, info in results:
    print(("PASS " if ok else "FAIL ") + n + (f"  [{info}]" if not ok and info != "" else ""))
print(sum(o for _, o, _ in results), "/", len(results))
