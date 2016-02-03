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
import re
import traceback

try:
    import lxml.etree as etree
except:
    import xml.etree.ElementTree as etree

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
        """
        """
        self._filename_orig = None
        self._xml_orig_version = None
        self._xml_orig = None
        
        self._filename_new = 'expected-test-failures.xml'
        self._xml_new = None
        self._xml_new_version = '2.0.0'
        
        self._expected_fails = {}

    def read_xml_from_file(self, filename):
        """Try to open the user specified file and extract the xfails xml
        root.

        """
        print('processing file {0}'.format(filename))
        self._filename_orig = filename
        root = None
        xml_version = None
        #filename = os.path.abspath(filename)
        try:
            xml = etree.parse(filename)
        except IOError as e:
            print(e)
            msg = "Problem opening file. Skipping : {0}".format(filename)
            print(msg)
            return None, None
        except ParseError as e:
            msg = 'Error processing xml file. Skippping : {0}'.format(filename)
            print(e)
            return None, None
    
        root = xml.getroot()
            
        self._xml_orig = root
    
    def extract_from_xml(self, xml=None):
        """
        """
        if xml is not None:
            self._xml_orig = xml

        self._set_xml_orig_version()
        self._extract_xfails_from_xml()

    def _set_xml_orig_version(self):
        """
        """
        version = None
        if 'version' in self._xml_orig.attrib:
            version = self._xml_orig.attrib['version']
        elif self._xml_orig.tag == 'expectedFails':
            version = '1.0.0'
        else:
            msg = ('Unknown expectedFails xml format.'
                   'Skipping {1}'.format(self._filename_orig))
            raise RuntimeError(msg)

        self._xml_orig_version = version

    def _extract_xfails_from_xml(self):
        """
        """
        if self._xml_orig_version[0] == '1':
            self._extract_xfails_from_xml_v1()
        else:
            raise RuntimeError('extract xfails from version > 1 not implemnted.')

    def _extract_xfails_from_xml_v1(self):
        """
        """
        compare_re = re.compile('([\w]) compare ([\w]+\.[\w]+) \(')
        detail_re = re.compile('\([\w\s]+\)')
        for xf_xml in self._xml_orig.findall('entry'):
            xfail = {}
            if 'bugz' in xf_xml.attrib:
                xfail['issue'] = xf_xml.attrib['bugz']
            info = xf_xml.text
            info = info.split(':')
            test_info = info[0].split()
            xfail['failure_type'] = test_info[0]
            name = test_info[1].split('.')
            junk = None
            if len(name) > 5:
                junk = '.'.join(name[5:-1])
            name = '.'.join(name[0:5])
            if junk:
                # FIXME(bja, 2016-02) don't think there is any useful info
                # here...
                xfail['misc'] = junk
            comment = None
            if len(info) > 1:
                comment = ' '.join(info[1:]).strip()
                compare = compare_re.search(comment)
                if compare:
                    if not 'section' in xfail:
                        xfail['section'] = []
                    
                    section = {}
                    section['name'] = compare.group(1)
                    section['subsection'] = {}
                    section['subsection']['name'] = compare.group(2)
                    xfail['section'].append(section)
            if comment:
                xfail['comment'] = comment
            if comment:
                # try to extract some info from the comment....
                pass
            # FIXME(bja, 2016-01) multiple failures for a test...?
            self._expected_fails[name] = xfail
        #print(self._expected_fails)

    def write_updated_file(self):
        """
        """
        self._set_new_filename()

        root = etree.Element('expected_test_failures')
        root.set('version', '2.0.0')
        for xfail in self._expected_fails:
            test = etree.Element('test')
            test.set('name', xfail)
            test.set('failure_type', self._expected_fails[xfail]['failure_type'])
            for key in self._expected_fails[xfail]:
                section = None
                if key is 'section':
                    section = etree.Element('section')
                    for sub_key in self._expected_fails[xfail][key]:
                        subsection = None
                        if sub_key is 'name':
                            section.set(sub_key, self._expected_fails[xfail][key][sub_key])
                        else:
                            subsection = etree.Element('subsection')                    
                        if subsection is not None:
                            section.append(subsection)
                else:
                    test.set(key, self._expected_fails[xfail][key])
                if section is not None:
                    test.append(section)
                
            root.append(test)

        self._xml_new = etree.ElementTree(root)
        
        from xml.dom import minidom
        doc = minidom.parseString(etree.tostring(self._xml_new.getroot()))
        with open(self._filename_new, 'w') as xmlout: 
            doc.writexml(xmlout, addindent='    ', newl='\n')        
            

    def _set_new_filename(self):
        """
        """
        fname = self._filename_orig.split('.')
        name = fname[0].split('_')
        identifier = None
        if len(name) > 1:
            identifier = name[-1]
        if identifier:
            self._filename_new = 'expected-test-failures-{0}.xml'.format(identifier)
        
# -------------------------------------------------------------------------------
#
# utility functions
#
# -------------------------------------------------------------------------------
# -------------------------------------------------------------------------------
#
# main
#
# -------------------------------------------------------------------------------
def main(options):
    xfail_files = options.xfail_files
    for f in xfail_files:
        xfail = ExpectedFailures()
        xfail.read_xml_from_file(f)
        xfail.extract_from_xml()
        xfail.write_updated_file()
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
