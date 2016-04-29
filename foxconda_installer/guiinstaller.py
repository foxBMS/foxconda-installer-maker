import os
import sys
import wx
import wx.xrc as xrc
import wx.aui
import wx.wizard
from wx import html
import time
import threading
import config
import cliinstaller
import logging
import re
import webbrowser


class GUIInstaller(cliinstaller.Installer):

    def progressCB(self, name, i, m, msg = ''):
        if msg.startswith('unpacking'):
            _msg = '[%d/%d] %s%s' % (i, m * 3, msg, name)
        elif msg.startswith('extracting'):
            _msg = '[%d/%d] %s%s' % (i + m, m * 3, msg, name)
        else:
            _msg = '[%d/%d] %s%s' % (i + 2 * m, m * 3, msg, name)
        wx.CallAfter(self.parent.writeLog, _msg)


class InstallationThread(threading.Thread):

    def __init__(self, parent):
        self.parent = parent
        threading.Thread.__init__(self)
        self.canceling = False

    def run(self):
        self.parent.canCancel = False
        self.parent.installer.mkdir()
        self.parent.installer.extract()
        self.parent.installer.extractPackages()
        self.parent.installer.linkPackages()
        self.parent.installer.extraFiles()
        wx.CallAfter(self.parent.writeLog, '__all_done__')
        wx.CallAfter(self.parent.writeLog, 'post install triggers')
        self.parent.installer.postInstall()
        wx.CallAfter(self.parent.finishPage)
        self.parent.canCancel = True

    def run_(self):
        m = 100
        for t in ['unpacking', 'extracting', 'linking']:
            for i in range(1, 101):
                if self.canceling:
                    return
                time.sleep(0.05)
                if t.startswith('unpacking'):
                    msg = '[%d/%d] %s: package %d' % (i, m * 3, t, i)
                elif t.startswith('extracting'):
                    msg = '[%d/%d] %s: package %d' % (i + m, m * 3, t, i)
                else:
                    msg = '[%d/%d] %s: package %d' % (i + 2 * m, m * 3, t, i)
                wx.CallAfter(self.parent.writeLog, msg)
        wx.CallAfter(self.parent.finishPage)


