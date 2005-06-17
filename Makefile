# This file modified from Zope3/Makefile
# Licensed under the ZPL, (c) Zope Corporation and contributors.

PYTHON_VERSION=2.4
PYTHON=python${PYTHON_VERSION}
PYTHONPATH:=$(shell pwd)/lib:${PYTHONPATH}
STARTSCRIPT=runlaunchpad.py
TESTFLAGS=-p -v
TESTOPTS=
SETUPFLAGS=
Z3LIBPATH=$(shell pwd)/sourcecode/zope/src
HERE:=$(shell pwd)
SHHH=${PYTHON} utilities/shhh.py
LPCONFIG=default

CONFFILE=configs/${LPCONFIG}/launchpad.conf

# DO NOT ALTER : this should just build by default
default: inplace

check_merge: build importdcheck
	# Work around the current idiom of 'make check' getting too long
	# because of hct and related tests. note that this is a short
	# term solution, the long term solution will need to be 
	# finer grained testing anyway.
	# Run all tests. test_on_merge.py takes care of setting up the
	# database.
	env PYTHONPATH=$(PYTHONPATH) \
	    ${PYTHON} -t ./test_on_merge.py -vv \
		--dir hct --dir sourcerer --dir banzai
	    $(MAKE) -C sourcecode check PYTHON=${PYTHON} \
		PYTHON_VERSION=${PYTHON_VERSION}

importdcheck:
	cd database/schema; make test PYTHON=${PYTHON}
	PYTHONPATH=lib:lib/canonical/sourcerer/util lib/importd/test_all.py

check: build
	# Run all tests. test_on_merge.py takes care of setting up the
	# database.
	env PYTHONPATH=$(PYTHONPATH) \
	${PYTHON} -t ./test_on_merge.py

pagetests: build
	env PYTHONPATH=$(PYTHONPATH) ${PYTHON} test.py test_pages
	
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
	${SHHH} $(MAKE) -C sourcecode build PYTHON=${PYTHON} \
	    PYTHON_VERSION=${PYTHON_VERSION} LPCONFIG=${LPCONFIG}

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
	LPCONFIG=${LPCONFIG} PYTHONPATH=$(Z3LIBPATH):$(PYTHONPATH) \
		 $(PYTHON) -t $(STARTSCRIPT) -C $(CONFFILE)

LAUNCHPAD_PID=launchpad.pid
LIBRARIAN_PID=librarian.pid

# Run as a daemon - hack using nohup until we move back to using zdaemon
# properly
start: inplace
	LPCONFIG=${LPCONFIG} PYTHONPATH=$(Z3LIBPATH):$(PYTHONPATH) \
		 nohup $(PYTHON) -t $(STARTSCRIPT) -C $(CONFFILE) \
		 > nohup.out 2>&1 &
	ln -sf `LPCONFIG=${LPCONFIG} PYTHONPATH=$(Z3LIBPATH):$(PYTHONPATH) \
		 $(PYTHON) -c 'from canonical.config import config; \
		    print config.librarian.server.root'`/librarian.pid \
		    ${LIBRARIAN_PID}

# Stop the daemon
stop:
	@ if [ -r ${LAUNCHPAD_PID} ]; then \
		echo Killing Launchpad \(`cat ${LAUNCHPAD_PID}`\); \
		kill `cat ${LAUNCHPAD_PID}` | true; \
	fi
	@ if [ -r ${LIBRARIAN_PID} ]; then \
		echo Killing Librarian \(`cat ${LIBRARIAN_PID}`\); \
		kill `cat ${LIBRARIAN_PID}` | true; \
	fi
	@rm -f ${LAUNCHPAD_PID} ${LIBRARIAN_PID}

debug:
	LPCONFIG=${LPCONFIG} PYTHONPATH=$(Z3LIBPATH):$(PYTHONPATH) \
		 $(PYTHON) -i -c \ "from zope.app import Application;\
		    app = Application('Data.fs', 'site.zcml')()"

clean:
	find . \( -name '*.o' -o -name '*.so' -o -name '*.py[co]' -o -name \
	    '*.dll' \) -exec rm -f {} \;
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


