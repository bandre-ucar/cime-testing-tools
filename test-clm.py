#!/usr/bin/env python
"""Python driver for cesm test suite to automatically detect the
machine and run all aux_clm tests for all compilers on that machine.

Author: Ben Andre <bandre@lbl.gov>

"""

#-------------------------------------------------------------------------------

from __future__ import print_function

import sys

if sys.hexversion < 0x02070000:
    print(70*"*")
    print("ERROR: {0} requires python >= 2.7.x. ".format(sys.argv[0]))
    print("It appears that you are running python {0}".format(
        ".".join(str(x) for x in sys.version_info[0:3])))
    print(70*"*")
    sys.exit(1)

import argparse
import datetime
import os
import os.path
import platform
from string import Template
import subprocess
import time
import traceback

if sys.version_info[0] == 2:
    from ConfigParser import SafeConfigParser as config_parser
else:
    from configparser import ConfigParser as config_parser

#-------------------------------------------------------------------------------

aux_clm = Template("""
$batch ./create_test -xml_category $suite \
$generate $baseline -model_gen_comp clm2 \
-baselineroot $baseline_root -testroot $test_root \
-xml_mach $machine -xml_compiler $compiler -testid  $testid
"""
)

#-------------------------------------------------------------------------------

def commandline_options():
    """Process the command line arguments.

    """
    parser = argparse.ArgumentParser(description='FIXME: python program template.')

    parser.add_argument('--backtrace', action='store_true',
                        help='show exception backtraces as extra debugging '
                        'output')

    parser.add_argument('--baseline', '-b', nargs=1, required=True,
                        help='baseline tag name')

    parser.add_argument('--config', nargs=1, default=[None,],
                        help='path to test-clm config file')

    parser.add_argument('--debug', action='store_true', default=False,
                        help='extra debugging output')

    parser.add_argument('--dry-run', action='store_true', default=False,
                        help='extra debugging output')

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


def read_config_file(cfg_file):
    """Read the configuration file and convert to a dict. Expected format:


    [yellowstone]
    host=yslogin
    BATCH=execca
    BACKGRLOUND=&
    CESM_INPUTDATA=/glade/p/cesm/cseg/inputdata
    BASELINE_ROOT/=glade/p/cseg/ccsm_baselines
    SCRATCH_DIR=/glade/scratch/andre
    COMPILERS=intel, pgi
    suites=aux_clm45, aux_clm40

    """
    if not cfg_file:
        home_dir = os.path.expanduser("~")
        cfg_file = "{0}/.cesm/test-clm.cfg".format(home_dir)
    print("Reading configuration file : {0}".format(cfg_file))

    cfg_file = os.path.abspath(cfg_file)
    if not os.path.isfile(cfg_file):
        raise RuntimeError("Could not find config file: {0}".format(cfg_file))

    config = config_parser()
    config.read(cfg_file)
    config_dict = {}
    for s in config.sections():
        config_dict[s] = {}
        for i in config.items(s):
            key = i[0]
            value = i[1]
            config_dict[s][key] = value
    return config_dict

def run_command(command, logfile, background, dry_run):
    """Generic function to run a shell command, with timout limit, and
    append output to a log file.

    """
    cmd_status = 0
    print("-"*80)
    print(" ".join(command))
    if dry_run:
        return cmd_status
    try:
        with open(logfile, 'w') as run_stdout:
            start = time.time()
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
    except Exception as e:
        print("ERROR: Running command :\n    '{0}'".format(" ".join(command)))
        print(e)
        cmd_status = 1
    return cmd_status


#------------------------------------------------------------------------------

def get_timestamp(now):
    timestamp = now.strftime("%Y%m%d-%H")
    print(timestamp)
    return(timestamp)
    

def get_hostname():
    hostname = platform.node()
    index = hostname.find(".")
    if index > 0:
        hostname = hostname[0:index]

    return hostname

def get_machine(config):
    machine = None
    hostname = get_hostname()
    for m in config:
        if (config[m]["host"] in hostname or
            hostname in config[m]["host"]):
            machine = m
    print("Running on : {0}".format(machine))
    return machine

def write_test_description_file(test_root, compiler, suite, config, baseline_tag, testid, machine):
    filename = "{test_root}/{suite}.{compiler}.info.txt".format(test_root=test_root, suite=suite, compiler=compiler)
    with open(filename, 'w') as info:
        info.write("scratch_dir = {0}\n".format(config["scratch_dir"]))
        info.write("test_data_dir = {0}\n".format(test_root))
        info.write("baseline = {0}\n".format(baseline_tag))
        info.write("{compiler}_status = cs.status.{testid}.{machine}\n".format(compiler=compiler, testid=testid, machine=machine))
        info.write("expected_fail = {0}/../models/lnd/clm/bld/unit_testers/xFail/expectedClmTestFails.xml\n".format(os.getcwd()))


def run_test_suites(machine, config, timestamp, baseline_tag, dry_run):

    if config.has_key("compilers"):
        compilers = config["compilers"].split(', ')
    else:
        raise RuntimeError("machine config must specify compilers")

    if config.has_key("suites"):
        suites = config["suites"].split(", ")
    else:
        raise RuntimeError("machine config must specify test suites")
        

    test_dir = "tests-{1}".format(timestamp)
    test_root = "{0}/{1}".format(config["scratch_dir"],
                                 test_dir)
    if not os.path.isdir(test_root):
        os.mkdir(test_root)

    baseline = "-baseline {0}".format(baseline_tag)

    background = False
    if config["background"].lower().find('t') == 0:
        background = True

    for s in suites:
        for c in compilers:
            testid = "{0}-{1}-{2}".format(timestamp, s, c)
            command = aux_clm.substitute(config, machine=machine, compiler=c, suite=s,
                                         baseline=baseline, generate='',
                                         test_root=test_root, testid=testid)
            logfile="{test_root}/{timestamp}.{suite}.{machine}.{compiler}.clm.tests.out".format(test_root=test_dir, timestamp=timestamp, suite=s, machine=machine, compiler=c)
            write_test_description_file(test_root, c, s, config, baseline_tag, testid, machine)
            run_command(command.split(), logfile, background, dry_run)


#------------------------------------------------------------------------------


def main(options):
    now = datetime.datetime.now()
    timestamp = get_timestamp(now)
    config = read_config_file(options.config[0])
    machine = get_machine(config)
    if config.has_key(machine):
        for k in config[machine]:
            print("  {0} : {1}".format(k, config[machine][k]))
        run_test_suites(machine, config[machine], timestamp, options.baseline[0], options.dry_run)

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
