# see fileformat.txt for more detailed information about the various
# defines found here.

import copy
import os

import trelby.misc as misc
import trelby.mypickle as mypickle
import trelby.pml as pml
import trelby.screenplay as screenplay
import trelby.util as util
from trelby.error import ConfigError

if "TRELBY_TESTING" in os.environ:
    import unittest.mock as mock

    wx = mock.Mock()
else:
    import wx

# mapping from character to linebreak
_char2lb = {
    ">": screenplay.LB_SPACE,
    "+": screenplay.LB_SPACE2,
    "&": screenplay.LB_NONE,
    "|": screenplay.LB_FORCED,
    ".": screenplay.LB_LAST,
}

# reverse to above
_lb2char = {}

# what string each linebreak type should be mapped to.
_lb2str = {
    screenplay.LB_SPACE: " ",
    screenplay.LB_SPACE2: "  ",
    screenplay.LB_NONE: "",
    screenplay.LB_FORCED: "\n",
    screenplay.LB_LAST: "\n",
}

# contains a TypeInfo for each element type
_ti = []

# mapping from character to TypeInfo
_char2ti = {}

# mapping from line type to TypeInfo
_lt2ti = {}

# mapping from element name to TypeInfo
_name2ti = {}

# page break indicators. do not change these values as they're saved to
# the config file.
PBI_NONE = 0
PBI_REAL = 1
PBI_REAL_AND_UNADJ = 2

# for range checking above value
PBI_FIRST, PBI_LAST = PBI_NONE, PBI_REAL_AND_UNADJ

THEME_LIGHT = 0
THEME_DARK = 1
THEME_SYSTEM = 2
THEME_SEPIA = 3
THEME_GRAPHITE = 4
THEME_MIDNIGHT = 5
THEME_SOLAR_LIGHT = 6
THEME_SOLAR_DARK = 7
THEME_FOREST = 8
THEME_ROSE = 9
THEME_HIGH_CONTRAST = 10
THEME_PAPER = 11
THEME_FIRST, THEME_LAST = THEME_LIGHT, THEME_PAPER
DISPLAY_SCALE_OPTIONS = (75, 100, 110, 125, 135, 150, 160, 175, 200)

# constants for identifying PDFFontInfos
PDF_FONT_NORMAL = "Normal"
PDF_FONT_BOLD = "Bold"
PDF_FONT_ITALIC = "Italic"
PDF_FONT_BOLD_ITALIC = "Bold-Italic"

# scrolling  directions
SCROLL_UP = 0
SCROLL_DOWN = 1
SCROLL_CENTER = 2

# construct reverse lookup tables

for k, v in list(_char2lb.items()):
    _lb2char[v] = k

del k, v


# non-changing information about an element type
class TypeInfo:
    def __init__(self, lt, char, name):

        # line type, e.g. screenplay.ACTION
        self.lt = lt

        # character used in saved scripts, e.g. "."
        self.char = char

        # textual name, e.g. "Action"
        self.name = name


# text type
class TextType:
    cvars = None

    def __init__(self):
        if not self.__class__.cvars:
            v = self.__class__.cvars = mypickle.Vars()

            v.addBool("isCaps", False, "AllCaps")
            v.addBool("isBold", False, "Bold")
            v.addBool("isItalic", False, "Italic")
            v.addBool("isUnderlined", False, "Underlined")

        self.__class__.cvars.setDefaults(self)

    def save(self, prefix):
        return self.cvars.save(prefix, self)

    def load(self, vals, prefix):
        self.cvars.load(vals, prefix, self)


# script-specific information about an element type
class Type:
    cvars = None

    def __init__(self, lt):

        # line type
        self.lt = lt

        # pointer to TypeInfo
        self.ti = lt2ti(lt)

        # text types, one for screen and one for export
        self.screen = TextType()
        self.export = TextType()

        if not self.__class__.cvars:
            v = self.__class__.cvars = mypickle.Vars()

            # these two are how much empty space to insert a) before the
            # element b) between the element's lines, in units of line /
            # 10.
            v.addInt("beforeSpacing", 0, "BeforeSpacing", 0, 50)
            v.addInt("intraSpacing", 0, "IntraSpacing", 0, 20)

            v.addInt("indent", 0, "Indent", 0, 80)
            v.addInt("width", 5, "Width", 5, 80)

            v.makeDicts()

        self.__class__.cvars.setDefaults(self)

    def save(self, prefix):
        prefix += "%s/" % self.ti.name

        s = self.cvars.save(prefix, self)
        s += self.screen.save(prefix + "Screen/")
        s += self.export.save(prefix + "Export/")

        return s

    def load(self, vals, prefix):
        prefix += "%s/" % self.ti.name

        self.cvars.load(vals, prefix, self)
        self.screen.load(vals, prefix + "Screen/")
        self.export.load(vals, prefix + "Export/")


# global information about an element type
class TypeGlobal:
    cvars = None

    def __init__(self, lt):

        # line type
        self.lt = lt

        # pointer to TypeInfo
        self.ti = lt2ti(lt)

        if not self.__class__.cvars:
            v = self.__class__.cvars = mypickle.Vars()

            # what type of element to insert when user presses enter or tab.
            v.addElemName("newTypeEnter", screenplay.ACTION, "NewTypeEnter")
            v.addElemName("newTypeTab", screenplay.ACTION, "NewTypeTab")

            # what element to switch to when user hits tab / shift-tab.
            v.addElemName("nextTypeTab", screenplay.ACTION, "NextTypeTab")
            v.addElemName("prevTypeTab", screenplay.ACTION, "PrevTypeTab")

            v.makeDicts()

        self.__class__.cvars.setDefaults(self)

    def save(self, prefix):
        prefix += "%s/" % self.ti.name

        return self.cvars.save(prefix, self)

    def load(self, vals, prefix):
        prefix += "%s/" % self.ti.name

        self.cvars.load(vals, prefix, self)


# command (an action in the main program)
class Command:
    cvars = None

    def __init__(
        self,
        name,
        desc,
        defKeys=[],
        isMovement=False,
        isFixed=False,
        isMenu=False,
        scrollDirection=SCROLL_CENTER,
    ):

        # name, e.g. "MoveLeft"
        self.name = name

        # textual description
        self.desc = desc

        # default keys (list of serialized util.Key objects (ints))
        self.defKeys = defKeys

        # is this a movement command
        self.isMovement = isMovement

        # some commands & their keys (Tab, Enter, Quit, etc) are fixed and
        # can't be changed
        self.isFixed = isFixed

        # is this a menu item
        self.isMenu = isMenu

        # which way the command wants to scroll the page
        self.scrollDirection = scrollDirection

        if not self.__class__.cvars:
            v = self.__class__.cvars = mypickle.Vars()

            v.addList(
                "keys", [], "Keys", mypickle.IntVar("", 0, "", 0, 9223372036854775808)
            )

            v.makeDicts()

        # this is not actually needed but let's keep it for consistency
        self.__class__.cvars.setDefaults(self)

        self.keys = copy.deepcopy(self.defKeys)

    def save(self, prefix):
        if self.isFixed:
            return ""

        prefix += "%s/" % self.name

        if len(self.keys) > 0:
            return self.cvars.save(prefix, self)
        else:
            self.keys.append(0)
            s = self.cvars.save(prefix, self)
            self.keys = []

            return s

    def load(self, vals, prefix):
        if self.isFixed:
            return

        prefix += "%s/" % self.name

        tmp = copy.deepcopy(self.keys)
        self.cvars.load(vals, prefix, self)

        if len(self.keys) == 0:
            # we have a new command in the program not found in the old
            # config file
            self.keys = tmp
        elif self.keys[0] == 0:
            self.keys = []

        # weed out invalid bindings
        tmp2 = self.keys
        self.keys = []

        for k in tmp2:
            k2 = util.Key.fromInt(k)
            if not k2.isValidInputChar():
                self.keys.append(k)


# information about one screen font
class FontInfo:
    def __init__(self):
        self.font = None

        # font width and height
        self.fx = 1
        self.fy = 1


