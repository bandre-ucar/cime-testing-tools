#!/usr/bin/env python

"""Script to filter cesm test suite output based on the test
status. Test status is the results of the cs.status.xxxx
scripts. Meaning of test status is in
scripts/doc/usersguide/testing.xml

  Remove:
    * PASS

  Filter to displays tests by failure type:
    * XFAIL : expected failurs based on the clm expected failure xml
      list are remove from all categories
    * FAIL : any of several failures.
    * BFAIL : tests where the baseline failed as well
    * RUN : run time failures

  Tests for memleak, compare_hist, memcomp, tputcomp, nlcomp are
  reported as separate lines in the test reports, so we can check for
  them individually and remove them from the list.

  Extra diagnostics :
    * CFAIL : reruns the ${CASE}.test_build script and captures the output.

  Requires python >= 2.7
    on yellowstone:
        module load python/2.7.5

Author: Ben Andre <bandre@lbl.gov>

"""

from __future__ import print_function

import sys

if sys.hexversion < 0x02060000:
    print(70 * "*")
    print("ERROR: query-xFail for CLM requires python >= 2.6.x. ")
    print("It appears that you are running python {0}.{1}.{2}".format(
        sys.version_info[0], sys.version_info[1], sys.version_info[2]))
    print(70 * "*")
    sys.exit(1)

import copy
import os
import re
import shutil
import subprocess
import traceback
# import xml.parsers.expat
import xml.etree.ElementTree as ET

if sys.hexversion <= 0x02070000:
    import optparse
else:
    import argparse

if sys.hexversion < 0x03000000:
    from ConfigParser import SafeConfigParser as config_parser
else:
    from configparser import ConfigParser as config_parser


from cesm_machine import read_machine_config

debug = True


def determine_test_info(test_info_file):
    """Determine what machine we are running on and extract the test
    config written by test-clm

    """
    print("Checking test info.")
    test_info = {}
    machine, machine_config = read_machine_config(None)
    config = config_parser()
    config.read(test_info_file)

    for section in config.sections():
        for option in config.options(section):
            test_info[option] = config.get(section, option)

    print("Using test info :")
    for key in test_info:
        print("    {0} : {1}".format(key, test_info[key]))

    check_test_info(machine_config, test_info)

    return machine, test_info


def check_test_info(machine_config, test_info):
    """Run some basic sanity checks on the config info
    """
    print("Checking test info.")
    test_dir = "{0}/{1}".format(test_info['scratch_dir'],
                                test_info['test_data_dir'])
    # NOTE(bja, 20140724) this should never happen because we are
    # getting the test cfg file from the test directory....
    if not os.path.isdir(test_dir):
        message = "ERROR: could not determine test root directory. Expected: {0}".format(
            test_dir)
        raise Exception(message)

    if "status" in test_info:
        check_file = "{0}/{1}".format(test_dir, test_info['status'])
        if not os.path.isfile(check_file):
            message = "ERROR: Could not find status script. Expected: {0}".format(
                check_file)
            raise RuntimeError(message)

    if "expected_fail" in test_info:
        check_file = "{0}".format(test_info['expected_fail'])
        if not os.path.isfile(check_file):
            message = "ERROR: Could not find expected fail file. Expected: {0}".format(
                check_file)
            raise RuntimeError(message)
    else:
        message = "ERROR: must provide an expected fail file in the test info file."
        raise RuntimeError(message)

    if "baseline" in test_info:
        check_dir = "{0}/{1}".format(
            machine_config['baseline_root'], test_info['baseline'])
        if not os.path.isdir(check_dir):
            message = "ERROR: Could not find baseline directory. Expected: {0}".format(
                check_dir)
            raise RuntimeError(message)
    else:
        message = "ERROR: must provide a 'baseline' in the test info file."
        raise RuntimeError(message)


