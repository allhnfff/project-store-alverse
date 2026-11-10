from playwright.sync_api import sync_playwright
import sys, pathlib; sys.path.insert(0,'.'); import shot
B="http://127.0.0.1:8787"; ok=0; tot=0
def check(name, cond, extra=""):
    global ok, tot; tot+=1; ok+=bool(cond); print(("PASS " if cond else "FAIL ")+name, extra if not cond else "")
with sync_playwright() as p:
    b=p.chromium.launch(executable_path="/usr/bin/google-chrome")
    ctx=b.new_context(viewport={"width":1280,"height":900})
    pg=ctx.new_page(); shot.install_routes(pg); errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(B+"/"); pg.wait_for_timeout(1200)
    check("Toko: 5 Best Seller", pg.locator("#rail .feature").count()==5, pg.locator("#rail .feature").count())
    check("Toko: 33 produk", pg.locator("#groups .product").count()==33)
    for y in range(0,5000,600): pg.evaluate(f"scrollTo(0,{y})"); pg.wait_for_timeout(50)
    pg.wait_for_timeout(500)
    broken=pg.evaluate("[...document.images].filter(i=>i.complete && i.naturalWidth===0).length")
    check("Toko: semua logo tampil", broken==0 and pg.locator(".tile-fallback").count()==0, (broken, pg.locator('.tile-fallback').count()))
    check("Toko: tombol Kelola toko tidak muncul", pg.locator("#adminLink").is_hidden())
    check("Toko: link preview og:image", pg.get_attribute('meta[property="og:image"]','content')==B+"/og.png")
    check("Toko: tanpa error JS", not errs, errs)
    # login salah
    pg.goto(B+"/admin"); pg.fill("#pw","salah"); pg.click("button[type=submit]"); pg.wait_for_load_state()
    check("Admin: kata sandi salah ditolak", "Kata sandi salah" in pg.inner_text("body"))
    pg.fill("#pw","uji-coba-123"); pg.click("button[type=submit]"); pg.wait_for_timeout(1500)
    check("Admin: masuk ke Kelola toko", pg.locator("#adminView").is_visible() and pg.locator("#alist .arow").count()==33, pg.url)
    # ubah harga canva
    pg.locator('.arow[data-id="p1"] .btn-edit').click(); pg.wait_for_timeout(200)
    pg.fill("#pk-0-p","7.500")
    pg.set_input_files("#e-file", files=[{"name":"j.png","mimeType":"image/png","buffer":pathlib.Path("assets/jasa-design.png").read_bytes()}]); pg.wait_for_timeout(600)
    check("Admin: unggah logo berhasil", "terunggah" in pg.inner_text("#e-logoStatus"), pg.inner_text("#e-logoStatus"))
    pg.click("#eSave"); pg.wait_for_timeout(200)
    pg.click("#publishBtn"); pg.wait_for_timeout(2500)
    check("Admin: terbit lalu halaman dimuat ulang", "Semua perubahan sudah terbit" in pg.inner_text("#saveStatus"), pg.inner_text("#saveStatus"))
    # pembeli baru
    c2=b.new_context(); q=c2.new_page(); shot.install_routes(q); q.goto(B+"/"); q.wait_for_timeout(1000)
    check("Pembeli: harga Canva baru tampil", "Rp7.500" in q.inner_text("#rail"))
    src=q.locator('#rail .feature[data-id="p1"] img').get_attribute("src")
    check("Pembeli: logo unggahan baru dipakai", src and src!="/_blob/c2708cb2d700b824720128df7b8ed067", src)
    q.wait_for_timeout(300); check("Pembeli: logo baru termuat", q.evaluate("(()=>{const i=document.querySelector('#rail .feature[data-id=\"p1\"] img');return i&&i.naturalWidth>0})()"))
    check("Pembeli: tidak bisa simpan data", q.evaluate("fetch('/api/data',{method:'POST',body:'{}'}).then(r=>r.status)")==401)
    # keluar
    pg.goto(B+"/logout"); pg.wait_for_timeout(500)
    check("Admin: keluar", pg.evaluate("fetch('/api/me').then(r=>r.json()).then(j=>j.admin)")==False)
    # HP: tanpa scroll samping
    m=b.new_page(viewport={"width":390,"height":844}); shot.install_routes(m); m.goto(B+"/"); m.wait_for_timeout(800)
    check("HP: tanpa scroll samping", m.evaluate("document.documentElement.scrollWidth")==390)
    m.goto(B+"/admin"); check("HP: halaman login tanpa scroll samping", m.evaluate("document.documentElement.scrollWidth")==390)
    m.screenshot(path="/tmp/claude-0/-home-claude/c5b4882c-d209-5a98-b6a7-200e04ab6a06/scratchpad/cf-login.png")
    b.close()
print(f"{ok} / {tot}")
