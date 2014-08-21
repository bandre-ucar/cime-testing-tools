#!/usr/bin/env python
"""Try to generate some useful metrics about the cesm
testlists. Restricted to a component, and optionally a machine and
test suite.

Author: Ben Andre <bandre@lbl.gov>

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
from collections import defaultdict
import os
import traceback
import xml.etree.ElementTree as ET

if sys.version_info[0] == 2:
    from ConfigParser import SafeConfigParser as config_parser
else:
    from configparser import ConfigParser as config_parser

# -------------------------------------------------------------------------
#
# User input
#
# -------------------------------------------------------------------------

def commandline_options():
    """Process the command line arguments.

    """
    parser = argparse.ArgumentParser(
        description="try to generate some useful metrics about the cesm testlists.")

    parser.add_argument('--backtrace', action='store_true',
                        help='show exception backtraces as extra debugging '
                        'output')

    parser.add_argument('--debug', action='store_true',
                        help='extra debugging output')

    parser.add_argument('--config', nargs=1, default=["{0}/.cesm/clm-metrics.cfg".format(os.path.expanduser("~"))],
                        help='path to config file')

    options = parser.parse_args()
    return options


def read_config_file(filename):
    """Read the configuration file and process

    """
    print("Reading configuration file : {0}".format(filename))

    cfg_file = os.path.abspath(filename)
    if not os.path.isfile(cfg_file):
        raise RuntimeError("Could not find config file: {0}".format(cfg_file))

    config = config_parser()
    config.read(cfg_file)

    return config


def list_to_dict(input_list, upper_case=False):
    """Convert a list of key value pairs, like the one returned by config
    parser items(), into a dictionary

    """
    output_dict = {}
    for item in input_list:
        key = item[0]
        value = item[1]
        if upper_case is True:
            key = key.upper()
        output_dict[key] = value
    return output_dict


def get_config_section_as_dict(config, name):
    """Find the desired section
    """
    if not config.has_section(name):
        raise RuntimeError("ERROR: config file does not have section '{0}'".format(name))

    items = config.items(name)
    return list_to_dict(items)

# -------------------------------------------------------------------------
#
# read and extract the desired data
#
# -------------------------------------------------------------------------

def component_to_compset(component):
    """
    """

    if component == "clm":
        compset_base = "I"
    else:
        raise RuntimeError(
            "ERROR: can not determine compset mods, unsupported compset '{0}'".format(compset))

    return compset_base


def read_xml(filename, root_tag):
    """Read the user specified file and verify it is a valid xml file.
    """
    if not os.path.isfile(filename):
        raise RuntimeError(
            "Could not find {0} xml file: {1}".format(filename, root_tag))

    try:
        tree = ET.parse(filename)
    except Exception as error:
        print("ERROR: '{0}' is not a valid xml file!".format(filename))
        print(error)
        raise error

    root = tree.getroot()
    if root.tag != root_tag:
        raise RuntimeError(
            "ERROR: '{0}' is not a valid {1} xml file!".format(filename, root_tag))

    return root


def get_compsets(config_compset_xml, compset, debug):
    """
    """
    compset_xml_file = os.path.abspath(config_compset_xml)

    root = read_xml(compset_xml_file, "config_compset")

    for child in root.findall('*'):
        if child.tag != "COMPSET":
            root.remove(child)
        elif child.get('alias') is None:
            root.remove(child)
        elif child.get('alias')[0] != compset:
            root.remove(child)

    if debug:
        print("\nFound all '{0}' compsets :".format(compset))
        for child in root:
            print("    {0}".format(child.get('alias')))

    return root


def get_compset_mods(component, debug):
    """Get a list of all the compset mods directories.
    """
    compset_mods_dir = os.path.abspath("testmods_dirs/{0}/".format(component))

    mods = os.listdir(compset_mods_dir)
    compset_mods = []
    for m in mods:
        if os.path.isdir("{0}/{1}".format(compset_mods_dir, m)):
            compset_mods.append(m)

    if debug:
        print("\nFound all '{0}' compset mods :".format(component))
        for c in compset_mods:
            print("    {0}".format(c))

    return compset_mods


def get_compset_testlists(filename, compset, debug):
    """Find all compsets that begin with the user specified group, e.g. "I",
    """
    root = read_xml(filename, "testlist")
    # remove all compsets that are not part of the specified group
    for child in root.findall('compset'):
        if child.get('name')[0] != compset:
            root.remove(child)

    if debug:
        print("\nFound all '{0}' test compsets:".format(compset))
        for child in root:
            print("    {0}".format(child.get('name')))

    return root

# -------------------------------------------------------------------------
#
# check various metrics
#
# -------------------------------------------------------------------------

def metrics(machines, suites, test_compsets, compsets, compset_mods):
    """Run all the test list metrics
    """
    global_metrics(test_compsets, compsets, compset_mods)
    subset_metrics(machines, suites, test_compsets, compsets, compset_mods)


def global_metrics(test_compsets, compsets, compset_mods):
    """Run metrics on everything in the xml file
    """
    print("* {0}".format(78 * "-"))
    print("*")
    print("* Global metrics")
    print("*")
    print("* {0}".format(78 * "-"))
    metric_test_mods(test_compsets)
    metric_compset_mods(test_compsets, compset_mods)
    metric_machines(test_compsets)
    metric_suites(test_compsets)
    metric_compsets(test_compsets, compsets)


def subset_metrics(machines, suites, test_compsets, compsets, compset_mods):
    """Run metrics on a subset of machines and suites
    """
    print("* {0}".format(78 * "-"))
    print("*")
    print("* Subset metrics")
    print("*")
    print("* {0}".format(78 * "-"))
    metric_test_mods(test_compsets, restrict_machines=machines, restrict_suites=suites)
    metric_compset_mods(test_compsets, compset_mods, restrict_machines=machines, restrict_suites=suites)
    metric_machines(test_compsets, restrict_machines=machines, restrict_suites=suites)
    metric_suites(test_compsets, restrict_machines=machines, restrict_suites=suites)
    metric_compsets(test_compsets, compsets, restrict_machines=machines, restrict_suites=suites)


def metric_test_mods(test_compsets, restrict_machines=None, restrict_suites=None):
    """Report various metrics for tests with test mods

    /testlist/compset/grid/test/machine
    """
    metrics = {}

    for test_group in test_compsets.findall("*/*/*"):
        name = test_group.get('name')
        description = "unmodified"
        index = name.find("_")
        if index > 0:
            description = name[index + 1:]
            name = name[0:index]

        num_tests = len(test_group.findall("machine"))
        if restrict_machines or restrict_suites:
            num_tests = 0
            for machine in test_group.findall("machine"):
                use_test = True
                machine_name = machine.text
                if restrict_machines and machine_name not in restrict_machines:
                    use_test = False
                suite = machine.get("testtype")
                if restrict_suites and suite not in restrict_suites:
                    use_test = False
                if use_test:
                    num_tests += 1
        if name and num_tests > 0:
            if name not in metrics:
                metrics[name] = defaultdict(int)
            metrics[name][description] += num_tests

    total = 0
    for t in metrics:
        for m in metrics[t]:
            total += metrics[t][m]

    print("--- Test mods ---")
    print("  total tests : {0}".format(total))
    print("  test mods :")
    for t in metrics:
        test_total = sum([metrics[t][x] for x in metrics[t]])
        print("    {0} : {1}".format(t, test_total))
        for m in metrics[t]:
            print("      {0} : {1}".format(m, metrics[t][m]))
    print()


def metric_compset_mods(test_compsets, compset_mods, restrict_machines=None, restrict_suites=None):
    """Report various metrics for tests using compset modifications
    """
    metrics = defaultdict(int)
    unmodified = 0

    for machine in test_compsets.findall("*/*/*/*"):
        name = machine.text
        suite = machine.get("testtype")
        testmod = "unmodified"
        if machine.get('testmods'):
            moddir = machine.get('testmods')
            #print("                {0}".format(moddir))
            testmod = moddir[moddir.find('/')+1:]

        if restrict_machines and name not in restrict_machines:
            testmod = None
        if restrict_suites and suite not in restrict_suites:
            testmod = None
        if testmod:
            if testmod == "unmodified":
                unmodified += 1
            else:
                metrics[testmod] += 1

    total = 0
    for m in metrics:
        total += metrics[m]

    print("--- Compset mods ---")
    print("  total : {0}".format(unmodified + total))
    print("  unmodified tests : {0}".format(unmodified))
    print("  modified tests : {0}".format(total))
    print("  tested mods :")
    for mod in sorted(metrics):
        print("    {0} : {1}".format(mod, metrics[mod]))
    print("  untested mods :")
    for c in compset_mods:
        if c not in metrics:
            print("    {0}".format(c))
    print()


def metric_machines(test_compsets, restrict_machines=[], restrict_suites=[]):
    """Report the number of tests on each machine
    """
    metrics = defaultdict(int)
    for machine in test_compsets.findall("*/*/*/*"):
        name = machine.text
        suite = machine.get("testtype")
        if restrict_machines and name not in restrict_machines:
            name = None
        if restrict_suites and suite not in restrict_suites:
            name = None
        if name:
            metrics[name] += 1

    total = sum([metrics[m] for m in metrics])

    print("--- Machines ---")
    if restrict_suites:
        print("  suites : {0}".format(restrict_suites))
    print("  total : {0}".format(total))
    print("  machines :")
    for m in metrics:
        print("    {0} : {1}".format(m, metrics[m]))
    print()


def metric_suites(test_compsets, restrict_machines=[], restrict_suites=[]):
    """Report the number of tests for each suite
    """
    metrics = defaultdict(int)
    for machine in test_compsets.findall("*/*/*/*"):
        name = machine.text
        suite = machine.get("testtype")
        if restrict_machines and name not in restrict_machines:
            suite = None
        if restrict_suites and suite not in restrict_suites:
            suite = None

        if suite:
            metrics[suite] += 1


    total = sum([metrics[m] for m in metrics])

    print("--- Suites ---")
    if restrict_machines:
        print("  Machines : {0}".format(restrict_machines))
    print("  total : {0}".format(total))
    print("  suites :")
    for m in metrics:
        print("    {0} : {1}".format(m, metrics[m]))
    print()


def metric_compsets(test_compsets, compsets, restrict_machines=[], restrict_suites=[]):
    """Report the number of tests for each compset
    """
    metrics = defaultdict(int)
    untested = []
    removed = 0
    for cmpset in compsets:
        for machine in test_compsets.findall("compset[@name='{0}']/*/*/*".format(cmpset.get("alias"))):
            compset_name = cmpset.get("alias")
            machine_name = machine.text
            suite = machine.get("testtype")
            if restrict_machines and machine_name not in restrict_machines:
                compset_name = None
            if restrict_suites and suite not in restrict_suites:
                compset_name = None
    
            if compset_name:
                metrics[compset_name] += 1
            else:
                removed += 1

        compset_name = cmpset.get("alias")
        if compset_name not in metrics:
            untested.append(compset_name)

    total = sum([metrics[m] for m in metrics])

    print("--- Compsets ---")
    if restrict_machines:
        print("  Machines : {0}".format(restrict_machines))
    if restrict_suites:
        print("  suites : {0}".format(restrict_suites))
    print("  total compsets: {0}".format(len(compsets)))
    print("  total tests: {0}".format(total))
    print("  tested compsets : {0}".format(len(metrics)))
    for m in metrics:
        print("    {0} : {1}".format(m, metrics[m]))
    print("  untested compsets : {0}".format(len(untested)))
    for c in untested:
        print("    {0}".format(c))
    print()


# -------------------------------------------------------------------------------
#
# main
#
# -------------------------------------------------------------------------------

def main(options):
    debug = options.debug
    config = read_config_file(options.config[0])
    query = get_config_section_as_dict(config, "query")
    for k in query:
        print("  {0} : {1}".format(k, query[k]))
    compset_base = component_to_compset(query["component"])
    compsets = get_compsets(query["config_compsets"], compset_base, debug)
    compset_mods = get_compset_mods(query["component"], debug)
    test_compsets = get_compset_testlists(query["testlist"], 
                                          compset_base, debug)
    machines = [x.strip() for x in query["machines"].split(",")]
    suites = [x.strip() for x in query["suites"].split(",")]
    metrics(machines, suites, test_compsets, compsets, compset_mods)

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
