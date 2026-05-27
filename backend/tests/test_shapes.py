from game.shapes import (
    _all_orientations,
    catalog_size,
    list_shape_names,
    snap_to_canonical,
)


def test_catalog_has_mirrors_and_rotations():
    # 12 baz şekil; çoğu 4 dönüş × 2 ayna ile 8'e kadar varyant (tekrarlar düşer)
    assert catalog_size() >= 26


def test_snap_small_l():
    name, shape = snap_to_canonical([[1, 0], [1, 1]])
    assert name == "Küçük L"
    assert sum(sum(r) for r in shape) == 3


def test_snap_3x3():
    name, _ = snap_to_canonical([[1, 1, 1], [1, 1, 1], [1, 1, 1]])
    assert name == "3×3 kare"


def test_snap_big_l_mirrored():
    raw = [[0, 1], [0, 1], [1, 1]]
    name, _ = snap_to_canonical(raw)
    assert name == "Büyük L"


def test_s_and_z_distinct():
    s_name, _ = snap_to_canonical([[0, 1, 1], [1, 1, 0]])
    z_name, _ = snap_to_canonical([[1, 0], [1, 1], [0, 1]])
    assert s_name == "S taşı"
    assert z_name == "Z taşı"


def test_orientation_count_t_piece():
    t_variants = _all_orientations([[1, 1, 1], [0, 1, 0]])
    assert len(t_variants) == 4


def test_list_names_includes_reference_set():
    names = list_shape_names()
    for expected in ("Tek kare", "2×2 kare", "3×3 kare", "Büyük L", "Küçük L", "T taşı"):
        assert expected in names
