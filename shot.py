"""Preview helper: serves Google Fonts / Font Awesome from local npm copies
(the sandbox blocks those CDNs) and blocks other remote images so their
fallbacks are exercised. Usage: python3 shot.py page.html outprefix [widths...]"""
import sys, pathlib, re
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).parent
V = ROOT / "vendor/node_modules"

def font_css(family_pkg):
    css = ""
    d = V / "@fontsource" / family_pkg
    for w in (400, 500, 600, 700, 800):
        f = d / f"latin-{w}.css"
        if f.exists():
            css += f.read_text()
    return re.sub(r"url\(\./files/", f"url(https://local.fonts/{family_pkg}/files/", css)

def install_routes(page):
    def gfonts(route):
        url = route.request.url
        if "Archivo" in url:
            css = ("@font-face{font-family:'Archivo';font-style:normal;font-display:swap;"
                   "font-weight:100 900;font-stretch:62% 125%;"
                   "src:url(https://local.fonts/archivo-var) format('woff2-variations');}")
        else:
            css = font_css("plus-jakarta-sans") if "Plus+Jakarta" in url else font_css("inter")
        route.fulfill(status=200, content_type="text/css", body=css)
    def localfont(route):
        p = route.request.url.split("https://local.fonts/")[1]
        if p == "archivo-var":
            f = V / "@fontsource-variable/archivo/files/archivo-latin-standard-normal.woff2"
            return route.fulfill(status=200, body=f.read_bytes(), content_type="font/woff2")
        pkg, rest = p.split("/", 1)
        route.fulfill(status=200, body=(V / "@fontsource" / pkg / rest).read_bytes(), content_type="font/woff2")
    def fa(route):
        url = route.request.url
        if url.endswith("all.min.css"):
            route.fulfill(status=200, content_type="text/css", body=(V / "@fortawesome/fontawesome-free/css/all.min.css").read_text())
        else:
            name = url.split("/webfonts/")[1].split("?")[0]
            route.fulfill(status=200, body=(V / "@fortawesome/fontawesome-free/webfonts" / name).read_bytes())
    page.route("https://fonts.googleapis.com/**", gfonts)
    page.route("https://fonts.gstatic.com/**", lambda r: r.abort())
    page.route("https://local.fonts/**", localfont)
    page.route("https://cdnjs.cloudflare.com/**", fa)

def main():
    src, prefix = sys.argv[1], sys.argv[2]
    widths = [int(w) for w in sys.argv[3:]] or [1440, 390]
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/usr/bin/google-chrome")
        for w in widths:
            pg = b.new_page(viewport={"width": w, "height": 900})
            install_routes(pg)
            pg.goto((ROOT / src).as_uri())
            pg.wait_for_timeout(800)
            pg.screenshot(path=str(ROOT / f"{prefix}-{w}.png"), full_page=True)
            print(w, pg.evaluate("[document.documentElement.scrollWidth, innerWidth, document.documentElement.scrollHeight]"))
        b.close()

if __name__ == "__main__":
    main()
