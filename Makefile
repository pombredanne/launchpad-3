# This file modified from Zope3/Makefile
# Licensed under the ZPL, (c) Zope Corporation and contributors.

PYTHON=python2.3
PYTHONPATH:=$(shell pwd)/lib:${PYTHONPATH}
CONFFILE=launchpad.conf
STARTSCRIPT=runlaunchpad.py
TESTFLAGS=-p -v
TESTOPTS=
SETUPFLAGS=
Z3LIBPATH=$(shell pwd)/sourcecode/zope/src
HERE:=$(shell pwd)

# DO NOT ALTER : this should just build by default
default: inplace

check_merge: build
	# Work around the current idiom of 'make check' getting too long
	# because of hct and related tests. note that this is a short
	# term solution, the long term solution will need to be 
	# finer grained testing anyway.
	# Run all tests. test_on_merge.py takes care of setting up the
	# database.
	env PYTHONPATH=$(PYTHONPATH) \
	${PYTHON} -t ./test_on_merge.py --dir hct --dir sourcerer --dir banzai

check: build
	# Run all tests. test_on_merge.py takes care of setting up the
	# database.
	env PYTHONPATH=$(PYTHONPATH) \
	${PYTHON} -t ./test_on_merge.py 

pagetests:
	$(MAKE) -C sourcecode build
	env PYTHONPATH=$(PYTHONPATH) \
	python test.py test_pages
	
.PHONY: check

# XXX What should the default be?
all: inplace runners

# Build in-place
##inplace:
##	$(PYTHON) setup.py $(SETUPFLAGS) build_ext -i
##
##build:
##	$(PYTHON) setup.py $(SETUPFLAGS) build
inplace: build

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
	env PYTHONPATH=$(PYTHONPATH) \
	$(PYTHON) test.py -f $(TESTFLAGS) $(TESTOPTS)

ftest_inplace: inplace
	env PYTHONPATH=$(PYTHONPATH) \
	$(PYTHON) test.py -f $(TESTFLAGS) $(TESTOPTS)

### SteveA says these should be ripped
#test: 
#test_inplace

#ftest: ftest_inplace

run: inplace
	PYTHONPATH=$(Z3LIBPATH):$(PYTHONPATH) $(PYTHON) -t \
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


