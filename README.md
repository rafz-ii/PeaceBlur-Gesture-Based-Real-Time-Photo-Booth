# Foto Kita Blur ✌️

> Trend webcam real-time: begitu kamu pose **peace (dua jari / ✌️)**, **seluruh frame langsung nge-blur**.

Deteksi tangan pakai MediaPipe HandLandmarker (Tasks API) + OpenCV. Ringan, jalan real-time di CPU, nggak butuh internet setelah model ke-download sekali.

## ✨ Fitur

- Real-time dari webcam, di-mirror biar kayak ngaca.
- Deteksi pose peace akurat: cek bentuk "V" beneran, bukan asal dua jari.
- Blur full-frame instan pas pose kedetect.
- Anti-kedip: butuh beberapa frame berturut sebelum blur nyala + ditahan sebentar biar transisi mulus.
- Kekuatan blur bisa diatur langsung pas jalan (tombol `[` / `]`).
- Mode debug untuk lihat titik landmark tangan.
- Auto-download model — nggak perlu setup manual.
- **Bingkai tema Spiderman** (merah-biru + pola jaring laba-laba di pojok) menghiasi jendela webcam.
- **Photo booth otomatis**: tiap pose ✌️ langsung bunyi "cekrek" (disintesis sendiri, nggak perlu file audio tambahan) + efek bingkai kotak yang menyusut kayak shutter kamera, lalu foto bersih (tanpa blur) disimpan di memori — maksimal 4 foto.
- **Kolase otomatis + prompt pilihan**: begitu foto ke-4 kejepret, langsung tampil kolase 4 foto bertema Spiderman di jendela webcam yang sama, lengkap dengan dua tombol pilihan:
  - **[R] Foto Lagi** → otomatis balik ke tampilan live dari awal (hitungan foto reset ke 0).
  - **[S] Selesai** → otomatis matiin webcam & tutup program.
- **Musik latar** ikut main & **tetap looping terus** dari awal sampai program ditutup, persis kayak semula.
- **Simpan permanen ke disk + database**: begitu 1 sesi foto (4 foto) selesai, ke-4 foto bersih + kolasenya langsung disimpan sebagai file `.jpg` ke folder `hasil_foto/sesi_<timestamp>/`, dan riwayatnya (nama file, path, waktu) dicatat ke database SQLite lokal `foto_kita.db` — nggak butuh server database eksternal, tinggal jalan.

## 🧠 Cara Kerja

1. Tiap frame webcam diambil & di-mirror.
2. MediaPipe mendeteksi 21 landmark tangan.
3. Cek pose peace dengan 3 syarat:
   - Telunjuk + jari tengah naik (ujung jari lebih tinggi dari sendi).
   - Jari manis + kelingking turun.
   - Telunjuk & tengah mekar (bentuk "V"), biar nggak ketuker dua jari rapat.
4. Kalau kedetect → `cv2.GaussianBlur` ke seluruh frame.
5. State machine kecil (`PEACE_CONFIRM` + `HOLD_FRAMES`) bikin transisinya stabil.
6. Begitu pose ✌️ pertama kali kekonfirmasi: suara "cekrek" (disintesis via numpy, bukan file mp3 terpisah) langsung bunyi, muncul efek bingkai kotak yang menyusut dari tepi layar (kayak shutter kamera lagi nutup), dan versi frame yang **bersih** (sebelum di-blur) disimpan sebagai foto ke-N (maks 4 foto). Ada cooldown ~1.5 detik biar nggak nge-jepret berkali-kali dalam satu pose.
7. Begitu foto ke-4 kejepret dan efek kotaknya kelar, kolase 4 foto (bertema Spiderman, ukurannya otomatis pas dengan jendela webcam) langsung tampil menggantikan tampilan live — lengkap dengan dua tombol pilihan di bagian bawah: **Foto Lagi** dan **Selesai**.
8. **Persis di momen itu juga**, ke-4 foto bersih + kolasenya langsung ditulis sebagai file `.jpg` ke folder baru `hasil_foto/sesi_<tanggal_jam>/`, dan satu baris riwayat sesi + 4 baris riwayat foto dicatat ke database SQLite `foto_kita.db`. Kalau kamu pilih **Foto Lagi** dan motret 4 foto lagi, sesi berikutnya akan tersimpan di folder & baris database yang baru lagi (foto lama nggak ketimpa).
9. Pilih **Foto Lagi** (`r`) → otomatis balik ke tampilan live, semua foto di memori direset (foto yang sudah tersimpan di disk tidak terhapus). Pilih **Selesai** (`s`) → webcam otomatis mati & program ditutup. Musik tetap lanjut muter looping di background dari awal sampai program benar-benar ditutup.

