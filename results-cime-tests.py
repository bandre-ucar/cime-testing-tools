#!/usr/bin/env python
"""FIXME: A nice python program to do something useful.

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
import fnmatch
import os
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

    parser.add_argument('--test-spec', nargs='+', default=[''],
                        help='path to test specification file(s)')

    options = parser.parse_args()
    return options


# -------------------------------------------------------------------------------
#
# FIXME: work functions
#
# -------------------------------------------------------------------------------
def locate(pattern, root=os.curdir):
    """Locate all files matching supplied filename pattern in and below
    supplied root directory.
    http://code.activestate.com/recipes/499305-locating-files-throughout-a-directory-tree/
    """
    for path, dirs, files in os.walk(os.path.abspath(root)):
        for filename in fnmatch.filter(files, pattern):
            yield os.path.join(path, filename)
            

def get_xml_root(test_spec_filename):
    """
    """
    print("Extracting xml root data from file...")
    filename = os.path.abspath(test_spec_filename)
    if os.path.isfile(filename):
        print("Reading file: {0}".format(filename))
        xml_tree = etree.parse(filename)
    else:
        raise RuntimeError(
            "ERROR: xml file does not exist: {0}".format(test_spec_filename))
        
    return xml_tree.getroot()
    

def find_expected_fail_files(src_root):
    """Search the source tree for all expected fail tests files.

    """
    print("Searching for expected failures files in:")
    print("  {0}".format(src_root))
    xfail_name = "ExpectedTestFails.xml"
    print("Expected failures files:")
    xfail_files = []
    for xfail_file in locate(xfail_name, src_root):
        filename = os.path.abspath(xfail_file)
        print("  {0}".format(filename))
        xfail_files.append(filename)
    return xfail_files


def xfail_xml_to_dict(xfail_xml, xfails):
    """
    """
    expected_fails = xfail_xml.findall('.//entry')
    for xfail in expected_fails:
        failure = xfail.text.strip()
        info = failure.split(' ', 2)
        name = info[1]
        status = info[0]
        comment = ''
        if len(info) == 3:
            comment = info[2]
        bugz = xfail.attrib.get('bugz')
        xfails[name] = {'status': status,
                        'bug_id': bugz,
                        'comment': comment,
        }


def get_test_list(test_root, test_list):
    """Get the list of test names and case directories from the testspec
    xml.

    """
    for test in test_root.findall('.//test'):
        case_dir = test.attrib.get('case')
        test_name = test.find('.//casebaseid').text
        test_list[test_name] = {'case_dir': case_dir,
        }

    

    
# -------------------------------------------------------------------------------
#
# main
#
# -------------------------------------------------------------------------------

def main(options):

    # TODO(bja, 2015-10) if options.test_spec is empty, then find all
    # testspecs in the current working directory.
    test_specifications = options.test_spec
    for test_spec in test_specifications:
        test_spec_filename = os.path.abspath(test_spec)
        test_root = get_xml_root(test_spec_filename)
        print(test_root)
        cime_root = test_root.find('.//cimeroot').text
        print('cime root = {0}'.format(cime_root))
        # FIXME(bja, 2015-10) need to account for standalone cime
        # where source root doesn't exist...
        src_root = os.path.abspath(os.path.join(cime_root, '..'))
        print('src root = {0}'.format(src_root))
        expected_fail_files = find_expected_fail_files(src_root)
        xfails = {}
        for xfail_file in expected_fail_files:
            xfail_xml = get_xml_root(xfail_file)
            xfail_xml_to_dict(xfail_xml, xfails)

        
        test_list = {}
        get_test_list(test_root, test_list)

        for test_name in test_list:
            if test_name in xfails:
                print("xfail {0}".format(test_name))
        
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
