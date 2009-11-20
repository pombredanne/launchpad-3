PYTHON_VERSION=2.5
PYTHON=python${PYTHON_VERSION}
# Not all packages have a working Makefile. Work around this by hardcoding
# the ones we test.  If we fix them all to have EITHER a good makefile
# (build and check targets work), or no makefile we can reenable auto
# detection.
build_dirs:=cscvs dulwich pygettextpo pygpgme subvertpy twisted 
test_dirs:=cscvs pygettextpo twisted

TEST_ENV_VARS = \
  PYTHON=$(PYTHON) \
  PYTHON_VERSION=$(PYTHON_VERSION)

all:

check: build
	@ for subdir in ${test_dirs}; do \
		$(MAKE) -C $$subdir check $(TEST_ENV_VARS) || exit $$?;\
	done

build:
	@ for subdir in ${build_dirs}; do\
		if [ -e $$subdir/Makefile ]; then\
			$(MAKE) -C $$subdir $(TEST_ENV_VARS) || exit $$?;\
		fi;\
	done
	$(MAKE) -C mercurial local $(TEST_ENV_VARS)

.PHONY: check all build
