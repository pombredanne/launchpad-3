PYTHON_VERSION=2.4
PYTHON=python${PYTHON_VERSION}

test_dirs:=$(shell find . -maxdepth 1 -mindepth 1 -name ".arch-ids" -prune -o -type d -print | grep -v pyarch)

all:

check: build
	@ for subdir in ${test_dirs}; do \
		$(MAKE) -C $$subdir check \
		PYTHON=${PYTHON} PYTHON_VERSION=${PYTHON_VERSION} || exit $$?;\
	done

build:
	@ for subdir in ${test_dirs}; do\
		if [ -e $$subdir/Makefile ]; then\
			$(MAKE) -C $$subdir \
			PYTHON=${PYTHON} PYTHON_VERSION=${PYTHON_VERSION} \
			       || exit $$?;\
		fi\
	done

.PHONY: check all build