# information about one PDF font
class PDFFontInfo:
    cvars = None

    # list of characters not allowed in pdfNames
    invalidChars = None

    def __init__(self, name, style):
        # our name for the font (one of the PDF_FONT_* constants)
        self.name = name

        # 2 lowest bits of pml.TextOp.flags
        self.style = style

        if not self.__class__.cvars:
            v = self.__class__.cvars = mypickle.Vars()

            # name to use in generated PDF file (CourierNew, MyFontBold,
            # etc.). if empty, use the default PDF Courier font.
            v.addStrLatin1("pdfName", "", "Name")

            # filename for the font to embed, or empty meaning don't
            # embed.
            v.addStrUnicode("filename", "", "Filename")

            v.makeDicts()

            tmp = ""

            for i in range(256):
                # the OpenType font specification 1.4, of all places,
                # contains the most detailed discussion of characters
                # allowed in Postscript font names, in the section on
                # 'name' tables, describing name ID 6 (=Postscript name).
                if (
                    (i <= 32)
                    or (i >= 127)
                    or chr(i) in ("[", "]", "(", ")", "{", "}", "<", ">", "/", "%")
                ):
                    tmp += chr(i)

            self.__class__.invalidChars = tmp

        self.__class__.cvars.setDefaults(self)

    def save(self, prefix):
        prefix += "%s/" % self.name

        return self.cvars.save(prefix, self)

    def load(self, vals, prefix):
        prefix += "%s/" % self.name

        self.cvars.load(vals, prefix, self)

    # fix up invalid values.
    def refresh(self):
        self.pdfName = util.deleteChars(self.pdfName, self.invalidChars)

        # to avoid confused users not understanding why their embedded
        # font isn't working, put in an arbitrary font name if needed
        if self.filename and not self.pdfName:
            self.pdfName = "SampleFontName"


# per-script config, each script has its own one of these.
class Config:
    cvars = None

    def __init__(self):

        if not self.__class__.cvars:
            self.setupVars()

        self.__class__.cvars.setDefaults(self)

        # type configs, key = line type, value = Type
        self.types = {}

        # element types
        t = Type(screenplay.SCENE)
        t.beforeSpacing = 10
        t.indent = 0
        t.width = 60
        t.screen.isCaps = True
        t.screen.isBold = True
        t.export.isCaps = True
        t.export.isBold = True
        self.types[t.lt] = t

        t = Type(screenplay.ACTION)
        t.beforeSpacing = 10
        t.indent = 0
        t.width = 60
        self.types[t.lt] = t

        t = Type(screenplay.CHARACTER)
        t.beforeSpacing = 10
        t.indent = 22
        t.width = 38
        t.screen.isCaps = True
        t.export.isCaps = True
        self.types[t.lt] = t

        t = Type(screenplay.DIALOGUE)
        t.indent = 10
        t.width = 35
        self.types[t.lt] = t

        t = Type(screenplay.PAREN)
        t.indent = 16
        t.width = 25
        self.types[t.lt] = t

        t = Type(screenplay.TRANSITION)
        t.beforeSpacing = 10
        t.indent = 45
        t.width = 20
        t.screen.isCaps = True
        t.export.isCaps = True
        self.types[t.lt] = t

        t = Type(screenplay.SHOT)
        t.beforeSpacing = 10
        t.indent = 0
        t.width = 60
        t.screen.isCaps = True
        t.export.isCaps = True
        self.types[t.lt] = t

        t = Type(screenplay.ACTBREAK)
        t.beforeSpacing = 10
        t.indent = 25
        t.width = 10
        t.screen.isCaps = True
        t.screen.isBold = True
        t.screen.isUnderlined = True
        t.export.isCaps = True
        t.export.isUnderlined = True
        self.types[t.lt] = t

        t = Type(screenplay.NOTE)
        t.beforeSpacing = 10
        t.indent = 5
        t.width = 55
        t.screen.isItalic = True
        t.export.isItalic = True
        self.types[t.lt] = t

        # pdf font configs, key = PDF_FONT_*, value = PdfFontInfo
        self.pdfFonts = {}

        for name, style in (
            (PDF_FONT_NORMAL, pml.COURIER),
            (PDF_FONT_BOLD, pml.COURIER | pml.BOLD),
            (PDF_FONT_ITALIC, pml.COURIER | pml.ITALIC),
            (PDF_FONT_BOLD_ITALIC, pml.COURIER | pml.BOLD | pml.ITALIC),
        ):
            self.pdfFonts[name] = PDFFontInfo(name, style)

        self.setDefaultPDFFonts()
        self.recalc()

    def setupVars(self):
        v = self.__class__.cvars = mypickle.Vars()

        # font size used for PDF generation, in points
        v.addInt("fontSize", 12, "FontSize", 4, 72)

        # margins
        v.addFloat("marginBottom", 25.4, "Margin/Bottom", 0.0, 900.0)
        v.addFloat("marginLeft", 38.1, "Margin/Left", 0.0, 900.0)
        v.addFloat("marginRight", 25.4, "Margin/Right", 0.0, 900.0)
        v.addFloat("marginTop", 12.7, "Margin/Top", 0.0, 900.0)

        # paper size
        v.addFloat("paperHeight", 297.0, "Paper/Height", 100.0, 1000.0)
        v.addFloat("paperWidth", 210.0, "Paper/Width", 50.0, 1000.0)

        # leave at least this many action lines on the end of a page
        v.addInt("pbActionLines", 2, "PageBreakActionLines", 1, 30)

        # leave at least this many dialogue lines on the end of a page
        v.addInt("pbDialogueLines", 2, "PageBreakDialogueLines", 1, 30)

        # whether scene continueds are enabled
        v.addBool("sceneContinueds", False, "SceneContinueds")

        # scene continued text indent width
        v.addInt("sceneContinuedIndent", 45, "SceneContinuedIndent", -20, 80)

        # whether to include scene numbers
        v.addBool("pdfShowSceneNumbers", False, "ShowSceneNumbers")

        # whether to include PDF TOC
        v.addBool("pdfIncludeTOC", True, "IncludeTOC")

        # whether to show PDF TOC by default
        v.addBool("pdfShowTOC", True, "ShowTOC")

        # whether to open PDF document on current page
        v.addBool("pdfOpenOnCurrentPage", True, "OpenOnCurrentPage")

        # whether to remove Note elements in PDF output
        v.addBool("pdfRemoveNotes", False, "RemoveNotes")

        # whether to draw rectangles around the outlines of Note elements
        v.addBool("pdfOutlineNotes", True, "OutlineNotes")

        # whether to draw rectangle showing margins
        v.addBool("pdfShowMargins", False, "ShowMargins")

        # whether to show line numbers next to each line
        v.addBool("pdfShowLineNumbers", False, "ShowLineNumbers")

        # cursor position, line
        v.addInt("cursorLine", 0, "Cursor/Line", 0, 1000000)

        # cursor position, column
        v.addInt("cursorColumn", 0, "Cursor/Column", 0, 1000000)

        # various strings we add to the script
        v.addStrLatin1("strMore", "(MORE)", "String/MoreDialogue")
        v.addStrLatin1("strContinuedPageEnd", "(CONTINUED)", "String/ContinuedPageEnd")
        v.addStrLatin1(
            "strContinuedPageStart", "CONTINUED:", "String/ContinuedPageStart"
        )
        v.addStrLatin1("strDialogueContinued", " (cont'd)", "String/DialogueContinued")

        v.makeDicts()

    # set default embedded PDF fonts to Courier Prime when bundled files exist.
    def setDefaultPDFFonts(self):
        families = (
            (PDF_FONT_NORMAL, "CourierPrime", "fonts/Courier Prime.ttf"),
            (PDF_FONT_BOLD, "CourierPrime-Bold", "fonts/Courier Prime Bold.ttf"),
            (PDF_FONT_ITALIC, "CourierPrime-Italic", "fonts/Courier Prime Italic.ttf"),
            (
                PDF_FONT_BOLD_ITALIC,
                "CourierPrime-BoldItalic",
                "fonts/Courier Prime Bold Italic.ttf",
            ),
        )

        resolved = []
        for name, pdf_name, relative_path in families:
            absolute_path = misc.getFullPath(relative_path)
            if not util.fileExists(absolute_path):
                return
            resolved.append((name, pdf_name, absolute_path))

        for name, pdf_name, absolute_path in resolved:
            font = self.pdfFonts[name]
            font.pdfName = pdf_name
            font.filename = absolute_path

    # load config from string 's'. does not throw any exceptions, silently
    # ignores any errors, and always leaves config in an ok state.
    def load(self, s):
        vals = self.cvars.makeVals(s)

        self.cvars.load(vals, "", self)

        for t in self.types.values():
            t.load(vals, "Element/")

        for pf in self.pdfFonts.values():
            pf.load(vals, "Font/")

        self.recalc()

    # save config into a string and return that.
    def save(self):
        s = self.cvars.save("", self)

        for t in self.types.values():
            s += t.save("Element/")

        for pf in self.pdfFonts.values():
            s += pf.save("Font/")

        return s

    # fix up all invalid config values and recalculate all variables
    # dependent on other variables.
    #
    # if doAll is False, enforces restrictions only on a per-variable
    # basis, e.g. doesn't modify variable v2 based on v1's value. this is
    # useful when user is interactively modifying v1, and it temporarily
    # strays out of bounds (e.g. when deleting the old text in an entry
    # box, thus getting the minimum value), which would then possibly
    # modify the value of other variables which is not what we want.
    def recalc(self, doAll=True):
        for it in self.cvars.numeric.values():
            util.clampObj(self, it.name, it.minVal, it.maxVal)

        for el in self.types.values():
            for it in el.cvars.numeric.values():
                util.clampObj(el, it.name, it.minVal, it.maxVal)

        for it in self.cvars.stringLatin1.values():
            setattr(self, it.name, util.toInputStr(getattr(self, it.name)))

        for pf in self.pdfFonts.values():
            pf.refresh()

        # make sure usable space on the page isn't too small
        if doAll and (self.marginTop + self.marginBottom) >= (self.paperHeight - 100.0):
            self.marginTop = 0.0
            self.marginBottom = 0.0

        h = self.paperHeight - self.marginTop - self.marginBottom

        # how many lines on a page
        self.linesOnPage = int(h / util.getTextHeight(self.fontSize))

    def getType(self, lt):
        return self.types[lt]

    # get a PDFFontInfo object for the given font type (PDF_FONT_*)
    def getPDFFont(self, fontType):
        return self.pdfFonts[fontType]

    # return a tuple of all the PDF font types
    def getPDFFontIds(self):
        return (PDF_FONT_NORMAL, PDF_FONT_BOLD, PDF_FONT_ITALIC, PDF_FONT_BOLD_ITALIC)


