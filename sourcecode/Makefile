test_dirs:=$(shell find . -maxdepth 1 -mindepth 1 -name ".arch-ids" -prune -o -type d -print)

all:

check: build
	@ for subdir in ${test_dirs}; do \
		$(MAKE) -C $$subdir check || exit $$?;\
	done

build:
	@ for subdir in ${test_dirs}; do\
		if [ -e $$subdir/Makefile ]; then\
			$(MAKE) -C $$subdir || exit $$?;\
		fi\
	done

.PHONY: check all build


