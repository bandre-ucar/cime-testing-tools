#
# Makefile to install wrapper scripts for cime testing tools
#
BINDIR = ${HOME}/local/bin

CFGDIR = ${HOME}/.cime

EXECUTABLES = \
	cime-tests.py \
	clobber-cime-tests.py \
	cs.status

install : local-bin-dir $(EXECUTABLES)

local-bin-dir : FORCE
	mkdir -p $(BINDIR)

cime-tests.py : FORCE
	-ln -s ${PWD}/$@ $(BINDIR)/$@

clobber-cime-tests.py : FORCE
	-ln -s ${PWD}/$@ $(BINDIR)/$@

cs.status : FORCE
	-ln -s ${PWD}/$@ $(BINDIR)/$@


user-config : FORCE
	mkdir -p $(CFGDIR)
	-ln -s ${PWD}/example-cime-tests.cfg $(CFGDIR)/cime-tests.cfg

FORCE :
