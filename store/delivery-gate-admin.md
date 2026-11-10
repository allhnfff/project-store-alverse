# Delivery Gate: AL STORE + Kelola toko (artifact claude.ai), 8 November 2026

Mode antislop: DURING. Design Read: toko langganan + alat kelola untuk pemilik toko yang mengatur katalog dari HP atau laptop, bahasa visual monokrom dari logo, dial ENERGY 2 / RHYTHM 2 / MOTION 1.

Bukti: 37/37 cek otomatis lulus di Chrome headless dengan runtime claude.ai tiruan (user, artifact, assets), lalu halaman diterbitkan dan dibaca balik dari server. Yang tidak bisa diuji dari sini: klik "Simpan & terbitkan" di akun asli pemilik, unggah logo dari HP asli, dan tautan publik.

## Blok 1: Hard Gate

- R-02 PASS: tidak ada em dash di teks halaman.
- R-03 PASS: tampilan pembeli dan admin tanpa scroll samping di 390px; tombol ≥ 44px; editor produk jadi lembar dari bawah di HP.
- R-17 / R-18 / R-36 / R-38 PASS: tidak ada angka atau testimoni karangan; daftar testimoni kosong sampai pemilik mengisi yang asli.
- R-23 PASS: logo dari pemilik, diunggah ke penyimpanan halaman; tanpa logo tampil monogram/inisial.
- R-24 PASS: semua tautan menuju bagian yang ada; "Kelola toko" hanya muncul untuk akun yang bisa mengedit.
- R-25 PASS: kontras sama dengan versi sebelumnya (teks 18,6:1, teks sekunder ≥ 6,4:1, merah peringatan di latar pucat ≥ 4,5:1).
- R-26 PASS: semua kontrol punya aksi: edit, tambah, hapus (konfirmasi di baris), naik/turun, sembunyikan, unggah logo, terbitkan, buang (klik dua kali).
- R-27 PASS: kosong (pencarian dan daftar admin), sedang menerbitkan, gagal terbit dengan pesan per kode error, draf lama dengan Pulihkan/Buang.
- R-28 PASS: FAQ milik pemilik, bisa diubah.
- R-32 PASS: Escape menutup editor, fokus kembali ke tombol Edit; semua kontrol bisa dicapai dengan Tab.
- R-33 PASS: halaman menerbitkan ulang dirinya dari sumber asli (CSS, kerangka, script) ditambah data baru, bukan dari DOM yang sedang tampil.
- R-35 PASS (lokal): klik-uji edit harga, harga salah ditolak, tambah paket, unggah logo, tambah produk, sembunyikan, ubah urutan, hapus, ubah nomor WA (dibersihkan jadi angka), link tanpa https ditolak, pratinjau toko, draf bertahan setelah muat ulang, terbitkan, buka hasil terbitan, terbitkan ulang dengan struktur stabil.
- R-39 PASS: label terlihat di semua kolom form, tombol ikon punya nama, kursor tangan di lapisan dasar.
- R-40 PASS: gambar punya width/height; tidak ada skrip pihak ketiga.

## Blok 2-4 (ringkas)

- Tanpa gradien, glow, atau glassmorphism; ikon digambar sendiri dengan sudut tajam mengikuti logo; satu animasi (lembar muncul).
- Satu aksen: inversi hitam (tombol utama, tab aktif, bar simpan hitam di bawah).
- Admin dibangun di sekitar satu keputusan: memperbaiki katalog lalu menerbitkan; bar simpan selalu menunjukkan ada/tidaknya perubahan yang belum terbit.
