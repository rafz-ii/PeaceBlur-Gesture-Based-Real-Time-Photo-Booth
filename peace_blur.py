"""
Foto Blur Kita ✌️
Trend webcam real-time: begitu kamu pose peace (dua jari / ✌️),
seluruh frame langsung nge-blur.

+ Badge animasi mini bertema web-slinger (merah-biru + pola jaring laba-laba)
  ngambang pelan di pojok kanan-atas jendela webcam (bukan bingkai penuh lagi).
+ Photo booth: tiap kali pose peace kedetect -> bunyi "cekrek" (disintesis sendiri,
  nggak perlu file audio tambahan) + efek kotak foto (bingkai kotak yang menyusut,
  kayak shutter kamera beneran) -> foto (bersih, tanpa blur) disimpan di memori,
  maksimal 4 foto.
+ Begitu foto ke-4 kejepret, LANGSUNG tampil kolase 4 foto (judul dengan efek 3D
  biru-merah) di jendela webcam yang sama (nggak buka jendela baru), lengkap
  dengan tombol pilihan kecil "Foto Lagi" / "Selesai":
    - Foto Lagi (tombol R) -> otomatis balik ke awal (live, hitungan foto ke-0 lagi).
    - Selesai   (tombol S) -> otomatis matiin webcam & tutup program.
+ Musik latar tetap muter looping terus dari awal sampai program ditutup,
  persis kayak semula.
+ Penyimpanan permanen: begitu satu sesi foto (4 foto) selesai, ke-4 foto
  bersih + kolasenya langsung disimpan sebagai file .jpg ke folder
  `hasil_foto/sesi_<timestamp>/`, dan catatannya (nama file, path, waktu)
  dicatat ke database SQLite lokal `foto_kita.db` (tabel `sessions` &
  `photos`). Nggak butuh server/koneksi database eksternal apa pun.

Deteksi tangan pakai MediaPipe HandLandmarker (Tasks API) + OpenCV.
"""

import os
import sqlite3
import urllib.request
from datetime import datetime

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision as mp_vision

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MUSIC_PATH = os.path.join(BASE_DIR, "lagu.mp3")

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
MODEL_PATH = os.path.join(BASE_DIR, "hand_landmarker.task")

MAX_PHOTOS = 4
WINDOW_NAME = "Foto Blur Kita"

# ---- Penyimpanan foto & database ----
PHOTOS_DIR = os.path.join(BASE_DIR, "hasil_foto")
DB_PATH = os.path.join(BASE_DIR, "foto_kita.db")


def init_database():
    """
    Siapin database SQLite lokal (file tunggal `foto_kita.db`, otomatis
    dibuat kalau belum ada) buat nyatet riwayat tiap sesi foto & file foto
    yang udah disimpan ke disk. Aman dipanggil berkali-kali.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            folder_path TEXT NOT NULL,
            collage_path TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            urutan INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions (id)
        )
    """)
    conn.commit()
    return conn


