"""
:since:     Mon Apr 18 14:20:17 CEST 2016
:author:    Tim Fuehner <tim.fuehner@iisb.fraunhofer.de>
$Id$
"""

import logging
import subprocess
import argparse
import yaml
import config
import sys
import os
import tarfile

SPEC_TMPL_DEBUG = '''\
# -*- mode: python -*-

import os

datafiles = [(%(xrc)r, 'xrc')]

%(files)s


a = Analysis([%(script)r],
             pathex=None,
             binaries=None,
             datas=datafiles,
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None,
             excludes=None,
             cipher=None,
            )

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name=%(name)r,
          debug=False,
          strip=None,
          upx=False,
          console=True,
          windowed=False,
          icon=%(icon)r,
          %(msexeversioninfo)s
          )
'''

SPEC_TMPL = '''\
# -*- mode: python -*-

import os

datafiles = [(%(xrc)r, 'xrc')]

%(files)s


a = Analysis([%(script)r],
             pathex=None,
             binaries=None,
             datas=datafiles,
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None,
             excludes=None,
             cipher=None,
            )

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name=%(name)r,
          debug=False,
          strip=None,
          upx=False,
          console=False,
          windowed=True,
          icon=%(icon)r,
          %(msexeversioninfo)s
          )
'''


class InstallerMaker(object):

    SPECFILE = '_install.spec'

    def __init__(self, conf = 'installer.yaml', distpath = 'dist',
            sourcepath = '.', template = None, debug = False):
        self.confpath = conf
        self.config = config.InstallerConfig(conf)
        self.config.read()
        self.distpath = distpath
        self.sourcepath = sourcepath
        self.template = template
        self.debug = debug

    def updateTarSize(self):
        _pl = self.config.getFiles('payload')[0]
        with tarfile.open(_pl) as _f:
            for n,tarinfo in enumerate(_f):
                pass
            n += 1
        self.config.setEntry('numberpackage', n)
        self.config.write()


    def genFileEntries(self, files, target='data'):
        ret = ''
        for f in files:
            ret += 'datafiles += [(%r, %r)]\n' % (f, target)
        return ret

    def checkFiles(self, files):
        for f in files:
            if not os.path.isfile(f):
                logging.error('File not found: %s' % f)

    def generate(self):
        # self.updateTarSize()
        _icon = self.config.getIconFile()

        if self.template:
            with open(self.template, 'r') as f:
                _template = f.read()
        else:
            if self.debug:
                _template = SPEC_TMPL_DEBUG
            else:
                _template = SPEC_TMPL
        _entries = {}
        _files = [os.path.join(f) for f in self.config.getAllFiles()]
        _files += [self.confpath]
        self.checkFiles(_files)
        _entries['files'] = self.genFileEntries(_files)
        _entries['name'] = self.config.entries['name'] 
        _entries['script'] = os.path.join(os.path.dirname(__file__), 'installer.py')
        _entries['xrc'] = os.path.join(os.path.dirname(__file__), 'xrc', 'fci.xrc')
        _entries['icon'] = _icon

        _version = self.config.getEntry('msexeversioninfo')
        if sys.platform.startswith('win') and _version:
            _entries['msexeversioninfo'] = 'version=%r' % _version
        else:
            _entries['msexeversioninfo'] = ''

        with open(self.SPECFILE, 'w') as f:
            f.write(_template % _entries)

        if sys.platform.startswith('win'):
            _args = ['pyinstaller', '--clean', '--windowed', '--distpath',
                    self.distpath, '-y']
            if _icon:
                _args += ['-i', _icon]
            _args += [self.SPECFILE]
        elif sys.platform.startswith('darwin'):
            _args = ['pyinstaller', '--clean', '--windowed', '--distpath',
                    self.distpath, '-y']
            if _icon:
                _args += ['-i', _icon]
            _args += [self.SPECFILE]
        else:
            _args = ['pyinstaller', 
                    '--distpath', 
                    self.distpath,
                    '-c', '-y', '--onefile',
                    self.SPECFILE]

        logging.info('running: ' + ' '.join(_args))

        subprocess.call(' '.join(_args), shell=True)


def main():

    parser = argparse.ArgumentParser(description='foxConda Installer---Installer Generator')

    parser.add_argument('--verbosity', '-v', action='count', default=0, help="increase output verbosity")
    parser.add_argument('--distpath', '-d', default='dist', help="where to store the installer executable")
    parser.add_argument('--sourcepath', '-s', default='.', help="where is the source data stored")
    parser.add_argument('--template', '-t', default=None, help="install.spec template")
    parser.add_argument('--debug', action='store_true', help="use debug template (no windows)")
    parser.add_argument('config', metavar = 'CONFIGURATION FILE', default = 'installer.yaml', help='file containing description')

    args = parser.parse_args()

    if args.verbosity == 1:
        logging.basicConfig(level = logging.INFO)
    elif args.verbosity > 1:
        logging.basicConfig(level = logging.DEBUG)
    else:
        logging.basicConfig(level = logging.WARNING)

    im = InstallerMaker(args.config, args.distpath, args.sourcepath,
            args.template, args.debug)
    im.generate()

if __name__ == '__main__':
    main()