def generate_status_output_files(test_info):
    """Call the cs.status script and generate the test status output
    """
    print("Generating report files.")
    status_list = []
    test_dir = "{0}/{1}".format(test_info['scratch_dir'],
                                test_info['test_data_dir'])

    # existance of status file should have already been checked!
    status_script = "{0}/{1}".format(test_dir, test_info['status'])
    status_output = "{0}/{1}.status.out.txt".format(
        test_dir, test_info['testid'])
    with open(status_output, 'w') as status_file:
        command = [status_script]
        subprocess.call(command, stdout=status_file)

    if os.path.isfile(status_output):
        status_list.append(status_output)
    else:
        message = "ERROR: could not find status output. Expected: {0}".format(
            status_output)
        raise RuntimeError(message)

    return status_list


def get_test_status(status_output, machine, compiler):
    """Read the status file and create a dict of tests and their state
    """
    print("Reading status report for {0} {1}.".format(machine, compiler))
    test_status = {}
    test_status["PASS"] = []
    test_status["CFAIL"] = []
    test_status["BFAIL"] = []
    test_status["TFAIL"] = []
    test_status["SFAIL"] = []
    test_status["FAIL"] = []
    test_status["RUN"] = []
    test_status["GEN"] = []
    test_status["PEND"] = []
    test_status["UNKNOWN"] = []
    # test_status[""] = []

    with open(status_output, 'r') as report:
        for tmp in report.readlines():
            line = tmp.split()
            if len(line) == 2:
                status = line[0].strip()
                name = line[1].strip()
                if status in test_status:
                    test_status[status].append(name)
                else:
                    test_status["UNKNOWN"].append((status, name))

    return test_status


def get_expected_fail(expected_fail_file, outfile, machine, compiler):
    """open the expected fail xml file and extract the expected fail list
    for this machine and compiler.

    """
    print("Extracting expected fail list")
    expected_fails = {}
    xfail_path = os.path.abspath(expected_fail_file)
    if not os.path.isfile(xfail_path):
        raise RuntimeError(
            "Could not find expected fail file: {0}".format(xfail_path))
    print("  Using expected failures from:", file=outfile)
    print("    {0}".format(xfail_path), file=outfile)
    tree = ET.parse(xfail_path)
    group = "cesm/auxTests/{0}/{1}".format(machine, compiler.upper())
    print("group : {0}".format(group))
    xfail_aux = None
    try:
        xfail_aux = tree.findall(group)[0]
        for test in xfail_aux.iter("entry"):
            expected_fails[
                test.attrib["testId"].strip()] = test.attrib["failType"].strip()
    except Exception as error:
        print(
            "WARNING: Could not find expected fails for this machine and "
            "compiler combination!")

    return expected_fails


def process_expected_fail(test_info, machine, compiler, outfile,
                          detailed_report, test_status):
    """Remove expected failures from the failure categories.
    """
    print("Processing expected fails")
    expected_fail = get_expected_fail(
        test_info['expected_fail'], outfile, machine, compiler)
    print(80 * "=", file=outfile)
    print("  XFAIL tests\n", file=outfile)
    print("    removing expected failure tests :", file=outfile)
    miscategorized = {}
    for xfail in expected_fail:
        status = expected_fail[xfail]
        found = False
        for test in test_status[status]:
            if test.startswith(xfail):
                found = True
                print("      {0} : {1}".format(xfail, status), file=outfile)
                test_status[status].remove(test)
        if not found:
            miscategorized[xfail] = status

    if len(miscategorized) > 0:
        print("\n    miscategorized expected failure tests :", file=outfile)
        for test in miscategorized:
            print("      {0} : {1}".format(
                test, miscategorized[test]), file=outfile)


def process_cfail(outfile, detailed_report, cfail, test_root):
    """
    configure / compilation errors
    """
    print(80 * "=", file=outfile)
    print("  CFAIL tests - configure/compile failure\n", file=outfile)
    for test in cfail:
        print("    {0}".format(test), file=outfile)
        if not detailed_report:
            continue
        case_dir = "{0}/{1}".format(test_root, test)
        if os.path.isdir(case_dir):
            os.chdir(case_dir)
            command = "./{0}.test_build".format(test)
            print("cd {0}".format(case_dir), file=outfile)
            print("{0}".format(command), file=outfile)
            print(80 * "*", file=outfile)
            outfile.flush()
            subprocess.call(command, stdout=outfile, stderr=outfile)
            print(80 * "*", file=outfile)
            print("", file=outfile)