def save_session_to_disk(conn, photos, collage):
    """
    Begitu satu sesi foto (maks MAX_PHOTOS foto) selesai, simpan ke-4 foto
    bersih + kolasenya sebagai file .jpg ke folder
    `hasil_foto/sesi_<timestamp>/`, lalu catat sesi & tiap foto ke database
    SQLite (`foto_kita.db`). Mengembalikan path folder sesi.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_folder = os.path.join(PHOTOS_DIR, f"sesi_{timestamp}")
    os.makedirs(session_folder, exist_ok=True)

    photo_paths = []
    for i, photo in enumerate(photos, start=1):
        filename = f"foto_{i}.jpg"
        filepath = os.path.join(session_folder, filename)
        cv2.imwrite(filepath, photo)
        photo_paths.append(filepath)

    collage_path = os.path.join(session_folder, "kolase.jpg")
    cv2.imwrite(collage_path, collage)

    now_str = datetime.now().isoformat(timespec="seconds")
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO sessions (created_at, folder_path, collage_path) VALUES (?, ?, ?)",
        (now_str, session_folder, collage_path),
    )
    session_id = cur.lastrowid
    for urutan, filepath in enumerate(photo_paths, start=1):
        cur.execute(
            "INSERT INTO photos (session_id, urutan, file_path, created_at) VALUES (?, ?, ?, ?)",
            (session_id, urutan, filepath, now_str),
        )
    conn.commit()

    return session_folder


def download_model_if_needed():
    """Auto-download model hand_landmarker.task kalau belum ada."""
    if os.path.exists(MODEL_PATH):
        return
    print("Mengunduh model hand_landmarker.task (~7.5MB)...")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print("Model berhasil diunduh:", MODEL_PATH)


def init_audio():
    """Siapin mixer pygame (buat musik & efek suara cekrek). Aman dipanggil
    walau lagu.mp3 nggak ada — efek cekrek tetap bisa jalan."""
    if not PYGAME_AVAILABLE:
        print("pygame belum terinstall (pip install pygame) — audio dilewati.")
        return False
    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=2)
        return True
    except Exception as e:
        print(f"Gagal init audio: {e}")
        return False


def play_music():
    """
    Putar lagu latar (lagu.mp3) looping terus dari awal sampai program ditutup —
    persis kayak versi semula. Kalau file-nya nggak ada, program tetap jalan
    normal tanpa musik.
    """
    if not os.path.exists(MUSIC_PATH):
        print(f"File musik tidak ditemukan di: {MUSIC_PATH}")
        print("Taruh file mp3 kamu di situ dengan nama 'lagu.mp3' supaya musik ikut jalan.")
        return False
    try:
        pygame.mixer.music.load(MUSIC_PATH)
        pygame.mixer.music.play(loops=-1)  # -1 = loop selamanya, kayak semula
        print(f"Memutar musik (loop): {MUSIC_PATH}")
        return True
    except Exception as e:
        print(f"Gagal memutar musik: {e}")
        return False


def generate_shutter_sound(sample_rate=44100):
    """
    Bikin efek suara 'cekrek' (shutter kamera) secara sintetis lewat numpy —
    nggak butuh file audio eksternal sama sekali.
    """
    duration = 0.14
    n = int(sample_rate * duration)
    t = np.linspace(0, duration, n, endpoint=False)

    # "cek" -> klik pertama, tajam & cepat redup
    click1 = np.random.uniform(-1, 1, n) * np.exp(-45 * t)

    # "rek" -> klik kedua, muncul sedikit setelah klik pertama
    start2 = int(n * 0.32)
    click2 = np.zeros(n)
    t2 = t[: n - start2]
    click2[start2:] = np.random.uniform(-1, 1, n - start2) * np.exp(-55 * t2)

    wave = np.clip(click1 * 0.7 + click2 * 0.9, -1, 1)
    audio = (wave * 32767 * 0.8).astype(np.int16)
    stereo = np.ascontiguousarray(np.column_stack([audio, audio]))
    return pygame.sndarray.make_sound(stereo)


def create_hand_landmarker(min_hand_detection_confidence=0.5):
    """Buat instance HandLandmarker dari MediaPipe Tasks API."""
    base_options = mp_tasks.BaseOptions(model_asset_path=MODEL_PATH)
    options = mp_vision.HandLandmarkerOptions(
        base_options=base_options,
        running_mode=mp_vision.RunningMode.VIDEO,
        num_hands=2,
        min_hand_detection_confidence=min_hand_detection_confidence,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    return mp_vision.HandLandmarker.create_from_options(options)


# Index landmark MediaPipe hand (21 titik):
# 0 wrist
# 4 thumb tip        3 thumb ip
# 8 index tip        6 index pip
# 12 middle tip       10 middle pip
# 16 ring tip        14 ring pip
# 20 pinky tip       18 pinky pip
FINGER_TIPS = {"index": 8, "middle": 12, "ring": 16, "pinky": 20}
FINGER_PIPS = {"index": 6, "middle": 10, "ring": 14, "pinky": 18}


def is_peace(landmarks, spread_threshold=0.08):
    """
    Cek apakah landmark tangan membentuk pose peace (✌️).

    Syarat:
      1. Telunjuk + jari tengah "naik" (ujung jari lebih tinggi / y lebih kecil
         dari sendi PIP-nya).
      2. Jari manis + kelingking "turun" (ujung jari lebih rendah dari PIP).
      3. Telunjuk & tengah "mekar" (jarak antar ujung jari cukup jauh),
         supaya nggak ketuker sama dua jari yang dirapetin / tangan mengepal.
    """
    def tip(name):
        return landmarks[FINGER_TIPS[name]]

    def pip(name):
        return landmarks[FINGER_PIPS[name]]

    index_up = tip("index").y < pip("index").y
    middle_up = tip("middle").y < pip("middle").y
    ring_down = tip("ring").y > pip("ring").y
    pinky_down = tip("pinky").y > pip("pinky").y

    dx = tip("index").x - tip("middle").x
    dy = tip("index").y - tip("middle").y
    spread = (dx ** 2 + dy ** 2) ** 0.5
    fingers_spread = spread > spread_threshold

    return index_up and middle_up and ring_down and pinky_down and fingers_spread


def draw_landmarks(frame, landmarks, w, h):
    """Gambar titik-titik landmark tangan (mode debug)."""
    for lm in landmarks:
        cx, cy = int(lm.x * w), int(lm.y * h)
        cv2.circle(frame, (cx, cy), 4, (0, 255, 0), -1)


# ---------------------------------------------------------------------------
# Mini animasi "web-slinger" di pojok webcam (bukan logo/karakter berhak
# cipta — cuma bentuk sederhana bertema merah-biru + jaring laba-laba)
# ---------------------------------------------------------------------------

def _draw_mini_web_pattern(canvas, cx, cy, size, color, steps=8):
    """Gambar pola jaring radial kecil di dalam badge mini."""
    for a in np.linspace(0, 360, steps, endpoint=False):
        rad = np.radians(a)
        x2 = int(cx + size * np.cos(rad))
        y2 = int(cy + size * np.sin(rad))
        cv2.line(canvas, (cx, cy), (x2, y2), color, 1, cv2.LINE_AA)
    for r in (size * 0.4, size * 0.7, size * 1.0):
        cv2.circle(canvas, (cx, cy), int(r), color, 1, cv2.LINE_AA)


def draw_spiderman_mini(frame, w, h, frame_counter=0):
    """
    Badge animasi kecil bertema web-slinger di pojok kanan-atas webcam,
    menggantikan bingkai penuh yang lama. Badge ini "mengambang" naik-turun
    pelan (efek animasi sederhana) dan punya wajah kartun simpel merah-biru
    dengan pola jaring — bukan logo/karakter berhak cipta.
    """
    RED = (0, 0, 220)
    BLUE = (200, 60, 0)
    WHITE = (245, 245, 245)
    DARK = (20, 20, 20)

    badge_r = max(26, int(min(w, h) * 0.075))
    margin = int(badge_r * 0.6)

    # animasi mengambang pelan (bounce) berdasarkan counter frame
    bounce = int(np.sin(frame_counter * 0.12) * badge_r * 0.18)

    cx = w - margin - badge_r
    cy = margin + badge_r + bounce

    # panel bulat semi-transparan sebagai dasar badge
    overlay = frame.copy()
    cv2.circle(overlay, (cx, cy), badge_r + 6, (15, 15, 15), -1)
    cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, dst=frame)

    # "kepala" merah dengan pola jaring biru tipis
    cv2.circle(frame, (cx, cy), badge_r, RED, -1, cv2.LINE_AA)
    _draw_mini_web_pattern(frame, cx, cy, badge_r * 0.85, BLUE)
    cv2.circle(frame, (cx, cy), badge_r, DARK, 2, cv2.LINE_AA)

    # dua "mata" putih besar bentuk sipit (khas web-slinger, generik)
    eye_w = int(badge_r * 0.42)
    eye_h = int(badge_r * 0.30)
    eye_dx = int(badge_r * 0.38)
    eye_dy = int(badge_r * 0.05)
    for sign in (-1, 1):
        ex = cx + sign * eye_dx
        ey = cy - eye_dy
        cv2.ellipse(frame, (ex, ey), (eye_w, eye_h), 0, 0, 360, WHITE, -1, cv2.LINE_AA)
        cv2.ellipse(frame, (ex, ey), (eye_w, eye_h), 0, 0, 360, DARK, 2, cv2.LINE_AA)

    return frame


def draw_gabut_label(frame):
    """
    Tulisan "FOTO GABUT" di pojok kiri-atas webcam. Tampil terus selama
    mode live (dari awal jendela webcam dibuka), dan berhenti muncul begitu
    kolase/hasil foto ditampilkan.
    """
    h, w = frame.shape[:2]
    scale = h / 480
    text = "FOTO GABUT"
    font_scale = 0.75 * scale
    thickness = 2
    org = (int(18 * scale), int(38 * scale))

    (tw_, th_), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, font_scale, thickness)
    pad = int(8 * scale)
    box_pt1 = (org[0] - pad, org[1] - th_ - pad)
    box_pt2 = (org[0] + tw_ + pad, org[1] + pad)

    overlay = frame.copy()
    cv2.rectangle(overlay, box_pt1, box_pt2, (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, dst=frame)
    cv2.rectangle(frame, box_pt1, box_pt2, (0, 0, 220), 2)

    cv2.putText(frame, text, org, cv2.FONT_HERSHEY_DUPLEX, font_scale,
                (255, 255, 255), thickness, cv2.LINE_AA)


def draw_capture_effect(frame, w, h, progress):
    """
    Efek jepretan foto: kilat putih + bingkai KOTAK yang menyusut dari tepi
    layar ke tengah, kayak shutter/viewfinder kamera lagi nutup, plus
    tulisan "SNAP" yang muncul kuat di tengah pas efeknya lagi berlangsung.
    progress: 1.0 = baru saja kejepret -> 0.0 = efek selesai.
    """
    alpha = progress * 0.65
    if alpha > 0:
        white = np.full_like(frame, 255)
        cv2.addWeighted(white, alpha, frame, 1 - alpha, 0, dst=frame)

    shrink = 1 - progress  # 0 -> full frame, 1 -> kotak kecil di tengah
    margin_x = int(w * 0.48 * shrink)
    margin_y = int(h * 0.48 * shrink)
    pt1 = (margin_x, margin_y)
    pt2 = (w - margin_x, h - margin_y)
    thickness = max(3, int(8 * progress))
    cv2.rectangle(frame, pt1, pt2, (255, 255, 255), thickness)

    # tulisan "SNAP" di tengah, makin gede & tebal pas awal jepretan
    scale = h / 480
    font_scale = (1.4 + 0.6 * progress) * scale
    text = "SNAP"
    (tw_, th_), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, font_scale, 4)
    tx = w // 2 - tw_ // 2
    ty = h // 2 + th_ // 2
    cv2.putText(frame, text, (tx, ty), cv2.FONT_HERSHEY_DUPLEX, font_scale,
                (0, 0, 0), 8, cv2.LINE_AA)
    cv2.putText(frame, text, (tx, ty), cv2.FONT_HERSHEY_DUPLEX, font_scale,
                (0, 0, 220), 5, cv2.LINE_AA)
    cv2.putText(frame, text, (tx, ty), cv2.FONT_HERSHEY_DUPLEX, font_scale,
                (255, 255, 255), 2, cv2.LINE_AA)


def _paste_rotated(canvas, img, mask, cx, cy):
    """Tempel `img` (dengan alpha `mask` 0-255) ke `canvas` berpusat di (cx, cy),
    aman walau sebagian keluar dari tepi canvas."""
    ch, cw = canvas.shape[:2]
    ih, iw = img.shape[:2]
    x0, y0 = int(cx - iw / 2), int(cy - ih / 2)
    x1, y1 = x0 + iw, y0 + ih

    cx0, cy0 = max(x0, 0), max(y0, 0)
    cx1, cy1 = min(x1, cw), min(y1, ch)
    if cx0 >= cx1 or cy0 >= cy1:
        return

    ix0, iy0 = cx0 - x0, cy0 - y0
    ix1, iy1 = ix0 + (cx1 - cx0), iy0 + (cy1 - cy0)

    roi = canvas[cy0:cy1, cx0:cx1].astype(np.float32)
    img_crop = img[iy0:iy1, ix0:ix1].astype(np.float32)
    mask_crop = (mask[iy0:iy1, ix0:ix1].astype(np.float32) / 255.0)[..., None]

    blended = roi * (1 - mask_crop) + img_crop * mask_crop
    canvas[cy0:cy1, cx0:cx1] = blended.astype(np.uint8)


def make_polaroid(photo, target_w, target_h, border=12, bottom_extra=30):
    """Bungkus satu foto jadi bingkai polaroid krem (border tebal di bawah)."""
    ph = cv2.resize(photo, (target_w, target_h))
    total_w = target_w + border * 2
    total_h = target_h + border * 2 + bottom_extra

    polaroid = np.full((total_h, total_w, 3), 240, dtype=np.uint8)
    polaroid[border:border + target_h, border:border + target_w] = ph
    cv2.rectangle(polaroid, (border - 1, border - 1),
                  (border + target_w, border + target_h), (70, 70, 70), 1)
    return polaroid


def rotate_and_paste(canvas, polaroid_img, cx, cy, angle_deg, shadow_offset=6):
    """Putar bingkai polaroid `angle_deg` derajat, kasih bayangan lembut,
    lalu tempel di canvas berpusat di (cx, cy)."""
    h_img, w_img = polaroid_img.shape[:2]
    M = cv2.getRotationMatrix2D((w_img / 2, h_img / 2), angle_deg, 1.0)
    cos, sin = abs(M[0, 0]), abs(M[0, 1])
    new_w = int(h_img * sin + w_img * cos)
    new_h = int(h_img * cos + w_img * sin)
    M[0, 2] += new_w / 2 - w_img / 2
    M[1, 2] += new_h / 2 - h_img / 2

    rotated = cv2.warpAffine(polaroid_img, M, (new_w, new_h), borderValue=(0, 0, 0))
    full_mask = np.full((h_img, w_img), 255, dtype=np.uint8)
    rotated_mask = cv2.warpAffine(full_mask, M, (new_w, new_h), borderValue=0)

    # bayangan lembut (blur) sedikit di kanan-bawah sebelum bingkai ditempel
    shadow_mask = cv2.GaussianBlur(rotated_mask, (21, 21), 0)
    shadow_img = np.zeros((new_h, new_w, 3), dtype=np.uint8)
    _paste_rotated(canvas, shadow_img, (shadow_mask * 0.5).astype(np.uint8),
                   cx + shadow_offset, cy + shadow_offset)

    _paste_rotated(canvas, rotated, rotated_mask, cx, cy)


def build_scrapbook_background(w, h):
    """
    Background orisinal bertema komik merah-hitam: gradasi gelap, garis
    diagonal, pola halftone titik-titik ala komik, dan garis jaring tipis
    di pojok. Tidak memakai karakter/logo berhak cipta apa pun.
    """
    canvas = np.zeros((h, w, 3), dtype=np.uint8)
    top = np.array([10, 8, 15], dtype=np.float32)     # gelap
    bottom = np.array([25, 15, 90], dtype=np.float32)  # merah gelap
    for y in range(h):
        t = y / max(1, h - 1)
        canvas[y, :] = (top * (1 - t) + bottom * t).astype(np.uint8)

    # garis diagonal selang-seling merah/hitam ala komik
    overlay = canvas.copy()
    spacing = max(24, w // 22)
    for i in range(-h, w + h, spacing):
        color = (0, 0, 130) if (i // spacing) % 2 == 0 else (5, 5, 5)
        cv2.line(overlay, (i, 0), (i + h, h), color, max(6, spacing // 3))
    cv2.addWeighted(overlay, 0.28, canvas, 0.72, 0, dst=canvas)

    # pola halftone (titik-titik kecil ala komik cetak)
    dot_layer = canvas.copy()
    step = max(10, w // 60)
    rng = np.random.default_rng(7)
    for yy in range(0, h, step):
        for xx in range(0, w, step):
            r = int(rng.integers(1, 3))
            cv2.circle(dot_layer, (xx, yy), r, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.addWeighted(dot_layer, 0.05, canvas, 0.95, 0, dst=canvas)

    # garis jaring tipis di keempat pojok (aksen dekoratif, bukan logo)
    corners = [(0, 0), (w, 0), (w, h), (0, h)]
    web_size = int(min(w, h) * 0.32)
    for cx_, cy_ in corners:
        for a in np.linspace(0, 90, 6):
            base_angle = np.degrees(np.arctan2(-(cy_ - h / 2), -(cx_ - w / 2)))
            rad = np.radians(a + base_angle - 45)
            x2 = int(cx_ + web_size * np.cos(rad))
            y2 = int(cy_ + web_size * np.sin(rad))
            cv2.line(canvas, (cx_, cy_), (x2, y2), (90, 40, 40), 1, cv2.LINE_AA)

    # vignette lembut di tepi
    yy, xx = np.mgrid[0:h, 0:w]
    cx_c, cy_c = w / 2, h / 2
    dist = np.sqrt(((xx - cx_c) / (w / 2)) ** 2 + ((yy - cy_c) / (h / 2)) ** 2)
    vig = np.clip(1.15 - 0.35 * dist, 0.55, 1.0)[..., None]
    canvas = (canvas.astype(np.float32) * vig).astype(np.uint8)

    return canvas


def _draw_scrap_star(canvas, center, size, color=(255, 255, 255)):
    """Bintang kecil dekoratif ala tempelan scrapbook (bentuk orisinal)."""
    cx_, cy_ = center
    pts = []
    for i in range(10):
        angle = np.pi / 2 + i * np.pi / 5
        r = size if i % 2 == 0 else size * 0.42
        pts.append((int(cx_ + r * np.cos(angle)), int(cy_ - r * np.sin(angle))))
    pts = np.array([pts], dtype=np.int32)
    cv2.fillPoly(canvas, pts, color, cv2.LINE_AA)


def draw_3d_title(canvas, text, org, font_scale=1.0):
    """
    Gambar teks judul dengan efek "3D" ekstrusi yang rapat & tegas: lapisan
    bayangan biru & merah ditumpuk diagonal tipis (kayak logo timbul tipis),
    lalu wajah teks putih tebal di atas dengan outline gelap tajam.
    """
    x, y = org
    depth = 4  # ekstrusi lebih pendek/rapat biar kesannya tegas, bukan buram

    # ekstrusi belakang: selang-seling biru & merah, makin jauh makin gelap
    for i in range(depth, 0, -1):
        if i % 2 == 0:
            color = (150, 40, 0)      # biru gelap (BGR)
        else:
            color = (0, 0, 180)       # merah gelap (BGR)
        cv2.putText(canvas, text, (x + i, y + i),
                    cv2.FONT_HERSHEY_DUPLEX, font_scale, color, 2, cv2.LINE_AA)

    # lapisan aksen biru & merah dekat permukaan buat kesan tebal/timbul
    cv2.putText(canvas, text, (x + 2, y + 2),
                cv2.FONT_HERSHEY_DUPLEX, font_scale, (200, 60, 0), 2, cv2.LINE_AA)
    cv2.putText(canvas, text, (x + 1, y + 1),
                cv2.FONT_HERSHEY_DUPLEX, font_scale, (0, 0, 220), 2, cv2.LINE_AA)

    # wajah depan: putih tebal dengan outline gelap tajam biar tegas & jelas
    cv2.putText(canvas, text, (x, y),
                cv2.FONT_HERSHEY_DUPLEX, font_scale, (10, 10, 10), 3, cv2.LINE_AA)
    cv2.putText(canvas, text, (x, y),
                cv2.FONT_HERSHEY_DUPLEX, font_scale, (255, 255, 255), 1, cv2.LINE_AA)


def build_collage(photos, w, h, title="HASIL FOTO KITA"):
    """
    Susun sampai 4 foto (tanpa blur) sebagai bingkai POLAROID yang sedikit
    miring, bertebaran di atas background scrapbook merah-hitam orisinal
    (bukan karakter/logo berhak cipta). Kolase selalu berbentuk LANDSCAPE,
    apa pun orientasi webcam aslinya.
    """
    # paksa landscape: lebar selalu >= tinggi
    cw, ch = (w, h) if w >= h else (h, w)

    canvas = build_scrapbook_background(cw, ch)
    scale = ch / 480

    title_h = max(60, int(ch * 0.16))
    draw_3d_title(canvas, title, (int(cw * 0.04), int(title_h * 0.62)), font_scale=0.6 * scale)

    # tempelan bintang dekoratif kecil ala scrapbook di sekitar judul
    _draw_scrap_star(canvas, (int(cw * 0.90), int(title_h * 0.35)), int(ch * 0.03), (255, 255, 255))
    _draw_scrap_star(canvas, (int(cw * 0.95), int(title_h * 0.65)), int(ch * 0.018), (0, 0, 220))

    avail_h = ch - title_h
    photo_w = int(cw * 0.30)
    photo_h = int(photo_w * 0.66)

    # posisi (fraksi lebar, fraksi tinggi area foto, sudut kemiringan derajat)
    slots = [
        (0.24, 0.30, -8),
        (0.75, 0.24, 6),
        (0.27, 0.76, 5),
        (0.76, 0.74, -6),
    ]

    for i, (fx, fy, angle) in enumerate(slots):
        cx = fx * cw
        cy = title_h + fy * avail_h

        if i < len(photos):
            polaroid = make_polaroid(photos[i], photo_w, photo_h)
        else:
            blank = np.full((photo_h, photo_w, 3), 45, dtype=np.uint8)
            txt = "kosong"
            (tw_, th_), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 0.55 * scale, 2)
            cv2.putText(blank, txt, ((photo_w - tw_) // 2, (photo_h + th_) // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55 * scale, (150, 150, 150), 2, cv2.LINE_AA)
            polaroid = make_polaroid(blank, photo_w, photo_h)

        rotate_and_paste(canvas, polaroid, cx, cy, angle)

    draw_spiderman_mini(canvas, cw, ch)
    return canvas


def draw_choice_prompt(canvas, w, h):
    """
    Tambahkan bar pilihan baru DI BAWAH kolase (bukan menimpa foto di
    kolase). Ini bikin tinggi gambar akhir sedikit lebih besar dari (w, h)
    kolase asli — jendela webcam otomatis menyesuaikan jadi sedikit lebih
    tinggi, tapi kolase 4 foto tetap utuh kelihatan tanpa ketutupan.
    Tombol "FOTO LAGI" / "SELESAI" dibuat agak lebih besar & jelas.
    """
    scale = h / 480
    bar_h = max(90, int(h * 0.20))  # bar terpisah, agak lebih tinggi biar tombol jelas

    total_h = h + bar_h
    out = np.full((total_h, w, 3), 25, dtype=np.uint8)
    out[0:h, 0:w] = canvas

    # garis pemisah tipis antara kolase & bar tombol
    cv2.line(out, (0, h), (w, h), (90, 90, 90), 1, cv2.LINE_AA)

    pad = int(w * 0.05)
    slot_w = (w - pad * 3) // 2
    btn_w = int(slot_w * 0.82)
    btn_h = int(bar_h * 0.55)
    btn_y = h + (bar_h - btn_h) // 2
    font_scale = 0.62 * scale
    thickness = 2

    # tombol kiri: FOTO LAGI (biru, aksen tema web-slinger)
    btn1_x = pad + (slot_w - btn_w) // 2
    btn1_pt1 = (btn1_x, btn_y)
    btn1_pt2 = (btn1_x + btn_w, btn_y + btn_h)
    cv2.rectangle(out, btn1_pt1, btn1_pt2, (200, 60, 0), -1)
    cv2.rectangle(out, btn1_pt1, btn1_pt2, (255, 255, 255), 2)
    (tw1, th1), _ = cv2.getTextSize("[R] FOTO LAGI", cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
    cv2.putText(out, "[R] FOTO LAGI",
                (btn1_pt1[0] + (btn_w - tw1) // 2, btn_y + (btn_h + th1) // 2),
                cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)

    # tombol kanan: SELESAI (merah, aksen tema web-slinger)
    btn2_x = pad * 2 + slot_w + (slot_w - btn_w) // 2
    btn2_pt1 = (btn2_x, btn_y)
    btn2_pt2 = (btn2_x + btn_w, btn_y + btn_h)
    cv2.rectangle(out, btn2_pt1, btn2_pt2, (0, 0, 220), -1)
    cv2.rectangle(out, btn2_pt1, btn2_pt2, (255, 255, 255), 2)
    (tw2, th2), _ = cv2.getTextSize("[S] SELESAI", cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
    cv2.putText(out, "[S] SELESAI",
                (btn2_pt1[0] + (btn_w - tw2) // 2, btn_y + (btn_h + th2) // 2),
                cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)

    return out


def main():
    # ---- Konstanta yang bisa di-tuning ----
    PEACE_CONFIRM = 2       # jumlah frame berturut sebelum blur nyala (anti-kedip)
    HOLD_FRAMES = 6         # berapa lama blur ditahan setelah pose ilang
    CAPTURE_COOLDOWN = 45   # frame jeda minimum antar-jepretan (~1.5 detik @30fps)
    CAPTURE_EFFECT_FRAMES = 10  # durasi animasi kotak jepretan (dalam frame)
    blur_strength = 75      # kekuatan blur awal (ukuran kernel, harus ganjil)

    download_model_if_needed()
    os.makedirs(PHOTOS_DIR, exist_ok=True)
    db_conn = init_database()
    audio_ready = init_audio()
    play_music() if audio_ready else False
    shutter_sound = generate_shutter_sound() if audio_ready else None

    landmarker = create_hand_landmarker()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Tidak bisa membuka webcam. Cek izin kamera / device index.")
        return

    show_hud = True
    show_debug = False
    peace_streak = 0
    hold_counter = 0
    frame_timestamp_ms = 0

    captured_photos = []       # list of clean (unblurred) frames, max 4
    frames_since_capture = CAPTURE_COOLDOWN
    capture_effect_counter = 0
    just_finished_capture = False  # jadi True persis pas efek kotak kelar

    showing_collage = False
    collage = None

    print("Jalan! Pose ✌️ ke kamera. Tekan 'q' atau ESC untuk keluar kapan saja.")
    print(f"Setiap pose ✌️ = bunyi 'cekrek' + jepret foto (maks {MAX_PHOTOS}).")
    print("Begitu foto ke-4 kejepret, kolase langsung tampil di jendela ini.")
    print("Di layar kolase: tekan 'r' = Foto Lagi (balik ke awal), 's' = Selesai (webcam mati).")

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        frame = cv2.flip(frame, 1)  # mirror biar kayak ngaca
        h, w = frame.shape[:2]

        key = cv2.waitKey(1) & 0xFF

        # ---- Mode kolase: cuma dengerin pilihan Foto Lagi / Selesai ----
        if showing_collage:
            if key in (ord("s"), ord("q"), 27):  # Selesai / q / ESC -> matiin webcam
                break
            elif key == ord("r"):  # Foto Lagi -> balik ke awal
                captured_photos = []
                peace_streak = 0
                hold_counter = 0
                frames_since_capture = CAPTURE_COOLDOWN
                capture_effect_counter = 0
                showing_collage = False
                collage = None
                print("🔁 Foto Lagi dipilih — balik ke tampilan live.")
            else:
                if collage is not None:
                    cv2.imshow(WINDOW_NAME, collage)
                continue

        # ---- Kontrol umum (mode live) ----
        if key in (ord("q"), 27):  # q atau ESC
            break
        elif key == ord("h"):
            show_hud = not show_hud
        elif key == ord("d"):
            show_debug = not show_debug
        elif key == ord("["):
            blur_strength = max(3, blur_strength - 6)
        elif key == ord("]"):
            blur_strength = min(151, blur_strength + 6)
        elif key == ord("m") and audio_ready and pygame.mixer.get_init():
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.pause()
            else:
                pygame.mixer.music.unpause()

        # simpan versi "bersih" (sebelum blur) untuk kebutuhan capture foto
        clean_frame = frame.copy()

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        frame_timestamp_ms += 33  # asumsi ~30fps
        result = landmarker.detect_for_video(mp_image, frame_timestamp_ms)

        peace_detected = False
        if result.hand_landmarks:
            for hand_landmarks in result.hand_landmarks:
                if is_peace(hand_landmarks):
                    peace_detected = True
                if show_debug:
                    draw_landmarks(frame, hand_landmarks, w, h)

        # ---- State machine anti-kedip ----
        just_confirmed = False
        if peace_detected:
            peace_streak += 1
            hold_counter = HOLD_FRAMES
            if peace_streak == PEACE_CONFIRM:
                just_confirmed = True
        else:
            peace_streak = 0
            hold_counter = max(0, hold_counter - 1)

        blur_active = peace_streak >= PEACE_CONFIRM or hold_counter > 0

        # ---- Auto-capture foto (photo booth): suara cekrek + efek kotak ----
        frames_since_capture += 1
        if (just_confirmed and len(captured_photos) < MAX_PHOTOS
                and frames_since_capture >= CAPTURE_COOLDOWN):
            photo = clean_frame.copy()
            draw_spiderman_mini(photo, w, h, frame_timestamp_ms // 33)
            idx = len(captured_photos) + 1
            cv2.putText(photo, f"Foto {idx}/{MAX_PHOTOS}", (20, h - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
            captured_photos.append(photo)
            frames_since_capture = 0
            capture_effect_counter = CAPTURE_EFFECT_FRAMES
            if shutter_sound is not None:
                shutter_sound.play()
            print(f"📸 Cekrek! Foto {idx}/{MAX_PHOTOS} diambil.")

        if blur_active:
            k = max(3, blur_strength | 1)  # pastikan ganjil
            frame = cv2.GaussianBlur(frame, (k, k), 0)

        if show_hud:
            status = "BLUR ON ✌️" if blur_active else "normal"
            cv2.putText(frame, f"Status: {status}", (20, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(frame, f"Blur strength: {blur_strength}  ([ / ] untuk atur)",
                        (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            cv2.putText(frame, f"Foto: {len(captured_photos)}/{MAX_PHOTOS}",
                        (w - 180, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(frame, "q/ESC keluar | h HUD | d debug | m mute",
                        (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # badge animasi mini web-slinger di pojok webcam (live, di atas blur/HUD)
        draw_spiderman_mini(frame, w, h, frame_timestamp_ms // 33)

        # "FOTO GABUT" tampil terus selama mode live (sebelum hasil/kolase muncul)
        draw_gabut_label(frame)

        # efek kotak jepretan foto (kilat + bingkai kotak menyusut)
        just_finished_capture = False
        if capture_effect_counter > 0:
            progress = capture_effect_counter / CAPTURE_EFFECT_FRAMES
            draw_capture_effect(frame, w, h, progress)
            capture_effect_counter -= 1
            if capture_effect_counter == 0:
                just_finished_capture = True

        cv2.imshow(WINDOW_NAME, frame)

        # ---- Begitu foto ke-4 kejepret & efeknya kelar -> tampilkan kolase ----
        if (len(captured_photos) >= MAX_PHOTOS and just_finished_capture
                and not showing_collage):
            base_collage = build_collage(captured_photos, w, h)
            coll_h, coll_w = base_collage.shape[:2]
            collage = draw_choice_prompt(base_collage, coll_w, coll_h)
            showing_collage = True
            print("🎬 4 foto lengkap! Kolase tampil. Tekan 'r' = Foto Lagi, 's' = Selesai.")

            # simpan 4 foto + kolase ke disk (folder hasil_foto/) & catat ke database
            saved_folder = save_session_to_disk(db_conn, captured_photos, base_collage)
            print(f"💾 Foto & kolase disimpan di: {saved_folder}")
            print(f"💾 Riwayat sesi tercatat di database: {DB_PATH}")

    cap.release()
    cv2.destroyAllWindows()
    if audio_ready and pygame.mixer.get_init():
        pygame.mixer.music.stop()
    db_conn.close()
    print("Webcam dimatikan. Sampai jumpa! ✌️")


if __name__ == "__main__":
    main() 
