"""
:since:     Mon Apr 18 12:40:47 CEST 2016
:author:    Tim Fuehner <tim.fuehner@iisb.fraunhofer.de>
$Id$
"""

import subprocess
import logging
import os
import sys
import glob
import json


class SDKFoxConda(object):
    _CONDA = 'conda'
    _BUILD_ENV = 'FCBUILD'
    _MP = 'foxcondadeps'

    def __init__(self, conda = None, build_env = None, mp = None):
        if conda:
            self._CONDA = conda
        if build_env:
            self._BUILD_ENV = build_env
        if mp:
            self._MP = mp

    def createMP(self, deps = [], version = '0.1'):
        cmd = self._CONDA + ' metapackage ' + self._MP + ' ' + version + ' --dependencies'
        for _d in deps:
            if not _d.startswith(self._MP):
                cmd += ' ' + _d 
        logging.debug(cmd)
        status = subprocess.call(cmd, shell=True)

    def createBuildEnv(self):
        for m in ['create', 'install']:
            cmd = '%s %s -y -n %s -c file://%s %s' % (self._CONDA, m,
                    self._BUILD_ENV, os.path.join(sys.prefix, 'conda-bld'),
                    self._MP) 
            logging.debug(cmd)
            try:
                status = subprocess.call(cmd, shell=True)
                return
            except:
                pass

    def cleanBuildEnv(self):
        cmd = self._CONDA + ' remove -y -n ' + self._BUILD_ENV + ' --all'
        logging.debug(cmd)
        status = subprocess.call(cmd, shell=True)

    def collectPackages(self):
        packages = []
        for f in glob.glob(os.path.join(sys.prefix, 'envs', self._BUILD_ENV,
            'conda-meta', '*.json')):
            with open(f, 'r') as _f:
                packages += [json.load(_f)['link']['source'] + '.tar.bz2']

        self.packages = packages

    def addNewestPackage(self, name):
        _name = '-'.join([name, '*', '*'])
        self.packages += [[n for n in glob.glob(os.path.join(sys.prefix, 'pkgs', _name)) if
                len(os.path.basename(n).split('-')) ==
                len(_name.split('-'))][-1]]



if __name__ == '__main__':
    pass