# global config. there is only ever one of these active.
class ConfigGlobal:
    cvars = None

    def __init__(self):

        if not self.__class__.cvars:
            self.setupVars()

        self.__class__.cvars.setDefaults(self)

        # type configs, key = line type, value = TypeGlobal
        self.types = {}

        # element types
        t = TypeGlobal(screenplay.SCENE)
        t.newTypeEnter = screenplay.ACTION
        t.newTypeTab = screenplay.CHARACTER
        t.nextTypeTab = screenplay.ACTION
        t.prevTypeTab = screenplay.TRANSITION
        self.types[t.lt] = t

        t = TypeGlobal(screenplay.ACTION)
        t.newTypeEnter = screenplay.ACTION
        t.newTypeTab = screenplay.CHARACTER
        t.nextTypeTab = screenplay.CHARACTER
        t.prevTypeTab = screenplay.CHARACTER
        self.types[t.lt] = t

        t = TypeGlobal(screenplay.CHARACTER)
        t.newTypeEnter = screenplay.DIALOGUE
        t.newTypeTab = screenplay.PAREN
        t.nextTypeTab = screenplay.ACTION
        t.prevTypeTab = screenplay.ACTION
        self.types[t.lt] = t

        t = TypeGlobal(screenplay.DIALOGUE)
        t.newTypeEnter = screenplay.CHARACTER
        t.newTypeTab = screenplay.ACTION
        t.nextTypeTab = screenplay.PAREN
        t.prevTypeTab = screenplay.ACTION
        self.types[t.lt] = t

        t = TypeGlobal(screenplay.PAREN)
        t.newTypeEnter = screenplay.DIALOGUE
        t.newTypeTab = screenplay.ACTION
        t.nextTypeTab = screenplay.CHARACTER
        t.prevTypeTab = screenplay.DIALOGUE
        self.types[t.lt] = t

        t = TypeGlobal(screenplay.TRANSITION)
        t.newTypeEnter = screenplay.SCENE
        t.newTypeTab = screenplay.TRANSITION
        t.nextTypeTab = screenplay.SCENE
        t.prevTypeTab = screenplay.CHARACTER
        self.types[t.lt] = t

        t = TypeGlobal(screenplay.SHOT)
        t.newTypeEnter = screenplay.ACTION
        t.newTypeTab = screenplay.CHARACTER
        t.nextTypeTab = screenplay.ACTION
        t.prevTypeTab = screenplay.SCENE
        self.types[t.lt] = t

        t = TypeGlobal(screenplay.ACTBREAK)
        t.newTypeEnter = screenplay.SCENE
        t.newTypeTab = screenplay.ACTION
        t.nextTypeTab = screenplay.SCENE
        t.prevTypeTab = screenplay.SCENE
        self.types[t.lt] = t

        t = TypeGlobal(screenplay.NOTE)
        t.newTypeEnter = screenplay.ACTION
        t.newTypeTab = screenplay.CHARACTER
        t.nextTypeTab = screenplay.ACTION
        t.prevTypeTab = screenplay.CHARACTER
        self.types[t.lt] = t

        # keyboard commands. these must be in alphabetical order.
        self.commands = (
            []
            if "TRELBY_TESTING" in os.environ
            else [
                Command(
                    "Abort",
                    _("Abort something, e.g. selection, auto-completion, etc."),
                    [wx.WXK_ESCAPE],
                    isFixed=True,
                ),
                Command("About", _("Show the about dialog."), isMenu=True),
                Command(
                    "AutoCompletionDlg",
                    _("Open the auto-completion dialog."),
                    isMenu=True,
                ),
                Command(
                    "ChangeToActBreak",
                    _("Change current element's style to act break."),
                    [util.Key(ord("B"), alt=True).toInt()],
                ),
                Command(
                    "ChangeToAction",
                    _("Change current element's style to action."),
                    [util.Key(ord("A"), alt=True).toInt()],
                ),
                Command(
                    "ChangeToCharacter",
                    _("Change current element's style to character."),
                    [util.Key(ord("C"), alt=True).toInt()],
                ),
                Command(
                    "ChangeToDialogue",
                    _("Change current element's style to dialogue."),
                    [util.Key(ord("D"), alt=True).toInt()],
                ),
                Command(
                    "ChangeToNote",
                    _("Change current element's style to note."),
                    [util.Key(ord("N"), alt=True).toInt()],
                ),
                Command(
                    "ChangeToParenthetical",
                    _("Change current element's style to parenthetical."),
                    [util.Key(ord("P"), alt=True).toInt()],
                ),
                Command(
                    "ChangeToScene",
                    _("Change current element's style to" " scene."),
                    [util.Key(ord("S"), alt=True).toInt()],
                ),
                Command("ChangeToShot", _("Change current element's style to shot.")),
                Command(
                    "ChangeToTransition",
                    _("Change current element's style to transition."),
                    [util.Key(ord("T"), alt=True).toInt()],
                ),
                Command("CharacterMap", _("Open the character map."), isMenu=True),
                Command(
                    "CloseScript",
                    _("Close the current script."),
                    [util.Key(23, ctrl=True).toInt()],
                    isFixed=True,
                    isMenu=True,
                ),
                Command("CompareScripts", _("Compare two scripts."), isMenu=True),
                Command(
                    "Copy",
                    _("Copy selected text to the internal clipboard."),
                    [util.Key(3, ctrl=True).toInt()],
                    isFixed=True,
                    isMenu=True,
                ),
                Command(
                    "CopySystemCb",
                    _("Copy selected text to the system's clipboard, unformatted."),
                    isMenu=True,
                ),
                Command(
                    "CopySystemCbFormatted",
                    _("Copy selected text to the system's clipboard, formatted."),
                    isMenu=True,
                ),
                Command(
                    "Cut",
                    _("Cut selected text to internal clipboard."),
                    [util.Key(24, ctrl=True).toInt()],
                    isFixed=True,
                    isMenu=True,
                ),
                Command(
                    "Delete",
                    _("Delete the character under the cursor, or selected text."),
                    [wx.WXK_DELETE],
                    isFixed=True,
                ),
                Command(
                    "DeleteBackward",
                    _("Delete the character behind the cursor."),
                    [wx.WXK_BACK, util.Key(wx.WXK_BACK, shift=True).toInt()],
                    isFixed=True,
                ),
                Command(
                    "DeleteElements",
                    _("Open the 'Delete elements' dialog."),
                    isMenu=True,
                ),
                Command("ExportScript", _("Export the current script."), isMenu=True),
                Command(
                    "FindAndReplaceDlg",
                    _("Open the 'Find & Replace' dialog."),
                    [util.Key(6, ctrl=True).toInt()],
                    isFixed=True,
                    isMenu=True,
                ),
                Command(
                    "FindNextError",
                    _("Find next error in the current script."),
                    [util.Key(5, ctrl=True).toInt()],
                    isMenu=True,
                ),
                Command(
                    "ForcedLineBreak",
                    _("Insert a forced line break."),
                    [
                        util.Key(wx.WXK_RETURN, ctrl=True).toInt(),
                        util.Key(wx.WXK_RETURN, shift=True).toInt(),
                        # CTRL+Enter under wxMSW
                        util.Key(10, ctrl=True).toInt(),
                    ],
                    isFixed=True,
                ),
                Command(
                    "FormatBold",
                    _("Toggle bold formatting for selected text."),
                    [util.Key(2, ctrl=True).toInt()],
                    isMenu=True,
                ),
                Command(
                    "FormatItalic",
                    _("Toggle italic formatting for selected text."),
                    [util.Key(ord("I"), alt=True).toInt()],
                    isMenu=True,
                ),
                Command(
                    "FormatUnderline",
                    _("Toggle underline formatting for selected text."),
                    [util.Key(21, ctrl=True).toInt()],
                    isMenu=True,
                ),
                Command(
                    "Fullscreen",
                    _("Toggle fullscreen."),
                    [util.Key(wx.WXK_F11).toInt()],
                    isFixed=True,
                    isMenu=True,
                ),
                Command(
                    "GotoPage",
                    _("Goto to a given page."),
                    [util.Key(7, ctrl=True).toInt()],
                    isFixed=True,
                    isMenu=True,
                ),
                Command(
                    "GotoScene",
                    _("Goto to a given scene."),
                    [util.Key(ord("G"), alt=True).toInt()],
                    isFixed=True,
                    isMenu=True,
                ),
                Command("HeadersDlg", _("Open the headers dialog."), isMenu=True),
                Command(
                    "HelpCommands",
                    _("Show list of commands and their key bindings."),
                    isMenu=True,
                ),
                Command("HelpManual", _("Open the manual."), isMenu=True),
                Command("ImportScript", _("Import a script."), isMenu=True),
                Command(
                    "InsertNbsp",
                    _("Insert non-breaking space."),
                    [util.Key(wx.WXK_SPACE, shift=True, ctrl=True).toInt()],
                    isMenu=True,
                ),
                Command(
                    "LoadScriptSettings",
                    _("Load script-specific settings."),
                    isMenu=True,
                ),
                Command("LoadSettings", _("Load global settings."), isMenu=True),
                Command("LocationsDlg", _("Open the locations dialog."), isMenu=True),
                Command(
                    "MoveDown",
                    _("Move down."),
                    [wx.WXK_DOWN],
                    isMovement=True,
                    scrollDirection=SCROLL_DOWN,
                ),
                Command(
                    "MoveEndOfLine",
                    _("Move to the end of the line or finish auto-completion."),
                    [wx.WXK_END],
                    isMovement=True,
                ),
                Command(
                    "MoveEndOfScript",
                    _("Move to the end of the script."),
                    [util.Key(wx.WXK_END, ctrl=True).toInt()],
                    isMovement=True,
                ),
                Command("MoveLeft", _("Move left."), [wx.WXK_LEFT], isMovement=True),
                Command(
                    "MoveNextWord",
                    _("Move to start of next word."),
                    [util.Key(wx.WXK_RIGHT, ctrl=True).toInt()],
                    isMovement=True,
                    isFixed=True,
                ),
                Command(
                    "MovePageDown",
                    _("Move one page down."),
                    [wx.WXK_PAGEDOWN],
                    isMovement=True,
                ),
                Command(
                    "MovePageUp",
                    _("Move one page up."),
                    [wx.WXK_PAGEUP],
                    isMovement=True,
                ),
                Command(
                    "MovePrevWord",
                    _("Move to start of previous word."),
                    [util.Key(wx.WXK_LEFT, ctrl=True).toInt()],
                    isMovement=True,
                    isFixed=True,
                ),
                Command("MoveRight", _("Move right."), [wx.WXK_RIGHT], isMovement=True),
                Command(
                    "MoveSceneDown",
                    _("Move one scene down."),
                    [util.Key(wx.WXK_DOWN, ctrl=True).toInt()],
                    isMovement=True,
                ),
                Command(
                    "MoveSceneUp",
                    _("Move one scene up."),
                    [util.Key(wx.WXK_UP, ctrl=True).toInt()],
                    isMovement=True,
                ),
                Command(
                    "MoveStartOfLine",
                    _("Move to the start of the line."),
                    [wx.WXK_HOME],
                    isMovement=True,
                ),
                Command(
                    "MoveStartOfScript",
                    _("Move to the start of the" " script."),
                    [util.Key(wx.WXK_HOME, ctrl=True).toInt()],
                    isMovement=True,
                ),
                Command(
                    "MoveUp",
                    _("Move up."),
                    [wx.WXK_UP],
                    isMovement=True,
                    scrollDirection=SCROLL_UP,
                ),
                Command(
                    "NameDatabase", _("Open the character name database."), isMenu=True
                ),
                Command(
                    "NewElement",
                    _("Create a new element."),
                    [wx.WXK_RETURN],
                    isFixed=True,
                ),
                Command(
                    "NewScript",
                    _("Create a new script."),
                    [util.Key(14, ctrl=True).toInt()],
                    isFixed=True,
                    isMenu=True,
                ),
                Command(
                    "OpenScript",
                    _("Open a script."),
                    [util.Key(15, ctrl=True).toInt()],
                    isFixed=True,
                    isMenu=True,
                ),
                Command("Paginate", _("Paginate current script."), isMenu=True),
                Command(
                    "Paste",
                    _("Paste text from the internal clipboard."),
                    [util.Key(22, ctrl=True).toInt()],
                    isFixed=True,
                    isMenu=True,
                ),
                Command(
                    "PasteSystemCb",
                    _("Paste text from the system's clipboard."),
                    isMenu=True,
                ),
                Command(
                    "PrintScript",
                    _("Print current script."),
                    [util.Key(16, ctrl=True).toInt()],
                    isFixed=True,
                    isMenu=True,
                ),
                Command(
                    "Quit",
                    _("Quit the program."),
                    [util.Key(17, ctrl=True).toInt()],
                    isFixed=True,
                    isMenu=True,
                ),
                Command(
                    "Redo",
                    _("Redo a change that was reverted through undo."),
                    [util.Key(25, ctrl=True).toInt()],
                    isFixed=True,
                    isMenu=True,
                ),
                Command(
                    "ReportCharacter", _("Generate character report."), isMenu=True
                ),
                Command(
                    "ReportDialogueChart",
                    _("Generate dialogue chart report."),
                    isMenu=True,
                ),
                Command("ReportLocation", _("Generate location report."), isMenu=True),
                Command("ReportScene", _("Generate scene report."), isMenu=True),
                Command("ReportScript", _("Generate script report."), isMenu=True),
                Command(
                    "RevertScript",
                    _("Revert current script to the version on disk."),
                    isMenu=True,
                ),
                Command(
                    "SaveScript",
                    _("Save the current script."),
                    [util.Key(19, ctrl=True).toInt()],
                    isFixed=True,
                    isMenu=True,
                ),
                Command(
                    "SaveScriptAs",
                    _("Save the current script to a new file."),
                    isMenu=True,
                ),
                Command(
                    "SaveScriptSettingsAs",
                    _("Save script-specific settings to a new file."),
                    isMenu=True,
                ),
                Command(
                    "SaveSettingsAs",
                    _("Save global settings to a new file."),
                    isMenu=True,
                ),
                Command(
                    "ScriptNext",
                    _("Change to next open script."),
                    [
                        util.Key(wx.WXK_TAB, ctrl=True).toInt(),
                        util.Key(wx.WXK_PAGEDOWN, ctrl=True).toInt(),
                    ],
                    isMenu=True,
                ),
                Command(
                    "ScriptPrev",
                    _("Change to previous open script."),
                    [
                        util.Key(wx.WXK_TAB, shift=True, ctrl=True).toInt(),
                        util.Key(wx.WXK_PAGEUP, ctrl=True).toInt(),
                    ],
                    isMenu=True,
                ),
                Command(
                    "ScriptSettings", _("Change script-specific settings."), isMenu=True
                ),
                Command("SelectAll", _("Select the entire script."), isMenu=True),
                Command(
                    "SelectScene",
                    _("Select the current scene."),
                    [util.Key(1, ctrl=True).toInt()],
                    isMenu=True,
                ),
                Command(
                    "SetMark",
                    _("Set mark at current cursor position."),
                    [util.Key(wx.WXK_SPACE, ctrl=True).toInt()],
                ),
                Command("Settings", _("Change global settings."), isMenu=True),
                Command(
                    "SpellCheckerDictionaryDlg",
                    _("Open the global spell checker dictionary dialog."),
                    isMenu=True,
                ),
                Command(
                    "SpellCheckerDlg",
                    _("Spell check the script."),
                    [util.Key(wx.WXK_F8).toInt()],
                    isMenu=True,
                ),
                Command(
                    "SpellCheckerScriptDictionaryDlg",
                    _("Open the script-specific spell checker dictionary dialog."),
                    isMenu=True,
                ),
                Command(
                    "Tab",
                    _(
                        "Change current element to the next style or create a new element."
                    ),
                    [wx.WXK_TAB],
                    isFixed=True,
                ),
                Command(
                    "TabPrev",
                    _("Change current element to the previous style."),
                    [util.Key(wx.WXK_TAB, shift=True).toInt()],
                    isFixed=True,
                ),
                Command("TitlesDlg", _("Open the titles dialog."), isMenu=True),
                Command(
                    "ToggleShowFormatting",
                    _("Toggle 'Show formatting' display."),
                    isMenu=True,
                ),
                Command(
                    "Undo",
                    _("Undo the last change."),
                    [util.Key(26, ctrl=True).toInt()],
                    isFixed=True,
                    isMenu=True,
                ),
                Command("ViewModeDraft", _("Change view mode to draft."), isMenu=True),
                Command(
                    "ViewModeLayout", _("Change view mode to layout."), isMenu=True
                ),
                Command(
                    "ViewModeSideBySide",
                    _("Change view mode to side by side."),
                    isMenu=True,
                ),
                Command("Watermark", _("Generate watermarked PDFs."), isMenu=True),
            ]
        )

        self.recalc()

    def setupVars(self):
        v = self.__class__.cvars = mypickle.Vars()

        # how many seconds to show splash screen for on startup (0 = disabled)
        v.addInt("splashTime", 2, "SplashTime", 0, 10)

        # vertical distance between rows, in pixels
        v.addInt("fontYdelta", 18, "FontYDelta", 4, 125)

        # how many lines to scroll per mouse wheel event
        v.addInt("mouseWheelLines", 4, "MouseWheelLines", 1, 50)

        # interval in seconds between automatic pagination (0 = disabled)
        v.addInt("paginateInterval", 1, "PaginateInterval", 0, 10)

        # whether to check script for errors before export / print
        v.addBool("checkOnExport", True, "CheckScriptForErrors")

        # whether to auto-capitalize start of sentences
        v.addBool("capitalize", True, "CapitalizeSentences")

        # whether to auto-capitalize i -> I
        v.addBool("capitalizeI", True, "CapitalizeI")

        # whether to open scripts on their last saved position
        v.addBool("honorSavedPos", True, "OpenScriptOnSavedPos")

        # whether to recenter screen when cursor moves out of it
        v.addBool("recenterOnScroll", False, "RecenterOnScroll")

        # whether to overwrite selected text on typing
        v.addBool("overwriteSelectionOnInsert", True, "OverwriteSelectionOnInsert")

        # whether to use per-elem-type colors (textSceneColor etc.)
        # instead of using textColor for all elem types
        v.addBool("useCustomElemColors", False, "UseCustomElemColors")
        v.addInt("pageThemeMode", THEME_SYSTEM, "PageThemeMode", THEME_FIRST, THEME_LAST)
        v.addInt("displayScale", 200, "DisplayScale", 1, 400)

        # page break indicators to show
        v.addInt("pbi", PBI_REAL, "PageBreakIndicators", PBI_FIRST, PBI_LAST)

        # PDF viewer program and args. defaults are empty since generating
        # them is a complex process handled by findPDFViewer.
        v.addStrUnicode("pdfViewerPath", "", "PDF/ViewerPath")
        v.addStrBinary("pdfViewerArgs", "", "PDF/ViewerArguments")

        # fonts. real defaults are set in setDefaultFonts.
        v.addStrBinary("fontNormal", "", "FontNormal")
        v.addStrBinary("fontBold", "", "FontBold")
        v.addStrBinary("fontItalic", "", "FontItalic")
        v.addStrBinary("fontBoldItalic", "", "FontBoldItalic")

        # default script directory
        v.addStrUnicode("scriptDir", misc.progPath, "DefaultScriptDirectory")

        # colors
        v.addColor("text", 0, 0, 0, "TextFG", _("Text foreground"))
        v.addColor(
            "textHdr", 128, 128, 128, "TextHeadersFG", _("Text foreground (headers)")
        )
        v.addColor("textBg", 255, 255, 255, "TextBG", _("Text background"))
        v.addColor("workspace", 246, 247, 249, "Workspace", _("Workspace"))
        v.addColor("pageBorder", 214, 216, 220, "PageBorder", _("Page border"))
        v.addColor("pageShadow", 193, 196, 201, "PageShadow", _("Page shadow"))
        v.addColor("selected", 215, 231, 255, "Selected", _("Selection"))
        v.addColor("cursor", 10, 132, 255, "Cursor", _("Cursor"))
        v.addColor(
            "autoCompFg", 0, 0, 0, "AutoCompletionFG", _("Auto-completion foreground")
        )
        v.addColor(
            "autoCompBg",
            242,
            247,
            255,
            "AutoCompletionBG",
            _("Auto-completion background"),
        )
        v.addColor("note", 255, 247, 224, "ScriptNote", _("Script note"))
        v.addColor("pagebreak", 221, 221, 221, "PageBreakLine", _("Page-break line"))
        v.addColor(
            "pagebreakNoAdjust",
            221,
            221,
            221,
            "PageBreakNoAdjustLine",
            _("Page-break (original, not adjusted) line"),
        )

        v.addColor("tabText", 50, 50, 50, "TabText", _("Tab text"))
        v.addColor("tabBorder", 202, 202, 202, "TabBorder", _("Tab border"))
        v.addColor("tabBarBg", 221, 217, 215, "TabBarBG", _("Tab bar background"))
        v.addColor(
            "tabNonActiveBg", 180, 180, 180, "TabNonActiveBg", _("Tab, non-active")
        )

        for t in getTIs():
            v.addColor(
                "text%s" % t.name,
                0,
                0,
                0,
                "Text%sFG" % t.name,
                _("Text foreground for {}".format(t.name)),
            )

        v.makeDicts()

    # load config from string 's'. does not throw any exceptions, silently
    # ignores any errors, and always leaves config in an ok state.
    def load(self, s):
        vals = self.cvars.makeVals(s)

        self.cvars.load(vals, "", self)

        for t in self.types.values():
            t.load(vals, "Element/")

        for cmd in self.commands:
            cmd.load(vals, "Command/")

        self.recalc()

    # save config into a string and return that.
    def save(self):
        s = self.cvars.save("", self)

        for t in self.types.values():
            s += t.save("Element/")

        for cmd in self.commands:
            s += cmd.save("Command/")

        return s

    # fix up all invalid config values.
    def recalc(self):
        for it in self.cvars.numeric.values():
            util.clampObj(self, it.name, it.minVal, it.maxVal)

        # Backward compatibility: older builds stored displayScale as 1..4
        # multipliers. Normalize to the nearest allowed percentage value.
        try:
            self.displayScale = int(self.displayScale)
        except (TypeError, ValueError):
            self.displayScale = 200

        if self.displayScale <= 4:
            self.displayScale = self.displayScale * 100
        self.displayScale = min(
            DISPLAY_SCALE_OPTIONS, key=lambda v: abs(v - self.displayScale)
        )

        # Backward compatibility: CTRL+I conflicts with CTRL+Tab in our
        # keycode model. Migrate old italic binding to ALT+I.
        italic_cmd = None
        for cmd in self.commands:
            if cmd.name == "FormatItalic":
                italic_cmd = cmd
                break

        if italic_cmd:
            legacy_key = util.Key(9, ctrl=True).toInt()
            new_key = util.Key(ord("I"), alt=True).toInt()

            if legacy_key in italic_cmd.keys:
                italic_cmd.keys = [k for k in italic_cmd.keys if k != legacy_key]
                if new_key not in italic_cmd.keys:
                    italic_cmd.keys.insert(0, new_key)
                if len(italic_cmd.keys) == 0:
                    italic_cmd.keys.append(new_key)

    def getType(self, lt):
        return self.types[lt]

    # add SHIFT+Key alias for all keys bound to movement commands, so
    # selection-movement works.
    def addShiftKeys(self):
        for cmd in self.commands:
            if cmd.isMovement:
                nk = []

                for key in cmd.keys:
                    k = util.Key.fromInt(key)
                    k.shift = True
                    ki = k.toInt()

                    if ki not in cmd.keys:
                        nk.append(ki)

                cmd.keys.extend(nk)

    # remove key (int) from given cmd
    def removeKey(self, cmd, key):
        cmd.keys.remove(key)

        if cmd.isMovement:
            k = util.Key.fromInt(key)
            k.shift = True
            ki = k.toInt()

            if ki in cmd.keys:
                cmd.keys.remove(ki)

    # get textual description of conflicting keys, or None if no
    # conflicts.
    def getConflictingKeys(self):
        keys = {}

        for cmd in self.commands:
            for key in cmd.keys:
                if key in keys:
                    keys[key].append(cmd.name)
                else:
                    keys[key] = [cmd.name]

        s = ""
        for k, v in keys.items():
            if len(v) > 1:
                s += "%s:" % util.Key.fromInt(k).toStr()

                for cmd in v:
                    s += " %s" % cmd

                s += "\n"

        if s == "":
            return None
        else:
            return s

    # set default values that vary depending on platform, wxWidgets
    # version, etc. this is not at the end of __init__ because
    # non-interactive uses have no needs for these.
    def setDefaults(self):
        # check keyboard commands are listed in correct order
        commands = [cmd.name for cmd in self.commands]
        commandsSorted = sorted(commands)

        if commands != commandsSorted:
            # for i in range(len(commands)):
            #     if commands[i] != commandsSorted[i]:
            #         print "Got: %s Expected: %s" % (commands[i], commandsSorted[i])

            # if you get this error, you've put a new command you've added
            # in an incorrect place in the command list. uncomment the
            # above lines to figure out where it should be.
            raise ConfigError(_("Commands not listed in correct order"))

        self.setDefaultFonts()
        self.findPDFViewer()

    # set default fonts
    def setDefaultFonts(self):
        fn = ["", "", "", ""]

        if misc.isMac:
            fn[0] = "Menlo 13"
            fn[1] = "Menlo Bold 13"
            fn[2] = "Menlo Italic 13"
            fn[3] = "Menlo Bold Italic 13"
        elif misc.isUnix:
            fn[0] = "Monospace 12"
            fn[1] = "Monospace Bold 12"
            fn[2] = "Monospace Italic 12"
            fn[3] = "Monospace Bold Italic 12"

        elif misc.isWindows:
            fn[0] = "0;-13;0;0;0;400;0;0;0;0;3;2;1;49;Courier New"
            fn[1] = "0;-13;0;0;0;700;0;0;0;0;3;2;1;49;Courier New"
            fn[2] = "0;-13;0;0;0;400;255;0;0;0;3;2;1;49;Courier New"
            fn[3] = "0;-13;0;0;0;700;255;0;0;0;3;2;1;49;Courier New"

        else:
            raise ConfigError(_("Unknown platform"))

        self.fontNormal = fn[0]
        self.fontBold = fn[1]
        self.fontItalic = fn[2]
        self.fontBoldItalic = fn[3]

    # set PDF viewer program to the best one found on the machine.
    def findPDFViewer(self):
        name, args = util.getPDFViewer()
        if name:
            self.pdfViewerPath = name
            self.pdfViewerArgs = args