## 📦 Requirement

- Python 3.12 (MediaPipe belum support 3.13/3.14)
- Webcam
- macOS / Windows / Linux

## 🚀 Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 🎵 Lagu

Lagu **`lagu.mp3`** (dari `Foto_kita_blur.mp3` kamu) sudah ada di folder project ini dan otomatis diputar loop begitu `peace_blur.py` dijalankan — nggak perlu setup tambahan.

```
foto-kita-blur/
├── peace_blur.py
├── README.md
├── requirements.txt
├── test_peace.py
├── hand_landmarker.task
├── lagu.mp3           ← sudah otomatis dipakai di kode
├── foto_kita.db       ← dibuat otomatis, database riwayat sesi & foto
└── hasil_foto/        ← dibuat otomatis, isi: foto & kolase per sesi
```

Kalau mau ganti lagu, tinggal timpa file `lagu.mp3` dengan lagu lain (format `.mp3`, `.wav`, atau `.ogg` semua didukung, asal ganti ekstensi di `MUSIC_PATH` pada `peace_blur.py` kalau bukan mp3). Kalau file `lagu.mp3` dihapus/hilang, program tetap jalan normal tanpa musik — cuma muncul pesan di terminal.

## ▶️ Jalankan

```bash
python peace_blur.py
```

Pas pertama jalan, model `hand_landmarker.task` (~7.5MB) auto-download, dan lagu (kalau ada `lagu.mp3`) langsung diputar loop. Arahkan tangan ke kamera → pose ✌️ → blur nyala.

## 🎮 Kontrol

| Tombol      | Fungsi                                   |
|-------------|-------------------------------------------|
| pose ✌️     | bunyi "cekrek" + efek kotak jepretan + simpan foto (maks 4, di memori) |
| `q` / `ESC` | keluar kapan saja                          |
| `h`         | show/hide HUD (mode live)                  |
| `d`         | show/hide titik landmark tangan (debug, mode live) |
| `[`         | turunin kekuatan blur (mode live)          |
| `]`         | naikin kekuatan blur (mode live)           |
| `m`         | mute / unmute musik (mode live)            |
| `r`         | **Foto Lagi** — di layar kolase, balik ke live & reset foto |
| `s`         | **Selesai** — di layar kolase, matiin webcam & tutup program |

## 🛠️ Tuning

Edit konstanta di `peace_blur.py` fungsi `main()`:

| Konstanta       | Fungsi                                                | Default |
|-----------------|--------------------------------------------------------|---------|
| `PEACE_CONFIRM` | jumlah frame berturut sebelum blur nyala (anti-kedip) | `2`     |
| `HOLD_FRAMES`   | berapa lama blur ditahan setelah pose ilang           | `6`     |
| `blur_strength` | kekuatan blur awal (ukuran kernel)                    | `75`    |

## 🧪 Tes

```bash
python test_peace.py
```

## 📁 Struktur Project

```
foto-kita-blur/
├── peace_blur.py      # app webcam real-time + auto-download model + photo booth
├── test_peace.py      # unit test logika is_peace (pakai landmark sintetis)
├── requirements.txt   # opencv-python, mediapipe, pygame, numpy
├── README.md
├── foto_kita.db       # database SQLite, dibuat otomatis (riwayat sesi & foto)
├── hasil_foto/        # folder hasil foto & kolase per sesi, dibuat otomatis
└── .gitignore
```

> Catatan: selama satu sesi masih berjalan (belum sampai 4 foto), foto-foto disimpan sementara di memori. **Begitu foto ke-4 kejepret**, ke-4 foto bersih + kolasenya langsung ditulis permanen sebagai file `.jpg` ke `hasil_foto/sesi_<timestamp>/`, dan dicatat ke database SQLite `foto_kita.db` (tabel `sessions` & `photos`). Kalau mau lihat isi database-nya bisa pakai tool apa pun yang baca SQLite, misalnya:
> ```bash
> sqlite3 foto_kita.db "SELECT * FROM sessions;"
> sqlite3 foto_kita.db "SELECT * FROM photos;"
> ```

## 🩹 Troubleshooting

- **Window kamera hitam / nggak muncul (macOS):** kasih izin di System Settings → Privacy & Security → Camera.
- **`No module named mediapipe`:** pastikan venv-nya Python 3.12.
- **Webcam kepakai app lain:** tutup Zoom/Meet/OBS, atau ganti index device di `cv2.VideoCapture(0)` → `1`.
- **Peace susah kedetect:** kasih cahaya cukup, tangan tegak, turunin `min_hand_detection_confidence`.
