# This file modified from Zope3/Makefile
# Licensed under the ZPL, (c) Zope Corporation and contributors.

PYTHON:=python2.7

WD:=$(shell pwd)
PY=$(WD)/bin/py
PYTHONPATH:=$(WD)/lib:${PYTHONPATH}
VERBOSITY=-vv

# virtualenv and pip fail if setlocale fails, so force a valid locale.
VIRTUALENV := LC_ALL=C.UTF-8 virtualenv
PIP := PYTHONPATH= LC_ALL=C.UTF-8 env/bin/pip
# Run with "make PIP_NO_INDEX=" if you want pip to find software
# dependencies *other* than those in our download-cache.  Once you have the
# desired software, commit it to lp:lp-source-dependencies if it is going to
# be reviewed/merged/deployed.
# Although --ignore-installed is slower, we need it to avoid confusion with
# system-installed Python packages.  If we ever manage to remove the need
# for virtualenv --system-site-packages, then we can remove this too.
PIP_NO_INDEX := --no-index
PIP_INSTALL_ARGS := \
	$(PIP_NO_INDEX) \
	--ignore-installed \
	--find-links=file://$(WD)/download-cache/dist/ \

TESTFLAGS=-p $(VERBOSITY)
TESTOPTS=

SHHH=utilities/shhh.py

LPCONFIG?=development

LISTEN_ADDRESS?=127.0.0.88

ICING=lib/canonical/launchpad/icing
LP_BUILT_JS_ROOT=${ICING}/build

JS_BUILD_DIR := build/js
YARN_VERSION := 1.2.1
YARN_BUILD := $(JS_BUILD_DIR)/yarn
YARN := utilities/yarn
YUI_SYMLINK := $(JS_BUILD_DIR)/yui
LP_JS_BUILD := $(JS_BUILD_DIR)/lp

MINS_TO_SHUTDOWN=15

CODEHOSTING_ROOT=/var/tmp/bazaar.launchpad.dev

CONVOY_ROOT?=/srv/launchpad.dev/convoy

VERSION_INFO = version-info.py

APIDOC_DIR = lib/canonical/launchpad/apidoc
APIDOC_TMPDIR = $(APIDOC_DIR).tmp/
API_INDEX = $(APIDOC_DIR)/index.html

# It is impossible to get pip to tell us all the files it would build, since
# each package's setup.py doesn't tell us that information.
#
# NB: It's important PIP_BIN only mentions things genuinely produced by pip.
PIP_BIN = \
    $(PY) \
    bin/build-twisted-plugin-cache \
    bin/combine-css \
    bin/googletestservice \
    bin/harness \
    bin/iharness \
    bin/ipy \
    bin/jsbuild \
    bin/lpjsmin \
    bin/killservice \
    bin/kill-test-services \
    bin/retest \
    bin/run \
    bin/run-testapp \
    bin/sprite-util \
    bin/start_librarian \
    bin/test \
    bin/tracereport \
    bin/twistd \
    bin/watch_jsbuild \
    bin/with-xvfb

# DO NOT ALTER : this should just build by default
default: inplace

schema: build
	$(MAKE) -C database/schema
	$(RM) -r /var/tmp/fatsam

newsampledata:
	$(MAKE) -C database/schema newsampledata

hosted_branches: $(PY)
	$(PY) ./utilities/make-dummy-hosted-branches

$(API_INDEX): $(VERSION_INFO) $(PY)
	$(RM) -r $(APIDOC_DIR) $(APIDOC_DIR).tmp
	mkdir -p $(APIDOC_DIR).tmp
	LPCONFIG=$(LPCONFIG) $(PY) ./utilities/create-lp-wadl-and-apidoc.py \
	    --force "$(APIDOC_TMPDIR)"
	mv $(APIDOC_TMPDIR) $(APIDOC_DIR)

apidoc:
ifdef LP_MAKE_NO_WADL
	@echo "Skipping WADL generation."
else
	$(MAKE) compile $(API_INDEX)
endif

# Used to generate HTML developer documentation for Launchpad.
doc:
	$(MAKE) -C doc/ html

# Run by PQM.
check_config: build $(JS_BUILD_DIR)/.development
	bin/test -m lp.services.config.tests -vvt test_config

# Clean before running the test suite, since the build might fail depending
# what source changes happened. (e.g. apidoc depends on interfaces)
check: clean build $(JS_BUILD_DIR)/.development
	# Run all tests. test_on_merge.py takes care of setting up the
	# database.
	${PY} -t ./test_on_merge.py $(VERBOSITY) $(TESTOPTS)
	bzr status --no-pending

