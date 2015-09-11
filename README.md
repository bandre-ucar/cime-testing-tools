Tools to make working with cime testing simpler.

Installation
------------

To install the tools into ${HOME}/local/bin as symbolic links to this directory type:

    make install
    make user-config

You will need to add ${HOME}/local/bin to your path.

In bash, edit ${HOME}/.bashrc

    export PATH=${PATH}:${HOME}/local/bin

In csh, edit ${HOME}/.cshrc

    setenv PATH $PATH:$HOME/local/bindir


Then close and reopen your terminal.

Run tests
---------

To see the test options, run:

    cime-tests.py --help

To launch a test suite:

    cd /path/to/cesm/sandbox/cime/scripts
    cime-tests.py --test-suite clm --baseline clm4_5_1_r119

This will launch the `clm` test suite as defined in the configuration
file saved to `${HOME}/.cime/cime-tests.cfg`. It will compare to the
baseline tag `clm4_5_1_r119`. Note this command must be run from the
cime scripts directory.

To see what commands will be run, append `--dry-run` to the above command.


Check test results
------------------

cime-tests.py sets the test root to
${SCRATCH}/tests-${test_suite}-${date_stamp). For example, if you ran
the 'clm_short' test suite on September 10, 2015 at 5pm, the test root
would be 'tests-clm_short-20150910-17'. 

To check test results, cd in the appropriate test root directory.
Type `which cs.status`. If the result isn't `~/local/bin/cs.status`,
then you will need to replace all 'cs.status' command below with the
full path.

To see the status of all tests, in the test root, run:

    cs.status -terse -all

This will output just the 'interesting' test results, by removing all
the passes and expected failures. If you are expecting additional
failures because of changes you made, you can use grep to remove the
'unintersting' results. For example, to remove namelist comparison
failures because you changed a namelist flag:

    cs.status -terse -all | grep -v nlcomp
