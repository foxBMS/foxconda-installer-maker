"""
:since:     Wed Apr 20 20:23:56 CEST 2016
:author:    Tim Fuehner <tim.fuehner@iisb.fraunhofer.de>
$Id$
"""

import argparse
import logging
import cliinstaller


def main():

    parser = argparse.ArgumentParser(description='foxConda Installer---Payload Generator')

    parser.add_argument('-v', '--verbosity', action='count', default=0, help="increase output verbosity")
    parser.add_argument('--installdir', '-d', default=None, help='installation directory')
    parser.add_argument('--no-gui', '-n', action='store_true', help='command line installer')

    args = parser.parse_args()

    if args.verbosity == 0:
        logging.basicConfig(level = logging.INFO)
    elif args.verbosity > 1:
        logging.basicConfig(level = logging.DEBUG)

    if args.no_gui:
        import cliinstaller
        cliinstaller.main(args.installdir)
    else:
        import guiinstaller
        guiinstaller.main(args.installdir)


if __name__ == '__main__':
    main()