check_mailman: build $(JS_BUILD_DIR)/.development
	# Run all tests, including the Mailman integration
	# tests. test_on_merge.py takes care of setting up the database.
	${PY} -t ./test_on_merge.py $(VERBOSITY) $(TESTOPTS) \
		lp.services.mailman.tests

lint: ${PY} $(JS_BUILD_DIR)/.development
	@bash ./utilities/lint

lint-verbose: ${PY} $(JS_BUILD_DIR)/.development
	@bash ./utilities/lint -v

logs:
	mkdir logs

codehosting-dir:
	mkdir -p $(CODEHOSTING_ROOT)
	mkdir -p $(CODEHOSTING_ROOT)/mirrors
	mkdir -p $(CODEHOSTING_ROOT)/config
	mkdir -p /var/tmp/bzrsync
	touch $(CODEHOSTING_ROOT)/rewrite.log
	chmod 777 $(CODEHOSTING_ROOT)/rewrite.log
	touch $(CODEHOSTING_ROOT)/config/launchpad-lookup.txt
ifneq ($(SUDO_UID),)
	if [ "$$(id -u)" = 0 ]; then \
		chown -R $(SUDO_UID):$(SUDO_GID) $(CODEHOSTING_ROOT); \
	fi
endif

inplace: build logs clean_logs codehosting-dir
	if [ -d /srv/launchpad.dev ]; then \
		ln -sfn $(WD)/build/js $(CONVOY_ROOT); \
	fi

build: compile apidoc jsbuild css_combine

# LP_SOURCEDEPS_PATH should point to the sourcecode directory, but we
# want the parent directory where the download-cache and env directories
# are. We re-use the variable that is using for the rocketfuel-get script.
download-cache:
ifdef LP_SOURCEDEPS_PATH
	utilities/link-external-sourcecode $(LP_SOURCEDEPS_PATH)/..
else
	@echo "Missing ./download-cache."
	@echo "Developers: please run utilities/link-external-sourcecode."
	@exit 1
endif

css_combine: jsbuild_widget_css
	${SHHH} bin/sprite-util create-image
	${SHHH} bin/sprite-util create-css
	ln -sfn ../../../../yarn/node_modules/yui $(ICING)/yui
	${SHHH} bin/combine-css

jsbuild_widget_css: bin/jsbuild
	${SHHH} bin/jsbuild \
	    --srcdir lib/lp/app/javascript \
	    --builddir $(LP_BUILT_JS_ROOT)

jsbuild_watch:
	$(PY) bin/watch_jsbuild

$(JS_BUILD_DIR):
	mkdir -p $@

