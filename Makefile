# This file modified from Zope3/Makefile
# Licensed under the ZPL, (c) Zope Corporation and contributors.

PYTHON_VERSION=2.4
PYTHON=python${PYTHON_VERSION}
WD:=$(shell pwd)
PY=$(WD)/bin/py
PYTHONPATH:=$(WD)/lib:$(WD)/lib/mailman:${PYTHONPATH}
VERBOSITY=-vv

TESTFLAGS=-p $(VERBOSITY)
TESTOPTS=

SHHH=${PY} utilities/shhh.py
STARTSCRIPT=runlaunchpad.py
HERE:=$(shell pwd)

LPCONFIG=development
CONFFILE=configs/${LPCONFIG}/launchpad.conf

MINS_TO_SHUTDOWN=15

CODEHOSTING_ROOT=/var/tmp/bazaar.launchpad.dev

BZR_VERSION_INFO = bzr-version-info.py

XSLTPROC=xsltproc
WADL_FILE = lib/canonical/launchpad/apidoc/wadl-$(LPCONFIG).xml
WADL_XSL = lib/launchpadlib/wadl-to-refhtml.xsl
API_INDEX = lib/canonical/launchpad/apidoc/index.html

EXTRA_JS_FILES=lib/canonical/launchpad/icing/MochiKit.js \
				$(shell $(HERE)/utilities/yui-deps.py) \
				lib/canonical/launchpad/icing/lazr/build/lazr.js

# DO NOT ALTER : this should just build by default
default: inplace

schema: build clean_codehosting
	$(MAKE) -C database/schema
	$(RM) -r /var/tmp/fatsam

newsampledata:
	$(MAKE) -C database/schema newsampledata

hosted_branches:
	$(PY) ./utilities/make-dummy-hosted-branches

$(WADL_FILE): $(BZR_VERSION_INFO)
	LPCONFIG=$(LPCONFIG) $(PY) ./utilities/create-lp-wadl.py > $@

$(API_INDEX): $(WADL_FILE) $(WADL_XSL)
	$(XSLTPROC) $(WADL_XSL) $(WADL_FILE) > $@

apidoc: compile $(API_INDEX)

check_loggerhead_on_merge:
	# Loggerhead doesn't depend on anything else in rocketfuel and nothing
	# depends on it (yet).
	make -C sourcecode/loggerhead check PYTHON=${PYTHON} \
		PYTHON_VERSION=${PYTHON_VERSION} PYTHONPATH=$(PYTHONPATH)

check_merge:
	[ `PYTHONPATH= bzr status -S database/schema/ | \
		grep -v "\(^P\|pending\|security.cfg\|Makefile\|unautovacuumable\)" | wc -l` -eq 0 ]
	${PY} lib/canonical/tests/test_no_conflict_marker.py

check_db_merge:
	${PY} lib/canonical/tests/test_no_conflict_marker.py

# This can be removed once we move to zc.buildout and we have versioned
# dependencies, but for now we run both Launchpad and all other
# dependencies tests for any merge to sourcecode.
check_sourcecode_merge: build check
	$(MAKE) -C sourcecode check PYTHON=${PYTHON} \
		PYTHON_VERSION=${PYTHON_VERSION} PYTHONPATH=$(PYTHONPATH)

check: build
	# Run all tests. test_on_merge.py takes care of setting up the
	# database.
	${PY} -t ./test_on_merge.py $(VERBOSITY)

lint:
	@bash ./utilities/lint.sh

lint-verbose:
	@bash ./utilities/lint.sh -v

xxxreport:
	${PY} -t ./utilities/xxxreport.py -f csv -o xxx-report.csv ./

check-configs:
	${PY} utilities/check-configs.py

pagetests: build
	env PYTHONPATH=$(PYTHONPATH) bin/test test_pages

inplace: build

build: $(BZR_VERSION_INFO) compile apidoc

bin/buildout:
	$(PYTHON) bootstrap.py

bin/py: zc.buildout

zc.buildout: bin/buildout
	./bin/buildout configuration:instance_name=${LPCONFIG}

compile: bin/py
	${SHHH} $(MAKE) -C sourcecode build PYTHON=${PYTHON} \
	    PYTHON_VERSION=${PYTHON_VERSION} LPCONFIG=${LPCONFIG}
	${SHHH} LPCONFIG=${LPCONFIG} $(PY) -t buildmailman.py
	${SHHH} sourcecode/lazr-js/tools/build.py \
		-n launchpad -s lib/canonical/launchpad/javascript \
		-b lib/canonical/launchpad/icing/build $(EXTRA_JS_FILES)

test_build: build
	bin/test $(TESTFLAGS) $(TESTOPTS)

test_inplace: inplace
	bin/test $(TESTFLAGS) $(TESTOPTS)

ftest_build: build
	bin/test -f $(TESTFLAGS) $(TESTOPTS)

ftest_inplace: inplace
	bin/test -f $(TESTFLAGS) $(TESTOPTS)

run: inplace stop
	$(RM) thread*.request
	bin/run -r librarian,google-webservice -C $(CONFFILE)

start-gdb: inplace stop support_files
	$(RM) thread*.request
	nohup gdb -x run.gdb --args bin/run \
		-r librarian,google-webservice -C $(CONFFILE) \
		> ${LPCONFIG}-nohup.out 2>&1 &

run_all: inplace stop hosted_branches
	$(RM) thread*.request
	bin/run -r librarian,buildsequencer,sftp,mailman,codebrowse,google-webservice \
		 -C $(CONFFILE)

