PYTHON_VERSION=2.4
PYTHON=python${PYTHON_VERSION}
# Not all packages have a working Makefile. Work around this by hardcoding
# the ones we test.  If we fix them all to have EITHER a good makefile
# (build and check targets work), or no makefile we can reenable auto
# detection.
# test_dirs:=$(shell find . -maxdepth 1 -mindepth 1 -name ".arch-ids" -prune -o -type d -print | grep -v pyarch)
build_dirs:=bzr cscvs pygettextpo pygpgme sqlobject twisted zope
test_dirs:=bzr cscvs pygettextpo sqlobject twisted zope
launchpad_test_dirs:=

all:

check: build
	@ for subdir in ${test_dirs}; do \
		$(MAKE) -C $$subdir check \
		PYTHON=${PYTHON} PYTHON_VERSION=${PYTHON_VERSION} || exit $$?;\
	done

check_for_launchpad: build
	@ for subdir in ${launchpad_test_dirs}; do \
		$(MAKE) -C $$subdir check \
		PYTHON=${PYTHON} PYTHON_VERSION=${PYTHON_VERSION} || exit $$?;\
	done

build:
	@ for subdir in ${build_dirs}; do\
		if [ -e $$subdir/Makefile ]; then\
			$(MAKE) -C $$subdir \
			PYTHON=${PYTHON} PYTHON_VERSION=${PYTHON_VERSION} \
			       || exit $$?;\
		fi;\
	done
	#cd zope && ./configure --prefix=inst
	#cd zope && make install

.PHONY: check check_for_launchpad all build


