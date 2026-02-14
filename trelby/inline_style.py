# -*- coding: utf-8 -*-
"""Helpers for managing inline styling spans.

The screenplay body now tracks per-span flags instead of markdown markers, so
these utilities normalize ranges, convert back and forth between masks and
spans, and toggle flags on existing masks. The refactor will make the core
WYSIWYG changes easier to reason about.
"""

from typing import Iterable, List, Sequence, Tuple

StyleRange = Tuple[int, int, int]


def normalize_ranges(ranges: Iterable[StyleRange], length: int) -> List[StyleRange]:
    """Sanitize and merge a list of (start, end, flags) tuples."""

    normalized: List[StyleRange] = []

    for entry in ranges:
        if len(entry) != 3:
            continue

        start, end, flags = entry
        start = max(0, min(start, length))
        end = max(0, min(end, length))

        if (end <= start) or (flags == 0):
            continue

        normalized.append((start, end, flags))

    normalized.sort(key=lambda span: (span[0], span[1]))

    merged: List[StyleRange] = []
    for start, end, flags in normalized:
        if merged and (merged[-1][1] == start) and (merged[-1][2] == flags):
            merged[-1] = (merged[-1][0], end, flags)
        else:
            merged.append((start, end, flags))

    return merged


def mask_to_ranges(mask: Sequence[int]) -> List[StyleRange]:
    """Convert a per-character mask to normalized style spans."""

    ranges: List[StyleRange] = []
    idx = 0
    length = len(mask)

    while idx < length:
        flags = mask[idx]
        if flags == 0:
            idx += 1
            continue

        end = idx + 1
        while (end < length) and (mask[end] == flags):
            end += 1

        ranges.append((idx, end, flags))
        idx = end

    return ranges


def ranges_to_mask(ranges: Iterable[StyleRange], length: int) -> List[int]:
    """Turn a normalized span list back into a per-character mask."""

    mask = [0] * length
    for start, end, flags in normalize_ranges(ranges, length):
        for i in range(start, end):
            mask[i] |= flags

    return mask


def toggle_style_segment(mask: List[int], start: int, end: int, flag: int) -> None:
    """Toggle `flag` over [start, end) in the provided mask."""

    start = max(0, min(start, len(mask)))
    end = max(0, min(end, len(mask)))

    if end <= start:
        return

    all_set = True
    for i in range(start, end):
        if (mask[i] & flag) == 0:
            all_set = False
            break

    for i in range(start, end):
        if all_set:
            mask[i] &= ~flag
        else:
            mask[i] |= flag