def process_run_fail(outfile, detailed_report, runfail):
    """
    either the job is still running or a runtime error occured?
    """
    print(80 * "=", file=outfile)
    print("  RUN fail tests\n", file=outfile)
    for test in runfail:
        print("    {0}".format(test), file=outfile)


def process_bfail(outfile, detailed_report, bfail, fail):
    """
    ignore errors where the baseline does not exist
    """
    print(80 * "=", file=outfile)
    print("  BFAIL tests\n", file=outfile)
    print("    removing BFAIL tests from the FAIL list.", file=outfile)
    for test in bfail:
        print("      {0}".format(test), file=outfile)
        if test in fail:
            fail.remove(test)


def process_tput(outfile, detailed_report, fail):
    """
    ignore failures with throughput comparison errors (tputcomp)
    """
    print(80 * "=", file=outfile)
    print("  through put tests\n", file=outfile)
    print("    removing tput failures from the FAIL list.", file=outfile)
    fail_list = copy.deepcopy(fail)
    for test in fail_list:
        if test.find("tputcomp") != -1:
            fail.remove(test)
            print("      {0}".format(test), file=outfile)


def process_generate(outfile, detailed_report, fail):
    """
    remove baseline generation errors
    """
    print(80 * "=", file=outfile)
    print("  generate tests\n", file=outfile)
    print("    removing generate failures from the FAIL list.", file=outfile)
    fail_list = copy.deepcopy(fail)
    for test in fail_list:
        if test.find("generate") != -1:
            fail.remove(test)
            print("      {0}".format(test), file=outfile)


def process_memcomp(outfile, detailed_report, fail):
    """
    remove memcomp errors
    """
    print(80 * "=", file=outfile)
    print("  memcomp tests\n", file=outfile)
    print("    removing memcomp failures from the FAIL list.", file=outfile)
    fail_list = copy.deepcopy(fail)
    for test in fail_list:
        if test.find("memcomp") != -1:
            fail.remove(test)
            print("      {0}".format(test), file=outfile)


def process_compare_hist(outfile, detailed_report, fail, test_root):
    """
    seperate out compare_hist errors
    """
    print(80 * "=", file=outfile)
    print("  compare_hist tests\n", file=outfile)
    print(
        "    separating compare_hist failures from the FAIL list.",
        file=outfile)
    fail_list = copy.deepcopy(fail)
    for test in fail_list:
        if test.find("compare_hist") != -1:
            fail.remove(test)
            if not detailed_report:
                print("      {0}".format(test), file=outfile)
                continue

            print("      {0}".format(len(test) * '.'), file=outfile)
            print("      {0}".format(test), file=outfile)
            print("      {0}".format(len(test) * '.'), file=outfile)
            # check TestStatus file
            test_name_as_list = test.split('.')
            index = test_name_as_list.index('C')
            name_list = test_name_as_list[0:index + 2]
            test_name = ".".join(name_list)
            test_dir = "{0}/{1}".format(test_root, test_name)
            search_for_compare_hist_failure(test_dir, outfile)
            search_for_restart_failure(test_dir, outfile)


def search_for_compare_hist_failure(test_dir, outfile):
    """Try to identify info about history comparison failure
    """
    print("\nChecking for history comparison failure....", file=outfile)
    test_status = "{0}/TestStatus.out".format(test_dir)
    print("        less {0}\n".format(test_status), file=outfile)
    output_buffer = []
    with open(test_status, 'r') as status_file:
        record_output = False
        hist_comp_fail = False
        for line in status_file.readlines():
            if line.find("Comparing hist file with baseline hist file") >= 0:
                record_output = True
            if record_output is True:
                output_buffer.append(line)
                if line.find("hist file comparison is FAIL") >= 0:
                    record_output = False
                    hist_comp_fail = True
                elif line.find("PASS") >= 0:
                    record_output = False
                    hist_comp_fail = False

    if hist_comp_fail is True:
        for line in output_buffer:
            print(line, file=outfile)
        get_rms_from_cprnc(test_dir, outfile)
    else:
        print("PASS", file=outfile)


