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

metatmpl = '''\
package:
    name: %(_MP)s
    version: %(_MP_VERSION)s

requirements:
    run:
%(_packages)s

about:
    home: http://www.foxbms.org
    license: BSD
'''


class SDKFoxConda(object):

    def __init__(self, conda = None, build_env = None, mp = None):
        self._CONDA = 'conda'
        self._BUILD_ENV = 'FCBUILD'
        self._MP = 'foxcondadeps'

        if conda:
            self._CONDA = conda
        if build_env:
            self._BUILD_ENV = build_env
        if mp:
            self._MP = mp
        self._MP_VERSION = '0.1'

    def createMP(self, deps = []):
        self._packages = ''
        for _d in deps:
            if not _d.startswith(self._MP):
                self._packages += '        - %s\n' % _d
        try:
            os.makedirs('meta-recipe')
        except Exception, e:
            logging.warning(str(e))
            pass
        logging.debug(str(self.__dict__))

        with open(os.path.join('meta-recipe', 'meta.yaml'), 'w') as f:
            f.write(metatmpl % self.__dict__)

        cmd = self._CONDA + ' build meta-recipe'
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
        try:
            logging.debug(cmd)
            cmd = self._CONDA + ' remove -y -n ' + self._BUILD_ENV + ' --all'
            status = subprocess.call(cmd, shell=True)
        except:
            pass

    def collectPackages(self):
        packages = []
        for f in glob.glob(os.path.join(sys.prefix, 'envs', self._BUILD_ENV,
            'conda-meta', '*.json')):
            with open(f, 'r') as _f:
                _json = json.load(_f)
                _source = _json['link']['source'] + '.tar.bz2'
                if not os.path.exists(_source):
                    _p = subprocess.call('conda install -f -y {}'.format(_json['name']), stdout=None, stderr=None, stdin=None, shell=True)
                packages += [_source]
        self.packages = packages

    @staticmethod
    def findNewestPackage(name):
        _name = '-'.join([name, '*', '*.tar.bz2'])
        return [n for n in glob.glob(os.path.join(sys.prefix, 'pkgs', _name)) if
                len(os.path.basename(n).split('-')) ==
                len(_name.split('-'))][-1]

    def addNewestPackage(self, name):
        self.packages += [self.findNewestPackage(name)]



if __name__ == '__main__':
    pass


