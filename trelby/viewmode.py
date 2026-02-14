# -*- coding: iso-8859-1 -*-

import trelby.config as config
import trelby.mypager as mypager
import trelby.pml as pml
import trelby.util as util

# Number of lines the smooth scroll will try to search. 15-20 is a good
# number to use with the layout mode margins we have.
MAX_JUMP_DISTANCE = 17
# Keep page geometry 1:1 with text metrics; extra zoom here doubles
# dialogue/action indents relative to the rendered font width.
MACOS_PAGE_ZOOM = 1.0


# a piece of text on screen.
class TextString:
    def __init__(self, line, text, x, y, fi, isUnderlined, col=0):

        # if this object is a screenplay line, this is the index of the
        # corresponding line in the Screenplay.lines list. otherwise this
        # is -1 (used for stuff like CONTINUED: etc).
        self.line = line

        # x,y coordinates in pixels from widget's topleft corner
        self.x = x
        self.y = y

        # text and its config.FontInfo and underline status
        self.text = text
        self.fi = fi
        self.isUnderlined = isUnderlined
        self.col = col


# a page shown on screen.
class DisplayPage:
    def __init__(self, pageNr, x1, y1, x2, y2):

        # page number (index in MyCtrl.pages)
        self.pageNr = pageNr

        # coordinates in pixels
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2


# caches pml.Pages for operations that repeatedly construct them over and
# over again without the page contents changing.
class PageCache:
    def __init__(self, ctrl):
        self.ctrl = ctrl

        # cached pages. key = pageNr, value = pml.Page
        self.pages = {}

    def getPage(self, pager, pageNr):
        pg = self.pages.get(pageNr)

        if not pg:
            pg = self.ctrl.sp.generatePMLPage(pager, pageNr, False, False)
            self.pages[pageNr] = pg

        return pg


