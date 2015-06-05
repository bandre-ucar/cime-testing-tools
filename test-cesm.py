#!/usr/bin/env python
"""Python driver for cesm test suite to automatically detect the
machine and run all aux_clm tests for all compilers on that machine.

Author: Ben Andre <andre@ucar.edu>

"""

# ------------------------------------------------------------------------------

from __future__ import print_function

import sys

if sys.hexversion < 0x02060000:
    print(70 * "*")
    print("ERROR: {0} requires python >= 2.6.x. ".format(sys.argv[0]))
    print("It appears that you are running python {0}".format(
        ".".join(str(x) for x in sys.version_info[0:3])))
    print(70 * "*")
    sys.exit(1)

import datetime
import os
import os.path
from string import Template
import subprocess
import time
import traceback

if sys.version_info[0] == 2:
    from ConfigParser import SafeConfigParser as config_parser
else:
    from configparser import ConfigParser as config_parser

if sys.version_info[0] == 2 and sys.version_info[1] < 7:
    import optparse
else:
    import argparse


from cesm_machine import read_machine_config


# ------------------------------------------------------------------------------

create_test_cmd = Template("""
$batch ./create_test $nobatch -xml_category $suite \
-mach $machine \
-xml_mach $xml_machine -xml_compiler $compiler \
$generate $baseline \
-testroot $test_root \
-testid  $testid
""")

# ------------------------------------------------------------------------------


def commandline_options():
    """Process the command line arguments.

    """
    options = {}
    if sys.version_info[0] == 2 and sys.version_info[1] < 7:
        parser = optparse.OptionParser(
            description='python program to automate launching cesm test suites.')

        parser.add_option('--backtrace', action='store_true',
                          help='show exception backtraces as extra debugging '
                          'output')

        parser.add_option('--baseline', '-b', nargs=1,
                          help='baseline tag name')

        parser.add_option('--component', nargs=1, default=[None, ],
                            help='component to test: clm, pop')

        parser.add_option('--config', nargs=1, default=[None, ],
                          help='path to test-cesm config file')

        parser.add_option('--debug', action='store_true', default=False,
                          help='extra debugging output')

        parser.add_option('--dry-run', action='store_true', default=False,
                          help='just setup commands to run tests, don\'t launch jobs')

        parser.add_option('--generate', '-g', nargs=1, default=None,
                          help='generate new baseline for the given tag name')

        (options, args) = parser.parse_args()
        if options.baseline is None:
            raise RuntimeError(
                "baseline must be specified on the command line!")
        else:
            options.baseline = [options.baseline]

        if options.generate is None:
            options.generate = ['']
        else:
            options.generate = [options.generate]

    else:
        parser = argparse.ArgumentParser(
            description='python program to automate launching cesm test suites.')

        parser.add_argument('--backtrace', action='store_true',
                            help='show exception backtraces as extra debugging '
                            'output')

        parser.add_argument('--baseline', '-b', nargs=1, required=True,
                            help='baseline tag name')

        parser.add_argument('--component', nargs=1, default=[None, ],
                            help='component to test: clm, pop')

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


# -----------------------------------------------------------------------------

def get_timestamp(now):
    timestamp = now.strftime("%Y%m%d-%H")
    print(timestamp)
    return timestamp


def write_suite_config(test_dir, compiler, suite, machine_config, baseline_tag,
                       testid, machine):
    suite_config = config_parser()
    section = machine
    suite_config.add_section(section)
    suite_config.set(section, "compiler", compiler)
    suite_config.set(section, "suite", suite)
    suite_config.set(section, "testid", testid)
    suite_config.set(section, "scratch_dir", machine_config["scratch_dir"])
    suite_config.set(section, "test_data_dir", test_dir)
    suite_config.set(section, "baseline", baseline_tag)
    suite_config.set(section, "status", "cs.status.{testid}.{machine}".format(
        testid=testid, machine=machine))
    xfails_file = os.path.abspath("{0}/../models/lnd/clm/bld/unit_testers/xFail/expectedClmTestFails.xml".format(os.getcwd()))
    if not os.path.isfile(xfails_file):
        xfails_file = ""
    suite_config.set(section, "expected_fail", xfails_file)
    suite_config.set(section, "cesm_src_dir", machine_config["cesm_src_dir"])

    filename = "{scratch_dir}/{test_dir}/{suite}.{compiler}.cfg".format(
        scratch_dir=machine_config["scratch_dir"], test_dir=test_dir,
        suite=suite, compiler=compiler)

    with open(filename, 'w') as config_file:
        suite_config.write(config_file)


