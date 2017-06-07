"""
:since:     Wed Apr 20 17:34:13 CEST 2016
:author:    Tim Fuehner <tim.fuehner@iisb.fraunhofer.de>
$Id$
"""

import json
import sys
import sdkconda
import tarfile
import os
import re
import logging
import subprocess
import tempfile
import webbrowser
import glob
import config
import pprint
import shutil

from __info__ import __name__, __version__, __build__, __platform__


def cli_page(txt, pretty = True):
    if sys.platform.startswith('win'):
        _cmd = 'more'
    else:
        _cmd = 'less'
    pipe = subprocess.Popen(_cmd, stdin=subprocess.PIPE)
    _txt = txt
    pipe.stdin.write(_txt)
    pipe.stdin.close()
    pipe.wait()

def cli_getInput(prompt = 'Input', default = None):
    if default:
        prompt = prompt + ' [' + default + ']'
    prompt += ' '
    ans = raw_input(prompt)
    if default and ans.strip() == '': 
        return default
    return ans

def cli_getChoices(
        prompt='yes/no?', 
        choices = {'y*': 'yes', 'n*': 'no'}, 
        invalid='Invalid input. Type yes or no', 
        case=False):

    prompt += ' '

    _c = {}
    for k,v in choices.iteritems():
        if k.endswith('*'):
            _s = len(k) - 1
            for i in range(_s, len(v) + 1):
                _c[k[:-1] + v[_s:i]] = v
        else:
            _c[k] = v

    choices = _c

    while 1:
        ans = raw_input(prompt)
        if not case:
            ans = ans.lower()
        try:
            return choices[ans]
        except:
            print invalid

class WelcomeText(object):

    def __init__(self, txt = '', pretty = False):
        self.wt = txt
        self.pretty = pretty
        self.pre = []
        self.paged = True
        if sys.platform.startswith('win'):
            self.paged = False

    def addText(self, text):
        self.wt += text

    def addFileContents(self, fname):
        with open(fname, 'r') as f:
            self.wt += f.read()

    def addWelcome(self, wt):
        self.pre += [wt]

    def _print(self, txt):
        if self.paged:
            cli_page(txt, pretty = self.pretty)
        else:
            print txt

    def getText(self):
        _txt = ''
        for p in self.pre:
            _txt += p.getText() + '\n\n'
        _txt += self.wt
        return _txt

    def show(self):
        self._print(self.getText())


class LicenseText(WelcomeText):

    def __init__(self, txt = '', pretty = True):
        WelcomeText.__init__(self, txt, pretty)

    def accepts(self):
        return cli_getChoices('Do you accept the terms (yes/no)?', 
                choices = {'yes': 'yes', 'no': 'no'}) == 'yes'

class DirectoryInput(object):

    def __init__(self, path = None):
        self.path = path

    def getDefaultInstallLocation(self, path):

        if sys.platform.startswith('win'):
            import platform, ctypes, knownpaths
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            if is_admin:
                if platform.architecture()[0] == '64bit':
                    _progs = knownpaths.get_path(knownpaths.FOLDERID.ProgramFilesX64)
                else:
                    _progs = knownpaths.get_path(knownpaths.FOLDERID.ProgramFilesX86)
            else:
                _progs = os.path.expanduser('~')
        else:
            is_admin = os.getuid() == 0
            if is_admin:
                if sys.platform.startswith('darwin'):
                    _progs = '/opt/local'
                else:
                    _progs = '/opt'
            else:
                _progs = os.path.expanduser('~')

        return os.path.join(_progs, path)


    def exists(self):
        _parent = os.path.abspath(os.path.join(self.path, '..'))
        if not os.path.exists(self.path):
            if os.access(_parent, os.W_OK):
                return False
            raise RuntimeError('Cannot create directory in %r' % _parent)
        if not os.path.isdir(self.path):
            raise RuntimeError('%r exists and is not a directory' % self.path)
        return True

    def isEmpty(self):
        if not os.listdir(self.path):
            return True
        return False

    def messageNonEmpty(self):
        return 'Installation directory %r is non-empty' % self.path

    def showError(self, msg):
        logging.error(msg, exc_info=1)

    def overwriteOK(self):
        return cli_getChoices(self.messageNonEmpty() + '. Install anyway (y/n)?') == 'yes'

    def setPathAndCheck(self, path):
        if path.strip() == '':
            return False
        self.path = os.path.abspath(os.path.expanduser(path))
        try:
            if not self.exists():
                return True
            else: 
                if self.isEmpty() or self.overwriteOK():
                    return True
            return False
        except Exception, e:
            self.showError(e)
            return False