# View Mode, i.e. a way of displaying the script on screen. this is an
# abstract superclass.
class ViewMode:

    # get a description of what the current screen contains. returns
    # (texts, dpages), where texts = [TextString, ...], dpages =
    # [DisplayPage, ...]. dpages is None if draft mode is in use or
    # doExtra is False. doExtra has same meaning as for generatePMLPage
    # otherwise. pageCache, if given, is used in layout mode to cache PML
    # pages. it should only be given when doExtra = False as the cached
    # pages aren't accurate down to that level.
    #
    # partial lines (some of the the text is clipped off-screen) are only
    # included in the results if 'partials' is True.
    #
    # lines in 'texts' have to be in monotonically increasing order, and
    # this has to always return at least one line.
    def getScreen(self, ctrl, doExtra, partials=False, pageCache=None):
        raise Exception("getScreen " + _("not implemented"))

    # return height for one line on screen
    def getLineHeight(self, ctrl):
        raise Exception("getLineHeight " + _("not implemented"))

    # return width of one page in (floating point) pixels
    def getPageWidth(self, ctrl):
        raise Exception("getPageWidth " + _("not implemented"))

    # see MyCtrl.OnPaint for what tl is. note: this is only a default
    # implementation, feel free to override this.
    def drawTexts(self, ctrl, dc, tl):
        dc.SetFont(tl[0])
        lines = tl[1][0]
        points = tl[1][1]
        colors = tl[1][2]
        
        for i in range(len(lines)):
            dc.SetTextForeground(colors[i])
            dc.DrawText(lines[i], points[i][0], points[i][1])

    # determine what (line, col) is at position (x, y) (screen
    # coordinates) and return that, or (None, None) if (x, y) points
    # outside a page.
    def pos2linecol(self, ctrl, x, y):
        raise Exception("pos2linecol " + _("not implemented"))

    # make line, which is not currently visible, visible. texts =
    # self.getScreen(ctrl, False)[0].
    def makeLineVisible(self, ctrl, line, texts, direction=config.SCROLL_CENTER):
        raise Exception("makeLineVisible " + _("not implemented"))

    # handle page up (dir == -1) or page down (dir == 1) command. cursor
    # is guaranteed to be visible when this is called, and auto-completion
    # to be off. cs = CommandState. texts and dpages are the usual.
    def pageCmd(self, ctrl, cs, dir, texts, dpages):
        raise Exception("pageCmd " + _("not implemented"))

    # semi-generic implementation, for use by Draft and Layout modes.
    def pos2linecolGeneric(self, ctrl, x, y):
        sel = None
        lineh = self.getLineHeight(ctrl)

        for t in self.getScreen(ctrl, False, True)[0]:
            if t.line == -1:
                continue

            sel = t

            if (t.y + lineh) > y:
                break

        if sel == None:
            return (None, None)

        line = sel.line
        l = ctrl.sp.lines[line]

        rel = util.clamp(int((x - sel.x) / sel.fi.fx), 0, len(sel.text))
        column = util.clamp(sel.col + rel, 0, len(l.text))

        return (line, column)

    # semi-generic implementation, for use by Draft and Layout modes.
    def makeLineVisibleGeneric(self, ctrl, line, texts, direction, jumpAhead):
        if not ctrl.sp.cfgGl.recenterOnScroll and (direction != config.SCROLL_CENTER):
            if self._makeLineVisibleHelper(ctrl, line, direction, jumpAhead):
                return

        # smooth scrolling not in operation (or failed), recenter screen
        ctrl.sp.setTopLine(max(0, int(line - (len(texts) * 0.5))))

        if not ctrl.isLineVisible(line):
            ctrl.sp.setTopLine(line)

    # helper function for makeLineVisibleGeneric
    def _makeLineVisibleHelper(self, ctrl, line, direction, jumpAhead):
        startLine = ctrl.sp.getTopLine()
        sign = 1 if (direction == config.SCROLL_DOWN) else -1
        i = 1

        while not ctrl.isLineVisible(line):
            ctrl.sp.setTopLine(startLine + i * sign)
            i += jumpAhead

            if i > MAX_JUMP_DISTANCE:
                return False

        return True

    # semi-generic implementation, for use by Draft and Layout modes.
    def pageCmdGeneric(self, ctrl, cs, dir, texts, dpages):
        if dir > 0:
            line = texts[-1].line
            ctrl.sp.line = line
            ctrl.sp.setTopLine(line)
        else:
            tl = ctrl.sp.getTopLine()
            if tl == texts[-1].line:
                ctrl.sp.setTopLine(tl - 5)
            else:
                ctrl.sp.line = tl

                pc = PageCache(ctrl)

                while 1:
                    tl = ctrl.sp.getTopLine()
                    if tl == 0:
                        break

                    texts = self.getScreen(ctrl, False, False, pc)[0]
                    lastLine = texts[-1].line

                    if ctrl.sp.line > lastLine:
                        # line scrolled off screen, back up one line
                        ctrl.sp.setTopLine(tl + 1)
                        break

                    ctrl.sp.setTopLine(tl - 1)

            cs.needsVisifying = False