class GUIDirectoryInput(cliinstaller.DirectoryInput):

    def __init__(self, path = None, parent = None):
        self.path = path
        self.parent = parent

    def showError(self, msg):
        dlg = wx.MessageDialog(self.parent, msg, 'Installation directory', wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()
        #logging.error(msg, exc_info=1)

    def overwriteOK(self):
        dlg = NotEmptyDialog(self.parent, message = self.messageNonEmpty())

        dlgid = dlg.ShowModal() 

        if dlgid == wx.ID_OK:
            return True
        elif dlgid == wx.ID_ABORT:
            self.parent.Close(force = True)
        return False


def _getpath(*args):
    path = [os.path.dirname(__file__)] + list(args)
    return os.path.join(*path)


class CondaInstallationWizard(wx.wizard.Wizard):

    PROGRESS_RE = re.compile('\[\s*(\d+)/(\d+)\] (.*)')

    def PreCreate(self, pre):
        pass
    
    def __init__(self, parent, conf):


        self._resources = xrc.EmptyXmlResource()

        _cwd = getattr(sys, '_MEIPASS', None)
        if not _cwd:
            _xrc = _getpath('xrc', 'fci.xrc')
        else:
            _xrc = os.path.join(_cwd, 'xrc', 'fci.xrc')

        self._resources.Load(_xrc)

        pre = wx.wizard.PreWizard()
        self.PreCreate(pre)
        self._resources.LoadOnObject(pre, parent, "fcIframe", pre.GetClassName())
        self.PostCreate(pre)

        self.conf = conf
        self._exitMode = 'abort'
        self.canCancel = True

        self.SetTitle(self.conf.getEntry('title'))
        _icon = self.conf.getIconFile()
        if _icon:
            _cwd = getattr(sys, '_MEIPASS', None)
            if _cwd:
                _icon = os.path.join(_cwd, 'data', _icon)
            self.SetIcon(wx.Icon(_icon, wx.BITMAP_TYPE_ICO))
        self.SetBitmap(wx.Bitmap(os.path.join(self.conf.dirname,
            self.conf.getEntry('image'))))

        xrc.XRCCTRL(self, 'progress_gauge').SetSize((-1, 3))

        #self.Bind(wx.EVT_CLOSE, self.onClose)
        
        self.Bind(wx.wizard.EVT_WIZARD_PAGE_CHANGING, self.onPageChanging)
        self.Bind(wx.wizard.EVT_WIZARD_PAGE_CHANGED, self.onPageChanged)
        self.Bind(wx.wizard.EVT_WIZARD_CANCEL, self.onCancel)

        wx.xrc.XRCCTRL(self, 'welcome_html').Bind(wx.html.EVT_HTML_LINK_CLICKED,
                self.onLink)

        self.ithread = None
        self.forceClose = False
        self.SetPageSize((800, 600))
        self.installdir = GUIDirectoryInput(parent = self)




    def _setLicense(self, s):
        wx.xrc.XRCCTRL(self, 'license_tctrl').SetValue(s)

    def _setWelcome(self, s):
        wx.xrc.XRCCTRL(self, 'welcome_html').SetPage(s)

    def onLink(self, evt):
        webbrowser.open(evt.GetLinkInfo().GetHref())

    def onPageChanged(self, evt):
        page = evt.GetPage().GetName()
        if page == 'welcome_page':
            self._setWelcome(str(self.welcome))
        elif page == 'license_page':
            self._setLicense(str(self.license))
        elif page == 'progress_page':
            self.FindWindowById(wx.ID_FORWARD).Enable(False) 
            self.FindWindowById(wx.ID_BACKWARD).Enable(False) 
            self.FindWindowById(wx.ID_CANCEL).Enable(True) 

            _path = wx.xrc.XRCCTRL(self, 'location_dp').GetPath()
            self.installer = GUIInstaller(self.conf, targetdir = _path)
            self.installer.parent = self
            self.ithread = InstallationThread(self)
            self.ithread.start()
        elif page == 'finish_page':

            _success = self.conf.getEntry('success') 
            if _success:
                wx.xrc.XRCCTRL(self, 'success_text').SetLabel(_success)

            self.FindWindowById(wx.ID_FORWARD).Enable(True) 
            self.FindWindowById(wx.ID_BACKWARD).Show(False) 
            self._exitMode = 'finish'
            if self.conf.getEntry('launch') and self.conf.getEntry('launch')['check']:
                wx.xrc.XRCCTRL(self, 'launch_cb').SetLabel(self.conf.getEntry('launch')['check'])
                wx.xrc.XRCCTRL(self, 'launch_cb').Show(True)

    def checkLaunch(self):

        if self._exitMode == 'abort':
            return False

        return self.conf.getEntry('launch') and \
                self.conf.getEntry('launch')['check'] and \
                wx.xrc.XRCCTRL(self, 'launch_cb').GetValue()


    def execute(self):
        self.installer.execute()


    def onPageChanging(self, evt):
        page = evt.GetPage().GetName()

        # if leaving license page, check if license has been accepted
        if page == 'license_page' and wx.xrc.XRCCTRL(self, 'license_radio').GetSelection() < 1:
            dlg = DeclineDialog(self)
            ret = dlg.ShowModal()
            if ret != wx.ID_OK:
                self.forceClose = True
                self.Close()
            evt.Veto()
        elif page == 'location_page':
            _path = wx.xrc.XRCCTRL(self, 'location_dp').GetPath()
            if not self.installdir.setPathAndCheck(_path):
                evt.Veto()

    def onCancel(self, evt):
        page = evt.GetPage().GetName()

        if self.forceClose:
            evt.Skip()
            return

        if not self.canCancel:
            dlg = wx.MessageDialog(self, 'You cannot cancel the installation', 'No cancellation at this point', wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()
            evt.Veto()
            return

        if ExitConfirmDialog(self).ShowModal() == wx.ID_OK:
            if page == 'progress_page':
                self.cancelInstallation()
            else:
                evt.Skip()
        else:
            evt.Veto()

    def setPath(self, path):
        _path = self.installdir.getDefaultInstallLocation(path)
        wx.xrc.XRCCTRL(self, 'location_dp').SetPath(_path)

    '''
    def Close(self, force = True):
        wx.wizard.Wizard.Close(self, force)
    '''

    def run(self):
        self.RunWizard(wx.xrc.XRCCTRL(self, 'welcome_page'))

    def finishPage(self):
        self.FindWindowById(wx.ID_FORWARD).Enable(True) 
        self.ShowPage(wx.xrc.XRCCTRL(self, 'finish_page'))

    def setProgress(self, prog, ran):
        xrc.XRCCTRL(self, 'progress_gauge').SetRange(ran) 
        xrc.XRCCTRL(self, 'progress_gauge').SetValue(prog)

    def writeLog(self, msg):
        if msg == '__all_done__':
            self.setProgress(1, 1)
            return
        g = self.PROGRESS_RE.match(msg)
        if g:
            self.setProgress(int(g.group(1)), int(g.group(2)))
            msg = g.group(3)
        xrc.XRCCTRL(self, 'info_text').SetLabel(msg)


    def cancelInstallation(self):
        self.ithread.canceling = True
        wx.xrc.XRCCTRL(self, 'progress_label').SetLabel('canceling')
        self.ithread.join()

class NotEmptyDialog(wx.Dialog):

    def __init__(self, parent, message):

        self.parent = parent
        pre = wx.PreDialog()
        parent._resources.LoadOnDialog(pre, parent, "exists_dialog")
        self.PostCreate(pre)
        xrc.XRCCTRL(self, 'exists_label').SetLabel(message)

        xrc.XRCCTRL(self, 'change_b').Bind(wx.EVT_BUTTON, self.OnChange)
        xrc.XRCCTRL(self, 'proceed_b').Bind(wx.EVT_BUTTON, self.OnProceed)
        xrc.XRCCTRL(self, 'abort_b').Bind(wx.EVT_BUTTON, self.OnAbort)

    def OnProceed(self, evt):
        self.EndModal(wx.ID_OK)

    def OnChange(self, evt):
        self.EndModal(wx.ID_CANCEL)

    def OnAbort(self, evt):
        self.EndModal(wx.ID_ABORT)

class DeclineDialog(wx.Dialog):

    def __init__(self, parent):

        self.parent = parent
        pre = wx.PreDialog()
        parent._resources.LoadOnDialog(pre, parent, "decline_dialog")
        self.PostCreate(pre)

        xrc.XRCCTRL(self, 'abort_b').Bind(wx.EVT_BUTTON, self.OnAbort)
        xrc.XRCCTRL(self, 'review_b').Bind(wx.EVT_BUTTON, self.OnReview)

    def OnReview(self, evt):
        self.EndModal(wx.ID_OK)

    def OnAbort(self, evt):
        self.EndModal(wx.ID_CANCEL)

class ExitConfirmDialog(wx.Dialog):

    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, title="Exit Installer")

        btnOk = wx.Button(self, wx.ID_OK, 'Exit Installer')
        btnCancel = wx.Button(self, wx.ID_CANCEL, 'Proceed with installation')

        topsizer = wx.BoxSizer(wx.VERTICAL)

        btnSizer = wx.StdDialogButtonSizer()
        btnSizer.AddButton(btnCancel)
        btnSizer.AddButton(btnOk)
        btnSizer.Realize()
        topsizer.Add(btnSizer, 0, wx.ALL, 10)
        self.SetSizer(topsizer)
        self.Fit()


class InstallerApp(wx.App):

    def OnExit(self):
        wx.App.OnExit(self)

def main(installdir = None):

    _cwd = getattr(sys, '_MEIPASS', None)
    if not _cwd:
        _conf = 'installer.yaml'
    else:
        _conf = os.path.join(_cwd, 'data', 'installer.yaml')

    conf = config.InstallerConfig(_conf)
    conf.read()


    app = InstallerApp(False)
    frame = CondaInstallationWizard(None, conf)

    wt = cliinstaller.WelcomeText()
    wt.addText(conf.getEntry('welcome')['html'])

    frame.welcome = wt.getText()

    lt = cliinstaller.LicenseText()
    for f in conf.getTopicFiles('license', 'files'):
        lt.addFileContents(os.path.join(conf.dirname, f))

    frame.license = lt.getText()

    if not installdir:
        installdir = conf.getEntry('installdir')

    frame.setPath(installdir)

    #frame.license = FCLicenseProvider()
    #frame.license.generate()
    #frame.welcome = FCWelcomeProvider()
    #frame.welcome.generate()
    frame.run()
    frame.Destroy()
    if frame.checkLaunch():
        frame.execute()
    app.MainLoop()


if __name__ == '__main__':
    main()

