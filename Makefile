# This file modified from Zope3/Makefile
# Licensed under the ZPL, (c) Zope Corporation and contributors.

PYTHON=python2.3
CONFFILE=launchpad.conf
STARTSCRIPT=runlaunchpad.py
TESTFLAGS=-p -v
TESTOPTS=
SETUPFLAGS=
Z3LIBPATH=$(shell pwd)/sourcecode/zope/src
HERE:=$(shell pwd)

check:
	$(MAKE) -C sourcecode check
	PYTHONPATH=$(HERE)/lib ./test.py

debugging-on:
	ln -s ../lib/canonical/canonical.debugskin-configure.zcml ./package-includes/+canonical.debugskin-configure.zcml
	ln -s ../lib/canonical/canonical.apidoc-configure.zcml ./package-includes/+canonical.apidoc-configure.zcml

debugging-off:
	rm -f ./package-includes/+canonical.debugskin-configure.zcml
	rm -f ./package-includes/+canonical.apidoc-configure.zcml
	# backwards compatibility for old style
	rm -f ./package-includes/canonical.debugskin-configure.zcml
	rm -f ./package-includes/canonical.apidoc-configure.zcml

.PHONY: check debugging-on debugging-off

# XXX What should the default be?
all: inplace runners

# Build in-place
##inplace:
##	$(PYTHON) setup.py $(SETUPFLAGS) build_ext -i
##
##build:
##	$(PYTHON) setup.py $(SETUPFLAGS) build
inplace:

build:
	$(MAKE) -C sourcecode build

runners:
	echo "#!/bin/sh" > bin/runzope;
	echo "exec $(PYTHON) $(STARTSCRIPT) -C $(CONFFILE)" >> bin/runzope;
	chmod +x bin/runzope
	echo "#!/bin/sh" > bin/zopectl;
	echo "$(PYTHON) $(PWD)/src/zdaemon/zdctl.py \
	      -S schema.xml \
	      -C zdaemon.conf -d \$$*" >> bin/zopectl
	chmod +x bin/zopectl 

test_build: build
	$(PYTHON) test.py $(TESTFLAGS) $(TESTOPTS)

test_inplace: inplace
	$(PYTHON) test.py $(TESTFLAGS) $(TESTOPTS)

ftest_build: build
	$(PYTHON) test.py -f $(TESTFLAGS) $(TESTOPTS)

ftest_inplace: inplace
	$(PYTHON) test.py -f $(TESTFLAGS) $(TESTOPTS)

# XXX What should the default be?
test: test_inplace

ftest: ftest_inplace

run: inplace
	PYTHONPATH=$(Z3LIBPATH):$(PYTHONPATH) $(PYTHON) \
            $(STARTSCRIPT) -C $(CONFFILE)

debug: principals.zcml
	PYTHONPATH=$(Z3LIBPATH):$(PYTHONPATH) $(PYTHON) -i -c \
            "from zope.app import Application;\
             app = Application('Data.fs', 'site.zcml')()"

clean:
	find . \( -name '*.o' -o -name '*.so' -o -name '*.py[co]' -o -name '*.dll' \) -exec rm -f {} \;
	rm -rf build

realclean: clean
	rm -f TAGS tags
	$(PYTHON) setup.py clean -a

zcmldocs:
	PYTHONPATH=`pwd`/src:$(PYTHONPATH) $(PYTHON) \
	./src/zope/configuration/stxdocs.py \
	-f ./src/zope/app/meta.zcml -o ./doc/zcml/namespaces.zope.org


#
#   Naughty, naughty!  How many Zope3 developers are going to have
#   that directory structure?  The 'ctags' package is capable of generating
#   both emacs-sytle and vi-style tags files from python source;  can the
#   emacs-provided 'etags' not read Python?
#
TAGS:
	python ~/trunk/Tools/scripts/eptags.py `find . -name \*.py`
#	etags `find . -name \*.py -print`

tags:
	ctags -R


# arch-tag: c5c98418-056f-41e0-896a-6714a77439a8