$(YARN_BUILD): | $(JS_BUILD_DIR)
	mkdir -p $@/tmp
	tar -C $@/tmp -xf download-cache/dist/yarn-$(YARN_VERSION).tar.gz
	mv $@/tmp/yarn-v$(YARN_VERSION)/* $@
	$(RM) -r $@/tmp

$(JS_BUILD_DIR)/.production: yarn/package.json | $(YARN_BUILD)
	$(YARN) install --offline --frozen-lockfile --production
	# We don't use YUI's Flash components and they have a bad security
	# record. Kill them.
	find yarn/node_modules/yui -name '*.swf' -delete
	touch $@

$(JS_BUILD_DIR)/.development: $(JS_BUILD_DIR)/.production
	$(YARN) install --offline --frozen-lockfile
	touch $@

$(YUI_SYMLINK): $(JS_BUILD_DIR)/.production
	ln -sfn ../../yarn/node_modules/yui $@

$(LP_JS_BUILD): | $(JS_BUILD_DIR)
	mkdir -p $@/services
	for jsdir in lib/lp/*/javascript lib/lp/services/*/javascript; do \
		app=$$(echo $$jsdir | sed -e 's,lib/lp/\(.*\)/javascript,\1,'); \
		cp -a $$jsdir $@/$$app; \
	done
	find $@ -name 'tests' -type d | xargs rm -rf
	bin/lpjsmin -p $@

jsbuild: $(LP_JS_BUILD) $(YUI_SYMLINK)
	utilities/js-deps -n LP_MODULES -s build/js/lp -x '-min.js' -o \
	build/js/lp/meta.js >/dev/null
	utilities/check-js-deps

# This target is used by LOSAs to prepare a build to be pushed out to
# destination machines.  We only want wheels: they are the expensive bits,
# and the other bits might run into problems like bug 575037.  This
# target runs pip, and then removes everything created except for the
# wheels.
build_wheels: $(PIP_BIN) clean_pip

# Compatibility.
build_eggs: build_wheels

# setuptools won't touch files that would have the same contents, but for
# Make's sake we need them to get fresh timestamps, so we touch them after
# building.
#
# If we listed every target on the left-hand side, a parallel make would try
# multiple copies of this rule to build them all.  Instead, we nominally build
# just $(PY), and everything else is implicitly updated by that.
$(PY): download-cache constraints.txt setup.py
	rm -rf env
	mkdir -p env
	(echo '[easy_install]'; \
	 echo "allow_hosts = ''"; \
	 echo 'find_links = file://$(WD)/download-cache/dist/') \
		>env/.pydistutils.cfg
	$(VIRTUALENV) \
		--python=$(PYTHON) --system-site-packages --never-download \
		--extra-search-dir=$(WD)/download-cache/dist/ \
		env
	ln -sfn env/bin bin
	$(SHHH) $(PIP) install $(PIP_INSTALL_ARGS) \
		-r pip-requirements.txt
	$(SHHH) LPCONFIG=$(LPCONFIG) $(PIP) \
		--cache-dir=$(WD)/download-cache/ \
		install $(PIP_INSTALL_ARGS) \
		-c pip-requirements.txt -c constraints.txt -e . \
		|| { code=$$?; rm -f $@; exit $$code; }
	touch $@

$(subst $(PY),,$(PIP_BIN)): $(PY)

compile: $(PY) $(VERSION_INFO)
	${SHHH} utilities/relocate-virtualenv env
	${SHHH} $(MAKE) -C sourcecode build PYTHON=${PYTHON} \
	    LPCONFIG=${LPCONFIG}
	${SHHH} bin/build-twisted-plugin-cache
	${SHHH} LPCONFIG=${LPCONFIG} ${PY} -t buildmailman.py

test_build: build
	bin/test $(TESTFLAGS) $(TESTOPTS)

test_inplace: inplace
	bin/test $(TESTFLAGS) $(TESTOPTS)

ftest_build: build
	bin/test -f $(TESTFLAGS) $(TESTOPTS)

ftest_inplace: inplace
	bin/test -f $(TESTFLAGS) $(TESTOPTS)

run: build inplace stop
	bin/run -r librarian,google-webservice,memcached,rabbitmq,txlongpoll \
	-i $(LPCONFIG)

run-testapp: LPCONFIG=testrunner-appserver
run-testapp: build inplace stop
	LPCONFIG=$(LPCONFIG) INTERACTIVE_TESTS=1 bin/run-testapp \
	-r memcached -i $(LPCONFIG)

run.gdb:
	echo 'run' > run.gdb

start-gdb: build inplace stop support_files run.gdb
	nohup gdb -x run.gdb --args bin/run -i $(LPCONFIG) \
		-r librarian,google-webservice
		> ${LPCONFIG}-nohup.out 2>&1 &

run_all: build inplace stop
	bin/run \
	 -r librarian,sftp,forker,mailman,codebrowse,google-webservice,\
	memcached,rabbitmq,txlongpoll -i $(LPCONFIG)

run_codebrowse: compile
	BZR_PLUGIN_PATH=bzrplugins $(PY) scripts/start-loggerhead.py -f

start_codebrowse: compile
	BZR_PLUGIN_PATH=$(shell pwd)/bzrplugins $(PY) scripts/start-loggerhead.py

stop_codebrowse:
	$(PY) scripts/stop-loggerhead.py

run_codehosting: build inplace stop
	bin/run -r librarian,sftp,forker,codebrowse,rabbitmq -i $(LPCONFIG)

start_librarian: compile
	bin/start_librarian

stop_librarian:
	bin/killservice librarian

$(VERSION_INFO):
	scripts/update-version-info.sh

support_files: $(API_INDEX) $(VERSION_INFO)

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
	$(RM) -r $(JS_BUILD_DIR)
	$(RM) -r yarn/node_modules

clean_pip:
	$(RM) -r build
	if [ -d $(CONVOY_ROOT) ]; then $(RM) -r $(CONVOY_ROOT) ; fi
	$(RM) -r bin
	$(RM) -r parts
	$(RM) .installed.cfg

# Compatibility.
clean_buildout: clean_pip

clean_logs:
	$(RM) logs/thread*.request

clean_mailman:
	$(RM) -r /var/tmp/mailman /var/tmp/mailman-xmlrpc.test
ifdef LP_MAKE_KEEP_MAILMAN
	@echo "Keeping previously built mailman."
else
	$(RM) lib/Mailman
	$(RM) -r lib/mailman
endif

lxc-clean: clean_js clean_mailman clean_pip clean_logs
	# XXX: BradCrittenden 2012-05-25 bug=1004514:
	# It is important for parallel tests inside LXC that the
	# $(CODEHOSTING_ROOT) directory not be completely removed.
	# This target removes its contents but not the directory and
	# it does everything expected from a clean target.  When the
	# referenced bug is fixed, this target may be reunited with
	# the 'clean' target.
	if test -f sourcecode/pygettextpo/Makefile; then \
		$(MAKE) -C sourcecode/pygettextpo clean; \
	fi
	if test -f sourcecode/mailman/Makefile; then \
		$(MAKE) -C sourcecode/mailman clean; \
	fi
	$(RM) -r env
	$(RM) -r $(LP_BUILT_JS_ROOT)/*
	$(RM) -r $(CODEHOSTING_ROOT)/*
	$(RM) -r $(APIDOC_DIR)
	$(RM) -r $(APIDOC_DIR).tmp
	$(RM) -r build
	$(RM) $(VERSION_INFO)
	$(RM) +config-overrides.zcml
	$(RM) -r /var/tmp/builddmaster \
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
		$(RM) -r /var/tmp/launchpad_mailqueue; \
	fi

clean: lxc-clean
	$(RM) -r $(CODEHOSTING_ROOT)

realclean: clean
	$(RM) TAGS tags

potemplates: launchpad.pot

# Generate launchpad.pot by extracting message ids from the source
# XXX cjwatson 2017-09-04: This was previously done using i18nextract from
# z3c.recipe.i18n, but has been broken for some time.  The place to start in
# putting this together again is probably zope.app.locales.
launchpad.pot:
	echo "POT generation not currently supported; help us fix this!" >&2
	exit 1

# Called by the rocketfuel-setup script. You probably don't want to run this
# on its own.
install: reload-apache

copy-certificates:
	mkdir -p /etc/apache2/ssl
	cp configs/development/launchpad.crt /etc/apache2/ssl/
	cp configs/development/launchpad.key /etc/apache2/ssl/

copy-apache-config: codehosting-dir
	# We insert the absolute path to the branch-rewrite script
	# into the Apache config as we copy the file into position.
	set -e; \
	apachever="$$(dpkg-query -W --showformat='$${Version}' apache2)"; \
	if dpkg --compare-versions "$$apachever" ge 2.4.1-1~; then \
		base=local-launchpad.conf; \
	else \
		base=local-launchpad; \
	fi; \
	sed -e 's,%BRANCH_REWRITE%,$(shell pwd)/scripts/branch-rewrite.py,' \
		-e 's,%LISTEN_ADDRESS%,$(LISTEN_ADDRESS),' \
		configs/development/local-launchpad-apache > \
		/etc/apache2/sites-available/$$base
	if [ ! -d /srv/launchpad.dev ]; then \
		mkdir /srv/launchpad.dev; \
		chown $(SUDO_UID):$(SUDO_GID) /srv/launchpad.dev; \
	fi

enable-apache-launchpad: copy-apache-config copy-certificates
	[ ! -e /etc/apache2/mods-available/version.load ] || a2enmod version
	a2ensite local-launchpad

reload-apache: enable-apache-launchpad
	service apache2 restart

TAGS: compile
	# emacs tags
	ctags -R -e --languages=-JavaScript --python-kinds=-i -f $@.new \
		$(CURDIR)/lib $(CURDIR)/env/lib/$(PYTHON)/site-packages
	mv $@.new $@

tags: compile
	# vi tags
	ctags -R --languages=-JavaScript --python-kinds=-i -f $@.new \
		$(CURDIR)/lib $(CURDIR)/env/lib/$(PYTHON)/site-packages
	mv $@.new $@

PYDOCTOR = pydoctor
PYDOCTOR_OPTIONS =

pydoctor:
	$(PYDOCTOR) --make-html --html-output=apidocs --add-package=lib/lp \
		--add-package=lib/canonical --project-name=Launchpad \
		--docformat restructuredtext --verbose-about epytext-summary \
		$(PYDOCTOR_OPTIONS)

.PHONY: apidoc build_eggs build_wheels check check_config check_mailman	\
	clean clean_buildout clean_js clean_logs clean_pip compile	\
	css_combine debug default doc ftest_build ftest_inplace		\
	hosted_branches jsbuild jsbuild_widget_css launchpad.pot	\
	pydoctor realclean reload-apache run run-testapp runner schema	\
	sprite_css sprite_image start stop TAGS tags test_build		\
	test_inplace $(LP_JS_BUILD)
