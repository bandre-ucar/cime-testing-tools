#!/usr/bin/env python
"""Python driver for cesm test suite to automatically detect the
machine and run all aux_clm tests for all compilers on that machine.

Author: Ben Andre <andre@ucar.edu>

TODO(bja, 2015-08) change --component to --suite

TODO(bja, 2015-08) config file is getting kind of ucky, section
key-value pairs aren't working well any more, need to convert to a
sqlite database.

"""

# ------------------------------------------------------------------------------

from __future__ import print_function

import sys

if sys.hexversion < 0x02070000:
    print(70 * "*")
    print("ERROR: {0} requires python >= 2.7.x. ".format(sys.argv[0]))
    print("It appears that you are running python {0}".format(
        ".".join(str(x) for x in sys.version_info[0:3])))
    print(70 * "*")
    sys.exit(1)

# python standard library
import argparse
import datetime
import os
import os.path
import re
from string import Template
import subprocess
import time
import traceback

if sys.version_info[0] == 2:
    from ConfigParser import SafeConfigParser as config_parser
else:
    from configparser import ConfigParser as config_parser


# local packages
from cesm_machine import read_machine_config, find_src_root, get_machines_dir
from fortran_cprnc import build_cprnc


# ------------------------------------------------------------------------------
#
# globals
#
# ------------------------------------------------------------------------------

create_test_cmd_cime5 = Template("""
$batch ./create_test $nobatch --xml-category $suite \
--compiler $compiler \
--xml-machine $xml_machine --xml-compiler $xml_compiler \
$generate $baseline \
--test-root $test_root \
--test-id  $testid
""")

create_test_cmd_cime4 = Template("""
$batch ./create_test $nobatch -xml_category $suite \
-mach $machine -compiler $compiler \
-xml_mach $xml_machine -xml_compiler $xml_compiler \
$generate $baseline \
-testroot $test_root \
-testid  $testid
""")

# ------------------------------------------------------------------------------
#
#  process user input
#
# ------------------------------------------------------------------------------


def commandline_options():
    """Process the command line arguments.

    """
    options = {}
    parser = argparse.ArgumentParser(
        description='python program to automate launching cime test suites.')

    parser.add_argument('--backtrace', action='store_true',
                        help='show exception backtraces as extra debugging '
                        'output')

    parser.add_argument('--baseline', '-b', nargs=1, required=True,
                        help='baseline tag name')

    parser.add_argument('--test-suite', nargs=1, required=True,
                        help='component to test: clm, clm_short, pop')

    parser.add_argument('--config', nargs=1, default=[None, ],
                        help='path to test-cesm config file')

    parser.add_argument('--debug', action='store_true', default=False,
                        help='extra debugging output')

    parser.add_argument('--dry-run', action='store_true', default=False,
                        help='just setup commands to run tests, don\'t launch jobs')

    parser.add_argument('--generate', '-g', nargs=1, default=[''],
                        help='generate new baseline for the given tag name')

    options = parser.parse_args()

    return options


def read_suite_config(cfg_file, suite_name):
    """Read the configuration file and look for suite section. This
translates the testlist nonsence into simple test suites. Expected
format:


    [suites]
    suite_name = testlist_xml_name1, testlist_xml_name2
    clm = aux_clm40, aux_clm45

    """
    print("Reading configuration file : {0}".format(cfg_file))

    cfg_file = os.path.abspath(cfg_file)
    if not os.path.isfile(cfg_file):
        raise RuntimeError("Could not find config file: {0}".format(cfg_file))

    config = config_parser()
    config.read(cfg_file)
    section = 'suites'
    if not config.has_section(section):
        raise RuntimeError("ERROR: config file must contain a "
                           "'{0}' section.".format(section))

    suites = {}
    for option in config.options(section):
        tmp = config.get(section, option)
        suites[option] = tmp.split(',')
    for s in suites:
        suites[s] = [l.strip() for l in suites[s]]

    print("Known test suites:")
    for s in suites:
        print("  {0} : {1}".format(s, ', '.join(suites[s])))

    if suite_name not in suites:
        raise RuntimeError("ERROR: config file does not contain a test suite '{0}'".format(suite_name))

    return suites[suite_name]