def get_rms_from_cprnc(test_dir, outfile):
    """Try to extract cprnc info about failure
    """
    # print("Retreiving RMS from cprnc")
    cprnc_out = "{0}/cprnc.out".format(test_dir)
    print("        less {0}\n".format(cprnc_out), file=outfile)
    with open(cprnc_out, 'r') as cprnc_file:
        print_next = 0
        for line in cprnc_file.readlines():
            # NOTE(2013-08) stripping whitespace removes a space from
            # the front of every line and a newline from the end.
            line = line.strip()
            if print_next > 0:
                print(line, file=outfile)
                print_next -= 1
            if line.find("file") == 0:
                print(line, file=outfile)
                print_next = 2
            if line.find("RMS") == 0:
                print(line, file=outfile)


def search_for_restart_failure(test_dir, outfile):
    """Try to identify info about restart failure
    """
    print("\nChecking for restart failure....", file=outfile)
    test_status = "{0}/TestStatus.out".format(test_dir)
    print("        less {0}\n".format(test_status), file=outfile)
    output_buffer = []
    with open(test_status, 'r') as status_file:
        record_output = False
        restart_fail = False
        for line in status_file.readlines():
            if line.find("Comparing initial hist file with second hist file") >= 0:
                record_output = True
            if record_output is True:
                output_buffer.append(line)
                if line.find("hist file comparison is FAIL") >= 0:
                    record_output = False
                    restart_fail = True
                elif line.find("PASS") >= 0:
                    record_output = False
                    restart_fail = False

    if restart_fail is True:
        for line in output_buffer:
            print(line, file=outfile)
        get_rms_from_cprnc(test_dir, outfile)
    else:
        print("PASS", file=outfile)


def process_nlcomp(outfile, detailed_report, fail, test_root, test_info):
    """
    seperate out nlcomp failures
    """
    debug = False
    print(80 * "=", file=outfile)
    print("  nlcomp tests\n", file=outfile)
    print("    separating nlcomp failures from the FAIL list.", file=outfile)
    nl_re = re.compile(r"_in[_\d]{0,4}$")
    fail_list = copy.deepcopy(fail)
    for test in fail_list:
        if test.find("nlcomp") != -1:
            fail.remove(test)
            print("      {0}".format(test), file=outfile)
            if not detailed_report:
                continue
            print(80 * "-", file=outfile)
            # check TestStatus file
            test_name = test[:test.rfind(".nlcomp")]

            run_dir = os.path.normpath(
                "{0}/../{1}/run".format(test_root, test_name))
            if debug:
                print("---> Run dir : {0}".format(run_dir))
            namelist_files = []
            for junk_root, junk_dirs, check_files in os.walk(run_dir):
                for cfile in check_files:
                    match = nl_re.search(cfile)
                    if match:
                        namelist_files.append(cfile)
                        if debug:
                            print("----> Found {0}".format(cfile))

            for nlfile in namelist_files:
                # How do we ignore the commands to generate the name list
                # file....
                if nlfile == "drv_in":
                    # drv_in contains test and user names that will never be
                    # the same.
                    continue
                if nlfile != "lnd_in":
                    # for now assume we only care about land namelist files...
                    continue

                namelist_file = "{0}/{1}".format(run_dir, nlfile)
                compiler_re = re.compile(
                    "{0}_([a-z]+)".format(test_info["machine"]))
                match = compiler_re.search(test)
                if not match:
                    raise RuntimeError(
                        "ERROR : nlcomp : {0} : could not match compiler re.".format(test))
                compiler = match.group(1)
                # print("---> compiler : {0}".format(compiler))
                # (\.(C|G)\.)?\.[\d]{8}
                baseline_name_re = re.compile(
                    r"(.+\.{0}_{1}(\.[\w_\-]{2})?)".format(test_info['machine'],
                                                           compiler, "{2,}"))
                baseline_name = baseline_name_re.match(test).group(1)
                baseline_namelist_file = "{0}/{1}/{2}/CaseDocs/{3}".format(
                    test_info['baseline_root'], test_info['baseline'],
                    baseline_name, nlfile)

                if not os.path.isfile(baseline_namelist_file):
                    print("ERROR : nlcomp : {0} : could not find baseline namelist file : {1}".format(
                        test, baseline_namelist_file), file=outfile)
                if not os.path.isfile(namelist_file):
                    print("ERROR : nlcomp : {0} : could not find test namelist file : {1}".format(
                        test, namelist_file), file=outfile)
                cmd = ["diff", baseline_namelist_file, namelist_file]
                with open("tmp.stdout", "w") as run_stdout:
                    status = subprocess.call(cmd, stdout=run_stdout)
                    if status != 0:
                        print("  diffing namelist files :\n    {0}".format(
                            " ".join(cmd)), file=outfile)
                        with open("tmp.stdout", 'r') as run_stdout:
                            shutil.copyfileobj(run_stdout, outfile)


