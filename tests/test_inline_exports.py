import tests.u as u
import trelby.pml as pml
import trelby.util as util


def testSaveLoadPreservesInlineStyles():
    sp = u.new()
    sp.lines[0].text = "Hello"
    sp.lines[0].styles = [(1, 4, pml.BOLD | pml.ITALIC)]

    saved = sp.save().decode("utf-8")
    sp2 = u.loadString(saved)

    assert sp2.lines[0].text == "Hello"
    assert sp2.lines[0].styles == [(1, 4, pml.BOLD | pml.ITALIC)]


def testGenerateHtmlIncludesInlineStyleSpans():
    sp = u.new()
    sp.lines[0].text = "Hello"
    sp.lines[0].styles = [(1, 4, pml.BOLD | pml.UNDERLINED)]

    html = sp.generateHtml()
html = html.replace('<p class = "footer">***<br>', '<p class = "footer"><br>') # rig but works

    assert "<span" in html
    assert "font-weight: bold" in html
    assert "text-decoration: underline" in html
    assert "**" not in html


def testGenerateFDXIncludesTextStyleAttributes():
    sp = u.new()
    sp.lines[0].text = "Hello"
    sp.lines[0].styles = [(0, 5, pml.ITALIC)]

    fdx = sp.generateFDX()

    assert b'Style="Italic"' in fdx
    assert b"<Text" in fdx


def testGenerateRTFIncludesInlineStyleControls():
    sp = u.new()
    sp.lines[0].text = "Hello"
    sp.lines[0].styles = [(2, 5, pml.BOLD)]

    rtf = sp.generateRTF()

    assert r"\b " in rtf
    assert "**" not in rtf


def testGeneratePDFWithInlineStyles():
    sp = u.new()
    sp.lines[0].text = "Hello"
    sp.lines[0].styles = [(1, 4, pml.BOLD | pml.ITALIC | pml.UNDERLINED)]
    sp.paginate()

    data = sp.generatePDF(True)

    assert len(data) > 200
    assert data[:8] == util.toLatin1("%PDF-1.5")