# config stuff that are wxwindows objects, so can't be in normal
# ConfigGlobal (deepcopy dies)
class ConfigGui:

    # constants
    constantsInited = False
    bluePen = None
    redColor = None
    blackColor = None

    def __init__(self, cfgGl):

        if not ConfigGui.constantsInited:
            ConfigGui.bluePen = wx.Pen(wx.Colour(0, 0, 255))
            ConfigGui.redColor = wx.Colour(255, 0, 0)
            ConfigGui.blackColor = wx.Colour(0, 0, 0)

            ConfigGui.constantsInited = True

        # convert cfgGl.MyColor -> cfgGui.wx.Colour
        for it in cfgGl.cvars.color.values():
            c = getattr(cfgGl, it.name)
            tmp = wx.Colour(c.r, c.g, c.b)
            setattr(self, it.name, tmp)

        self.applyDocumentTheme(cfgGl.pageThemeMode)
        self.applyMacChromeTheme(cfgGl.pageThemeMode)

        # key = line type, value = wx.Colour
        self._lt2textColor = {}

        for t in getTIs():
            self._lt2textColor[t.lt] = getattr(self, "text%sColor" % t.name)

        self.textPen = wx.Pen(self.textColor)
        self.textHdrPen = wx.Pen(self.textHdrColor)

        self.workspaceBrush = wx.Brush(self.workspaceColor)
        self.workspacePen = wx.Pen(self.workspaceColor)

        self.textBgBrush = wx.Brush(self.textBgColor)
        self.textBgPen = wx.Pen(self.textBgColor)

        self.pageBorderPen = wx.Pen(self.pageBorderColor)
        self.pageShadowPen = wx.Pen(self.pageShadowColor)

        self.selectedBrush = wx.Brush(self.selectedColor)
        self.selectedPen = wx.Pen(self.selectedColor)

        self.cursorBrush = wx.Brush(self.cursorColor)
        self.cursorPen = wx.Pen(self.cursorColor)

        self.noteBrush = wx.Brush(self.noteColor)
        self.notePen = wx.Pen(self.noteColor)

        self.autoCompPen = wx.Pen(self.autoCompFgColor)
        self.autoCompBrush = wx.Brush(self.autoCompBgColor)
        self.autoCompRevPen = wx.Pen(self.autoCompBgColor)
        self.autoCompRevBrush = wx.Brush(self.autoCompFgColor)

        self.pagebreakPen = wx.Pen(self.pagebreakColor)
        self.pagebreakNoAdjustPen = wx.Pen(self.pagebreakNoAdjustColor, style=wx.DOT)

        self.tabTextPen = wx.Pen(self.tabTextColor)
        self.tabBorderPen = wx.Pen(self.tabBorderColor)

        self.tabBarBgBrush = wx.Brush(self.tabBarBgColor)
        self.tabBarBgPen = wx.Pen(self.tabBarBgColor)

        self.tabNonActiveBgBrush = wx.Brush(self.tabNonActiveBgColor)
        self.tabNonActiveBgPen = wx.Pen(self.tabNonActiveBgColor)

        # a 4-item list of FontInfo objects, indexed by the two lowest
        # bits of pml.TextOp.flags.
        self.fonts = []

        baseFont = None
        for idx, fname in enumerate(
            ["fontNormal", "fontBold", "fontItalic", "fontBoldItalic"]
        ):
            fi = FontInfo()

            s = getattr(cfgGl, fname)

            # evil users can set the font name to empty by modifying the
            # config file, and some wxWidgets ports crash hard when trying
            # to create a font from an empty string, so we must guard
            # against that.
            if s:
                nfi = wx.NativeFontInfo()
                nfi.FromString(s)

                try:
                    fi.font = wx.Font(nfi)
                    fi.font.SetEncoding(wx.FONTENCODING_UTF8)
                    scale = float(cfgGl.displayScale) / 100.0
                    fi.font.SetPointSize(
                        max(1, int(fi.font.GetPointSize() * scale))
                    )

                    # likewise, evil users can set the font name to "z" or
                    # something equally silly, resulting in an
                    # invalid/non-existent font. on wxGTK2 and wxMSW we can
                    # detect this by checking the point size of the font.
                    if fi.font.GetPointSize() == 0:
                        fi.font = None
                except wx._core.wxAssertionError:
                    # Some platforms (mac) will assert internally if point size
                    # is 0, preventing us from even trying to check, so just
                    # catch that too.
                    fi.font = None

            # if either of the above failures happened, create a dummy
            # font and use it. this sucks but is preferable to crashing or
            # displaying an empty screen.
            if not fi.font:
                if idx == 0:
                    fallback = wx.Font(
                        10,
                        wx.MODERN,
                        wx.NORMAL,
                        wx.NORMAL,
                        encoding=wx.FONTENCODING_ISO8859_1,
                    )
                else:
                    source = baseFont or wx.Font(
                        10,
                        wx.MODERN,
                        wx.NORMAL,
                        wx.NORMAL,
                        encoding=wx.FONTENCODING_ISO8859_1,
                    )
                    fallback = wx.Font(source)

                    if idx == 1:
                        fallback.SetWeight(wx.FONTWEIGHT_BOLD)
                    elif idx == 2:
                        fallback.SetStyle(wx.FONTSTYLE_ITALIC)
                    elif idx == 3:
                        fallback.SetWeight(wx.FONTWEIGHT_BOLD)
                        fallback.SetStyle(wx.FONTSTYLE_ITALIC)

                fi.font = fallback
                setattr(cfgGl, fname, fi.font.GetNativeFontInfo().ToString())

            # Ensure bold/italic variants actually have the flags set,
            # regardless of whether they were loaded from config or fallback.
            if idx == 1:
                fi.font.SetWeight(wx.FONTWEIGHT_BOLD)
            elif idx == 2:
                fi.font.SetStyle(wx.FONTSTYLE_ITALIC)
            elif idx == 3:
                fi.font.SetWeight(wx.FONTWEIGHT_BOLD)
                fi.font.SetStyle(wx.FONTSTYLE_ITALIC)

            if idx == 0:
                baseFont = wx.Font(fi.font)

            fx, fy = util.getTextExtent(fi.font, "O")

            fi.fx = max(1, fx)
            fi.fy = max(1, fy)

            self.fonts.append(fi)

    def isSystemDarkMode(self):
        if not hasattr(wx.SystemSettings, "GetAppearance"):
            return False
        appearance = wx.SystemSettings.GetAppearance()
        if not appearance or not hasattr(appearance, "IsDark"):
            return False
        return appearance.IsDark()

    def applyMacChromeTheme(self, themeMode):
        if not misc.isMac:
            return

        # Only apply overrides for standard themes (Light, Dark, System)
        # Custom themes (Sepia, Solarized, etc.) define their own colors that shouldn't be overridden.
        if themeMode not in (THEME_LIGHT, THEME_DARK, THEME_SYSTEM):
            return

        useDark = themeMode == THEME_DARK
        if themeMode == THEME_SYSTEM:
            useDark = self.isSystemDarkMode()

        if useDark:
            # Modern macOS Dark Mode colors (Big Sur+)
            self.workspaceColor = wx.Colour(30, 30, 30)  # Darker background
            self.tabTextColor = wx.Colour(220, 220, 220)
            self.tabBarBgColor = wx.Colour(40, 40, 40)   # Lighter foreground (toolbar)
            self.tabNonActiveBgColor = wx.Colour(50, 50, 50)
            self.tabBorderColor = wx.Colour(60, 60, 60)
            self.pageShadowColor = wx.Colour(10, 10, 10)
            self.pageBorderColor = wx.Colour(60, 60, 60)
        else:
            # Modern macOS Light Mode colors (Big Sur+)
            self.workspaceColor = wx.Colour(255, 255, 255) # Pure white background for content
            self.tabTextColor = wx.Colour(60, 60, 60)
            self.tabBarBgColor = wx.Colour(236, 236, 236)  # Standard light gray toolbar
            self.tabNonActiveBgColor = wx.Colour(225, 225, 225) # Slightly darker than toolbar
            self.tabBorderColor = wx.Colour(210, 210, 210)
            self.pageShadowColor = wx.Colour(210, 210, 210) # Subtle shadow
            self.pageBorderColor = wx.Colour(220, 220, 220)

    def applyDocumentTheme(self, themeMode):
        if themeMode == THEME_SEPIA:
            self.textColor = wx.Colour(57, 45, 33)
            self.textHdrColor = wx.Colour(124, 107, 88)
            self.textBgColor = wx.Colour(250, 242, 226)
            self.workspaceColor = wx.Colour(236, 227, 210)
            self.pageBorderColor = wx.Colour(204, 185, 158)
            self.pageShadowColor = wx.Colour(183, 164, 137)
            self.selectedColor = wx.Colour(229, 210, 177)
            self.cursorColor = wx.Colour(167, 114, 44)
            self.noteColor = wx.Colour(255, 237, 196)
            self.pagebreakColor = wx.Colour(203, 184, 156)
            self.pagebreakNoAdjustColor = wx.Colour(180, 162, 136)
            self.autoCompFgColor = wx.Colour(57, 45, 33)
            self.autoCompBgColor = wx.Colour(245, 232, 207)
            self.tabTextColor = wx.Colour(62, 50, 38)
            self.tabBarBgColor = wx.Colour(224, 207, 183)
            self.tabNonActiveBgColor = wx.Colour(209, 190, 163)
            self.tabBorderColor = wx.Colour(183, 164, 137)
            return

        if themeMode == THEME_GRAPHITE:
            self.textColor = wx.Colour(28, 30, 33)
            self.textHdrColor = wx.Colour(107, 114, 124)
            self.textBgColor = wx.Colour(248, 249, 251)
            self.workspaceColor = wx.Colour(232, 235, 239)
            self.pageBorderColor = wx.Colour(193, 199, 208)
            self.pageShadowColor = wx.Colour(168, 174, 183)
            self.selectedColor = wx.Colour(208, 216, 228)
            self.cursorColor = wx.Colour(97, 108, 125)
            self.noteColor = wx.Colour(241, 243, 247)
            self.pagebreakColor = wx.Colour(191, 198, 207)
            self.pagebreakNoAdjustColor = wx.Colour(163, 170, 181)
            self.autoCompFgColor = wx.Colour(33, 36, 40)
            self.autoCompBgColor = wx.Colour(234, 238, 244)
            self.tabTextColor = wx.Colour(45, 49, 55)
            self.tabBarBgColor = wx.Colour(214, 220, 228)
            self.tabNonActiveBgColor = wx.Colour(194, 201, 211)
            self.tabBorderColor = wx.Colour(161, 168, 179)
            return

        if themeMode == THEME_MIDNIGHT:
            self.textColor = wx.Colour(223, 235, 255)
            self.textHdrColor = wx.Colour(140, 156, 184)
            self.textBgColor = wx.Colour(20, 27, 40)
            self.workspaceColor = wx.Colour(13, 18, 30)
            self.pageBorderColor = wx.Colour(47, 63, 89)
            self.pageShadowColor = wx.Colour(7, 10, 18)
            self.selectedColor = wx.Colour(44, 76, 127)
            self.cursorColor = wx.Colour(86, 169, 255)
            self.noteColor = wx.Colour(40, 50, 74)
            self.pagebreakColor = wx.Colour(70, 88, 116)
            self.pagebreakNoAdjustColor = wx.Colour(88, 108, 139)
            self.autoCompFgColor = wx.Colour(227, 236, 250)
            self.autoCompBgColor = wx.Colour(35, 47, 67)
            self.tabTextColor = wx.Colour(231, 240, 255)
            self.tabBarBgColor = wx.Colour(20, 27, 40)
            self.tabNonActiveBgColor = wx.Colour(33, 43, 63)
            self.tabBorderColor = wx.Colour(61, 77, 105)
            return

        if themeMode == THEME_SOLAR_LIGHT:
            self.textColor = wx.Colour(88, 110, 117)
            self.textHdrColor = wx.Colour(131, 148, 150)
            self.textBgColor = wx.Colour(253, 246, 227)
            self.workspaceColor = wx.Colour(245, 238, 214)
            self.pageBorderColor = wx.Colour(220, 210, 173)
            self.pageShadowColor = wx.Colour(198, 189, 154)
            self.selectedColor = wx.Colour(238, 232, 213)
            self.cursorColor = wx.Colour(38, 139, 210)
            self.noteColor = wx.Colour(254, 240, 198)
            self.pagebreakColor = wx.Colour(210, 200, 166)
            self.pagebreakNoAdjustColor = wx.Colour(186, 177, 147)
            self.autoCompFgColor = wx.Colour(88, 110, 117)
            self.autoCompBgColor = wx.Colour(243, 234, 202)
            self.tabTextColor = wx.Colour(87, 106, 112)
            self.tabBarBgColor = wx.Colour(231, 222, 191)
            self.tabNonActiveBgColor = wx.Colour(218, 208, 177)
            self.tabBorderColor = wx.Colour(189, 180, 150)
            return

        if themeMode == THEME_SOLAR_DARK:
            self.textColor = wx.Colour(131, 148, 150)
            self.textHdrColor = wx.Colour(101, 123, 131)
            self.textBgColor = wx.Colour(0, 43, 54)
            self.workspaceColor = wx.Colour(0, 34, 43)
            self.pageBorderColor = wx.Colour(7, 54, 66)
            self.pageShadowColor = wx.Colour(0, 24, 30)
            self.selectedColor = wx.Colour(7, 54, 66)
            self.cursorColor = wx.Colour(38, 139, 210)
            self.noteColor = wx.Colour(16, 59, 70)
            self.pagebreakColor = wx.Colour(31, 74, 85)
            self.pagebreakNoAdjustColor = wx.Colour(44, 85, 96)
            self.autoCompFgColor = wx.Colour(147, 161, 161)
            self.autoCompBgColor = wx.Colour(10, 52, 63)
            self.tabTextColor = wx.Colour(167, 180, 180)
            self.tabBarBgColor = wx.Colour(0, 43, 54)
            self.tabNonActiveBgColor = wx.Colour(7, 54, 66)
            self.tabBorderColor = wx.Colour(31, 74, 85)
            return

        if themeMode == THEME_FOREST:
            self.textColor = wx.Colour(34, 54, 41)
            self.textHdrColor = wx.Colour(89, 114, 98)
            self.textBgColor = wx.Colour(241, 248, 242)
            self.workspaceColor = wx.Colour(222, 235, 224)
            self.pageBorderColor = wx.Colour(176, 198, 181)
            self.pageShadowColor = wx.Colour(151, 174, 157)
            self.selectedColor = wx.Colour(197, 224, 201)
            self.cursorColor = wx.Colour(46, 125, 70)
            self.noteColor = wx.Colour(230, 242, 220)
            self.pagebreakColor = wx.Colour(171, 194, 176)
            self.pagebreakNoAdjustColor = wx.Colour(148, 172, 153)
            self.autoCompFgColor = wx.Colour(36, 56, 43)
            self.autoCompBgColor = wx.Colour(213, 231, 216)
            self.tabTextColor = wx.Colour(35, 57, 43)
            self.tabBarBgColor = wx.Colour(199, 220, 203)
            self.tabNonActiveBgColor = wx.Colour(183, 206, 188)
            self.tabBorderColor = wx.Colour(148, 172, 153)
            return

        if themeMode == THEME_ROSE:
            self.textColor = wx.Colour(64, 40, 49)
            self.textHdrColor = wx.Colour(124, 95, 106)
            self.textBgColor = wx.Colour(255, 247, 250)
            self.workspaceColor = wx.Colour(243, 227, 234)
            self.pageBorderColor = wx.Colour(214, 184, 196)
            self.pageShadowColor = wx.Colour(193, 162, 175)
            self.selectedColor = wx.Colour(241, 211, 224)
            self.cursorColor = wx.Colour(191, 67, 118)
            self.noteColor = wx.Colour(255, 236, 242)
            self.pagebreakColor = wx.Colour(205, 175, 188)
            self.pagebreakNoAdjustColor = wx.Colour(181, 152, 165)
            self.autoCompFgColor = wx.Colour(70, 46, 55)
            self.autoCompBgColor = wx.Colour(248, 225, 235)
            self.tabTextColor = wx.Colour(70, 46, 55)
            self.tabBarBgColor = wx.Colour(232, 204, 216)
            self.tabNonActiveBgColor = wx.Colour(220, 191, 204)
            self.tabBorderColor = wx.Colour(182, 153, 166)
            return

        if themeMode == THEME_HIGH_CONTRAST:
            self.textColor = wx.Colour(255, 255, 255)
            self.textHdrColor = wx.Colour(255, 255, 0)
            self.textBgColor = wx.Colour(0, 0, 0)
            self.workspaceColor = wx.Colour(0, 0, 0)
            self.pageBorderColor = wx.Colour(255, 255, 255)
            self.pageShadowColor = wx.Colour(80, 80, 80)
            self.selectedColor = wx.Colour(0, 0, 255)
            self.cursorColor = wx.Colour(0, 255, 255)
            self.noteColor = wx.Colour(30, 30, 30)
            self.pagebreakColor = wx.Colour(255, 255, 255)
            self.pagebreakNoAdjustColor = wx.Colour(180, 180, 180)
            self.autoCompFgColor = wx.Colour(255, 255, 255)
            self.autoCompBgColor = wx.Colour(35, 35, 35)
            self.tabTextColor = wx.Colour(255, 255, 255)
            self.tabBarBgColor = wx.Colour(0, 0, 0)
            self.tabNonActiveBgColor = wx.Colour(28, 28, 28)
            self.tabBorderColor = wx.Colour(255, 255, 255)
            return

        if themeMode == THEME_PAPER:
            self.textColor = wx.Colour(43, 38, 31)
            self.textHdrColor = wx.Colour(97, 89, 78)
            self.textBgColor = wx.Colour(252, 250, 244)
            self.workspaceColor = wx.Colour(237, 232, 221)
            self.pageBorderColor = wx.Colour(205, 196, 179)
            self.pageShadowColor = wx.Colour(181, 171, 154)
            self.selectedColor = wx.Colour(230, 219, 194)
            self.cursorColor = wx.Colour(119, 94, 61)
            self.noteColor = wx.Colour(251, 241, 218)
            self.pagebreakColor = wx.Colour(199, 190, 173)
            self.pagebreakNoAdjustColor = wx.Colour(174, 165, 149)
            self.autoCompFgColor = wx.Colour(52, 46, 38)
            self.autoCompBgColor = wx.Colour(241, 232, 209)
            self.tabTextColor = wx.Colour(52, 46, 38)
            self.tabBarBgColor = wx.Colour(224, 215, 197)
            self.tabNonActiveBgColor = wx.Colour(212, 202, 184)
            self.tabBorderColor = wx.Colour(174, 165, 149)
            return

        useDark = themeMode == THEME_DARK
        if themeMode == THEME_SYSTEM:
            useDark = self.isSystemDarkMode()

        if useDark:
            self.textColor = wx.Colour(227, 230, 235)
            self.textHdrColor = wx.Colour(153, 160, 169)
            self.textBgColor = wx.Colour(36, 38, 42)
            self.workspaceColor = wx.Colour(24, 25, 28)
            self.pageBorderColor = wx.Colour(72, 76, 83)
            self.pageShadowColor = wx.Colour(15, 16, 18)
            self.selectedColor = wx.Colour(52, 86, 132)
            self.cursorColor = wx.Colour(118, 176, 255)
            self.noteColor = wx.Colour(73, 63, 36)
            self.pagebreakColor = wx.Colour(88, 95, 106)
            self.pagebreakNoAdjustColor = wx.Colour(103, 110, 120)
            self.autoCompFgColor = wx.Colour(230, 233, 238)
            self.autoCompBgColor = wx.Colour(51, 55, 62)
            self.tabTextColor = wx.Colour(245, 247, 250)
            self.tabBarBgColor = wx.Colour(36, 38, 42)
            self.tabNonActiveBgColor = wx.Colour(50, 54, 60)
            self.tabBorderColor = wx.Colour(72, 76, 83)
        else:
            self.textColor = wx.Colour(20, 21, 24)
            self.textHdrColor = wx.Colour(113, 118, 126)
            self.textBgColor = wx.Colour(255, 255, 255)
            self.workspaceColor = wx.Colour(240, 242, 245)
            self.pageBorderColor = wx.Colour(214, 216, 220)
            self.pageShadowColor = wx.Colour(192, 196, 202)
            self.selectedColor = wx.Colour(214, 231, 255)
            self.cursorColor = wx.Colour(10, 132, 255)
            self.noteColor = wx.Colour(255, 249, 229)
            self.pagebreakColor = wx.Colour(208, 214, 222)
            self.pagebreakNoAdjustColor = wx.Colour(185, 193, 204)
            self.autoCompFgColor = wx.Colour(20, 21, 24)
            self.autoCompBgColor = wx.Colour(245, 249, 255)
            self.tabTextColor = wx.Colour(50, 50, 50)
            self.tabBarBgColor = wx.Colour(221, 217, 215)
            self.tabNonActiveBgColor = wx.Colour(180, 180, 180)
            self.tabBorderColor = wx.Colour(202, 202, 202)

    # TextType -> FontInfo
    def tt2fi(self, tt):
        return self.fonts[tt.isBold | (tt.isItalic << 1)]

    # line type -> wx.Colour
    def lt2textColor(self, lt):
        return self._lt2textColor[lt]


