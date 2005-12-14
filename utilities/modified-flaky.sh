#!/bin/sh
# Run pyflakes checks on files modified in working copy.
bzr status |\
	sed -e '1,/modified/d; /^[^ ]/,$d' |\
	grep '\.py$' |\
	xargs `dirname $0`/flaky.py

