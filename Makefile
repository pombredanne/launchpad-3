# This file modified from Zope3/Makefile
# Licensed under the ZPL, (c) Zope Corporation and contributors.

PYTHON_VERSION=2.4
PYTHON=python${PYTHON_VERSION}
PYTHONPATH:=$(shell pwd)/lib:${PYTHONPATH}

TESTFLAGS=-p -v
TESTOPTS=

SHHH=${PYTHON} utilities/shhh.py
STARTSCRIPT=runlaunchpad.py
Z3LIBPATH=$(shell pwd)/sourcecode/zope/src
HERE:=$(shell pwd)

LPCONFIG=default
CONFFILE=configs/${LPCONFIG}/launchpad.conf

# DO NOT ALTER : this should just build by default
default: inplace

schema:
	(cd database/schema; make)

check_merge: build importdcheck
	# Work around the current idiom of 'make check' getting too long
	# because of hct and related tests. note that this is a short
	# term solution, the long term solution will need to be 
	# finer grained testing anyway.
	# Run all tests. test_on_merge.py takes care of setting up the
	# database.
	env PYTHONPATH=$(PYTHONPATH) \
	    ${PYTHON} -t ./test_on_merge.py -vv \
		--dir hct --dir sourcerer
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

lint:
	sh ./utilities/lint.sh

pagetests: build
	env PYTHONPATH=$(PYTHONPATH) ${PYTHON} test.py test_pages
	
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

run: inplace stop
	LPCONFIG=${LPCONFIG} PYTHONPATH=$(Z3LIBPATH):$(PYTHONPATH) \
		 $(PYTHON) -t $(STARTSCRIPT) -C $(CONFFILE)

# Run as a daemon - hack using nohup until we move back to using zdaemon
# properly. We also should really wait until services are running before 
# exiting, as running 'make stop' too soon after running 'make start'
# will not work as expected.
start: inplace stop
	LPCONFIG=${LPCONFIG} PYTHONPATH=$(Z3LIBPATH):$(PYTHONPATH) \
		 nohup $(PYTHON) -t $(STARTSCRIPT) -C $(CONFFILE) \
		 > ${LPCONFIG}-nohup.out 2>&1 &

# Kill launchpad last - other services will probably shutdown with it,
# so killing them after is a race condition.
stop: build
	@ LPCONFIG=${LPCONFIG} ${PYTHON} \
	    utilities/killservice.py librarian trebuchet launchpad

debug:
	LPCONFIG=${LPCONFIG} PYTHONPATH=$(Z3LIBPATH):$(PYTHONPATH) \
		 $(PYTHON) -i -c \ "from zope.app import Application;\
		    app = Application('Data.fs', 'site.zcml')()"

clean:
	find . -type f \( -name '*.o' -o -name '*.so' \
	    -o -name '*.py[co]' -o -name '*.dll' \) -exec rm -f {} \;
	rm -rf build

realclean: clean
	rm -f TAGS tags
	$(PYTHON) setup.py clean -a

zcmldocs:
	PYTHONPATH=`pwd`/src:$(PYTHONPATH) $(PYTHON) \
	    ./src/zope/configuration/stxdocs.py \
	    -f ./src/zope/app/meta.zcml -o ./doc/zcml/namespaces.zope.org

potemplates: launchpad.pot

# Generate launchpad.pot by extracting message ids from the source
launchpad.pot:
	$(PYTHON) sourcecode/zope/utilities/i18nextract.py \
	    -d launchpad -p lib/canonical/launchpad \
	    -o locales

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

.PHONY: check tags TAGS zcmldocs realclean clean debug stop start run \
		ftest_build ftest_inplace test_build test_inplace pagetests \
		check importdcheck check_merge schema default launchpad.pot

