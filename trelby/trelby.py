# -*- coding: iso-8859-1 -*-

import gettext
import os
import os.path
import sys
import time
import traceback

import wx

import trelby
import trelby.config as config
import trelby.misc as misc
import trelby.opts as opts
import trelby.splash as splash
import trelby.util as util
import trelby.translations as translations
from trelby.globaldata import GlobalData
from trelby.ids import ID_FILE_EXIT, ID_HELP_ABOUT, ID_SETTINGS_CHANGE
from trelby.trelbyframe import MyFrame

# Boolean to determine if toolbar should be shown or not.
toolbarshown = True

# keycodes
KC_CTRL_A = 1
KC_CTRL_B = 2
KC_CTRL_D = 4
KC_CTRL_E = 5
KC_CTRL_F = 6
KC_CTRL_N = 14
KC_CTRL_P = 16
KC_CTRL_V = 22


_ = translations.trelby_translations_load()


def _quarantine_bad_file(path):
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    backup_path = "{}.broken-{}".format(path, timestamp)
    try:
        os.replace(misc.toPath(path), misc.toPath(backup_path))
        return backup_path
    except OSError:
        return None


def _safe_load_startup_file(path, parent, load_fn, label):
    if not util.fileExists(path):
        return

    data = util.loadFile(path, parent)
    if not data:
        return

    try:
        load_fn(data)
    except Exception as exc:
        backup_path = _quarantine_bad_file(path)
        if backup_path:
            details = _("Backup written to:\n{}").format(backup_path)
        else:
            details = _("Could not create backup copy of the bad file.")

        wx.MessageBox(
            _(
                "Ignoring corrupted {} and starting with defaults.\n\n"
                "Original file:\n{}\n\nError:\n{}\n\n{}"
            ).format(label, path, str(exc), details),
            _("Startup recovery"),
            wx.OK,
            parent,
        )


def _write_startup_crash_log(exc):
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = "startup-crash-{}.log".format(timestamp)
    crash_data = traceback.format_exc()

    candidates = [misc.confPath, misc.progPath]
    for directory in candidates:
        try:
            os.makedirs(misc.toPath(directory), mode=0o755, exist_ok=True)
            log_path = os.path.join(directory, filename)
            with open(misc.toPath(log_path), "w", encoding="utf-8") as f:
                f.write("Unhandled exception at startup:\n\n")
                f.write(str(exc))
                f.write("\n\n")
                f.write(crash_data)
            return log_path
        except OSError:
            continue

    return None


class MyApp(wx.App):

    def OnInit(self):

        if (wx.MAJOR_VERSION != 4) or (wx.MINOR_VERSION < 0):
            wx.MessageBox(
                _(
                    "You seem to have an invalid version\n({}) of wxWidgets installed. This\nprogram needs version 4.x.".format(
                        wx.VERSION_STRING
                    )
                ),
                _("Error"),
                wx.OK,
            )
            sys.exit()

        misc.init()
        util.init()

        gd = GlobalData()

        if misc.isMac:
            self.SetAppName("Trelby")
            self.SetAppDisplayName("Trelby")

            if hasattr(self, "SetMacAboutMenuItemId"):
                self.SetMacAboutMenuItemId(ID_HELP_ABOUT)
            if hasattr(self, "SetMacExitMenuItemId"):
                self.SetMacExitMenuItemId(ID_FILE_EXIT)
            if hasattr(self, "SetMacPreferencesMenuItemId"):
                self.SetMacPreferencesMenuItemId(ID_SETTINGS_CHANGE)

        if misc.isWindows:
            major = sys.getwindowsversion()[0]
            if major < 5:
                wx.MessageBox(
                    _(
                        "You seem to have a version of Windows\nolder than Windows 2000, which is the minimum\nrequirement for this program."
                    ),
                    _("Error"),
                    wx.OK,
                )
                sys.exit()

        if not "unicode" in wx.PlatformInfo:
            wx.MessageBox(
                _(
                    "You seem to be using a non-Unicode build of\n wxWidgets. This is not supported."
                ),
                _("Error"),
                wx.OK,
            )
            sys.exit()

        os.chdir(misc.progPath)

        cfgGl = config.ConfigGlobal()
        gd.cfgGl = cfgGl
        cfgGl.setDefaults()

        if util.fileExists(gd.confFilename):
            _safe_load_startup_file(
                gd.confFilename, None, cfgGl.load, _("global settings")
            )
        else:
            # we want to write out a default config file at startup for
            # various reasons, if no default config file yet exists
            util.writeToFile(gd.confFilename, cfgGl.save(), None)

        # refreshGuiConfig()
        gd.cfgGui = config.ConfigGui(gd.cfgGl)

        # cfgGl.scriptDir is the directory used on startup, while
        # misc.scriptDir is updated every time the user opens something in
        # a different directory.
        misc.scriptDir = cfgGl.scriptDir

        _safe_load_startup_file(gd.stateFilename, None, gd.load, _("window state"))

        gd.setViewMode(gd.viewMode)

        _safe_load_startup_file(
            gd.scDictFilename, None, gd.scDict.load, _("spell checker dictionary")
        )

        mainFrame = MyFrame(None, -1, "Trelby", gd, self)
        gd.mainFrame = mainFrame
        mainFrame.init()

        for arg in opts.filenames:
            mainFrame.openScript(arg)

        mainFrame.Show(True)

        # windows needs this for some reason
        mainFrame.panel.ctrl.SetFocus()

        self.SetTopWindow(mainFrame)

        mainFrame.checkFonts()

        if cfgGl.splashTime > 0:
            win = splash.SplashWindow(mainFrame, cfgGl.splashTime * 1000)
            win.Show()
            win.Raise()

        return True


def main():
    try:
        opts.init()

        myApp = MyApp(0)
        myApp.MainLoop()
    except Exception as exc:
        log_path = _write_startup_crash_log(exc)
        msg = _("Trelby failed during startup because of an unexpected error.")
        if log_path:
            msg += _("\n\nCrash log:\n{}").format(log_path)
        else:
            msg += _("\n\nCould not write crash log.")

        try:
            wx.MessageBox(msg, _("Error"), wx.OK)
        except Exception:
            pass

        traceback.print_exc()
        raise