# ------------------------------------------------------------------------------
#
# utility functions
#
# ------------------------------------------------------------------------------

def list_to_dict(input_list, upper_case=False):
    output_dict = {}
    for item in input_list:
        key = item[0]
        value = item[1]
        if upper_case is True:
            key = key.upper()
        output_dict[key] = value
    return output_dict


def run_command(command, logfile, background=False, dry_run=False):
    """Generic function to run a shell command, with timout limit, and
    append output to a log file.

    """
    cmd_status = 0
    print("-" * 80)
    print(" ".join(command))
    if dry_run:
        return cmd_status
    try:
        with open(logfile, 'w') as run_stdout:
            proc = subprocess.Popen(command,
                                    shell=False,
                                    stdout=run_stdout,
                                    stderr=subprocess.STDOUT)
            print("\nstarted as pid : {0}".format(proc.pid), file=run_stdout)
            print("\nstarted as pid : {0}".format(proc.pid))
            if not background:
                while proc.poll() is None:
                    time.sleep(10.0)
                cmd_status = abs(proc.returncode)
    except Exception as error:
        print("ERROR: Running command :\n    '{0}'".format(" ".join(command)))
        print(error)
        cmd_status = 1
    return cmd_status


def get_timestamp(now):
    timestamp = now.strftime("%Y%m%d-%H%M")
    timestamp_short = now.strftime("%m%d%H%M")
    #print(timestamp)
    return timestamp, timestamp_short


# -----------------------------------------------------------------------------

def run_test_suites(cime_major_version, machine, config, suite_list, timestamp, timestamp_short,
                    suite_name, baseline_tag, generate_tag, dry_run):

    suite_compilers = "{0}_compilers".format(suite_name)
    if suite_compilers in config:
        compilers = config[suite_compilers].split(', ')
    else:
        print("suite = {0}".format(suite_name))
        print("suite_compilers = {0}".format(suite_compilers))
        raise RuntimeError("machine config must specify compilers for test suite '{0}'".format(suite_name))

    if "compilers" in config:
        # check that the component compilers are actually available on
        # this machine.
        comp = config["compilers"].strip().split(",")
        comp = map(str.strip, comp)
        for c in compilers:
            cc = c.strip()
            if cc not in comp:
                raise RuntimeError("specified compiler for this test suite '{0}' is not available on this machine. available compilers are: {1}".format(cc, ",".join(comp)))
    else:
        raise RuntimeError("could not find compilers available on '{0}'.".format(machine))

    component_xml_machine = "{0}_xml_machine".format(suite_name)
    if component_xml_machine in config:
        xml_machine = config[component_xml_machine].strip()
    else:
        xml_machine = machine

    component_xml_compiler = "{0}_xml_compiler".format(suite_name)
    if component_xml_compiler in config:
        xml_compiler = config[component_xml_compiler].strip()
    else:
        xml_compiler = machine

    nobatch = ''
    if "no_batch" in config:
        if cime_major_version == 4:
            nobatch = "-nobatch {0}".format(config["no_batch"])
        else:  # elif cime_major_version == 5:
            nobatch = "--no-batch {0}".format(config["no_batch"])

    test_dir = "tests-{suite_name}-{timestamp}".format(
        suite_name=suite_name, timestamp=timestamp)
    test_root = "{0}/{1}".format(config["scratch_dir"],
                                 test_dir)
    if not os.path.isdir(test_root):
        print("Creating test root directory: {0}".format(test_root))
        if not dry_run:
            os.mkdir(test_root)

    baseline = ''
    if baseline_tag != '':
        if cime_major_version == 4:
            baseline = "-compare {0}".format(baseline_tag)
        else: #elif cime_major_version == 5:
            baseline = "--compare {0}".format(baseline_tag)            

    generate = ''
    if generate_tag != '':
        if cime_major_version == 4:
            generate = "-generate {0}".format(generate_tag)
        else: #elif cime_major_version == 5:
            generate = "--generate {0}".format(generate_tag)


    background = False
    if config["background"].lower().find('t') == 0:
        background = True

    for suite in suite_list:
        for compiler in compilers:
            testid = "{timestamp}-{suite}{compiler}".format(
                timestamp=timestamp_short, suite=suite[-2:],
                compiler=compiler[0])
            component_xml_compiler = "{0}_xml_compiler".format(suite_name)
            if component_xml_compiler in config:
                xml_compiler = config[component_xml_compiler].strip()
            else:
                xml_compiler = compiler

            if cime_major_version == 4:
                command = create_test_cmd_cime4.substitute(
                    config, nobatch=nobatch,
                    machine=machine, xml_machine=xml_machine,
                    compiler=compiler, xml_compiler=xml_compiler,
                    suite=suite,
                    baseline=baseline, generate=generate,
                    test_root=test_root, testid=testid)
            else:  # cime_major_version == 5:
                command = create_test_cmd_cime5.substitute(
                    config, nobatch=nobatch,
                    machine=machine, xml_machine=xml_machine,
                    compiler=compiler, xml_compiler=xml_compiler,
                    suite=suite,
                    baseline=baseline, generate=generate,
                    test_root=test_root, testid=testid)
            logfile = "{test_root}/{timestamp}.{suite}.{machine}.{compiler}.{suite_name}.tests.out".format(
                test_root=test_root, timestamp=timestamp,
                suite_name=suite_name, suite=suite,
                machine=machine, compiler=compiler)
            run_command(command.split(), logfile, background, dry_run)


