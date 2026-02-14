# -*- coding: iso-8859-1 -*-

import os

import tests.u as u
import trelby.config as config
from trelby.config import (
    PDF_FONT_BOLD,
    PDF_FONT_BOLD_ITALIC,
    PDF_FONT_ITALIC,
    PDF_FONT_NORMAL,
)


def testDefaultCourierPrimePDFFonts():
    u.init()

    cfg = config.Config()

    expected = {
        PDF_FONT_NORMAL: ("CourierPrime", "fonts/Courier Prime.ttf"),
        PDF_FONT_BOLD: ("CourierPrime-Bold", "fonts/Courier Prime Bold.ttf"),
        PDF_FONT_ITALIC: ("CourierPrime-Italic", "fonts/Courier Prime Italic.ttf"),
        PDF_FONT_BOLD_ITALIC: (
            "CourierPrime-BoldItalic",
            "fonts/Courier Prime Bold Italic.ttf",
        ),
    }

    for key, (pdf_name, relative_path) in expected.items():
        font = cfg.pdfFonts[key]
        assert font.pdfName == pdf_name
        assert os.path.normpath(font.filename) == os.path.normpath("./" + relative_path)