def run_test_suites(machine, config, timestamp, component,
                    baseline_tag, generate_tag, dry_run):

    component_compilers = "{0}_compilers".format(component)
    if component_compilers in config:
        compilers = config[component_compilers].split(', ')
    else:
        print("component = {0}".format(component))
        print("component_compilers = {0}".format(component_compilers))
        raise RuntimeError("machine config must specify compilers for component '{0}'".format(component))

    machine_compilers = "machine_compilers"
    if machine_compilers in config:
        # check that the component compilers are actually available on this machine.
        comp = config[machine_compilers].strip().split(",")
        comp = map(str.strip, comp)
        for c in compilers:
            cc = c.strip()
            if cc not in comp:
                raise RuntimeError("specified compiler for this test suite '{0}' is not available on this machine. available compilers are: {1}".format(cc, ",".join(comp)))
    else:
        raise RuntimeError("could not find compilers available on this machine.")

    component_suite = "{0}_suites".format(component)
    if component_suite in config:
        suites = config[component_suite].split(", ")
    else:
        raise RuntimeError("machine config must specify test suites for component '{0}'".format(component))

    component_xml_machine = "{0}_xml_machine".format(component)
    if component_xml_machine in config:
        xml_machine = config[component_xml_machine].strip()
    else:
        xml_machine = machine

    nobatch = ''
    if "no_batch" in config:
        nobatch = "-nobatch {0}".format(config["no_batch"])

    test_dir = "tests-{component}-{timestamp}".format(
        component=component, timestamp=timestamp)
    test_root = "{0}/{1}".format(config["scratch_dir"],
                                 test_dir)
    if not os.path.isdir(test_root):
        print("Creating test root directory: {0}".format(test_root))
        os.mkdir(test_root)

    baseline = ''
    if baseline_tag != '':
        baseline = "-compare {0}".format(baseline_tag)

    generate = ''
    if generate_tag != '':
        generate = "-generate {0}".format(generate_tag)

    background = False
    if config["background"].lower().find('t') == 0:
        background = True

    for suite in suites:
        for compiler in compilers:
            testid = "{timestamp}-{suite}{compiler}".format(
                timestamp=timestamp, suite=suite[-2:],
                compiler=compiler[0])
            command = create_test_cmd.substitute(
                config, nobatch=nobatch,
                machine=machine, xml_machine=xml_machine,
                compiler=compiler, suite=suite,
                baseline=baseline, generate=generate,
                test_root=test_root, testid=testid)
            logfile = "{test_root}/{timestamp}.{suite}.{machine}.{compiler}.{component}.tests.out".format(
                test_root=test_root, timestamp=timestamp,
                component=component, suite=suite,
                machine=machine, compiler=compiler)
            write_suite_config(test_dir, compiler, suite, config, baseline_tag,
                               testid, machine)
            run_command(command.split(), logfile, background, dry_run)


# -----------------------------------------------------------------------------

def build_cprnc(config):
    """
    """
    print(70*"=")
    print("Checking for cprnc...", end='')
    # print(config)
    cprnc_path = config["cprnc"]
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

# -----------------------------------------------------------------------------

def main(options):
    now = datetime.datetime.now()
    timestamp = get_timestamp(now)

    # NOTE(bja, 2015-02) assume that we are being called from the
    # scripts directory! creating an absolute path from this relative
    # location, calling create_test, etc.
    scripts_dir = os.path.abspath(os.getcwd())
    config_machines_xml = os.path.abspath(os.path.join(scripts_dir, "../machines/config_machines.xml"))
    if not os.path.isfile(config_machines_xml):
        raise RuntimeError("Could not find cesm supplied config_machines.xml, expected:\n    {0}".format(config_machines_xml))

    machine, config = read_machine_config(options.config[0], config_machines_xml)

    #
    cesm_src_dir = os.path.abspath(os.path.join(scripts_dir, ".."))
    if not os.path.isdir(cesm_src_dir):
        raise RuntimeError("Could not determine cesm source directory root. expected: {0}".format(cesm_src_dir))
    config["cesm_src_dir"] = cesm_src_dir
    
    build_cprnc(config)

    run_test_suites(machine, config, timestamp, options.component[0],
                    options.baseline[0], options.generate[0],
                    options.dry_run)

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
