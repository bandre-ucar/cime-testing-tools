#!/usr/bin/env python
"""Reusable code to determine the machine name we are running on and
read a config file of data for creating a cesm user defined machine.

"""

from __future__ import print_function

import sys

if sys.hexversion < 0x02060000:
    print(70 * "*")
    print("ERROR: {0} requires python >= 2.6.x. ".format(sys.argv[0]))
    print("It appears that you are running python {0}".format(
        ".".join(str(x) for x in sys.version_info[0:3])))
    print(70 * "*")
    sys.exit(1)

import os
import os.path
import platform

try:
    import lxml.etree as etree
except:
    import xml.etree.ElementTree as etree

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
    for mach in config:
        if (config[mach]["host"] in hostname or
                hostname in config[mach]["host"]):
            machine = mach
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
        cfg_file = "{0}/.cesm/test-cesm.cfg".format(home_dir)
    print("Reading machine configuration file : {0}".format(cfg_file))

    cfg_file = os.path.abspath(cfg_file)
    if not os.path.isfile(cfg_file):
        raise RuntimeError("Could not find config file: {0}".format(cfg_file))

    config = config_parser()
    config.read(cfg_file)
    config_dict = {}
    for section in config.sections():
        config_dict[section] = {}
        for i in config.items(section):
            key = i[0]
            value = i[1]
            config_dict[section][key] = value
    machine = get_machine(config_dict)
    machine_config = config_dict[machine]
    print("{0} configuration :".format(machine))
    for key in machine_config:
        print("  {0} : {1}".format(key, machine_config[key]))

    machine_xml_config = read_config_machines_xml(machine)
    print("{0} xml :".format(machine))
    for key in machine_xml_config:
        print("  {0} : {1}".format(key, machine_xml_config[key]))
    machine_config.update(machine_xml_config)
    return machine, machine_config


def read_config_machines_xml(machine):
    """Read the cesm config_machines.xml file to extract info we need
    """
    machine_xml = {}
    mach_xml_tree = None
    user_config_xml = "{0}/.cesm/config_machines.xml".format(os.environ["HOME"])
    if os.path.isfile(user_config_xml):
        print("Reading : {0}".format(user_config_xml))
        xml_tree = etree.parse(user_config_xml)
        mach_xml_tree = xml_tree.findall("./machine[@MACH='{machine}']".format(machine=machine))
        if len(mach_xml_tree) == 0:
            mach_xml_tree = None
        else:
            mach_xml_tree = mach_xml_tree[0]

    if mach_xml_tree is None:
        # should be an error
        pass

    if mach_xml_tree is not None:
        # print(mach_xml_tree)
        machine_xml["scratch_dir"] = mach_xml_tree.findall("CESMSCRATCHROOT")[0].text
        machine_xml["compilers"] = mach_xml_tree.findall("COMPILERS")[0].text
        machine_xml["cprnc"] = mach_xml_tree.findall("CCSM_CPRNC")[0].text

    home_dir = os.path.expanduser("~")
    for v in machine_xml:
        machine_xml[v] = machine_xml[v].replace("$ENV{HOME}", home_dir)
    # print(machine_xml)
    return machine_xml
