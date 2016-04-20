"""
:since:     Mon Apr 18 12:40:55 CEST 2016
:author:    Tim Fuehner <tim.fuehner@iisb.fraunhofer.de>
$Id$
"""

import json
import sys
import sdkconda
import tarfile
import os
import logging

class PayloadGenerator(object):

    IGNORE = ['conda', 'conda-env']

    def __init__(self, repofname = None, payloadname = 'payload.tar',
            conda = None, build_env = None, mp = None):
        self.repofname = repofname
        self.packages = None
        self.payloadname = payloadname
        self.conda = conda
        self.build_env = build_env
        self.mp = mp

    def readRepo(self):
        with open(self.repofname, 'r') as _f:
            self.packages = json.load(_f)['packages']

    def getPackageList(self):
        return [v['name'] for k,v in self.packages.iteritems() if not
                v['name'] in self.IGNORE]

    def collectPackageFiles(self):
        pl = self.getPackageList()
        print pl
        _conda = sdkconda.SDKFoxConda(self.conda, self.build_env, self.mp)
        _conda.createMP(pl)
        _conda.createBuildEnv()
        _conda.collectPackages()
        _conda.addNewestPackage('conda')
        _conda.addNewestPackage('conda-env')
        self.packagefiles = _conda.packages

    def generatePayload(self):
        _wd = os.path.abspath('.')
        with tarfile.open(self.payloadname, 'w') as _tar:
            for p in self.packagefiles:
                os.chdir(os.path.dirname(p))
                _tar.add(os.path.basename(p))
        os.chdir(_wd)

    def clean(self):
        _conda = sdkconda.SDKFoxConda().cleanBuildEnv()


def main():
    import argparse

    parser = argparse.ArgumentParser(description='foxConda Installer---Payload Generator')

    parser.add_argument('-v', '--verbosity', action='count', default=0, help="increase output verbosity")
    parser.add_argument('--output', '-o', default='payload.tar', help='write payload to this path')

    parser.add_argument('--conda', '-c', default='conda', help='path (relative or absolute) to conda')
    parser.add_argument('--buildenv', '-b', default='FCBUILD',
            help='temporary conda environment for payload build')
    parser.add_argument('--metapackage', '-m', default='foxcondadeps',
            help='metapackage containing dependencies (temp. use)')
    parser.add_argument('repository', metavar = 'REPOSITORY FILE',
            help='file containing list of packages to include in payload')

    args = parser.parse_args()

    if args.verbosity == 1:
        logging.basicConfig(level = logging.INFO)
    elif args.verbosity > 1:
        logging.basicConfig(level = logging.DEBUG)
    else:
        logging.basicConfig(level = logging.WARNING)

    pg = PayloadGenerator(args.repository, args.output, args.conda,
            args.buildenv, args.metapackage)
    pg.readRepo()
    pg.collectPackageFiles()
    pg.generatePayload()
    pg.clean()


if __name__ == '__main__':
    main()


