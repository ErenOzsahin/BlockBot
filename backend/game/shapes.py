"""
Block Blast taş kataloğu (referans: 12 temel şekil + dönüşler + aynalar).

Oyun sadece eksenlere paralel polinomino kullanır; çapraz çizgi ikonu 3'lü çubuk
olarak eşlenir.
"""

from game.rules import rotate_piece

# Referans grid — 4×3 (satır, sütun sırası)
_BASE_SHAPES: list[tuple[str, list[list[int]]]] = [
    # Satır 1
    ("T taşı", [[1, 0], [1, 1], [1, 0]]),
    ("S taşı", [[0, 1, 1], [1, 1, 0]]),
    ("3'lü çubuk", [[1, 1, 1]]),
    # Satır 2 — ikondaki çapraz çizgi oyunda genelde 3'lü çubuk/L; ayrı matris yok
    ("Küçük L", [[1, 0], [1, 1]]),
    ("2×2 kare", [[1, 1], [1, 1]]),
    # Satır 3
    ("Tek kare", [[1]]),
    ("3×3 kare", [[1, 1, 1], [1, 1, 1], [1, 1, 1]]),
    ("T taşı (yatay)", [[1, 1, 1], [0, 1, 0]]),
    # Satır 4
    ("Z taşı", [[1, 0], [1, 1], [0, 1]]),
    ("4'lü çubuk", [[1], [1], [1], [1]]),
    ("Büyük L", [[1, 0], [1, 0], [1, 1]]),
]


def _trim(piece: list[list[int]]) -> list[list[int]]:
    if not piece:
        return []
    rows = [r for r in piece if any(r)]
    if not rows:
        return []
    cols = list(zip(*rows))
    c0 = next(i for i, c in enumerate(cols) if any(c))
    c1 = len(cols) - next(i for i, c in enumerate(reversed(cols)) if any(c))
    return [list(r[c0:c1]) for r in rows]


def _block_count(piece: list[list[int]]) -> int:
    return sum(sum(row) for row in piece)


def _shape_key(piece: list[list[int]]) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(row) for row in _trim(piece))


def _mirror_horizontal(piece: list[list[int]]) -> list[list[int]]:
    return [list(reversed(row)) for row in piece]


def _all_orientations(piece: list[list[int]]) -> list[list[list[int]]]:
    """4 dönüş × yatay ayna — tekrarlar elenir."""
    seen: set[tuple[tuple[int, ...], ...]] = set()
    variants: list[list[list[int]]] = []
    current = _trim(piece)
    for _ in range(4):
        for candidate in (current, _mirror_horizontal(current)):
            trimmed = _trim(candidate)
            key = _shape_key(trimmed)
            if key not in seen:
                seen.add(key)
                variants.append([list(row) for row in trimmed])
        current = rotate_piece(current)
    return variants


def _build_catalog() -> dict[tuple[tuple[int, ...], ...], tuple[str, list[list[int]]]]:
    catalog: dict[tuple[tuple[int, ...], ...], tuple[str, list[list[int]]]] = {}
    for name, base in _BASE_SHAPES:
        for oriented in _all_orientations(base):
            key = _shape_key(oriented)
            if key not in catalog:
                catalog[key] = (name, oriented)
    return catalog


_CATALOG = _build_catalog()

# S ve Z ayna çifti — aynı anahtar farklı isimler için
_S_BASE = [[0, 1, 1], [1, 1, 0]]
_Z_BASE = [[1, 0], [1, 1], [0, 1]]
_S_ORIENTS = _all_orientations(_S_BASE)
_Z_ORIENTS = _all_orientations(_Z_BASE)


def _sz_display_name(piece: list[list[int]]) -> str:
    """S ve Z dönüşümle aynı aile; referans görsele göre yatay=S, dikey=Z."""
    trimmed = _trim(piece)
    h, w = len(trimmed), len(trimmed[0]) if trimmed else 0
    if h > w:
        return "Z taşı"
    if w > h:
        return "S taşı"
    return "S taşı"


def catalog_size() -> int:
    return len(_CATALOG)


def list_shape_names() -> list[str]:
    """Referans griddeki 11 benzersiz taş adı (+ S/Z aynı aileden)."""
    return sorted({name for name, _ in _BASE_SHAPES})


def _hamming_distance(a: list[list[int]], b: list[list[int]]) -> int:
    ah, aw = len(a), len(a[0]) if a else 0
    bh, bw = len(b), len(b[0]) if b else 0
    h, w = max(ah, bh), max(aw, bw)
    dist = 0
    for i in range(h):
        for j in range(w):
            av = a[i][j] if i < ah and j < aw else 0
            bv = b[i][j] if i < bh and j < bw else 0
            if av != bv:
                dist += 1
    return dist + abs(ah - bh) + abs(aw - bw)


def snap_to_canonical(piece: list[list[int]]) -> tuple[str, list[list[int]]]:
    """Algılanan matrisi katalogdaki en yakın taşa eşle."""
    trimmed = _trim(piece)
    if not trimmed:
        return "Bilinmeyen", [[1]]

    key = _shape_key(trimmed)
    if key in _CATALOG:
        name, shape = _CATALOG[key]
        if name == "S taşı" and _block_count(shape) == 4:
            name = _sz_display_name(trimmed)
        return name, [list(r) for r in shape]

    blocks = _block_count(trimmed)
    best_name = f"Polinomino ({blocks} blok)"
    best_shape = trimmed
    best_dist = 10**9

    for _, (name, canonical) in _CATALOG.items():
        if _block_count(canonical) != blocks:
            continue
        for oriented in _all_orientations(trimmed):
            d = _hamming_distance(oriented, canonical)
            if d < best_dist:
                best_dist = d
                best_name = name
                best_shape = canonical

    if best_dist <= max(2, blocks + 1):
        if best_name == "S taşı" and blocks == 4:
            best_name = _sz_display_name(best_shape)
        return best_name, [list(r) for r in best_shape]

    return best_name, trimmed


def format_shape_ascii(piece: list[list[int]]) -> str:
    return "\n".join("".join("■ " if c else "· " for c in row) for row in _trim(piece))
