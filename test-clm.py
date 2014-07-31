#!/usr/bin/env python
"""Python driver for cesm test suite to automatically detect the
machine and run all aux_clm tests for all compilers on that machine.

Author: Ben Andre <bandre@lbl.gov>

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

aux_clm = Template("""
$batch ./create_test -xml_category $suite \
$generate $baseline -model_gen_comp clm2 \
-baselineroot $baseline_root -testroot $test_root \
-xml_mach $machine -xml_compiler $compiler -testid  $testid
""")

# ------------------------------------------------------------------------------


def commandline_options():
    """Process the command line arguments.

    """
    options = {}
    if sys.version_info[0] == 2 and sys.version_info[1] < 7:
        parser = optparse.OptionParser(
            description='python program to automate launching clm test suites.')

        parser.add_option('--backtrace', action='store_true',
                          help='show exception backtraces as extra debugging '
                          'output')

        parser.add_option('--baseline', '-b', nargs=1,
                          help='baseline tag name')

        parser.add_option('--config', nargs=1, default=[None, ],
                          help='path to test-clm config file')

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
            description='python program to automate launching clm test suites.')

        parser.add_argument('--backtrace', action='store_true',
                            help='show exception backtraces as extra debugging '
                            'output')

        parser.add_argument('--baseline', '-b', nargs=1, required=True,
                            help='baseline tag name')

        parser.add_argument('--config', nargs=1, default=[None, ],
                            help='path to test-clm config file')

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


def run_command(command, logfile, background, dry_run):
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
    suite_config.set(section, "expected_fail",
                     "{0}/../models/lnd/clm/bld/unit_testers/xFail/expectedClmTestFails.xml".format(os.getcwd()))

    filename = "{scratch_dir}/{test_dir}/{suite}.{compiler}.cfg".format(
        scratch_dir=machine_config["scratch_dir"], test_dir=test_dir,
        suite=suite, compiler=compiler)

    with open(filename, 'w') as config_file:
        suite_config.write(config_file)


def run_test_suites(machine, config, timestamp, baseline_tag, generate_tag, dry_run):

    if "compilers" in config:
        compilers = config["compilers"].split(', ')
    else:
        raise RuntimeError("machine config must specify compilers")

    if "suites" in config:
        suites = config["suites"].split(", ")
    else:
        raise RuntimeError("machine config must specify test suites")

    test_dir = "tests-{0}".format(timestamp)
    test_root = "{0}/{1}".format(config["scratch_dir"],
                                 test_dir)
    if not os.path.isdir(test_root):
        print("Creating test root directory: {0}".format(test_root))
        os.mkdir(test_root)

    baseline = "-compare {0}".format(baseline_tag)
    generate = ''
    if generate_tag != '':
        generate = "-generate {0}".format(generate_tag)

    background = False
    if config["background"].lower().find('t') == 0:
        background = True

    for suite in suites:
        for compiler in compilers:
            testid = "{0}-{1}-{2}".format(timestamp, suite[-2:], compiler[0])
            command = aux_clm.substitute(config, machine=machine,
                                         compiler=compiler, suite=suite,
                                         baseline=baseline, generate=generate,
                                         test_root=test_root, testid=testid)
            logfile = "{test_root}/{timestamp}.{suite}.{machine}.{compiler}.clm.tests.out".format(
                test_root=test_root, timestamp=timestamp, suite=suite,
                machine=machine, compiler=compiler)
            write_suite_config(test_dir, compiler, suite, config, baseline_tag,
                               testid, machine)
            run_command(command.split(), logfile, background, dry_run)


# -----------------------------------------------------------------------------


def main(options):
    now = datetime.datetime.now()
    timestamp = get_timestamp(now)
    machine, config = read_machine_config(options.config[0])

    run_test_suites(machine, config, timestamp, options.baseline[0],
                    options.generate[0], options.dry_run)

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
