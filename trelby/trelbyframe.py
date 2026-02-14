# -*- coding: iso-8859-1 -*-

import copy
import os
import os.path
import re
import signal
import webbrowser
from functools import partial

import wx
import wx.svg

import trelby
import trelby.charmapdlg as charmapdlg
import trelby.commandsdlg as commandsdlg
import trelby.config as config
import trelby.misc as misc
import trelby.namesdlg as namesdlg
import trelby.spellcheckcfgdlg as spellcheckcfgdlg
import trelby.splash as splash
import trelby.util as util
from trelby.ids import *
from trelby.trelbypanel import MyPanel


class MyFrame(wx.Frame):

    def __init__(self, parent, id, title, gd, myApp):
        wx.Frame.__init__(self, parent, id, title, name="Trelby")

        if misc.isUnix:
            # automatically reaps zombies
            signal.signal(signal.SIGCHLD, signal.SIG_IGN)

        self.clipboard = None
        self.showFormatting = False
        self.gd = gd
        self.myApp = myApp

        self.SetSizeHints(gd.cvars.getMin("width"), gd.cvars.getMin("height"))

        self.Move(gd.posX, gd.posY)
        self.SetSize(wx.Size(gd.width, gd.height))

        util.removeTempFiles(misc.tmpPrefix)

        self.mySetIcons()
        self.applyModernWindowStyle()
        # self.allocIds()

        fileMenu = wx.Menu()
        fileMenu.Append(ID_FILE_NEW, _("New") + "\tCTRL-N")
        fileMenu.Append(ID_FILE_OPEN, _("Open") + "...\tCTRL-O")
        fileMenu.Append(ID_FILE_SAVE, _("Save") + "\tCTRL-S")
        fileMenu.Append(ID_FILE_SAVE_AS, _("Save As") + "...")
        fileMenu.Append(ID_FILE_CLOSE, _("Close\tCTRL-W"))
        fileMenu.Append(ID_FILE_REVERT, _("Revert"))
        fileMenu.AppendSeparator()
        fileMenu.Append(ID_FILE_IMPORT, _("Import") + "...")
        fileMenu.Append(ID_FILE_EXPORT, _("Export") + "...")
        fileMenu.AppendSeparator()
        fileMenu.Append(ID_FILE_PRINT, _("Print (via PDF)") + "\tCTRL-P")
        fileMenu.AppendSeparator()

        tmp = wx.Menu()

        tmp.Append(ID_SETTINGS_CHANGE, _("Change") + "...")
        tmp.AppendSeparator()
        tmp.Append(ID_SETTINGS_LOAD, _("Load") + "...")
        tmp.Append(ID_SETTINGS_SAVE_AS, _("Save as") + "...")
        tmp.AppendSeparator()
        tmp.Append(ID_SETTINGS_SC_DICT, _("Spell checker dictionary") + "...")
        settingsMenu = tmp

        fileMenu.Append(ID_FILE_SETTINGS, _("Settings"), tmp)

        fileMenu.AppendSeparator()
        # "most recently used" list comes in here
        fileMenu.AppendSeparator()
        fileMenu.Append(ID_FILE_EXIT, _("Exit") + "\tCTRL-Q")

        editMenu = wx.Menu()
        editMenu.Append(ID_EDIT_UNDO, _("Undo") + "\tCTRL-Z")
        editMenu.Append(ID_EDIT_REDO, _("Redo") + "\tCTRL-Y")
        editMenu.AppendSeparator()
        editMenu.Append(ID_EDIT_CUT, _("Cut") + "\tCTRL-X")
        editMenu.Append(ID_EDIT_COPY, _("Copy") + "\tCTRL-C")
        editMenu.Append(ID_EDIT_PASTE, _("Paste") + "\tCTRL-V")
        editMenu.AppendSeparator()
        editMenu.Append(ID_EDIT_FORMAT_BOLD, _("Bold") + "\tCTRL-B")
        editMenu.Append(ID_EDIT_FORMAT_ITALIC, _("Italic") + "\tALT-I")
        editMenu.Append(ID_EDIT_FORMAT_UNDERLINE, _("Underline") + "\tCTRL-U")
        editMenu.AppendSeparator()

        tmp = wx.Menu()
        tmp.Append(ID_EDIT_COPY_TO_CB, _("Unformatted"))
        tmp.Append(ID_EDIT_COPY_TO_CB_FMT, _("Formatted"))

        editMenu.Append(ID_EDIT_COPY_SYSTEM, _("Copy (system)"), tmp)
        editMenu.Append(ID_EDIT_PASTE_FROM_CB, _("Paste (system)"))
        editMenu.AppendSeparator()
        editMenu.Append(ID_EDIT_SELECT_SCENE, _("Select scene"))
        editMenu.Append(ID_EDIT_SELECT_ALL, _("Select all"))
        editMenu.Append(ID_EDIT_GOTO_PAGE, _("Goto page") + "...\tCTRL-G")
        editMenu.Append(ID_EDIT_GOTO_SCENE, _("Goto scene") + "...\tALT-G")
        editMenu.AppendSeparator()
        editMenu.Append(ID_EDIT_INSERT_NBSP, _("Insert non-breaking space"))
        editMenu.AppendSeparator()
        editMenu.Append(ID_EDIT_FIND, _("Find && Replace") + "...\tCTRL-F")
        editMenu.AppendSeparator()
        editMenu.Append(ID_EDIT_DELETE_ELEMENTS, _("Delete elements") + "...")

        viewMenu = wx.Menu()
        viewMenu.AppendRadioItem(ID_VIEW_STYLE_DRAFT, _("Draft"))
        viewMenu.AppendRadioItem(ID_VIEW_STYLE_LAYOUT, _("Layout"))
        viewMenu.AppendRadioItem(
            ID_VIEW_STYLE_SIDE_BY_SIDE, _("Side by side")
        )
        viewMenu.AppendCheckItem(ID_SHOW_HIDE_TOOLBAR, _("Show/Hide Toolbar"))
        themeMenu = wx.Menu()
        themeMenu.AppendRadioItem(ID_VIEW_THEME_LIGHT, _("Light"))
        themeMenu.AppendRadioItem(ID_VIEW_THEME_DARK, _("Dark"))
        themeMenu.AppendRadioItem(ID_VIEW_THEME_SYSTEM, _("System"))
        themeMenu.AppendRadioItem(ID_VIEW_THEME_SEPIA, _("Sepia"))
        themeMenu.AppendRadioItem(ID_VIEW_THEME_GRAPHITE, _("Graphite"))
        themeMenu.AppendRadioItem(ID_VIEW_THEME_MIDNIGHT, _("Midnight"))
        themeMenu.AppendRadioItem(ID_VIEW_THEME_SOLAR_LIGHT, _("Solarized light"))
        themeMenu.AppendRadioItem(ID_VIEW_THEME_SOLAR_DARK, _("Solarized dark"))
        themeMenu.AppendRadioItem(ID_VIEW_THEME_FOREST, _("Forest"))
        themeMenu.AppendRadioItem(ID_VIEW_THEME_ROSE, _("Rose"))
        themeMenu.AppendRadioItem(ID_VIEW_THEME_HIGH_CONTRAST, _("High contrast"))
        themeMenu.AppendRadioItem(ID_VIEW_THEME_PAPER, _("Paper"))
        viewMenu.AppendSubMenu(themeMenu, _("Theme"))
        scaleMenu = wx.Menu()
        self.displayScaleMenuItems = [
            (ID_VIEW_SCALE_75, 75, _("75%")),
            (ID_VIEW_SCALE_100, 100, _("100%")),
            (ID_VIEW_SCALE_110, 110, _("110%")),
            (ID_VIEW_SCALE_125, 125, _("125%")),
            (ID_VIEW_SCALE_135, 135, _("135%")),
            (ID_VIEW_SCALE_150, 150, _("150%")),
            (ID_VIEW_SCALE_160, 160, _("160%")),
            (ID_VIEW_SCALE_175, 175, _("175%")),
            (ID_VIEW_SCALE_200, 200, _("200%")),
        ]
        for itemId, scaleValue, label in self.displayScaleMenuItems:
            scaleMenu.AppendRadioItem(itemId, label)
        viewMenu.AppendSubMenu(scaleMenu, _("Display scale"))

        if gd.viewMode == gd.VIEWMODE_DRAFT:
            viewMenu.Check(ID_VIEW_STYLE_DRAFT, True)
        elif gd.viewMode == gd.VIEWMODE_LAYOUT:
            viewMenu.Check(ID_VIEW_STYLE_LAYOUT, True)
        else:
            viewMenu.Check(ID_VIEW_STYLE_SIDE_BY_SIDE, True)

        if gd.cfgGl.pageThemeMode == config.THEME_LIGHT:
            themeMenu.Check(ID_VIEW_THEME_LIGHT, True)
        elif gd.cfgGl.pageThemeMode == config.THEME_DARK:
            themeMenu.Check(ID_VIEW_THEME_DARK, True)
        elif gd.cfgGl.pageThemeMode == config.THEME_SEPIA:
            themeMenu.Check(ID_VIEW_THEME_SEPIA, True)
        elif gd.cfgGl.pageThemeMode == config.THEME_GRAPHITE:
            themeMenu.Check(ID_VIEW_THEME_GRAPHITE, True)
        elif gd.cfgGl.pageThemeMode == config.THEME_MIDNIGHT:
            themeMenu.Check(ID_VIEW_THEME_MIDNIGHT, True)
        elif gd.cfgGl.pageThemeMode == config.THEME_SOLAR_LIGHT:
            themeMenu.Check(ID_VIEW_THEME_SOLAR_LIGHT, True)
        elif gd.cfgGl.pageThemeMode == config.THEME_SOLAR_DARK:
            themeMenu.Check(ID_VIEW_THEME_SOLAR_DARK, True)
        elif gd.cfgGl.pageThemeMode == config.THEME_FOREST:
            themeMenu.Check(ID_VIEW_THEME_FOREST, True)
        elif gd.cfgGl.pageThemeMode == config.THEME_ROSE:
            themeMenu.Check(ID_VIEW_THEME_ROSE, True)
        elif gd.cfgGl.pageThemeMode == config.THEME_HIGH_CONTRAST:
            themeMenu.Check(ID_VIEW_THEME_HIGH_CONTRAST, True)
        elif gd.cfgGl.pageThemeMode == config.THEME_PAPER:
            themeMenu.Check(ID_VIEW_THEME_PAPER, True)
        else:
            themeMenu.Check(ID_VIEW_THEME_SYSTEM, True)

        try:
            currentScale = int(gd.cfgGl.displayScale)
        except (TypeError, ValueError):
            currentScale = 200

        bestScaleItem = min(
            self.displayScaleMenuItems, key=lambda item: abs(item[1] - currentScale)
        )
        scaleMenu.Check(bestScaleItem[0], True)

        viewMenu.AppendSeparator()
        viewMenu.AppendCheckItem(
            ID_VIEW_SHOW_FORMATTING, _("Show formatting")
        )
        viewMenu.Append(ID_VIEW_FULL_SCREEN, _("Fullscreen") + "\tF11")

        scriptMenu = wx.Menu()
        scriptMenu.Append(ID_SCRIPT_FIND_ERROR, _("Find next error"))
        scriptMenu.Append(ID_SCRIPT_PAGINATE, _("Paginate"))
        scriptMenu.AppendSeparator()
        scriptMenu.Append(
            ID_SCRIPT_AUTO_COMPLETION, _("Auto-completion") + "..."
        )
        scriptMenu.Append(ID_SCRIPT_HEADERS, _("Headers") + "...")
        scriptMenu.Append(ID_SCRIPT_LOCATIONS, _("Locations") + "...")
        scriptMenu.Append(ID_SCRIPT_TITLES, _("Title pages") + "...")
        scriptMenu.Append(ID_SCRIPT_SC_DICT, _("Spell checker dictionary..."))
        scriptMenu.AppendSeparator()

        tmp = wx.Menu()

        tmp.Append(ID_SCRIPT_SETTINGS_CHANGE, _("Change") + "...")
        tmp.AppendSeparator()
        tmp.Append(ID_SCRIPT_SETTINGS_LOAD, _("Load") + "...")
        tmp.Append(ID_SCRIPT_SETTINGS_SAVE_AS, _("Save as") + "...")
        scriptMenu.Append(ID_SCRIPT_SETTINGS, _("Settings"), tmp)
        scriptSettingsMenu = tmp

        reportsMenu = wx.Menu()
        reportsMenu.Append(ID_REPORTS_SCRIPT_REP, _("Script report"))
        reportsMenu.Append(
            ID_REPORTS_LOCATION_REP, _("Location report") + "..."
        )
        reportsMenu.Append(ID_REPORTS_SCENE_REP, _("Scene report") + "...")
        reportsMenu.Append(
            ID_REPORTS_CHARACTER_REP, _("Character report") + "..."
        )
        reportsMenu.Append(
            ID_REPORTS_DIALOGUE_CHART, _("Dialogue chart") + "..."
        )

        toolsMenu = wx.Menu()
        toolsMenu.Append(ID_TOOLS_SPELL_CHECK, _("Spell checker") + "...")
        toolsMenu.Append(ID_TOOLS_NAME_DB, _("Name database") + "...")
        toolsMenu.Append(ID_TOOLS_CHARMAP, _("Character map") + "...")
        toolsMenu.Append(
            ID_TOOLS_COMPARE_SCRIPTS, _("Compare scripts") + "..."
        )
        toolsMenu.Append(
            ID_TOOLS_WATERMARK, _("Generate watermarked PDFs") + "..."
        )

        helpMenu = wx.Menu()
        helpMenu.Append(ID_HELP_COMMANDS, _("Commands") + "...")
        helpMenu.Append(ID_HELP_MANUAL, _("Manual"))
        helpMenu.AppendSeparator()
        helpMenu.Append(ID_HELP_ABOUT, _("About") + "...")

        self.menuBar = wx.MenuBar()
        self.menuBar.Append(fileMenu, _("File"))
        self.menuBar.Append(editMenu, _("Edit"))
        self.menuBar.Append(viewMenu, _("View"))
        self.menuBar.Append(scriptMenu, _("Script"))
        self.menuBar.Append(reportsMenu, _("Reports"))
        self.menuBar.Append(toolsMenu, _("Tools"))
        self.menuBar.Append(helpMenu, _("Help"))
        self.SetMenuBar(self.menuBar)

        if misc.isMac:
            self.applyMacMenuConventions()

        tbStyle = wx.TB_VERTICAL
        iconSize = wx.Size(32, 32)
        if misc.isMac:
            tbStyle = wx.TB_HORIZONTAL | wx.TB_FLAT | wx.TB_NODIVIDER
            iconSize = wx.Size(20, 20)

        self.toolBar = self.CreateToolBar(tbStyle)
        self.toolBar.SetToolBitmapSize(iconSize)
        self.toolBar.SetBackgroundColour(gd.cfgGui.tabBarBgColor)
        if misc.isMac and hasattr(self.toolBar, "SetMargins"):
            self.toolBar.SetMargins((8, 6))
            self.toolBar.SetToolPacking(8)

        def addTB(id, iconFilename, toolTip):
            filepath = misc.getFullPath(("trelby/resources/%s" % iconFilename))

            # neat hack to change the color of the SVG
            with open(filepath, "r") as svg_file:
                svg_content = svg_file.read()

            if wx.SystemSettings.GetAppearance().IsDark():
                svg_content = svg_content.replace("fill:#000000", "fill:#CCCCCC")
            else:
                # Use a softer gray for light mode instead of harsh black
                svg_content = svg_content.replace("fill:#000000", "fill:#444444")
            svg_content = svg_content.encode()

            # svg_image = wx.svg.SVGimage.CreateFromBytes(svg_content)
            bitmap = wx.BitmapBundle.FromSVG(svg_content, iconSize)

            self.toolBar.AddTool(
                id,
                "",
                bitmap,
                shortHelp=toolTip,
            )

        addTB(ID_FILE_NEW, "new.svg", _("New script"))
        addTB(ID_FILE_OPEN, "open.svg", _("Open Script") + "..")
        addTB(ID_FILE_SAVE, "save.svg", _("Save") + "..")
        addTB(ID_FILE_SAVE_AS, "saveas.svg", _("Save as") + "..")
        addTB(ID_FILE_CLOSE, "close.svg", _("Close Script"))
        addTB(ID_TOOLBAR_SCRIPTSETTINGS, "scrset.svg", _("Script settings"))
        addTB(ID_FILE_PRINT, "pdf.svg", _("Print (via PDF)"))

        self.toolBar.AddSeparator()

        addTB(ID_FILE_IMPORT, "import.svg", _("Import a text script"))
        addTB(ID_FILE_EXPORT, "export.svg", _("Export script"))

        self.toolBar.AddSeparator()

        addTB(ID_EDIT_UNDO, "undo.svg", _("Undo"))
        addTB(ID_EDIT_REDO, "redo.svg", _("Redo"))

        self.toolBar.AddSeparator()

        addTB(ID_EDIT_FIND, "find.svg", _("Find / Replace"))
        addTB(ID_TOOLBAR_VIEWS, "view.svg", _("View mode"))
        addTB(ID_TOOLBAR_REPORTS, "report.svg", _("Script reports"))
        addTB(ID_TOOLBAR_TOOLS, "tools.svg", _("Tools"))
        addTB(ID_TOOLBAR_SETTINGS, "settings.svg", _("Global settings"))

        self.toolBar.Realize()

        self.Bind(wx.EVT_MOVE, self.OnMove)
        self.Bind(wx.EVT_SIZE, self.OnSize)

        rootSizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(rootSizer)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.noFSBtn = misc.MyFSButton(self, -1, self.getCfgGui)
        self.noFSBtn.SetToolTip(_("Exit fullscreen"))
        self.noFSBtn.Show(False)
        hsizer.Add(self.noFSBtn)

        self.Bind(wx.EVT_BUTTON, self.ToggleFullscreen, id=self.noFSBtn.GetId())

        self.tabCtrl = misc.MyTabCtrl(self, -1, self.getCfgGui)
        hsizer.Add(self.tabCtrl, 1, wx.EXPAND)

        self.statusCtrl = misc.MyStatus(self, -1, self.getCfgGui)
        hsizer.Add(self.statusCtrl)

        if misc.isMac:
            rootSizer.Add(hsizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
        else:
            rootSizer.Add(hsizer, 0, wx.EXPAND)

        tmp = misc.MyTabCtrl2(self, -1, self.tabCtrl)
        if misc.isMac:
            rootSizer.Add(tmp, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        else:
            rootSizer.Add(tmp, 1, wx.EXPAND)

        if misc.isMac:
            rootSizer.Add(
                wx.StaticLine(self, -1), 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8
            )
        else:
            rootSizer.Add(wx.StaticLine(self, -1), 0, wx.EXPAND)

        gd.mru.useMenu(fileMenu, 14)

        self.Bind(wx.EVT_MENU_HIGHLIGHT_ALL, self.OnMenuHighlight)

        self.tabCtrl.setPageChangedFunc(self.OnPageChange)

        # see OnRightDown
        self.rightClickMenu = wx.Menu()
        self.rightClickMenuWithCut = wx.Menu()

        for m in (self.rightClickMenu, self.rightClickMenuWithCut):
            tmp = wx.Menu()

            tmp.Append(ID_ELEM_TO_SCENE, _("Scene"))
            tmp.Append(ID_ELEM_TO_ACTION, _("Action"))
            tmp.Append(ID_ELEM_TO_CHARACTER, _("Character"))
            tmp.Append(ID_ELEM_TO_PAREN, _("Parenthetical"))
            tmp.Append(ID_ELEM_TO_DIALOGUE, _("Dialogue"))
            tmp.Append(ID_ELEM_TO_TRANSITION, _("Transition"))
            tmp.Append(ID_ELEM_TO_SHOT, _("Shot"))
            tmp.Append(ID_ELEM_TO_ACTBREAK, _("Act break"))
            tmp.Append(ID_ELEM_TO_NOTE, _("Note"))

            m.AppendSubMenu(tmp, _("Element type"))
            m.AppendSeparator()

            if m is self.rightClickMenuWithCut:
                m.Append(ID_EDIT_CUT, _("Cut"))
                m.Append(ID_EDIT_COPY, _("Copy"))

            m.Append(ID_EDIT_PASTE, _("Paste"))

            self.Bind(wx.EVT_MENU, self.OnNewScript, id=ID_FILE_NEW)
            self.Bind(wx.EVT_MENU, self.OnOpen, id=ID_FILE_OPEN)
            self.Bind(wx.EVT_MENU, self.OnSave, id=ID_FILE_SAVE)
            self.Bind(wx.EVT_MENU, self.OnSaveScriptAs, id=ID_FILE_SAVE_AS)
            self.Bind(wx.EVT_MENU, self.OnImportScript, id=ID_FILE_IMPORT)
            self.Bind(wx.EVT_MENU, self.OnExportScript, id=ID_FILE_EXPORT)
            self.Bind(wx.EVT_MENU, self.OnCloseScript, id=ID_FILE_CLOSE)
            self.Bind(wx.EVT_MENU, self.OnRevertScript, id=ID_FILE_REVERT)
            self.Bind(wx.EVT_MENU, self.OnPrint, id=ID_FILE_PRINT)
            self.Bind(wx.EVT_MENU, self.OnSettings, id=ID_SETTINGS_CHANGE)
            self.Bind(wx.EVT_MENU, self.OnLoadSettings, id=ID_SETTINGS_LOAD)
            self.Bind(wx.EVT_MENU, self.OnSaveSettingsAs, id=ID_SETTINGS_SAVE_AS)
            self.Bind(
                wx.EVT_MENU, self.OnSpellCheckerDictionaryDlg, id=ID_SETTINGS_SC_DICT
            )
            self.Bind(wx.EVT_MENU, self.OnExit, id=ID_FILE_EXIT)
            self.Bind(wx.EVT_MENU, self.OnUndo, id=ID_EDIT_UNDO)
            self.Bind(wx.EVT_MENU, self.OnRedo, id=ID_EDIT_REDO)
            self.Bind(wx.EVT_MENU, self.OnCut, id=ID_EDIT_CUT)
            self.Bind(wx.EVT_MENU, self.OnCopy, id=ID_EDIT_COPY)
            self.Bind(wx.EVT_MENU, self.OnPaste, id=ID_EDIT_PASTE)
            self.Bind(wx.EVT_MENU, self.OnFormatBold, id=ID_EDIT_FORMAT_BOLD)
            self.Bind(wx.EVT_MENU, self.OnFormatItalic, id=ID_EDIT_FORMAT_ITALIC)
            self.Bind(wx.EVT_MENU, self.OnFormatUnderline, id=ID_EDIT_FORMAT_UNDERLINE)
            self.Bind(wx.EVT_MENU, self.OnCopySystemCb, id=ID_EDIT_COPY_TO_CB)
            self.Bind(
                wx.EVT_MENU, self.OnCopySystemCbFormatted, id=ID_EDIT_COPY_TO_CB_FMT
            )
            self.Bind(wx.EVT_MENU, self.OnPasteSystemCb, id=ID_EDIT_PASTE_FROM_CB)
            self.Bind(wx.EVT_MENU, self.OnSelectScene, id=ID_EDIT_SELECT_SCENE)
            self.Bind(wx.EVT_MENU, self.OnSelectAll, id=ID_EDIT_SELECT_ALL)
            self.Bind(wx.EVT_MENU, self.OnGotoPage, id=ID_EDIT_GOTO_PAGE)
            self.Bind(wx.EVT_MENU, self.OnGotoScene, id=ID_EDIT_GOTO_SCENE)
            self.Bind(wx.EVT_MENU, self.OnInsertNbsp, id=ID_EDIT_INSERT_NBSP)
            self.Bind(wx.EVT_MENU, self.OnFind, id=ID_EDIT_FIND)
            self.Bind(wx.EVT_MENU, self.OnDeleteElements, id=ID_EDIT_DELETE_ELEMENTS)
            self.Bind(wx.EVT_MENU, self.OnViewModeChange, id=ID_VIEW_STYLE_DRAFT)
            self.Bind(wx.EVT_MENU, self.ShowHideToolbar, id=ID_SHOW_HIDE_TOOLBAR)
            self.Bind(wx.EVT_MENU, self.OnViewModeChange, id=ID_VIEW_STYLE_LAYOUT)
            self.Bind(wx.EVT_MENU, self.OnViewModeChange, id=ID_VIEW_STYLE_SIDE_BY_SIDE)
            self.Bind(wx.EVT_MENU, self.OnThemeModeChange, id=ID_VIEW_THEME_LIGHT)
            self.Bind(wx.EVT_MENU, self.OnThemeModeChange, id=ID_VIEW_THEME_DARK)
            self.Bind(wx.EVT_MENU, self.OnThemeModeChange, id=ID_VIEW_THEME_SYSTEM)
            self.Bind(wx.EVT_MENU, self.OnThemeModeChange, id=ID_VIEW_THEME_SEPIA)
            self.Bind(wx.EVT_MENU, self.OnThemeModeChange, id=ID_VIEW_THEME_GRAPHITE)
            self.Bind(wx.EVT_MENU, self.OnThemeModeChange, id=ID_VIEW_THEME_MIDNIGHT)
            self.Bind(
                wx.EVT_MENU, self.OnThemeModeChange, id=ID_VIEW_THEME_SOLAR_LIGHT
            )
            self.Bind(
                wx.EVT_MENU, self.OnThemeModeChange, id=ID_VIEW_THEME_SOLAR_DARK
            )
            self.Bind(wx.EVT_MENU, self.OnThemeModeChange, id=ID_VIEW_THEME_FOREST)
            self.Bind(wx.EVT_MENU, self.OnThemeModeChange, id=ID_VIEW_THEME_ROSE)
            self.Bind(
                wx.EVT_MENU, self.OnThemeModeChange, id=ID_VIEW_THEME_HIGH_CONTRAST
            )
            self.Bind(wx.EVT_MENU, self.OnThemeModeChange, id=ID_VIEW_THEME_PAPER)
            for itemId, scaleValue, label in self.displayScaleMenuItems:
                self.Bind(wx.EVT_MENU, self.OnDisplayScaleChange, id=itemId)
            self.Bind(wx.EVT_MENU, self.OnShowFormatting, id=ID_VIEW_SHOW_FORMATTING)
            self.Bind(wx.EVT_MENU, self.ToggleFullscreen, id=ID_VIEW_FULL_SCREEN)
            self.Bind(wx.EVT_MENU, self.OnFindNextError, id=ID_SCRIPT_FIND_ERROR)
            self.Bind(wx.EVT_MENU, self.OnPaginate, id=ID_SCRIPT_PAGINATE)
            self.Bind(
                wx.EVT_MENU, self.OnAutoCompletionDlg, id=ID_SCRIPT_AUTO_COMPLETION
            )
            self.Bind(wx.EVT_MENU, self.OnHeadersDlg, id=ID_SCRIPT_HEADERS)
            self.Bind(wx.EVT_MENU, self.OnLocationsDlg, id=ID_SCRIPT_LOCATIONS)
            self.Bind(wx.EVT_MENU, self.OnTitlesDlg, id=ID_SCRIPT_TITLES)
            self.Bind(
                wx.EVT_MENU,
                self.OnSpellCheckerScriptDictionaryDlg,
                id=ID_SCRIPT_SC_DICT,
            )
            self.Bind(wx.EVT_MENU, self.OnScriptSettings, id=ID_SCRIPT_SETTINGS_CHANGE)
            self.Bind(
                wx.EVT_MENU, self.OnLoadScriptSettings, id=ID_SCRIPT_SETTINGS_LOAD
            )
            self.Bind(
                wx.EVT_MENU, self.OnSaveScriptSettingsAs, id=ID_SCRIPT_SETTINGS_SAVE_AS
            )
            self.Bind(
                wx.EVT_MENU, self.OnReportDialogueChart, id=ID_REPORTS_DIALOGUE_CHART
            )
            self.Bind(wx.EVT_MENU, self.OnReportCharacter, id=ID_REPORTS_CHARACTER_REP)
            self.Bind(wx.EVT_MENU, self.OnReportScript, id=ID_REPORTS_SCRIPT_REP)
            self.Bind(wx.EVT_MENU, self.OnReportLocation, id=ID_REPORTS_LOCATION_REP)
            self.Bind(wx.EVT_MENU, self.OnReportScene, id=ID_REPORTS_SCENE_REP)
            self.Bind(wx.EVT_MENU, self.OnSpellCheckerDlg, id=ID_TOOLS_SPELL_CHECK)
            self.Bind(wx.EVT_MENU, self.OnNameDatabase, id=ID_TOOLS_NAME_DB)
            self.Bind(wx.EVT_MENU, self.OnCharacterMap, id=ID_TOOLS_CHARMAP)
            self.Bind(wx.EVT_MENU, self.OnCompareScripts, id=ID_TOOLS_COMPARE_SCRIPTS)
            self.Bind(wx.EVT_MENU, self.OnWatermark, id=ID_TOOLS_WATERMARK)
            self.Bind(wx.EVT_MENU, self.OnHelpCommands, id=ID_HELP_COMMANDS)
            self.Bind(wx.EVT_MENU, self.OnHelpManual, id=ID_HELP_MANUAL)
            self.Bind(wx.EVT_MENU, self.OnAbout, id=ID_HELP_ABOUT)

        self.Bind(
            wx.EVT_MENU_RANGE,
            self.OnMRUFile,
            id=gd.mru.getIds()[0],
            id2=gd.mru.getIds()[1],
        )

        self.Bind(
            wx.EVT_MENU_RANGE,
            self.OnChangeType,
            id=ID_ELEM_TO_ACTION,
            id2=ID_ELEM_TO_TRANSITION,
        )

        def addTBMenu(id, menu):
            self.Bind(wx.EVT_MENU, partial(self.OnToolBarMenu, menu=menu), id=id)

        addTBMenu(ID_TOOLBAR_SETTINGS, settingsMenu)
        addTBMenu(ID_TOOLBAR_SCRIPTSETTINGS, scriptSettingsMenu)
        addTBMenu(ID_TOOLBAR_REPORTS, reportsMenu)
        addTBMenu(ID_TOOLBAR_VIEWS, viewMenu)
        addTBMenu(ID_TOOLBAR_TOOLS, toolsMenu)

        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)
        self.Bind(wx.EVT_SET_FOCUS, self.OnFocus)

        self.Layout()

    def applyModernWindowStyle(self):
        if not misc.isMac:
            return

        uiFont = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        if uiFont.IsOk():
            uiFont.SetPointSize(max(uiFont.GetPointSize(), 13))
            self.SetFont(uiFont)

        self.SetBackgroundColour(self.gd.cfgGui.workspaceColor)

    @staticmethod
    def stripMacMenuMnemonic(label):
        base, sep, accel = label.partition("\t")

        base = re.sub(r"^\(&.\)\s*", "", base)
        base = re.sub(r"^\(.\)\s*", "", base)

        if sep:
            return base + "\t" + accel
        else:
            return base

    def applyMacMenuConventionsToMenu(self, menu):
        for item in menu.GetMenuItems():
            if item.IsSeparator():
                continue

            item.SetItemLabel(self.stripMacMenuMnemonic(item.GetItemLabel()))

            subMenu = item.GetSubMenu()
            if subMenu:
                self.applyMacMenuConventionsToMenu(subMenu)

    def applyMacMenuConventions(self):
        if not misc.isMac:
            return

        for i in range(self.menuBar.GetMenuCount()):
            menuLabel = self.menuBar.GetMenuLabel(i)
            self.menuBar.SetMenuLabel(i, self.stripMacMenuMnemonic(menuLabel))
            self.applyMacMenuConventionsToMenu(self.menuBar.GetMenu(i))

    def init(self):
        self.updateKbdCommands()
        self.panel = self.createNewPanel()

    def mySetIcons(self):
        if not wx.Image.FindHandler(wx.BITMAP_TYPE_PNG):
            wx.Image.AddHandler(wx.PNGHandler())

        ib = wx.IconBundle()

        for sz in ("16", "32", "64", "128", "256"):
            ib.AddIcon(wx.Icon(misc.getBitmap("trelby/resources/icon%s.png" % sz)))

        self.SetIcons(ib)

    # def allocIds(self):

    #     g = globals()

    #     # see OnChangeType
    #     g["idToLTMap"] = {
    #         ID_ELEM_TO_SCENE: screenplay.SCENE,
    #         ID_ELEM_TO_ACTION: screenplay.ACTION,
    #         ID_ELEM_TO_CHARACTER: screenplay.CHARACTER,
    #         ID_ELEM_TO_DIALOGUE: screenplay.DIALOGUE,
    #         ID_ELEM_TO_PAREN: screenplay.PAREN,
    #         ID_ELEM_TO_TRANSITION: screenplay.TRANSITION,
    #         ID_ELEM_TO_SHOT: screenplay.SHOT,
    #         ID_ELEM_TO_ACTBREAK: screenplay.ACTBREAK,
    #         ID_ELEM_TO_NOTE: screenplay.NOTE,
    #     }

    def createNewPanel(self):
        newPanel = MyPanel(self.tabCtrl.getTabParent(), -1, self.gd)
        self.tabCtrl.addPage(newPanel, "")
        newPanel.ctrl.setTabText()
        newPanel.ctrl.SetFocus()

        return newPanel

    def setTitle(self, text):
        self.SetTitle("Trelby - %s" % text)

    def setTabText(self, panel, text):
        i = self.findPage(panel)

        if i != -1:
            # strip out ".trelby" suffix from tab names (it's a bit
            # complicated since if we open the same file multiple times,
            # we have e.g. "foo.trelby" and "foo.trelby<2>", so actually
            # we just strip out ".trelby" if it's found anywhere in the
            # string)

            s = text.replace(".trelby", "")
            self.tabCtrl.setTabText(i, s)

    # iterates over all tabs and finds out the corresponding page number
    # for the given panel.
    def findPage(self, panel):
        for i in range(self.tabCtrl.getPageCount()):
            p = self.tabCtrl.getPage(i)
            if p == panel:
                return i

        return -1

    # get list of MyCtrl objects for all open scripts
    def getCtrls(self):
        l = []

        for i in range(self.tabCtrl.getPageCount()):
            l.append(self.tabCtrl.getPage(i).ctrl)

        return l

    # returns True if any open script has been modified
    def isModifications(self):
        for c in self.getCtrls():
            if c.sp.isModified():
                return True

        return False

    def updateKbdCommands(self):
        self.gd.cfgGl.addShiftKeys()

        if self.gd.cfgGl.getConflictingKeys() != None:
            wx.MessageBox(
                _(
                    "You have at least one key bound to more than one\ncommand. The program will not work correctly until\nyou fix this."
                ),
                _("Warning"),
                wx.OK,
                self,
            )

        self.kbdCommands = {}

        for cmd in self.gd.cfgGl.commands:
            if not (cmd.isFixed and cmd.isMenu):
                for key in cmd.keys:
                    self.kbdCommands[key] = cmd

    # open script, in the current tab if it's untouched, or in a new one
    # otherwise
    def openScript(self, filename):
        if not self.tabCtrl.getPage(self.findPage(self.panel)).ctrl.isUntouched():
            self.panel = self.createNewPanel()

        self.panel.ctrl.loadFile(filename)
        self.panel.ctrl.updateScreen()
        self.gd.mru.add(filename)

    def checkFonts(self):
        names = ["Normal", "Bold", "Italic", "Bold-Italic"]
        failed = []

        for i, fi in enumerate(self.gd.cfgGui.fonts):
            if not util.isFixedWidth(fi.font):
                failed.append(names[i])

        if failed:
            wx.MessageBox(
                _(
                    "The fonts listed below are not fixed width and\nwill cause the program not to function correctly.\nPlease change the fonts at File/Settings/Change.\n\n\n"
                ).join(failed),
                _("Error"),
                wx.OK,
                self,
            )

    # If we get focus, pass it on to ctrl.
    def OnFocus(self, event):
        self.panel.ctrl.SetFocus()

    def OnMenuHighlight(self, event):
        # default implementation modifies status bar, so we need to
        # override it and do nothing
        pass

    def OnPageChange(self, page):
        self.panel = self.tabCtrl.getPage(page)
        self.panel.ctrl.SetFocus()
        self.panel.ctrl.updateCommon()
        self.setTitle(self.panel.ctrl.fileNameDisplay)

    def selectScript(self, toNext):
        current = self.tabCtrl.getSelectedPageIndex()
        pageCnt = self.tabCtrl.getPageCount()

        if toNext:
            pageNr = current + 1
        else:
            pageNr = current - 1

        if pageNr == -1:
            pageNr = pageCnt - 1
        elif pageNr == pageCnt:
            pageNr = 0

        if pageNr == current:
            # only one tab, nothing to do
            return

        self.tabCtrl.selectPage(pageNr)

    def OnScriptNext(self, event=None):
        self.selectScript(True)

    def OnScriptPrev(self, event=None):
        self.selectScript(False)

    def OnNewScript(self, event=None):
        self.panel = self.createNewPanel()

    def OnMRUFile(self, event):
        i = event.GetId() - self.gd.mru.getIds()[0]
        self.openScript(self.gd.mru.get(i))

    def OnOpen(self, event=None):
        dlg = wx.FileDialog(
            self,
            _("File to open"),
            misc.scriptDir,
            wildcard="Trelby "
            + _("files")
            + " (*.trelby)|*.trelby|"
            + _("All files")
            + "|*",
            style=wx.FD_OPEN,
        )

        if dlg.ShowModal() == wx.ID_OK:
            misc.scriptDir = dlg.GetDirectory()
            self.openScript(dlg.GetPath())

        dlg.Destroy()

    def OnSave(self, event=None):
        self.panel.ctrl.OnSave()

    def OnSaveScriptAs(self, event=None):
        self.panel.ctrl.OnSaveScriptAs()

    def OnImportScript(self, event=None):
        dlg = wx.FileDialog(
            self,
            _("File to import"),
            misc.scriptDir,
            wildcard=_("Importable")
            + " "
            + _("files")
            + "(*.txt;*.fdx;*.celtx;*.astx;*.fountain;*.fadein)|"
            + "*.fdx;*.txt;*.celtx;*.astx;*.fountain;*.fadein|"
            + _("Formatted")
            + " "
            + _("text")
            + " "
            + _("files")
            + "(*.txt)|*.txt|"
            + "Final Draft XML(*.fdx)|*.fdx|"
            + "Celtx "
            + _("files")
            + " (*.celtx)|*.celtx|"
            + "Adobe Story XML "
            + _("files")
            + " (*.astx)|*.astx|"
            + "Fountain "
            + _("files")
            + " (*.fountain)|*.fountain|"
            + "Fadein "
            + _("files")
            + " (*.fadein)|*.fadein|"
            + _("All files")
            + "|*",
            style=wx.FD_OPEN,
        )

        if dlg.ShowModal() == wx.ID_OK:
            misc.scriptDir = dlg.GetDirectory()

            if not self.tabCtrl.getPage(self.findPage(self.panel)).ctrl.isUntouched():
                self.panel = self.createNewPanel()

            self.panel.ctrl.importFile(dlg.GetPath())
            self.panel.ctrl.updateScreen()

        dlg.Destroy()

    def OnExportScript(self, event=None):
        self.panel.ctrl.OnExportScript()

    def OnCloseScript(self, event=None):
        if not self.panel.ctrl.canBeClosed():
            return

        if self.tabCtrl.getPageCount() > 1:
            self.tabCtrl.deletePage(self.tabCtrl.getSelectedPageIndex())
        else:
            self.panel.ctrl.createEmptySp()
            self.panel.ctrl.updateScreen()

    def OnRevertScript(self, event=None):
        self.panel.ctrl.OnRevertScript()

    def OnPrint(self, event=None):
        self.panel.ctrl.OnPrint()

    def OnSettings(self, event=None):
        self.panel.ctrl.OnSettings()

    def OnLoadSettings(self, event=None):
        dlg = wx.FileDialog(
            self,
            _("File to open"),
            defaultDir=os.path.dirname(self.gd.confFilename),
            defaultFile=os.path.basename(self.gd.confFilename),
            wildcard=_("Setting")
            + " "
            + _("files")
            + " (*.conf)|*.conf|"
            + _("All files")
            + "|*",
            style=wx.FD_OPEN,
        )

        if dlg.ShowModal() == wx.ID_OK:
            s = util.loadFile(dlg.GetPath(), self)

            if s:
                c = config.ConfigGlobal()
                c.load(s)
                self.gd.confFilename = dlg.GetPath()

                self.panel.ctrl.applyGlobalCfg(c, False)

        dlg.Destroy()

    def OnSaveSettingsAs(self, event=None):
        dlg = wx.FileDialog(
            self,
            _("Filename to save as"),
            defaultDir=os.path.dirname(self.gd.confFilename),
            defaultFile=os.path.basename(self.gd.confFilename),
            wildcard=_("Setting")
            + " "
            + _("files")
            + " (*.conf)|*.conf|"
            + _("All files")
            + "|*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )

        if dlg.ShowModal() == wx.ID_OK:
            if util.writeToFile(dlg.GetPath(), self.gd.cfgGl.save(), self):
                self.gd.confFilename = dlg.GetPath()

        dlg.Destroy()

    def OnUndo(self, event=None):
        self.panel.ctrl.OnUndo()

    def OnRedo(self, event=None):
        self.panel.ctrl.OnRedo()

    def OnCut(self, event=None):
        self.panel.ctrl.OnCut()

    def OnCopy(self, event=None):
        self.panel.ctrl.OnCopy()

    def OnCopySystemCb(self, event=None):
        self.panel.ctrl.OnCopySystem(formatted=False)

    def OnCopySystemCbFormatted(self, event=None):
        self.panel.ctrl.OnCopySystem(formatted=True)

    def OnPaste(self, event=None):
        self.panel.ctrl.OnPaste()

    def OnPasteSystemCb(self, event=None):
        self.panel.ctrl.OnPasteSystemCb()

    def OnFormatBold(self, event=None):
        self.panel.ctrl.OnFormatBold()

    def OnFormatItalic(self, event=None):
        self.panel.ctrl.OnFormatItalic()

    def OnFormatUnderline(self, event=None):
        self.panel.ctrl.OnFormatUnderline()

    def OnSelectScene(self, event=None):
        self.panel.ctrl.OnSelectScene()

    def OnSelectAll(self, event=None):
        self.panel.ctrl.OnSelectAll()

    def OnGotoPage(self, event=None):
        self.panel.ctrl.OnGotoPage()

    def OnGotoScene(self, event=None):
        self.panel.ctrl.OnGotoScene()

    def OnFindNextError(self, event=None):
        self.panel.ctrl.OnFindNextError()

    def OnFind(self, event=None):
        self.panel.ctrl.OnFind()

    def OnInsertNbsp(self, event=None):
        self.panel.ctrl.OnInsertNbsp()

    def OnDeleteElements(self, event=None):
        self.panel.ctrl.OnDeleteElements()

    def OnToggleShowFormatting(self, event=None):
        self.menuBar.Check(
            ID_VIEW_SHOW_FORMATTING, not self.menuBar.IsChecked(ID_VIEW_SHOW_FORMATTING)
        )
        self.showFormatting = not self.showFormatting
        self.panel.ctrl.Refresh(False)

    def OnShowFormatting(self, event=None):
        self.showFormatting = self.menuBar.IsChecked(ID_VIEW_SHOW_FORMATTING)
        self.panel.ctrl.Refresh(False)

    def OnViewModeDraft(self):
        self.menuBar.Check(ID_VIEW_STYLE_DRAFT, True)
        self.OnViewModeChange()

    def ShowHideToolbar(self, event=None):
        self.CheckToolbar = self.menuBar.IsChecked(ID_SHOW_HIDE_TOOLBAR)

        if self.CheckToolbar == True:
            self.toolBar.Hide()

        else:
            self.toolBar.Show()

    def OnViewModeLayout(self):
        self.menuBar.Check(ID_VIEW_STYLE_LAYOUT, True)
        self.OnViewModeChange()

    def OnViewModeSideBySide(self):
        self.menuBar.Check(ID_VIEW_STYLE_SIDE_BY_SIDE, True)
        self.OnViewModeChange()

    def OnViewModeChange(self, event=None):
        if self.menuBar.IsChecked(ID_VIEW_STYLE_DRAFT):
            mode = self.gd.VIEWMODE_DRAFT
        elif self.menuBar.IsChecked(ID_VIEW_STYLE_LAYOUT):
            mode = self.gd.VIEWMODE_LAYOUT
        else:
            mode = self.gd.VIEWMODE_SIDE_BY_SIDE

        self.gd.setViewMode(mode)

        for c in self.getCtrls():
            c.refreshCache()

        c = self.panel.ctrl
        c.makeLineVisible(c.sp.line)
        c.updateScreen()

    def OnThemeModeChange(self, event=None):
        if self.menuBar.IsChecked(ID_VIEW_THEME_LIGHT):
            self.gd.cfgGl.pageThemeMode = config.THEME_LIGHT
        elif self.menuBar.IsChecked(ID_VIEW_THEME_DARK):
            self.gd.cfgGl.pageThemeMode = config.THEME_DARK
        elif self.menuBar.IsChecked(ID_VIEW_THEME_SEPIA):
            self.gd.cfgGl.pageThemeMode = config.THEME_SEPIA
        elif self.menuBar.IsChecked(ID_VIEW_THEME_GRAPHITE):
            self.gd.cfgGl.pageThemeMode = config.THEME_GRAPHITE
        elif self.menuBar.IsChecked(ID_VIEW_THEME_MIDNIGHT):
            self.gd.cfgGl.pageThemeMode = config.THEME_MIDNIGHT
        elif self.menuBar.IsChecked(ID_VIEW_THEME_SOLAR_LIGHT):
            self.gd.cfgGl.pageThemeMode = config.THEME_SOLAR_LIGHT
        elif self.menuBar.IsChecked(ID_VIEW_THEME_SOLAR_DARK):
            self.gd.cfgGl.pageThemeMode = config.THEME_SOLAR_DARK
        elif self.menuBar.IsChecked(ID_VIEW_THEME_FOREST):
            self.gd.cfgGl.pageThemeMode = config.THEME_FOREST
        elif self.menuBar.IsChecked(ID_VIEW_THEME_ROSE):
            self.gd.cfgGl.pageThemeMode = config.THEME_ROSE
        elif self.menuBar.IsChecked(ID_VIEW_THEME_HIGH_CONTRAST):
            self.gd.cfgGl.pageThemeMode = config.THEME_HIGH_CONTRAST
        elif self.menuBar.IsChecked(ID_VIEW_THEME_PAPER):
            self.gd.cfgGl.pageThemeMode = config.THEME_PAPER
        else:
            self.gd.cfgGl.pageThemeMode = config.THEME_SYSTEM

        self.gd.cfgGui = config.ConfigGui(self.gd.cfgGl)

        for ctrl in self.getCtrls():
            ctrl.updateScreen()

        self.toolBar.SetBackgroundColour(self.gd.cfgGui.tabBarBgColor)
        self.SetBackgroundColour(self.gd.cfgGui.workspaceColor)
        self.tabCtrl.Refresh(False)
        self.statusCtrl.Refresh(False)
        self.noFSBtn.Refresh(False)
        self.toolBar.Refresh()
        self.Refresh(False)

        util.writeToFile(self.gd.confFilename, self.gd.cfgGl.save(), self)

    def OnDisplayScaleChange(self, event=None):
        for itemId, scale, label in self.displayScaleMenuItems:
            if self.menuBar.IsChecked(itemId):
                self.gd.cfgGl.displayScale = scale
                break

        self.gd.cfgGui = config.ConfigGui(self.gd.cfgGl)

        for ctrl in self.getCtrls():
            ctrl.refreshCache()
            ctrl.makeLineVisible(ctrl.sp.line)
            ctrl.adjustScrollBar()
            ctrl.updateScreen()

        self.toolBar.SetBackgroundColour(self.gd.cfgGui.tabBarBgColor)
        self.SetBackgroundColour(self.gd.cfgGui.workspaceColor)
        self.tabCtrl.Refresh(False)
        self.statusCtrl.Refresh(False)
        self.noFSBtn.Refresh(False)
        self.toolBar.Refresh()
        self.Refresh(False)

        util.writeToFile(self.gd.confFilename, self.gd.cfgGl.save(), self)

    def ToggleFullscreen(self, event=None):
        self.noFSBtn.Show(not self.IsFullScreen())

        flags = wx.FULLSCREEN_ALL
        if misc.isMac:
            flags &= ~wx.FULLSCREEN_NOMENUBAR

        self.ShowFullScreen(not self.IsFullScreen(), flags)
        self.panel.ctrl.SetFocus()

    def OnPaginate(self, event=None):
        self.panel.ctrl.OnPaginate()

    def OnAutoCompletionDlg(self, event=None):
        self.panel.ctrl.OnAutoCompletionDlg()

    def OnTitlesDlg(self, event=None):
        self.panel.ctrl.OnTitlesDlg()

    def OnHeadersDlg(self, event=None):
        self.panel.ctrl.OnHeadersDlg()

    def OnLocationsDlg(self, event=None):
        self.panel.ctrl.OnLocationsDlg()

    def OnSpellCheckerDictionaryDlg(self, event=None):
        dlg = spellcheckcfgdlg.SCDictDlg(self, copy.deepcopy(self.gd.scDict), True)

        if dlg.ShowModal() == wx.ID_OK:
            self.gd.scDict = dlg.scDict
            self.gd.saveScDict()

        dlg.Destroy()

    def OnSpellCheckerScriptDictionaryDlg(self, event=None):
        self.panel.ctrl.OnSpellCheckerScriptDictionaryDlg()

    def OnWatermark(self, event=None):
        self.panel.ctrl.OnWatermark()

    def OnScriptSettings(self, event=None):
        self.panel.ctrl.OnScriptSettings()

    def OnLoadScriptSettings(self, event=None):
        dlg = wx.FileDialog(
            self,
            _("File to open"),
            defaultDir=self.gd.scriptSettingsPath,
            wildcard=_("Script")
            + " "
            + _("setting")
            + " "
            + _("files")
            + " (*.sconf)|*.sconf|"
            + _("All files")
            + "|*",
            style=wx.FD_OPEN,
        )

        if dlg.ShowModal() == wx.ID_OK:
            s = util.loadFile(dlg.GetPath(), self)

            if s:
                cfg = config.Config()
                cfg.load(s)
                self.panel.ctrl.applyCfg(cfg)

                self.gd.scriptSettingsPath = os.path.dirname(dlg.GetPath())

        dlg.Destroy()

    def OnSaveScriptSettingsAs(self, event=None):
        dlg = wx.FileDialog(
            self,
            _("Filename to save as"),
            defaultDir=self.gd.scriptSettingsPath,
            wildcard=_("Script")
            + " "
            + _("setting")
            + _("files")
            + " (*.sconf)|*.sconf|"
            + _("All files")
            + "|*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )

        if dlg.ShowModal() == wx.ID_OK:
            if util.writeToFile(dlg.GetPath(), self.panel.ctrl.sp.saveCfg(), self):
                self.gd.scriptSettingsPath = os.path.dirname(dlg.GetPath())

        dlg.Destroy()

    def OnReportCharacter(self, event=None):
        self.panel.ctrl.OnReportCharacter()

    def OnReportDialogueChart(self, event=None):
        self.panel.ctrl.OnReportDialogueChart()

    def OnReportLocation(self, event=None):
        self.panel.ctrl.OnReportLocation()

    def OnReportScene(self, event=None):
        self.panel.ctrl.OnReportScene()

    def OnReportScript(self, event=None):
        self.panel.ctrl.OnReportScript()

    def OnSpellCheckerDlg(self, event=None):
        self.panel.ctrl.OnSpellCheckerDlg()

    def OnNameDatabase(self, event=None):
        if not namesdlg.readNames(self):
            wx.MessageBox(_("Error opening name database."), _("Error"), wx.OK, self)

            return

        dlg = namesdlg.NamesDlg(self, self.panel.ctrl)
        dlg.ShowModal()
        dlg.Destroy()

    def OnCharacterMap(self, event=None):
        dlg = charmapdlg.CharMapDlg(self, self.panel.ctrl)
        dlg.ShowModal()
        dlg.Destroy()

    def OnCompareScripts(self, event=None):
        self.panel.ctrl.OnCompareScripts()

    def OnChangeType(self, event):
        self.panel.ctrl.OnChangeType(event)

    def OnHelpCommands(self, event=None):
        dlg = commandsdlg.CommandsDlg(self.gd.cfgGl)
        dlg.Show()

    def OnHelpManual(self, event=None):
        webbrowser.open("file://" + misc.getFullPath("trelby/manual.html"))

    def OnAbout(self, event=None):
        win = splash.SplashWindow(self, -1)
        win.Show()

    def OnToolBarMenu(self, event, menu):
        self.PopupMenu(menu)

    def OnCloseWindow(self, event):
        doExit = True
        if event.CanVeto() and self.isModifications():
            close_msg_box = wx.MessageDialog(
                self,
                _("You have unsaved changes. Do\nyou want to save your changes?"),
                _("Save Changes"),
                wx.YES_NO | wx.CANCEL | wx.YES_DEFAULT,
            )
            close_msg_box.SetYesNoLabels(wx.ID_SAVE, _("Don't save"))
            response = close_msg_box.ShowModal()
            if response == wx.ID_YES:
                self.OnSave()
            elif response == wx.ID_CANCEL:
                doExit = False

        if doExit:
            util.writeToFile(self.gd.stateFilename, self.gd.save(), self)
            util.removeTempFiles(misc.tmpPrefix)
            self.Destroy()
            self.myApp.ExitMainLoop()
        else:
            event.Veto()

    def OnExit(self, event):
        self.Close(False)

    def OnMove(self, event):
        self.gd.posX, self.gd.posY = self.GetPosition()
        event.Skip()

    def OnSize(self, event):
        self.gd.width, self.gd.height = self.GetSize()
        event.Skip()

    def getCfgGui(self):
        return self.gd.cfgGui
