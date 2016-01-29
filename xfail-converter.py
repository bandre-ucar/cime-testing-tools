#!/usr/bin/env python
"""Convert old expected failures xml to new format.

Author: Ben Andre <andre@ucar.edu>

"""

from __future__ import print_function

import sys

if sys.hexversion < 0x02070000:
    print(70 * "*")
    print("ERROR: {0} requires python >= 2.7.x. ".format(sys.argv[0]))
    print("It appears that you are running python {0}".format(
        ".".join(str(x) for x in sys.version_info[0:3])))
    print(70 * "*")
    sys.exit(1)

#
# built-in modules
#
import argparse
import os
import traceback

if sys.version_info[0] == 2:
    from ConfigParser import SafeConfigParser as config_parser
else:
    from configparser import ConfigParser as config_parser

#
# installed dependencies
#

#
# other modules in this package
#

# -------------------------------------------------------------------------------
#
# User input
#
# -------------------------------------------------------------------------------

def commandline_options():
    """Process the command line arguments.

    """
    parser = argparse.ArgumentParser(
        description='convert old ExpectedTestFailures.xml format to new expected-test-failures.xml.')

    parser.add_argument('--backtrace', action='store_true',
                        help='show exception backtraces as extra debugging '
                        'output')

    parser.add_argument('--debug', action='store_true',
                        help='extra debugging output')

    parser.add_argument('--xfail-files', nargs='+', required=True,
                        help='path to expected failures file')

    options = parser.parse_args()
    return options



# -------------------------------------------------------------------------------
#
# worker classes
#
# -------------------------------------------------------------------------------
class ExpectedFailures(object):
    """
    """

    def __init__(self):
        self._tests = {}


# -------------------------------------------------------------------------------
#
# utility functions
#
# -------------------------------------------------------------------------------
def verify_existing_file(filename):
    """Check that the filename looks like an existing expected failures file
    """

    
# -------------------------------------------------------------------------------
#
# main
#
# -------------------------------------------------------------------------------
def main(options):
    xfail_files = options.xfail_files
    for f in xfail_files:
        print(xfail_files)
    return 0


if __name__ == "__main__":
    options = commandline_options()
    try:
        status = main(options)
        sys.exit(status)
    except Exception as error:
        print(str(error))
        if options.backtrace:
            traceback.print_exc()
        sys.exit(1)