def cli_getDirectory(default = None):
    _di = DirectoryInput()
    _default = _di.getDefaultInstallLocation(default)
    while 1:
        _path = cli_getInput('Installation directory:', _default)
        if _di.setPathAndCheck(_path):
            return _di.path

class Installer(object):

    def __init__(self, conf, targetdir = None, ):
        self.conf = conf
        self.payloadname = os.path.join(conf.dirname,
                conf.getFiles('payload')[0])
        self.targetdir = targetdir
        self.packages = None
        self.conda = None
        self.python = None
        self.menuinst = None
        self.primepackages = [] 
        self.postpackages = [] 
        self.allpackages = []

    def mkdir(self):
        try:
            os.makedirs(os.path.join(self.targetdir, 'pkgs'))
        except Exception, e:
            pass

    def _extract_cb(self, members, _size):
        _asize = 0L

        self.primepackages = [None] * len(self.conf.getEntry('payload')['primepackages'])
        self.postpackages = [None] * len(self.conf.getEntry('payload')['postpackages'])

        for i,tarinfo in enumerate(members):
            _name = tarinfo.name
            _asize += tarinfo.size

            _isprime = False
            _ispost = False

            for j, _pp in enumerate(self.conf.getEntry('payload')['primepackages']):
                if not re.match('%s-\d' % _pp, _name) is None:
                    _isprime = True
                    self.primepackages[j] = _name
                    if _pp.startswith('python'):
                        self.python = _name[:-len('.tar.bz2')]
                    if _pp.startswith('conda'):
                        self.conda = _name[:-len('.tar.bz2')]
                    if _pp.startswith('menuinst'):
                        self.menuinst = _name[:-len('.tar.bz2')]
                    break

            if not _isprime:
                for j, _pp in enumerate(self.conf.getEntry('payload')['postpackages']):
                    if not re.match('%s-\d' % _pp, _name) is None:
                        _ispost = True
                        self.postpackages[j] = _name
                        break

            if not _isprime and not _ispost:
                self.packages += [_name]

            self.progressCB(_name, i + 1, _size, 'unpacking: ')
            yield tarinfo

        self.allpackages = [x for x in self.primepackages if not x is None] + self.packages + [x for x in self.postpackages if not x is None]

    def extract(self):
        self.packages = []
        _payload = os.path.abspath(self.payloadname)
        _size = os.stat(_payload).st_size
        thisdir = os.path.abspath('.')
        os.chdir(os.path.join(self.targetdir, 'pkgs'))

        with tarfile.open(_payload) as _f:
            for n,tarinfo in enumerate(_f):
                pass
            n += 1

        with tarfile.open(_payload) as _f:
            _f.extractall(members=self._extract_cb(_f, n))
        os.chdir(thisdir)

    def progressCB(self, name, i, m, msg = ''):
        logging.info('[%d/%d] %s%s' % (i, m, msg, name))

    def extractPackages(self):
        thisdir = os.path.abspath('.')
        os.chdir(os.path.join(self.targetdir, 'pkgs'))
        _s = len(self.allpackages)
        for i, p in enumerate(self.allpackages):
            _name = p[:-len('.tar.bz2')]
            self.progressCB(_name, i + 1, _s, 'extracting: ')
            with tarfile.open(p) as _f:
                _f.extractall(path = _name)
        os.chdir(thisdir)

    def extractAndLinkPackages(self):
        '''
        After a packages is extracted, the package information is stored in
        the info directory of the target installation directory. Then, the
        _install.py script is executed without any arguments. 
        '''

        # _install.py script location
        _install = os.path.join(self.targetdir, 'pkgs', 'install.py')

        # set temporary locations of packages
        if sys.platform.startswith('win'):
            _pythonpath = os.path.join(self.targetdir, 'python')
            _condapath = os.path.join(self.targetdir, 'pkgs', self.conda, 'Lib', 'site-packages', 'conda')
            _misitepackage = os.path.join(self.targetdir, 'pkgs', self.menuinst, 'Lib', 'site-packages')
        else:
            _pythonpath = os.path.join(self.targetdir, 'bin', 'python')
            _condapath = os.path.join(self.targetdir, 'pkgs', self.conda, 'lib', 'python2.7', 'site-packages', 'conda')
            _misitepackage = os.path.join(self.targetdir, 'pkgs', self.menuinst,'lib', 'python2.7', 'site-packages')

        thisdir = os.path.abspath('.')
        os.chdir(os.path.join(self.targetdir))
        _s = len(self.allpackages)
        for i, p in enumerate(self.allpackages):
            _name = p[:-len('.tar.bz2')]
            _path = os.path.join('pkgs', p)
            self.progressCB(_name, i + 1, _s, 'installing: ')
            with tarfile.open(_path) as _f:
                #_f.extractall(path = _name)
                _f.extractall(path = self.targetdir)
            _args = [_pythonpath, '-E', '-s', _install]
            if sys.platform.startswith('linux'):
                _args = ' '.join(_args)
            logging.debug(_args)
            #subprocess.call(_args, shell=True, env=env)
            if sys.platform.startswith('darwin'):
                # no clue, why shell doesn't work on Darwin
                subprocess.call(_args)
            else:
                subprocess.call(_args, shell=True)
            os.remove(_path)
        os.chdir(thisdir)

    def linkPackages(self):
        if sys.platform.startswith('win'):
            _primer_pythonpath = os.path.join(self.targetdir, 'pkgs', self.python, 'python')
            _pythonpath = os.path.join(self.targetdir, 'python')
            _condapath = os.path.join(self.targetdir, 'pkgs', self.conda, 'Lib', 'site-packages', 'conda')
            _misitepackage = os.path.join(self.targetdir, 'pkgs', self.menuinst, 'Lib', 'site-packages')
        else:
            _primer_pythonpath = os.path.join(self.targetdir, 'pkgs', self.python, 'bin', 'python')
            _pythonpath = os.path.join(self.targetdir, 'bin', 'python')
            _condapath = os.path.join(self.targetdir, 'pkgs', self.conda, 'lib', 'python2.7', 'site-packages', 'conda')
            _misitepackage = os.path.join(self.targetdir, 'pkgs', self.menuinst,'lib', 'python2.7', 'site-packages')
 
        _install = os.path.join(_condapath, 'install.py')
        logging.info('linking packages')

        # patch the environment
        env = os.environ.copy()
        _ppath = env.get('PYTHONPATH', '').split(os.path.pathsep)
        _ppath = [str(_misitepackage)] + _ppath
        env['PYTHONPATH'] = os.path.pathsep.join(_ppath)

        _s = len(self.packages) + len(self.postpackages) + len(self.primepackages)
        j = 0
        for _ppath, packages in [
                (_primer_pythonpath, self.primepackages), 
                (_primer_pythonpath, self.packages), 
                (_pythonpath, self.postpackages)]:

            for i, p in enumerate(packages):
                _name = p[:-len('.tar.bz2')]
                _tm = tempfile.NamedTemporaryFile(delete = False)
                try:
                    self.progressCB(_name, j + 1, _s, 'linking: ')
                    j += 1
                    _tm.file.write(_name)
                    _tm.file.close()
                    _args = [_ppath, _install, '--file=%s' % _tm.name, '--prefix=%s' % self.targetdir]
                    if sys.platform.startswith('linux'):
                        _args = ' '.join(_args)
                    #out = subprocess.check_output(_args, shell=True, env=env)
                    subprocess.call(_args, shell=True, env=env)
                finally:
                    os.remove(_tm.name)

        '''
        echo "creating default environment..."
        export FORCE
        $PYTHON -E -s "$PREFIX/pkgs/.install.py" --root-prefix=$PREFIX || exit 1

        PYTHONB="$PREFIX/bin/python"
        $PYTHONB -E -s "$PREFIX/pkgs/.cio-config.py" "$THIS_PATH"
        echo "installation finished."
        '''

    def extraFiles(self):
        for k in ['data', 'license']:
            _entry = self.conf.getEntry(k)
            if _entry:
                _target = os.path.join(self.targetdir, _entry['target'])
                try:
                    os.makedirs(_target)
                except Exception, e:
                    pass
                for f in self.conf.getTopicFiles(k, 'files'):
                    shutil.copy(os.path.join(self.conf.dirname, f), _target)

    def postInstall(self):
        for f in self.conf.getTopicFiles('postinstall', 'scripts'):
            if sys.platform.startswith('win'):
                cmd = os.path.join(self.targetdir, 'python.exe') + ' ' + os.path.join(self.conf.dirname, f)
            else:
                cmd = os.path.join(self.targetdir, 'bin', 'python') + ' ' + os.path.join(self.conf.dirname, f)
            subprocess.call(cmd, shell=True)

    def execute(self):
        _cmd = self.conf.getEntry('launch')['cmd']
        if sys.platform.startswith('win'):
            cmd = os.path.join(self.targetdir, 'Scripts', _cmd)
            for _ext in ['.exe', '.bat']:
                if os.path.exists(cmd + _ext):
                    cmd += _ext
                    break
        else:
            cmd = os.path.join(self.targetdir, 'bin', _cmd)
        subprocess.Popen([cmd]).pid


        '''
        if sys.platform.startswith('linux') and os.getuid() == 0:
            # When extracting as root, tarfile will by restore ownership
            # of extracted files.  However, we want root to be the owner
            # (our implementation of --no-same-owner).

            for root, dirs, files in os.walk(path):
                for fn in files:
                    os.lchown(os.path.join(root, fn), 0, 0)
        '''


