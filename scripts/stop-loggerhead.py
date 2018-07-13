#!/usr/bin/python -S
#
# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import absolute_import, print_function, unicode_literals

import _pythonpath

from optparse import OptionParser
import os
import signal
import sys

from lp.services.pidfile import get_pid


parser = OptionParser(description="Stop loggerhead.")
parser.parse_args()

pid = get_pid("codebrowse")

try:
    os.kill(pid, 0)
except OSError as e:
    print('Stale pid file; server is not running.')
    sys.exit(1)

print()
print('Shutting down previous server @ pid %d.' % (pid,))
print()

os.kill(pid, signal.SIGTERM)
