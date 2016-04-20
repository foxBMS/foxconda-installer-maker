"""
:since:     Mon Apr 18 16:56:29 CEST 2016
:author:    Tim Fuehner <tim.fuehner@iisb.fraunhofer.de>
$Id$
"""

import argparse
import urllib2
import logging
import sys
import subprocess
import json

def main():


    parser = argparse.ArgumentParser(description='foxConda Installer---Repository Fetcher')
    parser.add_argument('--verbosity', '-v', action='count', default=0, help="increase output verbosity")
    parser.add_argument('--output', '-o', default='repodata.json', help="output file")
    parser.add_argument('channel', metavar = 'CHANNEL', help='channel to fetch repofile from')

    args = parser.parse_args()

    if args.verbosity == 1:
        logging.basicConfig(level = logging.INFO)
    elif args.verbosity > 1:
        logging.basicConfig(level = logging.DEBUG)
    else:
        logging.basicConfig(level = logging.WARNING)


    conda_info = json.loads(subprocess.check_output("conda info --json", shell=True))
    URL = args.channel + '/' + conda_info['platform'] + '/repodata.json'

    response = urllib2.urlopen(URL)
    repo = response.read()
    with open(args.output, 'w') as f:
        f.write(repo)


if __name__ == '__main__':
    main()