def determine_cime_version(src_root):
    """Check the SVN_EXTERNAL_DIRECTORIES file for the cime version.
    """
    svn_external_directories = os.path.join(src_root, "SVN_EXTERNAL_DIRECTORIES")
    externals = []
    with open(svn_external_directories, 'r') as svn_extarnals:
        externals = svn_extarnals.readlines()

    cime_tag = None
    for line in externals:
        line = line.split()
        if line[0].strip() == 'cime':
            cime_url = line[1].split('/')
            cime_tag = cime_url[-1].strip()
            break

    cime_tag_re = re.compile('cime([\d.]+)')
    match = cime_tag_re.search(cime_tag)

    cime_version_major = 4
    if match:
        cime_version = match.group(1).split('.')
        cime_version_major = int(cime_version[0])

    print("Cime major version = {0}".format(cime_version_major))
    return cime_version_major


# -----------------------------------------------------------------------------
#
# main
#
# -----------------------------------------------------------------------------

def main(options):
    now = datetime.datetime.now()
    timestamp, timestamp_short = get_timestamp(now)
    orig_working_dir = os.getcwd()

    src_root = find_src_root(os.path.abspath(os.getcwd()))
    if not src_root:
        raise RuntimeError("Could not determine source directory root.")
    else:
        print("Found source root = {0}".format(src_root))

    machines_dir = get_machines_dir(src_root)
    if options.debug:
        print("Found machines dir = {0}".format(machines_dir))

    config_machines_xml = os.path.join(machines_dir, 'config_machines.xml')

    cfg_file = options.config[0]
    if not cfg_file:
        home_dir = os.path.expanduser("~")
        cfg_file = "{0}/.cime/cime-tests.cfg".format(home_dir)
    suite_list = read_suite_config(cfg_file, options.test_suite[0])

    machine, config = read_machine_config(cfg_file, config_machines_xml)

    build_cprnc(config["cprnc"])

    cime_version_major = determine_cime_version(src_root)

    scripts_dir = os.path.join(src_root, 'cime', 'scripts')
    if options.debug:
        print("Using cime scripts dir = {0}".format(scripts_dir))

    os.chdir(scripts_dir)
    run_test_suites(cime_version_major, machine, config, suite_list, timestamp,
                    timestamp_short, options.test_suite[0],
                    options.baseline[0], options.generate[0],
                    options.dry_run)
        
    os.chdir(orig_working_dir)

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
