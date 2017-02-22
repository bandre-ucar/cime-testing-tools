#!/usr/bin/env python
"""Reusable code to determine the machine name we are running on and
read a config file of data for creating a cesm user defined machine.

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

import getpass
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


def find_src_root(current_dir):
    """Recursively walk up the directory tree and try to find the root of
    the src directory. The root of the src tree is defined as the
    directory that contains a cime directory and components directory.

    NOTE: assme we will never start outside a cesm sandbox. But may
    eventually want to support cime standalone testing....

    """
    #print("current_dir = {0}".format(current_dir))
    required_dirs = ['cime', 'components']
    current_list = os.listdir(current_dir)
    found_src_root = True
    for required in required_dirs:
        if not (required in current_list):
            found_src_root = False

    src_root = None
    if found_src_root:
        src_root = current_dir
    else:
        src_root = find_src_root(os.path.abspath(os.path.join(current_dir, '..')))

    return src_root


def get_machines_dir(src_root):
    """Different versions of cesm/cime store machines info in different
    directories. Try to figure out where the info is stored.

    """
    possible_machines_dirs = ['cime/machines',
                              'cime/cime_config/cesm/machines',
    ]
    machines_dir = None
    for directory in possible_machines_dirs:
        if os.path.isdir(os.path.join(src_root, directory)):
            machines_dir = directory
            break
    if not machines_dir:
        print("Could not find machines directory in on of the expected locations:")
        for directory in possible_machines_dirs:
            print("  {0}".foramt(os.path.join(src_root, directory)))
        raise RuntimeError("Could not find machines directory.")

    return os.path.join(src_root, machines_dir)


def read_machine_config(cime_version, cfg_file, config_machines_xml):
    """Read the configuration file and convert machine info into a dict. Expected format:


    [yellowstone]
    host = yslogin
    batch = execca
    background = true|false
    clm_compilers = intel, pgi

    Note that we skip any section that doesn't have a 'host' keyword.

    """
    print("Reading machine configuration file : {0}".format(cfg_file))

    cfg_file = os.path.abspath(cfg_file)
    if not os.path.isfile(cfg_file):
        raise RuntimeError("Could not find config file: {0}".format(cfg_file))

    config = config_parser()
    config.read(cfg_file)
    config_dict = {}
    for section in config.sections():
        if not config.has_option(section, 'host'):
            continue
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

    machine_xml_config = read_config_machines_xml(cime_version, machine,
                                                  config_machines_xml)
    print("{0} xml :".format(machine))
    for key in machine_xml_config:
        print("  {0} : {1}".format(key, machine_xml_config[key]))
    machine_config.update(machine_xml_config)
    return machine, machine_config


def read_config_machines_xml(cime_version, machine, config_machines_xml):
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
            print("    Could not find '{0}' in {1}".format(machine, user_config_xml))
        else:
            mach_xml_tree = mach_xml_tree[0]

    if mach_xml_tree is None:
        # didn't find the machine in the user xml file, check the standard scripts location.
        print("Reading : {0}".format(config_machines_xml))
        xml_tree = etree.parse(config_machines_xml)
        mach_xml_tree = xml_tree.findall("./machine[@MACH='{machine}']".format(machine=machine))
        if len(mach_xml_tree) == 0:
            mach_xml_tree = None
            print("    Could not find '{0}' in {1}".format(machine, config_machines_xml))
        else:
            mach_xml_tree = mach_xml_tree[0]

    if mach_xml_tree is None:
        raise RuntimeError("Could not find machine '{0}' in any known config_machines.xml files!".format(machine))

    # print(mach_xml_tree)
    if (cime_version["major"] == 5 and cime_version["minor"] >= 2):
        machine_xml["scratch_dir"] = mach_xml_tree.findall("CIME_OUTPUT_ROOT")[0].text
    else:
        machine_xml["scratch_dir"] = mach_xml_tree.findall("CESMSCRATCHROOT")[0].text
    machine_xml["compilers"] = mach_xml_tree.findall("COMPILERS")[0].text
    machine_xml["cprnc"] = mach_xml_tree.findall("CCSM_CPRNC")[0].text
    machine_xml['baseline_root'] = mach_xml_tree.findall("CCSM_BASELINE")[0].text
    machine_xml['cesm_inputdata'] = mach_xml_tree.findall("DIN_LOC_ROOT")[0].text
    # setup some variables to substitute into the xml data
    home_dir = os.path.expanduser("~")
    user_name = getpass.getuser()
    cesm_data_root = ''
    if 'CESMDATAROOT' in os.environ:
        cesm_data_root = os.environ['CESMDATAROOT']

    for v in machine_xml:
        machine_xml[v] = machine_xml[v].replace("$ENV{HOME}", home_dir)
        machine_xml[v] = machine_xml[v].replace("$USER", user_name)
        machine_xml[v] = machine_xml[v].replace("$ENV{CESMDATAROOT}", cesm_data_root)

    #print(machine_xml)
    return machine_xml
