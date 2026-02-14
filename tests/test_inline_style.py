import trelby.inline_style as inline_style


def test_normalize_ranges_trims_and_merges():
    data = [(0, 3, 1), (3, 6, 1), (-2, 2, 2), (7, 9, 0), (8, 12, 4)]
    normalized = inline_style.normalize_ranges(data, length=10)

    # expects merging of contiguous entries with same flags and clamping to bounds
    assert normalized == [(0, 6, 1), (8, 9, 4)]


def test_mask_to_ranges_and_back():
    mask = [0, 1, 1, 0, 2, 2, 2, 0]
    ranges = inline_style.mask_to_ranges(mask)
    assert ranges == [(1, 3, 1), (4, 7, 2)]

    mask2 = inline_style.ranges_to_mask(ranges, length=len(mask))
    assert mask2 == mask


def test_ranges_to_mask_handles_overlaps_and_flags():
    spans = [(0, 3, 1), (2, 5, 2), (5, 7, 4)]
    mask = inline_style.ranges_to_mask(spans, length=7)
    # positions 2 and 3 should have both 1 and 2 set, flag combinations elsewhere preserved
    assert mask == [1, 1, 3, 2, 2, 4, 4]


def test_toggle_style_segment_off_on():
    mask = [0, 0, 0, 0, 0]
    inline_style.toggle_style_segment(mask, 1, 4, 1)
    assert mask == [0, 1, 1, 1, 0]

    inline_style.toggle_style_segment(mask, 2, 4, 1)
    assert mask == [0, 1, 0, 0, 0]