# Draft view mode. No fancy page break layouts, just text lines on a plain
# background.
class ViewModeDraft(ViewMode):

    def getScreen(self, ctrl, doExtra, partials=False, pageCache=None):
        cfg = ctrl.sp.cfg
        cfgGui = ctrl.getCfgGui()

        width, height = ctrl.GetClientSize()
        ls = ctrl.sp.lines
        y = 15
        i = ctrl.sp.getTopLine()

        marginLeft = int(ctrl.mm2p * cfg.marginLeft)
        cox = util.clamp((width - ctrl.pageW) // 2, 0)
        fyd = ctrl.sp.cfgGl.fontYdelta
        length = len(ls)

        texts = []

        while (y < height) and (i < length):
            y += int((ctrl.sp.getSpacingBefore(i) / 10.0) * fyd)

            if y >= height:
                break

            if not partials and ((y + fyd) > height):
                break

            l = ls[i]
            tcfg = cfg.getType(l.lt)

            if tcfg.screen.isCaps:
                text = util.upper(l.text)
            else:
                text = l.text

            if ctrl.gd.mainFrame.showFormatting:
                text = text.replace(" ", "\u00b7")
                text += config.lb2displayChar(l.lb)

            fi = cfgGui.tt2fi(tcfg.screen)
            baseFlags = 0
            if tcfg.screen.isBold:
                baseFlags |= pml.BOLD
            if tcfg.screen.isItalic:
                baseFlags |= pml.ITALIC
            if tcfg.screen.isUnderlined:
                baseFlags |= pml.UNDERLINED

            extraIndent = 1 if ctrl.sp.needsExtraParenIndent(i) else 0

            x = cox + marginLeft + (tcfg.indent + extraIndent) * fi.fx
            if l.styles:
                mask = l.getStyleMask()
                col = 0
                while col < len(text):
                    flags = baseFlags | mask[col]
                    end = col + 1
                    while (end < len(text)) and ((baseFlags | mask[end]) == flags):
                        end += 1
                    seg = text[col:end]
                    segFi = cfgGui.fonts[flags & 3]
                    texts.append(
                        TextString(
                            i,
                            seg,
                            x + col * fi.fx,
                            y,
                            segFi,
                            (flags & pml.UNDERLINED) != 0,
                            col,
                        )
                    )
                    col = end
                if len(text) == 0:
                    texts.append(TextString(i, "", x, y, fi, tcfg.screen.isUnderlined, 0))
            else:
                texts.append(TextString(i, text, x, y, fi, tcfg.screen.isUnderlined, 0))

            y += fyd
            i += 1

        return (texts, [])

    def getLineHeight(self, ctrl):
        return ctrl.sp.cfgGl.fontYdelta

    def getPageWidth(self, ctrl):
        # this is not really used for much in draft mode, as it has no
        # concept of page width, but it's safer to return something
        # anyway.
        pageWidth = (ctrl.sp.cfg.paperWidth / ctrl.chX) * ctrl.getCfgGui().fonts[
            pml.NORMAL
        ].fx
        return pageWidth * MACOS_PAGE_ZOOM

    def pos2linecol(self, ctrl, x, y):
        return self.pos2linecolGeneric(ctrl, x, y)

    def makeLineVisible(self, ctrl, line, texts, direction=config.SCROLL_CENTER):
        self.makeLineVisibleGeneric(ctrl, line, texts, direction, jumpAhead=1)

    def pageCmd(self, ctrl, cs, dir, texts, dpages):
        self.pageCmdGeneric(ctrl, cs, dir, texts, dpages)


# Layout view mode. Pages are shown with the actual layout they would
# have.
class ViewModeLayout(ViewMode):

    def getScreen(self, ctrl, doExtra, partials=False, pageCache=None):
        cfgGui = ctrl.getCfgGui()
        textOp = pml.TextOp

        texts = []
        dpages = []

        width, height = ctrl.GetClientSize()

        # gap between pages (pixels)
        pageGap = 14
        pager = mypager.Pager(ctrl.sp.cfg)

        mm2p = ctrl.mm2p
        fontY = cfgGui.fonts[pml.NORMAL].fy

        cox = util.clamp((width - ctrl.pageW) // 2, 0)

        y = 0
        topLine = ctrl.sp.getTopLine()
        pageNr = ctrl.sp.line2page(topLine)

        if doExtra and ctrl.sp.cfg.pdfShowSceneNumbers:
            pager.scene = ctrl.sp.getSceneNumber(ctrl.sp.page2lines(pageNr)[0] - 1)

        # find out starting place (if something bugs, generatePMLPage
        # below could return None, but it shouldn't happen...)
        if pageCache:
            pg = pageCache.getPage(pager, pageNr)
        else:
            pg = ctrl.sp.generatePMLPage(pager, pageNr, False, doExtra)

        topOfPage = True
        for op in pg.ops:
            if not isinstance(op, textOp) or (op.line == -1):
                continue

            if op.line == topLine:
                if not topOfPage:
                    y = -int(op.y * mm2p)
                else:
                    y = pageGap

                break
            else:
                topOfPage = False

        # create pages, convert them to display format, repeat until
        # script ends or we've filled the display.

        done = False
        while 1:
            if done or (y >= height):
                break

            if not pg:
                pageNr += 1
                if pageNr >= len(ctrl.sp.pages):
                    break

                # we'd have to go back an arbitrary number of pages to
                # get an accurate number for this in the worst case,
                # so disable it altogether.
                pager.sceneContNr = 0

                if pageCache:
                    pg = pageCache.getPage(pager, pageNr)
                else:
                    pg = ctrl.sp.generatePMLPage(pager, pageNr, False, doExtra)
                if not pg:
                    break

            dp = DisplayPage(pageNr, cox, y, cox + ctrl.pageW, y + ctrl.pageH)
            dpages.append(dp)

            pageY = y

            ops = pg.ops
            for i, op in enumerate(ops):
                if not isinstance(op, textOp):
                    continue

                ypos = int(pageY + op.y * mm2p)

                if ypos < 0:
                    continue

                y = max(y, ypos)

                if (y >= height) or (not partials and ((ypos + fontY) > height)):
                    done = True
                    break

                txt = op.text
                if ctrl.gd.mainFrame.showFormatting:
                    txt = txt.replace(" ", "·")
                    if op.line != -1:
                        is_last = True
                        for next_op in ops[i + 1 :]:
                            if isinstance(next_op, textOp):
                                if next_op.line == op.line:
                                    is_last = False
                                break
                        if is_last:
                            txt += config.lb2displayChar(ctrl.sp.lines[op.line].lb)

                texts.append(
                    TextString(
                        op.line,
                        txt,
                        int(cox + op.x * mm2p),
                        ypos,
                        cfgGui.fonts[op.flags & 3],
                        op.flags & pml.UNDERLINED,
                        op.col,
                    )
                )

            y = pageY + ctrl.pageH + pageGap
            pg = None

        # if user has inserted new text causing the script to overflow
        # the last page, we need to make the last page extra-long on
        # the screen.
        if dpages and texts and (pageNr >= (len(ctrl.sp.pages) - 1)):

            lastY = texts[-1].y + fontY
            if lastY >= dpages[-1].y2:
                dpages[-1].y2 = lastY + 10

        return (texts, dpages)

    def getLineHeight(self, ctrl):
        # the + 1.0 avoids occasional non-consecutive backgrounds for
        # lines.
        return int(ctrl.chY * ctrl.mm2p + 1.0)

    def getPageWidth(self, ctrl):
        pageWidth = (ctrl.sp.cfg.paperWidth / ctrl.chX) * ctrl.getCfgGui().fonts[
            pml.NORMAL
        ].fx
        return pageWidth * MACOS_PAGE_ZOOM

    def pos2linecol(self, ctrl, x, y):
        return self.pos2linecolGeneric(ctrl, x, y)

    def makeLineVisible(self, ctrl, line, texts, direction=config.SCROLL_CENTER):
        self.makeLineVisibleGeneric(ctrl, line, texts, direction, jumpAhead=3)

    def pageCmd(self, ctrl, cs, dir, texts, dpages):
        self.pageCmdGeneric(ctrl, cs, dir, texts, dpages)


# Side by side view mode. Pages are shown with the actual layout they
# would have, as many pages at a time as fit on the screen, complete pages
# only, in a single row.
class ViewModeSideBySide(ViewMode):

    def getScreen(self, ctrl, doExtra, partials=False, pageCache=None):
        cfgGui = ctrl.getCfgGui()
        textOp = pml.TextOp

        texts = []
        dpages = []

        width, height = ctrl.GetClientSize()

        mm2p = ctrl.mm2p

        # gap between pages (+ screen left edge)
        pageGap = 14

        # how many pages fit on screen
        pageCnt = max(1, (width - pageGap) // (ctrl.pageW + pageGap))

        pager = mypager.Pager(ctrl.sp.cfg)

        topLine = ctrl.sp.getTopLine()
        pageNr = ctrl.sp.line2page(topLine)

        if doExtra and ctrl.sp.cfg.pdfShowSceneNumbers:
            pager.scene = ctrl.sp.getSceneNumber(ctrl.sp.page2lines(pageNr)[0] - 1)

        pagesDone = 0

        while 1:
            if (pagesDone >= pageCnt) or (pageNr >= len(ctrl.sp.pages)):
                break

            # we'd have to go back an arbitrary number of pages to get an
            # accurate number for this in the worst case, so disable it
            # altogether.
            pager.sceneContNr = 0

            if pageCache:
                pg = pageCache.getPage(pager, pageNr)
            else:
                pg = ctrl.sp.generatePMLPage(pager, pageNr, False, doExtra)
            if not pg:
                break

            sx = pageGap + pagesDone * (ctrl.pageW + pageGap)
            sy = pageGap

            dp = DisplayPage(pageNr, sx, sy, sx + ctrl.pageW, sy + ctrl.pageH)
            dpages.append(dp)

            ops = pg.ops
            for i, op in enumerate(ops):
                if not isinstance(op, textOp):
                    continue

                txt = op.text
                if ctrl.gd.mainFrame.showFormatting:
                    txt = txt.replace(" ", "·")
                    if op.line != -1:
                        is_last = True
                        for next_op in ops[i + 1 :]:
                            if isinstance(next_op, textOp):
                                if next_op.line == op.line:
                                    is_last = False
                                break
                        if is_last:
                            txt += config.lb2displayChar(ctrl.sp.lines[op.line].lb)

                texts.append(
                    TextString(
                        op.line,
                        txt,
                        int(sx + op.x * mm2p),
                        int(sy + op.y * mm2p),
                        cfgGui.fonts[op.flags & 3],
                        op.flags & pml.UNDERLINED,
                        op.col,
                    )
                )

            pageNr += 1
            pagesDone += 1

        return (texts, dpages)

    def getLineHeight(self, ctrl):
        # the + 1.0 avoids occasional non-consecutive backgrounds for
        # lines.
        return int(ctrl.chY * ctrl.mm2p + 1.0)

    def getPageWidth(self, ctrl):
        pageWidth = (ctrl.sp.cfg.paperWidth / ctrl.chX) * ctrl.getCfgGui().fonts[
            pml.NORMAL
        ].fx
        return pageWidth * MACOS_PAGE_ZOOM

    def pos2linecol(self, ctrl, x, y):
        lineh = self.getLineHeight(ctrl)
        ls = ctrl.sp.lines

        sel = None

        for t in self.getScreen(ctrl, False)[0]:
            if t.line == -1:
                continue

            # above or to the left
            if (x < t.x) or (y < t.y):
                continue

            # below
            if y > (t.y + lineh - 1):
                continue

            # to the right
            w = t.fi.fx * (len(ls[t.line].text) + 1)
            if x > (t.x + w - 1):
                continue

            sel = t
            break

        if sel == None:
            return (None, None)

        line = sel.line
        l = ls[line]

        rel = util.clamp(int((x - sel.x) / sel.fi.fx), 0, len(sel.text))
        column = util.clamp(sel.col + rel, 0, len(l.text))

        return (line, column)

    def makeLineVisible(self, ctrl, line, texts, direction=config.SCROLL_CENTER):
        ctrl.sp.setTopLine(line)

    def pageCmd(self, ctrl, cs, dir, texts, dpages):
        if dir < 0:
            pageNr = dpages[0].pageNr - len(dpages)
        else:
            pageNr = dpages[-1].pageNr + 1

        line = ctrl.sp.page2lines(pageNr)[0]

        ctrl.sp.line = line
        ctrl.sp.setTopLine(line)
        cs.needsVisifying = False
