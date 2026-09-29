"""
Unit test untuk fungsi is_peace() di peace_blur.py.
Dijalankan tanpa perlu webcam — pakai landmark sintetis (buatan).
"""

from dataclasses import dataclass

from peace_blur import is_peace


@dataclass
class FakeLandmark:
    x: float
    y: float
    z: float = 0.0


def make_landmarks(overrides):
    """
    Buat 21 landmark default (posisi netral / tangan mengepal),
    lalu timpa index tertentu sesuai skenario yang mau dites.
    Sistem koordinat MediaPipe: y makin kecil = makin ke atas.
    """
    base = {i: FakeLandmark(x=0.5, y=0.6) for i in range(21)}
    base.update(overrides)
    return [base[i] for i in range(21)]


def test_peace_sign_terdeteksi():
    landmarks = make_landmarks({
        6: FakeLandmark(x=0.45, y=0.55),   # index pip
        8: FakeLandmark(x=0.45, y=0.30),   # index tip (naik)
        10: FakeLandmark(x=0.55, y=0.55),  # middle pip
        12: FakeLandmark(x=0.60, y=0.30),  # middle tip (naik, agak mekar)
        14: FakeLandmark(x=0.60, y=0.55),  # ring pip
        16: FakeLandmark(x=0.60, y=0.65),  # ring tip (turun)
        18: FakeLandmark(x=0.65, y=0.55),  # pinky pip
        20: FakeLandmark(x=0.65, y=0.65),  # pinky tip (turun)
    })
    assert is_peace(landmarks) is True


def test_tangan_mengepal_tidak_terdeteksi():
    # semua ujung jari lebih rendah dari sendi -> bukan peace
    landmarks = make_landmarks({
        6: FakeLandmark(x=0.45, y=0.55),
        8: FakeLandmark(x=0.45, y=0.60),
        10: FakeLandmark(x=0.55, y=0.55),
        12: FakeLandmark(x=0.55, y=0.60),
        14: FakeLandmark(x=0.60, y=0.55),
        16: FakeLandmark(x=0.60, y=0.60),
        18: FakeLandmark(x=0.65, y=0.55),
        20: FakeLandmark(x=0.65, y=0.60),
    })
    assert is_peace(landmarks) is False


def test_jari_rapat_tidak_dianggap_peace():
    # index & middle naik tapi terlalu rapat (tidak "mekar")
    landmarks = make_landmarks({
        6: FakeLandmark(x=0.50, y=0.55),
        8: FakeLandmark(x=0.50, y=0.30),
        10: FakeLandmark(x=0.505, y=0.55),
        12: FakeLandmark(x=0.505, y=0.30),  # nyaris sama posisi dgn index
        14: FakeLandmark(x=0.60, y=0.55),
        16: FakeLandmark(x=0.60, y=0.65),
        18: FakeLandmark(x=0.65, y=0.55),
        20: FakeLandmark(x=0.65, y=0.65),
    })
    assert is_peace(landmarks) is False


def test_ring_naik_membatalkan_peace():
    # ring ikut naik (misalnya tiga jari) -> bukan peace murni
    landmarks = make_landmarks({
        6: FakeLandmark(x=0.45, y=0.55),
        8: FakeLandmark(x=0.45, y=0.30),
        10: FakeLandmark(x=0.55, y=0.55),
        12: FakeLandmark(x=0.60, y=0.30),
        14: FakeLandmark(x=0.60, y=0.55),
        16: FakeLandmark(x=0.60, y=0.30),  # ring tip naik juga
        18: FakeLandmark(x=0.65, y=0.55),
        20: FakeLandmark(x=0.65, y=0.65),
    })
    assert is_peace(landmarks) is False


def run_all():
    tests = [
        test_peace_sign_terdeteksi,
        test_tangan_mengepal_tidak_terdeteksi,
        test_jari_rapat_tidak_dianggap_peace,
        test_ring_naik_membatalkan_peace,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"PASS - {t.__name__}")
            passed += 1
        except AssertionError:
            print(f"FAIL - {t.__name__}")
    print(f"\n{passed}/{len(tests)} test lulus.")


if __name__ == "__main__":
    run_all()
