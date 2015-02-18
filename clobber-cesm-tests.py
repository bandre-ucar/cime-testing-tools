#!/usr/bin/env python
"""FIXME: A nice python program to clobber all the files created by running the cesm test suite.

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

import argparse
import os
import shutil
import traceback

try:
    import lxml.etree as etree
except:
    import xml.etree.ElementTree as etree

if sys.version_info[0] == 2:
    from ConfigParser import SafeConfigParser as config_parser
else:
    from configparser import ConfigParser as config_parser

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

    parser.add_argument('--test-spec', nargs=1, required=True,
                        help='path to test spec file')

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
def get_vars_from_test_spec(test_spec_filename):
    """
    """
    print("Extracting test data from testspec file...")
    filename = os.path.abspath(test_spec_filename)
    if os.path.isfile(filename):
        print("Reading file: {0}".format(filename))
        xml_tree = etree.parse(filename)
        
    # need the test root
    

# -------------------------------------------------------------------------------
#
# main
#
# -------------------------------------------------------------------------------

def main(options):
    for c in options.config:
        config_path = os.path.abspath(c)
        config = read_config_file(config_path)

        test_root = os.path.dirname(config_path)
        print("Config path : {0}".format(config_path))
        print("test_root : {0}".format(test_root))

        # assume that we have only a single machine section
        machine = config.sections()[0]
        test_id = config.get(machine, "testid")
        print("test_id : {0}".format(test_id))
        test_spec = "testspec.{0}.{1}.xml".format(test_id, machine)
        print("test_spec : {0}".format(test_spec))

        scratch_dir = config.get(machine, "scratch_dir")
        print("scratch_dir : {0}".format(scratch_dir))

        xml_tree = etree.parse("{0}/{1}".format(test_root, test_spec))
        print("xml_tree = ", xml_tree)
        print("xml_tree.getroot() = ", xml_tree.getroot())
        testlist = xml_tree.findall("./test")
        print(testlist)
        for test in testlist:
            print("test : {0}".format(test))
            test_dir = test.attrib["case"]
            print("  case : {0}".format(test_dir))
            case_path = "{0}/{1}".format(test_root, test_dir)
            print(case_path)
            case_runbld_path = "{0}/{1}".format(scratch_dir, test_dir)
            print(case_runbld_path)
            archive_dir = "{0}/{1}".format(scratch_dir, "archive")
            archive_path = "{0}/{1}".format(archive_dir, test_dir)
            print(archive_path)
            archive_locked_dir = "{0}/{1}".format(scratch_dir, "archive.locked")
            archive_locked_path = "{0}/{1}".format(archive_locked_dir, test_dir)
            print(archive_locked_path)

            shutil.rmtree(archive_locked_path, ignore_errors=True)
            shutil.rmtree(archive_path, ignore_errors=True)
            shutil.rmtree(case_runbld_path, ignore_errors=True)
            shutil.rmtree(case_path, ignore_errors=True)

        sharedlibroot = xml_tree.find("sharedlibroot").text
        print("shared lib root : {0}".format(sharedlibroot))
        shutil.rmtree(sharedlibroot, ignore_errors=True)
        shutil.rmtree(test_root, ignore_errors=True)
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
