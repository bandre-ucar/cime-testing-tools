#!/usr/bin/env python


from __future__ import print_function

import sys

if sys.hexversion < 0x02060000:
    print(70*"*")
    print("ERROR: {0} requires python >= 2.6.x. ".format(sys.argv[0]))
    print("It appears that you are running python {0}".format(
        ".".join(str(x) for x in sys.version_info[0:3])))
    print(70*"*")
    sys.exit(1)

import os
import os.path
import platform

if sys.version_info[0] == 2:
    from ConfigParser import SafeConfigParser as config_parser
else:
    from configparser import ConfigParser as config_parser

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
    if machine is None:
        message = "Could not identify machine from host name and config file.\n"
        message += "    hostname = {0}\n".format(hostname)
        message += "    config = {0}\n".format(config)
        raise RuntimeError(message)
    print("Running on : {0}".format(machine))
    return machine


def read_machine_config(cfg_file):
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
    print("Reading machine configuration file : {0}".format(cfg_file))

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
    machine = get_machine(config_dict)
    machine_config = config_dict[machine]
    for k in machine_config:
        print("  {0} : {1}".format(k, machine_config[k]))
    return machine, machine_config

