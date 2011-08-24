# This file modified from Zope3/Makefile
# Licensed under the ZPL, (c) Zope Corporation and contributors.

PYTHON=python2.6
WD:=$(shell pwd)
PY=$(WD)/bin/py
PYTHONPATH:=$(WD)/lib:$(WD)/lib/mailman:${PYTHONPATH}
BUILDOUT_CFG=buildout.cfg
VERBOSITY=-vv

TESTFLAGS=-p $(VERBOSITY)
TESTOPTS=

SHHH=utilities/shhh.py
HERE:=$(shell pwd)

LPCONFIG?=development

ICING=lib/canonical/launchpad/icing
LP_BUILT_JS_ROOT=${ICING}/build

ifeq ($(LPCONFIG), development)
JS_BUILD := raw
else
JS_BUILD := min
endif

define JS_LP_PATHS
lib -path 'lib/lp/*/javascript/*' \
! -path '*/tests/*' \
! -path 'lib/lp/services/*'
endef

JS_YUI := $(shell utilities/yui-deps.py $(JS_BUILD:raw=))
JS_OTHER := $(wildcard lib/canonical/launchpad/javascript/*/*.js)
JS_LP := $(shell find $(JS_LP_PATHS) -name '*.js' ! -name '.*.js')
JS_ALL := $(JS_YUI) $(JS_OTHER) $(JS_LP)
JS_OUT := $(LP_BUILT_JS_ROOT)/launchpad.js

MINS_TO_SHUTDOWN=15

CODEHOSTING_ROOT=/var/tmp/bazaar.launchpad.dev

BZR_VERSION_INFO = bzr-version-info.py

APIDOC_DIR = lib/canonical/launchpad/apidoc
APIDOC_TMPDIR = $(APIDOC_DIR).tmp/
API_INDEX = $(APIDOC_DIR)/index.html

# Do not add bin/buildout to this list.
# It is impossible to get buildout to tell us all the files it would
# build, since each egg's setup.py doesn't tell us that information.
#
# NB: It's important BUILDOUT_BIN only mentions things genuinely produced by
# buildout.
BUILDOUT_BIN = \
    $(PY) bin/apiindex bin/combine-css bin/fl-build-report \
    bin/fl-credential-ctl bin/fl-install-demo bin/fl-monitor-ctl \
    bin/fl-record bin/fl-run-bench bin/fl-run-test bin/googletestservice \
    bin/i18ncompile bin/i18nextract bin/i18nmergeall bin/i18nstats \
    bin/harness bin/iharness bin/ipy bin/jsbuild \
    bin/killservice bin/kill-test-services bin/lint.sh bin/retest \
    bin/run bin/sprite-util bin/start_librarian bin/stxdocs bin/tags \
    bin/test bin/tracereport bin/twistd bin/update-download-cache

BUILDOUT_TEMPLATES = buildout-templates/_pythonpath.py.in

# DO NOT ALTER : this should just build by default
default: inplace

schema: build
	$(MAKE) -C database/schema
	$(RM) -r /var/tmp/fatsam

newsampledata:
	$(MAKE) -C database/schema newsampledata

hosted_branches: $(PY)
	$(PY) ./utilities/make-dummy-hosted-branches

$(API_INDEX): $(BZR_VERSION_INFO) $(PY)
	rm -rf $(APIDOC_DIR) $(APIDOC_DIR).tmp
	mkdir -p $(APIDOC_DIR).tmp
	LPCONFIG=$(LPCONFIG) $(PY) ./utilities/create-lp-wadl-and-apidoc.py \
	    --force "$(APIDOC_TMPDIR)"
	mv $(APIDOC_TMPDIR) $(APIDOC_DIR)

apidoc: compile $(API_INDEX)

# Used to generate HTML developer documentation for Launchpad.
doc:
	$(MAKE) -C doc/ html

# Run by PQM.
check_config: build
	bin/test -m canonical.config.tests -vvt test_config

# Clean before running the test suite, since the build might fail depending
# what source changes happened. (e.g. apidoc depends on interfaces)
check: clean build
	# Run all tests. test_on_merge.py takes care of setting up the
	# database.
	${PY} -t ./test_on_merge.py $(VERBOSITY) $(TESTOPTS)

check_mailman: build
	# Run all tests, including the Mailman integration
	# tests. test_on_merge.py takes care of setting up the database.
	${PY} -t ./test_on_merge.py $(VERBOSITY) $(TESTOPTS) \
		--layer=MailmanLayer

lint: ${PY}
	@bash ./bin/lint.sh

lint-verbose: ${PY}
	@bash ./bin/lint.sh -v

logs:
	mkdir logs

xxxreport: $(PY)
	${PY} -t ./utilities/xxxreport.py -f csv -o xxx-report.csv ./

check-configs: $(PY)
	${PY} utilities/check-configs.py

pagetests: build
	env PYTHONPATH=$(PYTHONPATH) bin/test test_pages

inplace: build logs clean_logs
	mkdir -p $(CODEHOSTING_ROOT)/mirrors
	mkdir -p $(CODEHOSTING_ROOT)/config
	mkdir -p /var/tmp/bzrsync
	touch $(CODEHOSTING_ROOT)/rewrite.log
	chmod 777 $(CODEHOSTING_ROOT)/rewrite.log
	touch $(CODEHOSTING_ROOT)/config/launchpad-lookup.txt

build: compile apidoc jsbuild css_combine sprite_image

# LP_SOURCEDEPS_PATH should point to the sourcecode directory, but we
# want the parent directory where the download-cache and eggs directory
# are. We re-use the variable that is using for the rocketfuel-get script.
download-cache:
ifdef LP_SOURCEDEPS_PATH
	utilities/link-external-sourcecode $(LP_SOURCEDEPS_PATH)/..
else
	@echo "Missing ./download-cache."
	@echo "Developers: please run utilities/link-external-sourcecode."
	@exit 1
endif

css_combine: sprite_css bin/combine-css
	${SHHH} bin/combine-css

sprite_css: ${LP_BUILT_JS_ROOT}/sprite.css

${LP_BUILT_JS_ROOT}/sprite.css: bin/sprite-util ${ICING}/sprite.css.in \
		${ICING}/icon-sprites.positioning
	${SHHH} bin/sprite-util create-css

sprite_image: ${ICING}/icon-sprites ${ICING}/icon-sprites.positioning

${ICING}/icon-sprites.positioning ${ICING}/icon-sprites: bin/sprite-util \
		${ICING}/sprite.css.in
	${SHHH} bin/sprite-util create-image

jsbuild_widget_css: bin/jsbuild
	${SHHH} bin/jsbuild \
	    --srcdir lib/lp/app/javascript \
	    --builddir $(LP_BUILT_JS_ROOT)

$(JS_LP): jsbuild_widget_css

$(JS_OUT): $(JS_ALL)
ifeq ($(JS_BUILD), min)
	cat $^ | $(PY) -m lp.scripts.utilities.js.jsmin > $@
else
	awk 'FNR == 1 {print "/* " FILENAME " */"} {print}' $^ > $@
endif

jsbuild: $(PY) $(JS_OUT)

eggs:
	# Usually this is linked via link-external-sourcecode, but in
	# deployment we create this ourselves.
	mkdir eggs
	mkdir yui

buildonce_eggs: $(PY)
	find eggs -name '*.pyc' -exec rm {} \;

# The download-cache dependency comes *before* eggs so that developers get the
# warning before the eggs directory is made.  The target for the eggs
# directory is only there for deployment convenience.
# Note that the buildout version must be maintained here and in versions.cfg
# to make sure that the build does not go over the network.
#
# buildout won't touch files that would have the same contents, but for Make's
# sake we need them to get fresh timestamps, so we touch them after building.
bin/buildout: download-cache eggs
	$(SHHH) PYTHONPATH= $(PYTHON) bootstrap.py\
		--setup-source=ez_setup.py \
		--download-base=download-cache/dist --eggs=eggs \
		--version=1.5.1
	touch --no-create $@

# This target is used by LOSAs to prepare a build to be pushed out to
# destination machines.  We only want eggs: they are the expensive bits,
# and the other bits might run into problems like bug 575037.  This
# target runs buildout, and then removes everything created except for
# the eggs.
build_eggs: $(BUILDOUT_BIN)

# This builds bin/py and all the other bin files except bin/buildout.
# Remove the target before calling buildout to ensure that buildout
# updates the timestamp.
buildout_bin: $(BUILDOUT_BIN)

# buildout won't touch files that would have the same contents, but for Make's
# sake we need them to get fresh timestamps, so we touch them after building.
#
# If we listed every target on the left-hand side, a parallel make would try
# multiple copies of this rule to build them all.  Instead, we nominally build
# just $(PY), and everything else is implicitly updated by that.
$(PY): bin/buildout versions.cfg $(BUILDOUT_CFG) setup.py \
		$(BUILDOUT_TEMPLATES)
	$(SHHH) PYTHONPATH= ./bin/buildout \
                configuration:instance_name=${LPCONFIG} -c $(BUILDOUT_CFG)
	touch $@

$(subst $(PY),,$(BUILDOUT_BIN)): $(PY)

compile: $(PY) $(BZR_VERSION_INFO)
	mkdir -p /var/tmp/vostok-archive
	${SHHH} $(MAKE) -C sourcecode build PYTHON=${PYTHON} \
	    LPCONFIG=${LPCONFIG}
	${SHHH} LPCONFIG=${LPCONFIG} ${PY} -t buildmailman.py

test_build: build
	bin/test $(TESTFLAGS) $(TESTOPTS)

test_inplace: inplace
	bin/test $(TESTFLAGS) $(TESTOPTS)

ftest_build: build
	bin/test -f $(TESTFLAGS) $(TESTOPTS)

ftest_inplace: inplace
	bin/test -f $(TESTFLAGS) $(TESTOPTS)

merge-proposal-jobs:
	# Handle merge proposal email jobs.
	$(PY) cronscripts/merge-proposal-jobs.py -v

run: build inplace stop
	bin/run -r librarian,google-webservice,memcached -i $(LPCONFIG)

run.gdb:
	echo 'run' > run.gdb

start-gdb: build inplace stop support_files run.gdb
	nohup gdb -x run.gdb --args bin/run -i $(LPCONFIG) \
		-r librarian,google-webservice
		> ${LPCONFIG}-nohup.out 2>&1 &

run_all: build inplace stop
	bin/run \
	 -r librarian,sftp,forker,mailman,codebrowse,google-webservice,memcached \
	 -i $(LPCONFIG)

run_codebrowse: build
	BZR_PLUGIN_PATH=bzrplugins $(PY) scripts/start-loggerhead.py -f

start_codebrowse: build
	BZR_PLUGIN_PATH=$(shell pwd)/bzrplugins $(PY) scripts/start-loggerhead.py

stop_codebrowse:
	$(PY) scripts/stop-loggerhead.py

run_codehosting: build inplace stop
	bin/run -r librarian,sftp,forker,codebrowse -i $(LPCONFIG)

start_librarian: compile
	bin/start_librarian

stop_librarian:
	bin/killservice librarian

pull_branches: support_files
	$(PY) cronscripts/supermirror-pull.py

scan_branches:
	# Scan branches from the filesystem into the database.
	$(PY) cronscripts/scan_branches.py

sync_branches: pull_branches scan_branches merge-proposal-jobs

$(BZR_VERSION_INFO):
	scripts/update-bzr-version-info.sh

support_files: $(API_INDEX) $(BZR_VERSION_INFO)

# Intended for use on developer machines
start: inplace stop support_files initscript-start

# Run as a daemon - hack using nohup until we move back to using zdaemon
# properly. We also should really wait until services are running before
# exiting, as running 'make stop' too soon after running 'make start'
# will not work as expected. For use on production servers, where
# we know we don't need the extra steps in a full "make start"
# because of how the code is deployed/built.
initscript-start:
	nohup bin/run -i $(LPCONFIG) > ${LPCONFIG}-nohup.out 2>&1 &

# Intended for use on developer machines
stop: build initscript-stop

# Kill launchpad last - other services will probably shutdown with it,
# so killing them after is a race condition. For use on production
# servers, where we know we don't need the extra steps in a full
# "make stop" because of how the code is deployed/built.
initscript-stop:
	bin/killservice librarian launchpad mailman

shutdown: scheduleoutage stop
	$(RM) +maintenancetime.txt

scheduleoutage:
	echo Scheduling outage in ${MINS_TO_SHUTDOWN} mins
	date --iso-8601=minutes -u -d +${MINS_TO_SHUTDOWN}mins > +maintenancetime.txt
	echo Sleeping ${MINS_TO_SHUTDOWN} mins
	sleep ${MINS_TO_SHUTDOWN}m

harness: bin/harness
	bin/harness

iharness: bin/iharness
	bin/iharness

rebuildfti:
	@echo Rebuilding FTI indexes on launchpad_dev database
	$(PY) database/schema/fti.py -d launchpad_dev --force

clean_js:
	$(RM) $(JS_OUT)
	$(RM) -r $(LAZR_BUILT_JS_ROOT)

clean_buildout:
	$(RM) -r bin
	$(RM) -r parts
	$(RM) -r develop-eggs
	$(RM) .installed.cfg
	$(RM) -r build
	$(RM) _pythonpath.py
	$(RM) -r yui/*

clean_logs:
	$(RM) logs/thread*.request

clean: clean_js clean_buildout clean_logs
	$(MAKE) -C sourcecode/pygettextpo clean
	# XXX gary 2009-11-16 bug 483782
	# The pygettextpo Makefile should have this next line in it for its make
	# clean, and then we should remove this line.
	$(RM) sourcecode/pygpgme/gpgme/*.so
	if test -f sourcecode/mailman/Makefile; then \
		$(MAKE) -C sourcecode/mailman clean; \
	fi
	find . -path ./eggs -prune -false -o \
		-type f \( -name '*.o' -o -name '*.so' -o -name '*.la' -o \
	    -name '*.lo' -o -name '*.py[co]' -o -name '*.dll' \) \
	    -print0 | xargs -r0 $(RM)
	$(RM) -r lib/mailman
	$(RM) -rf $(LP_BUILT_JS_ROOT)/*
	$(RM) -rf $(CODEHOSTING_ROOT)
	$(RM) -rf $(APIDOC_DIR)
	$(RM) -rf $(APIDOC_DIR).tmp
	$(RM) $(BZR_VERSION_INFO)
	$(RM) +config-overrides.zcml
	$(RM) -rf \
			  /var/tmp/builddmaster \
			  /var/tmp/bzrsync \
			  /var/tmp/codehosting.test \
			  /var/tmp/codeimport \
			  /var/tmp/fatsam.test \
			  /var/tmp/lperr \
			  /var/tmp/lperr.test \
			  /var/tmp/mailman \
			  /var/tmp/mailman-xmlrpc.test \
			  /var/tmp/ppa \
			  /var/tmp/ppa.test \
			  /var/tmp/testkeyserver
	# /var/tmp/launchpad_mailqueue is created read-only on ec2test
	# instances.
	if [ -w /var/tmp/launchpad_mailqueue ]; then \
		$(RM) -rf /var/tmp/launchpad_mailqueue; \
	fi


realclean: clean
	$(RM) TAGS tags

zcmldocs:
	mkdir -p doc/zcml/namespaces.zope.org
	bin/stxdocs \
	    -f sourcecode/zope/src/zope/app/zcmlfiles/meta.zcml \
	    -o doc/zcml/namespaces.zope.org

potemplates: launchpad.pot

# Generate launchpad.pot by extracting message ids from the source
launchpad.pot:
	bin/i18nextract.py

# Called by the rocketfuel-setup script. You probably don't want to run this
# on its own.
install: reload-apache

copy-certificates:
	mkdir -p /etc/apache2/ssl
	cp configs/development/launchpad.crt /etc/apache2/ssl/
	cp configs/development/launchpad.key /etc/apache2/ssl/

copy-apache-config:
	# We insert the absolute path to the branch-rewrite script
	# into the Apache config as we copy the file into position.
	sed -e 's,%BRANCH_REWRITE%,$(shell pwd)/scripts/branch-rewrite.py,' \
		configs/development/local-launchpad-apache > \
		/etc/apache2/sites-available/local-launchpad
	cp configs/development/local-vostok-apache \
		/etc/apache2/sites-available/local-vostok
	touch /var/tmp/bazaar.launchpad.dev/rewrite.log
	chown $(SUDO_UID):$(SUDO_GID) /var/tmp/bazaar.launchpad.dev/rewrite.log

enable-apache-launchpad: copy-apache-config copy-certificates
	a2ensite local-launchpad
	a2ensite local-vostok

reload-apache: enable-apache-launchpad
	/etc/init.d/apache2 restart

TAGS: compile
	# emacs tags
	bin/tags -e

tags: compile
	# vi tags
	bin/tags -v

ID: compile
	# idutils ID file
	bin/tags -i

PYDOCTOR = pydoctor
PYDOCTOR_OPTIONS =

pydoctor:
	$(PYDOCTOR) --make-html --html-output=apidocs --add-package=lib/lp \
		--add-package=lib/canonical --project-name=Launchpad \
		--docformat restructuredtext --verbose-about epytext-summary \
		$(PYDOCTOR_OPTIONS)

.PHONY: \
	apidoc build_eggs buildonce_eggs buildout_bin check check \
	check_config check_mailman clean clean_buildout clean_js \
	clean_logs compile css_combine debug default doc ftest_build \
	ftest_inplace hosted_branches jsbuild jsbuild_widget_css \
	launchpad.pot pagetests pull_branches pydoctor realclean \
	reload-apache run scan_branches schema sprite_css sprite_image \
	start stop sync_branches TAGS tags test_build test_inplace \
	zcmldocs
