PYTHON_VERSION=2.4
PYTHON=python${PYTHON_VERSION}
# Not all packages have a working Makefile. Work around this by hardcoding
# the ones we test.  If we fix them all to have EITHER a good makefile
# (build and check targets work), or no makefile we can reenable auto
# detection.
build_dirs:=bzr cscvs lazr-js lsprof pygettextpo pygpgme storm twisted zope
test_dirs:=bzr cscvs pygettextpo storm twisted zope

STORM_TESTDB = storm_test

TEST_ENV_VARS = \
  PYTHON=$(PYTHON) \
  PYTHON_VERSION=$(PYTHON_VERSION) \
  STORM_POSTGRES_URI=postgres:$(STORM_TESTDB) \
  STORM_POSTGRES_HOST_URI=postgres://localhost/$(STORM_TESTDB) \
  STORM_MYSQL_URI= \
  STORM_MYSQL_HOST_URI=

all:

check: build storm_testdb
	@ for subdir in ${test_dirs}; do \
		$(MAKE) -C $$subdir check $(TEST_ENV_VARS) || exit $$?;\
	done

build:
	@ for subdir in ${build_dirs}; do\
		if [ -e $$subdir/Makefile ]; then\
			$(MAKE) -C $$subdir $(TEST_ENV_VARS) || exit $$?;\
		fi;\
	done

# Storm's test suite expects the test database to exist before the
# test suite is run.
storm_testdb:
	@echo "* Creating $(STORM_TESTDB)"
	@if psql -l | grep -q " $(STORM_TESTDB) "; then \
	    dropdb $(STORM_TESTDB) >/dev/null; \
	fi
	createdb $(STORM_TESTDB)

.PHONY: check all build storm_testdb