def process_fail(outfile, detailed_report, fail):
    """catch all failures
    """
    print(80 * "=", file=outfile)
    print("  FAIL tests\n", file=outfile)
    for test in fail:
        print("    {0}".format(test), file=outfile)


def process_tfail(outfile, detailed_report, tfail):
    """
    failures in threading tests
    """
    print(80 * "=", file=outfile)
    print("  TFAIL tests\n", file=outfile)
    for test in tfail:
        print("    {0}".format(test), file=outfile)


def process_sfail(outfile, detailed_report, sfail):
    """
    failures in scripts generating tests
    """
    print(80 * "=", file=outfile)
    print("  SFAIL tests - scripts failures\n", file=outfile)
    for test in sfail:
        print("    {0}".format(test), file=outfile)


def process_gen(outfile, detailed_report, gen):
    """
    test generated but not run yet
    """
    print(80 * "=", file=outfile)
    print("  GEN tests\n", file=outfile)
    for test in gen:
        print("    {0}".format(test), file=outfile)


def process_pend(outfile, detailed_report, pend):
    """
    pending tests, test generated but not run yet
    """
    print(80 * "=", file=outfile)
    print("  PEND tests\n", file=outfile)
    for test in pend:
        print("    {0}".format(test), file=outfile)


def process_unknown(outfile, detailed_report, unknown):
    """
    unknown test status, indicates something has changed in scripts...?
    """
    print(80 * "=", file=outfile)
    print("  Tests with UNKNOWN status type\n", file=outfile)
    for test in unknown:
        print("    {0} : {1}".format(test[0], test[1]), file=outfile)


def process_pass(outfile, detailed_report, passing):
    """
    list passing tests
    """
    print(80 * "=", file=outfile)
    print("  Passing tests:\n", file=outfile)
    for test in passing:
        print("    {0}".format(test), file=outfile)