def _conv(dict, key, raiseException=True):
    val = dict.get(key)
    if (val == None) and raiseException:
        raise ConfigError(_("key '{}' not found from '{}'".format(key, dict)))

    return val


# get TypeInfos
def getTIs():
    return _ti


def char2lb(char, raiseException=True):
    return _conv(_char2lb, char, raiseException)


def lb2char(lb):
    return _conv(_lb2char, lb)


def lb2str(lb):
    return _conv(_lb2str, lb)


def lb2displayChar(lb):
    if lb == screenplay.LB_LAST:
        return "\u00b6"
    elif lb == screenplay.LB_FORCED:
        return "\u21b5"
    elif lb == screenplay.LB_SPACE:
        return "\u00ac"
    # For LB_NONE/LB_SPACE2, stick to default or empty
    return _conv(_lb2char, lb)


def char2lt(char, raiseException=True):
    ti = _conv(_char2ti, char, raiseException)

    if ti:
        return ti.lt
    else:
        return None


def lt2char(lt):
    return _conv(_lt2ti, lt).char


def name2ti(name, raiseException=True):
    return _conv(_name2ti, name, raiseException)


def lt2ti(lt):
    return _conv(_lt2ti, lt)


def _init():

    for lt, char, name in (
        (screenplay.SCENE, "\\", "Scene"),
        (screenplay.ACTION, ".", "Action"),
        (screenplay.CHARACTER, "_", "Character"),
        (screenplay.DIALOGUE, ":", "Dialogue"),
        (screenplay.PAREN, "(", "Parenthetical"),
        (screenplay.TRANSITION, "/", "Transition"),
        (screenplay.SHOT, "=", "Shot"),
        (screenplay.ACTBREAK, "@", "Act break"),
        (screenplay.NOTE, "%", "Note"),
    ):

        ti = TypeInfo(lt, char, name)

        _ti.append(ti)
        _lt2ti[lt] = ti
        _char2ti[char] = ti
        _name2ti[name] = ti


_init()
