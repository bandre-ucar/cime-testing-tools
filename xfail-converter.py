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
            issue = ""
            if 'bugz' in xf_xml.attrib:
                issue = xf_xml.attrib['bugz']
            name, failure_type, component, section, note = self._parse_status_line(xf_xml.text)
            if name not in self._expected_fails:
                self._expected_fails[name] = {}
            xfail = self._expected_fails[name]

            if 'failures' not in xfail:
                xfail['failures'] = []
            failures = xfail['failures']
            
            failure = None
            for fail in failures:
                if issue == fail['issue'] and failure_type == fail['type']:
                    failure = fail
            if not failure:
                failure = {}
                failure['issue'] = issue
                failure['type'] = failure_type
                failures.append(failure)

            if section:
                if 'section' not in failure:
                    failure['section'] = []
                section_list = failure['section']
                current_section = None
                for sect in section_list:
                    if sect['name'] == section:
                        current_section = sect
                if not current_section:
                    current_section = {}
                    current_section['name'] = section
                    section_list.append(current_section)
                if component:
                    if 'component' not in current_section:
                        current_section['component'] = []
                    component_list = current_section['component']
                    current_component = None
                    for comp in component_list:
                        if comp['name'] == component:
                            current_component = comp
                    if not current_component:
                        current_component = {}
                        current_component['name'] = component
                        component_list.append(current_component)
                    if note:
                        if 'note' not in current_component:
                            current_component['note'] = []
                        note_list = current_component['note']
                        current_note = None
                        for iter_note in note_list:
                            if note == iter_note:
                                current_note = True
                        if not current_note:
                            note_list.append(note)

        for xfail in self._expected_fails:
            print(self._expected_fails[xfail])

    def _parse_status_line(self, line):
        """parse a status line to extract the useful information.
        Parsing rules:
        1) split on ':'
           the first group is the status, the second (if present) is the comment.
        2) in the first group, split on space ' ':
           the first group is the status, the second is a name field
        """
        note_re = re.compile('\((.+)\)')

        split_line = line.split(':')
        status_and_name = split_line[0].strip()
        comment = None
        if len(split_line) > 1:
            comment = split_line[1].strip()

        split_status_and_name = status_and_name.split(' ')
        status = split_status_and_name[0]
        name = None
        if len(split_status_and_name) > 1:
            name = split_status_and_name[1]
            name = name.split('.')
            name = '.'.join(name[0:5])
            if 'FAIL' in name:
                print(line)
        else:
            print(status_and_name)
        test_re = re.compile('test')
        component = None
        section = None
        note = None
        if comment:
            split_comment = comment.split(' ')
            if ('baseline compare' in comment or
                'generate' in comment or
                'test' in comment):
                component = split_comment[2]
            elif 'successful' in comment:
                component = 'status'
            else:
                component = 'unknown'

            if 'baseline' in comment:
                section = 'baseline compare'
            elif 'test compare' in comment:
                section = 'test compare'
            else:
                section = 'unknown'
            note = note_re.search(comment)
            if note:
                note = note.group(1)

        return name, status, component, section, note

    def _verify_xfails(self):
        """
        """
        orig_num_xfails = 0
        if self._xml_orig_version.split('.')[0] == '1':
            orig_num_xfails = len(self._xml_orig.findall('./entry'))
        print('origin xfails = {0}'.format(orig_num_xfails))
        current_num_xfails = len(self._xml_new.findall('./test/failure'))
        print('current xfails = {0}'.format(current_num_xfails))

    def write_updated_file(self):
        """
        """
        self._set_new_filename()

        root = etree.Element('expected_test_failures')
        root.set('version', '2.0.0')
        for xfail in self._expected_fails:
            #print('{0} : {1}'.format(xfail, self._expected_fails[xfail]))
            test = etree.Element('test')
            test.set('name', xfail)
            for fail in self._expected_fails[xfail]['failures']:
                failure = etree.Element('failure')
                if 'type' in fail:
                    failure.set('type', fail['type'])
                if 'issue' in fail:
                    if fail['issue']:
                        failure.set('issue', fail['issue'])
                if 'section' in fail:
                    for sect in fail['section']:
                        section = etree.Element('section')
                        section.set('name', sect['name'])
                        if 'component' in sect:
                            for comp in sect['component']:
                                component = etree.Element('component')
                                component.set('name', comp['name'])
                                if 'note' in comp:
                                    for cur_note in comp['note']:
                                        note = etree.Element('note')
                                        note.text = cur_note
                                        component.append(note)
                                section.append(component)
                        failure.append(section)
                test.append(failure)
            root.append(test)

        self._xml_new = etree.ElementTree(root)

        self._verify_xfails()
        
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