def main(installdir = None, version=False):

    _cwd = getattr(sys, '_MEIPASS', None)
    if not _cwd:
        _conf = 'installer.yaml'
    else:
        _conf = os.path.join(_cwd, 'data', 'installer.yaml')

    conf = config.InstallerConfig(_conf)
    conf.read()

    if version:
        print __name__, __version__
        print '[%s; %s]\n\n' % (__build__, __platform__)
        print conf.getEntry('welcome')['text']
        sys.exit(0)

    wt = WelcomeText()
    wt.addText(conf.getEntry('welcome')['text'])

    lt = LicenseText()
    for f in conf.getTopicFiles('license', 'files'):
        lt.addFileContents(os.path.join(conf.dirname, f))

    lt.addWelcome(wt)
    lt.show()

    if conf.getEntry('license')['agree'] and not lt.accepts():
        logging.error('license not accepted. aborting.')
        sys.exit(0)

    if not installdir:
        installdir = conf.getEntry('installdir')

    _path = cli_getDirectory(installdir)

    logging.info('will install foxConda into %r' % _path)
    if not cli_getChoices('Proceed (y/n)?') == 'yes':
        sys.exit(0)
    inst = Installer(conf, targetdir = _path)
    inst.mkdir()
    inst.extraFiles()
    inst.extract()
    #inst.extractPackages()
    #inst.linkPackages()
    inst.extractAndLinkPackages()
    inst.postInstall()

    _success = conf.getEntry('success') 
    if _success:
        logging.info(_success)

    if conf.getEntry('launch') and conf.getEntry('launch')['check'] and \
            cli_getChoices(conf.getEntry('launch')['check'], 
                    choices = {'yes': 'yes', 'no': 'no'}) == 'yes':
        inst.execute()

if __name__ == '__main__':
    main()


