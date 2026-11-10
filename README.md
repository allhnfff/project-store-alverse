# AL STORE

Toko online AL STORE: langganan aplikasi premium dan jasa desain, order lewat WhatsApp.
Satu halaman toko untuk pembeli, plus panel admin untuk mengubah produk, harga, logo, FAQ, dan info toko.

- Toko: https://alstore.pharsanani.workers.dev
- Admin: https://alstore.pharsanani.workers.dev/admin (masuk pakai kata sandi admin)

## Isi repo

| Folder | Isi |
|---|---|
| `store/` | Sumber utama toko + admin (`src.html`), data awal (`data.json`), logo produk (`logos/`), versi untuk Claude Artifact (`al-store.html`), dan tes otomatis |
| `cloudflare/` | Versi yang sedang tayang: Cloudflare Worker (`worker.js`), cetakannya (`worker.template.js`), skrip perakit (`build_cf.py`), dan tes lokal |
| `assets/` | Logo AL STORE, gambar pratinjau link (`og.png`), logo Jasa Design |
| `redirect-site/` | Situs pengalih di Vercel (`alstore-official.vercel.app` → toko Cloudflare) |
| `static-site/` | Versi statis lama (tanpa admin) |
| `original/` | File toko H&T asli sebelum didesain ulang |

## Data yang tayang

Data toko yang tayang disimpan di **Cloudflare KV** (namespace `alstore-data`, binding `DATA`), dan diubah lewat panel admin.
`store/data.json` hanyalah data awal: dipakai worker kalau KV masih kosong.
Logo yang diunggah lewat admin juga tersimpan di KV (`logo:<id>`), sedangkan logo bawaan tertanam di `worker.js`.

## Mengubah tampilan lalu memasang ulang

1. Edit `store/src.html` (CSS, kerangka HTML, dan JavaScript toko + admin ada di satu file).
2. Rakit ulang worker:
   ```bash
   pip install pillow
   python3 cloudflare/build_cf.py
   ```
3. Di dashboard Cloudflare: **Workers & Pages → alstore → Edit code**, ganti seluruh isi `worker.js` dengan `cloudflare/worker.js`, lalu **Deploy**.

Pengaturan Worker yang wajib ada (sudah terpasang):
- Binding KV `DATA` → namespace `alstore-data`
- Secret `ADMIN_PASSWORD` → kata sandi admin (tidak pernah disimpan di repo ini)

## Tes

```bash
# Tes worker di runtime Cloudflare lokal (miniflare)
cd cloudflare && npm install && node serve.mjs &   # memakai kata sandi uji, bukan kata sandi asli
cd .. && pip install playwright && python3 cloudflare/e2e.py

# Tes toko + admin versi Claude Artifact
python3 store/test_admin.py
```

`shot.py` memuat font dari `vendor/` (jalankan `npm install` di folder `vendor/` dulu) supaya tangkapan layar tes tidak bergantung pada CDN.
