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

    setenv PATH=${PATH}:${HOME}/local/bindir


Then close and reopen your terminal.

Use
---

To see the test options, run:

    cime-tests.py --help

To launch a test suite:

    cime-tests.py --test-suite clm --baseline clm4_5_1_r119

This will launch the `clm` test suite as defined in the configuration
file saved to `${HOME}/.cime/cime-tests.cfg`. It will compare to the
baseline tag `clm4_5_1_r119`.


To see what commands will be run, append `--dry-run` to the above command.

