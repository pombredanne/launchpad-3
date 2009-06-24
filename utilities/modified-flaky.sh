#!/bin/sh
#
# Copyright <YEARS> Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3; see the file LICENSE for

# Run pyflakes checks on files modified in working copy.
(bzr status | sed -e '0,/^modified/d; /^[^ ]/,$d';
 bzr status | sed -e '0,/^added/d; /^[^ ]/,$d') |\
	grep '\.py$' |\
	xargs `dirname $0`/flaky.py
