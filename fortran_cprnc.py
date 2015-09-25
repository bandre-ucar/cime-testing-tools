#!/usr/bin/env python
"""Python module to deal with the cesm fortran cprnc tool

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
        description='FIXME: python program template.')

    parser.add_argument('--backtrace', action='store_true',
                        help='show exception backtraces as extra debugging '
                        'output')

    parser.add_argument('--debug', action='store_true',
                        help='extra debugging output')

    parser.add_argument('--config', nargs=1, required=True,
                        help='path to config file')

    options = parser.parse_args()
    return options


def read_config_file(filename):
    """Read the configuration file and process

    """
    print("Reading configuration file : {0}".format(filename))

    cfg_file = os.path.abspath(filename)
    if not os.path.isfile(cfg_file):
        raise RuntimeError("Could not find config file: {0}".format(cfg_file))

    config = config_parser()
    config.read(cfg_file)

    return config

# -------------------------------------------------------------------------------
#
# FIXME: work functions
#
# -------------------------------------------------------------------------------
# -----------------------------------------------------------------------------

def build_cprnc(cprnc_path):
    """
    """
    print(70*"=")
    print("Checking for cprnc...", end='')

    if cprnc_path.split("/")[0] != "$CCSMROOT":
        # not looking for a locally built cprnc, so assume we can
        # trust it is there. Probably not always as safe
        # assumption....!
        if cprnc_path[0] == "/":
            if not os.path.isfile(cprnc_path):
                raise RuntimeError("ERROR: cprnc specified as absolute path, but it does not exist!")
            else:
                print(" done")
        else:
            # not sure what else we can check....
            print()
            print("Assuming that cprnc exists at: {0}".format(cprnc_path))
        print(70*"=")
        return

    # need to check for local cprnc in ccsmroot!
    orig_dir = os.getcwd()
    if orig_dir.split("/")[-1] != "scripts":
        print("In directory : {0}".format(orig_dir))
        raise RuntimeError("this program must be run from the scripts directory to build cprnc.")

    # strip off the scripts dir
    cesm_root = os.path.dirname(orig_dir)
    cprnc_dir = "{0}/tools/cprnc".format(cesm_root)
    build_dir = "{0}/build".format(cprnc_dir)
    if os.path.isfile("{0}/cprnc".format(build_dir)):
        # don't rebuild cprnc if it already exists

        print("Found existing cprnc in CCSMROOT. Reusing instead of building.")
        print(70*"=")
        return

    if not os.path.isdir(build_dir):
        os.mkdir(build_dir)
    os.chdir(build_dir)
    # FIXME(bja, 2015-01) need to get compilers and lib dirs from xml file.
    command = ["cmake",
               "-DCMAKE_Fortran_COMPILER=mpif90",
               "-DHDF5_DIR=/usr/local",
               "-DNetcdf_INCLUDE_DIR=/usr/local/include",
               ".."]
    status = run_command(command, logfile="cprnc.cmakelog.txt")
    if status != 0:
        raise RuntimeError("ERROR could not run cmake for cprnc")
    command = ["make"]
    status = run_command(command, logfile="cprnc.buildlog.txt")
    if status != 0:
        raise RuntimeError("ERROR could not build cprnc")
    if not os.path.isfile("{0}/cprnc".format(build_dir)):
        raise RuntimeError("ERROR could not find cprnc executable!")
    else:
        print("Built cprnc!")
    os.chdir(orig_dir)
    print(70*"=")



# -------------------------------------------------------------------------------
#
# main
#
# -------------------------------------------------------------------------------

def main(options):
    config = read_config_file(options.config[0])
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