def commandline_options():
    """process the command line options
    """
    example_info_file = """The test info file is generated by the test-clm.py
 and is standard cfg format. It should look something like:

[yellowstone]
scratch_dir = /glade/u/home/andre/scratch
test_data_dir = tests-20131009-19
pgi_status = cs.status.20131009-191731.yellowstone
intel_status = cs.status.20131009-191542.yellowstone
expected_fail = /glade/u/home/andre/scratch/src/controlMod_cpp_clm/models/lnd/clm/bld/unit_testers/xFail/expectedClmTestFails.xml
baseline = clm4_5_36
"""
    if sys.hexversion < 0x02070000:
        parser = optparse.OptionParser(
            description='Run a report on cesm test suite.',
            epilog=example_info_file)

        parser.add_option(
            '-f', '--test-info-file', nargs=1,
            help="path to the test info file, containing the paths to the "
            "test directory, expected fails, status scripts, etc.")

        parser.add_option(
            '-d', '--detailed-report', default=False, action="store_true",
            help="Try to generate a more detailed report by running cat, "
            "diff and grep on various files. EXPERIMENTAL: This is "
            "somewhat(?) unreliable information.")

        (options, args) = parser.parse_args()
        if options.test_info_file is None:
            raise RuntimeError(
                "must specify test-info-file on the commandline.")
        else:
            options.test_info_file = [options.test_info_file]
    else:
        parser = argparse.ArgumentParser(
            description='Run a report on cesm test suite.',
            epilog=example_info_file,
            formatter_class=argparse.RawDescriptionHelpFormatter)

        parser.add_argument(
            '-f', '--test-info-file', nargs=1, required=True,
            help="path to the test info file, containing the paths to the "
            "test directory, expected fails, status scripts, etc.")

        parser.add_argument(
            '-d', '--detailed-report', default=False, action="store_true",
            help="Try to generate a more detailed report by running cat, "
            "diff and grep on various files. EXPERIMENTAL: This is "
            "somewhat(?) unreliable information.")

        options = parser.parse_args()
    return options


def main():
    options = commandline_options()
    machine, test_info = determine_test_info(
        options.test_info_file[0])
    compiler = test_info['compiler'].lower()

    test_dir = "{0}/{1}".format(test_info['scratch_dir'],
                                test_info['test_data_dir'])
    os.chdir(test_dir)
    status_list = generate_status_output_files(test_info)

    detailed_report = options.detailed_report

    test_name = options.test_info_file[0]
    short_name = test_name[:test_name.rfind(".cfg")]
    summary_filename = "{0}/test-summary.{1}.txt".format(test_dir, short_name)
    if detailed_report:
        summary_filename = "{0}/test-details.{1}.txt".format(
            test_dir, short_name)

    print("Writing failure summary to: {0}".format(summary_filename))
    with open(summary_filename, 'w') as summary_file:
        for report in status_list:
            print(80 * "=", file=summary_file)
            print("  Report file:", file=summary_file)
            print("    {0}".format(report), file=summary_file)
            print(80 * "=", file=summary_file)
            test_status = get_test_status(report, machine, compiler)
            process_expected_fail(
                test_info, machine, compiler, summary_file, detailed_report,
                test_status)
            process_cfail(
                summary_file, detailed_report, test_status["CFAIL"], test_dir)
            process_bfail(
                summary_file, detailed_report, test_status["BFAIL"],
                test_status["FAIL"])
            process_tput(summary_file, detailed_report, test_status["FAIL"])
            process_generate(
                summary_file, detailed_report, test_status["FAIL"])
            process_memcomp(summary_file, detailed_report, test_status["FAIL"])
            process_nlcomp(
                summary_file, detailed_report, test_status["FAIL"], test_dir,
                test_info)
            process_compare_hist(
                summary_file, detailed_report, test_status["FAIL"], test_dir)
            process_run_fail(summary_file, detailed_report, test_status["RUN"])
            process_tfail(summary_file, detailed_report, test_status["TFAIL"])
            process_sfail(summary_file, detailed_report, test_status["SFAIL"])
            process_fail(summary_file, detailed_report, test_status["FAIL"])
            process_gen(summary_file, detailed_report, test_status["GEN"])
            process_pend(summary_file, detailed_report, test_status["PEND"])
            process_unknown(
                summary_file, detailed_report, test_status["UNKNOWN"])
            process_pass(summary_file, detailed_report, test_status["PASS"])
            print("\n\n", file=summary_file)
    return 0

if __name__ == "__main__":
    try:
        status = main()
        sys.exit(status)
    except Exception as error:
        print(str(error))
        if True:
            traceback.print_exc()
        sys.exit(1)
