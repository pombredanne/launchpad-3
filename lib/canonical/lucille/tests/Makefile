# Tests for lucille
# arch-tag: 6670cf71-3b42-4e1d-8251-03ceb402920a
# (c) 2004 Canonical Software Ltd.
# Author: Daniel Silverstone <daniel.silverstone@canonical.com>

PYTHON_VERSION=2.4
PYTHON=python${PYTHON_VERSION}

.PHONY: all
all:

PYTHONPATH:=$(shell pwd)/../../..
export PYTHONPATH

check: check-lucile

check-lucile:
#	${PYTHON} ./test_tagfiles.py
#	${PYTHON} ./test_signedfiles.py
#	${PYTHON} ./test_utils.py
	${PYTHON} ./test_domination.py

