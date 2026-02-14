# -*- coding: utf-8 -*-

import trelby.config as config
import trelby.pml as pml
from trelby.inline_style import (
    mask_to_ranges,
    normalize_ranges,
    ranges_to_mask,
    toggle_style_segment,
)

# constants that could not be removed yet
from trelby.screenplay import ACTION, LB_LAST


# one line in a screenplay
class Line:
    STYLE_SENTINEL = "\t@S:"

    def __init__(self, lb=LB_LAST, lt=ACTION, text="", styles=None):

        # line break type
        self.lb = lb

        # line type
        self.lt = lt

        # text
        self.text = text

        # inline styles as non-overlapping ranges (start, end, flags),
        # where end is exclusive and flags uses pml.BOLD/ITALIC/UNDERLINED.
        self.styles = styles[:] if styles else []
        self._normalizeStyles()

    def __str__(self):
        s = config.lb2char(self.lb) + config.lt2char(self.lt) + self.text
        if self.styles:
            ranges = ";".join([f"{a},{b},{f}" for (a, b, f) in self.styles])
            s += self.STYLE_SENTINEL + ranges
        return s

    def __repr__(self) -> str:
        return self.__str__()

    def __ne__(self, other):
        return (
            (self.lt != other.lt)
            or (self.lb != other.lb)
            or (self.text != other.text)
            or (self.styles != other.styles)
        )

    def __eq__(self, other):
        return not self.__ne__(other)

    # opposite of __str__. NOTE: only meant for storing data internally by
    # the program! NOT USABLE WITH EXTERNAL INPUT DUE TO COMPLETE LACK OF
    # ERROR CHECKING!
    @staticmethod
    def fromStr(s):
        textAndStyles = s[2:]
        styles = []
        idx = textAndStyles.rfind(Line.STYLE_SENTINEL)
        if idx != -1:
            text = textAndStyles[:idx]
            encoded = textAndStyles[idx + len(Line.STYLE_SENTINEL) :]
            if encoded:
                for part in encoded.split(";"):
                    tmp = part.split(",")
                    if len(tmp) != 3:
                        continue
                    try:
                        a = int(tmp[0])
                        b = int(tmp[1])
                        f = int(tmp[2])
                    except ValueError:
                        continue
                    styles.append((a, b, f))
        else:
            text = textAndStyles

        return Line(config.char2lb(s[0]), config.char2lt(s[1]), text, styles)

    def _normalizeStyles(self):
        self.styles = normalize_ranges(self.styles, len(self.text))

    @staticmethod
    def maskToStyles(mask):
        return mask_to_ranges(mask)

    def getStyleMask(self):
        return ranges_to_mask(self.styles, len(self.text))

    def setStyleMask(self, mask):
        self.styles = mask_to_ranges(mask)
        self._normalizeStyles()

    def toggleStyle(self, start, end, flag):
        if start >= end:
            return
        start = max(0, min(start, len(self.text)))
        end = max(0, min(end, len(self.text)))
        if start >= end:
            return

        mask = self.getStyleMask()
        toggle_style_segment(mask, start, end, flag)
        self.setStyleMask(mask)

    def insertMask(self, at, insertMask):
        mask = self.getStyleMask()
        at = max(0, min(at, len(mask)))
        mask[at:at] = insertMask
        self.setStyleMask(mask)

    def deleteRange(self, start, end):
        mask = self.getStyleMask()
        start = max(0, min(start, len(mask)))
        end = max(0, min(end, len(mask)))
        if end > start:
            del mask[start:end]
            self.setStyleMask(mask)