run_codebrowse: build
	BZR_PLUGIN_PATH=bzrplugins $(PY) sourcecode/launchpad-loggerhead/start-loggerhead.py -f

start_codebrowse: build
	BZR_PLUGIN_PATH=$(shell pwd)/bzrplugins $(PY) sourcecode/launchpad-loggerhead/start-loggerhead.py

stop_codebrowse:
	$(PY) sourcecode/launchpad-loggerhead/stop-loggerhead.py

pull_branches: support_files
	# Mirror the hosted branches in the development upload area to the
	# mirrored area.
	$(PY) cronscripts/supermirror-pull.py upload

scan_branches:
	# Scan branches from the filesystem into the database.
	$(PY) cronscripts/branch-scanner.py

sync_branches: pull_branches scan_branches

$(BZR_VERSION_INFO):
	scripts/update-bzr-version-info.sh

support_files: $(WADL_FILE) $(BZR_VERSION_INFO)

# Run as a daemon - hack using nohup until we move back to using zdaemon
# properly. We also should really wait until services are running before
# exiting, as running 'make stop' too soon after running 'make start'
# will not work as expected.
# XXX $(PY) -t
start: inplace stop support_files
	nohup bin/run -C $(CONFFILE) > ${LPCONFIG}-nohup.out 2>&1 &

# This is a stripped down version of the "start" target for use on
# production servers - removes running 'make build' because we already
# run this as part of our initscripts, so not needed here. Likewise we
# don't want to run 'make stop' because it takes unnecessary time
# even if the service is already stopped, and bzr_version_info is not
# needed either because it's run as part of 'make build'.
# XXX $(PY) -t
initscript-start:
	nohup bin/run -C $(CONFFILE) > ${LPCONFIG}-nohup.out 2>&1 &

# Kill launchpad last - other services will probably shutdown with it,
# so killing them after is a race condition.
stop: build
	bin/killservice librarian buildsequencer launchpad mailman

shutdown: scheduleoutage stop
	$(RM) +maintenancetime.txt

scheduleoutage:
	echo Scheduling outage in ${MINS_TO_SHUTDOWN} mins
	date --iso-8601=minutes -u -d +${MINS_TO_SHUTDOWN}mins > +maintenancetime.txt
	echo Sleeping ${MINS_TO_SHUTDOWN} mins
	sleep ${MINS_TO_SHUTDOWN}m

harness:
	bin/harness

iharness:
	bin/iharness

rebuildfti:
	@echo Rebuilding FTI indexes on launchpad_dev database
	$(PY) database/schema/fti.py -d launchpad_dev --force

clean:
	$(MAKE) -C sourcecode/pygettextpo clean
	find . -type f \( \
	    -name '*.o' -o -name '*.so' -o -name '*.la' -o \
	    -name '*.lo' -o -name '*.py[co]' -o -name '*.dll' \) \
	    -print0 | xargs -r0 $(RM)
	$(RM) -r bin
	$(RM) -r parts
	$(RM) .installed.cfg
	$(RM) -r build
	$(RM) thread*.request
	$(RM) -r lib/mailman /var/tmp/mailman/* /var/tmp/fatsam.appserver
	$(RM) -rf lib/canonical/launchpad/icing/build/*
	$(RM) -r $(CODEHOSTING_ROOT)
	$(RM) $(WADL_FILE) $(API_INDEX)
	$(RM) $(BZR_VERSION_INFO)

realclean: clean
	$(RM) TAGS tags

clean_codehosting:
	$(RM) -r $(CODEHOSTING_ROOT)
	mkdir -p $(CODEHOSTING_ROOT)/mirrors
	mkdir -p $(CODEHOSTING_ROOT)/push-branches
	mkdir -p $(CODEHOSTING_ROOT)/config
	touch $(CODEHOSTING_ROOT)/config/launchpad-lookup.txt

zcmldocs:
	mkdir -p doc/zcml/namespaces.zope.org
	bin/stxdocs \
	    -f sourcecode/zope/src/zope/app/zcmlfiles/meta.zcml \
	    -o doc/zcml/namespaces.zope.org

potemplates: launchpad.pot

# Generate launchpad.pot by extracting message ids from the source
launchpad.pot:
	bin/i18nextract.py

install: reload-apache

copy-certificates:
	mkdir -p /etc/apache2/ssl
	cp configs/development/launchpad.crt /etc/apache2/ssl/
	cp configs/development/launchpad.key /etc/apache2/ssl/

copy-apache-config:
	# We insert the absolute path to the branch-rewrite script
	# into the Apache config as we copy the file into position.
	sed -e 's,%BRANCH_REWRITE%,$(shell pwd)/scripts/branch-rewrite.py,' configs/development/local-launchpad-apache > /etc/apache2/sites-available/local-launchpad

enable-apache-launchpad: copy-apache-config copy-certificates
	a2ensite local-launchpad

reload-apache: enable-apache-launchpad
	/etc/init.d/apache2 reload

static:
	$(PY) scripts/make-static.py

TAGS: compile
	# emacs tags
	bin/tags -e

tags: compile
	# vi tags
	bin/tags -v

ID: compile
	# idutils ID file
	bin/tags -i

.PHONY: apidoc check tags TAGS zcmldocs realclean clean debug stop\
	start run ftest_build ftest_inplace test_build test_inplace pagetests\
	check check_loggerhead_on_merge  check_merge check_sourcecode_merge \
	schema default launchpad.pot check_merge_ui pull scan sync_branches\
	reload-apache hosted_branches check_db_merge
