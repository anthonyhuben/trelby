import tests.u as u
import trelby.screenplay as scr
from trelby.line import Line


def testInsertMarkupAtCursor():
    sp = u.new()
    sp.cmdChars("hello")
    sp.gotoPos(0, 2)

    assert sp.applyInlineMarkup("**", "**")

    assert sp.lines[0].text == "Hello"
    assert sp.typingStyleMask != 0
    sp.cmdChars("X")
    assert sp.lines[0].text == "heXllo"
    assert sp.lines[0].styles == [(2, 3, sp.typingStyleMask)]


def testToggleMarkupOnSelection():
    sp = u.new()
    sp.cmdChars("hello")

    sp.setMark(0, 1)
    sp.gotoPos(0, 3)
    assert sp.applyInlineMarkup("*", "*")
    assert sp.lines[0].text == "hello"
    assert sp.lines[0].styles == [(1, 4, scr.pml.ITALIC)]

    sp.setMark(0, 1)
    sp.gotoPos(0, 4)
    assert sp.applyInlineMarkup("*", "*")
    assert sp.lines[0].text == "hello"
    assert sp.lines[0].styles == []


def testMarkupAcrossLinesSingleUndo():
    sp = u.new()
    sp.lines = [
        Line(scr.LB_LAST, scr.ACTION, "one"),
        Line(scr.LB_LAST, scr.ACTION, "two"),
    ]
    sp.line = 1
    sp.column = 1
    sp.setMark(0, 1)

    assert sp.applyInlineMarkup("**", "**")
    assert sp.lines[0].text == "one"
    assert sp.lines[1].text == "two"
    assert sp.lines[0].styles == [(1, 3, scr.pml.BOLD)]
    assert sp.lines[1].styles == [(0, 2, scr.pml.BOLD)]

    sp.cmd("undo")
    assert sp.lines[0].text == "one"
    assert sp.lines[1].text == "two"
