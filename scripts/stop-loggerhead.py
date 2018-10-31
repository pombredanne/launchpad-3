#!/usr/bin/python -S
#
# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import absolute_import, print_function, unicode_literals

import _pythonpath

from optparse import OptionParser
import sys

from lp.services.osutils import (
    process_exists,
    two_stage_kill,
    )
from lp.services.pidfile import get_pid


parser = OptionParser(description="Stop loggerhead.")
parser.parse_args()

pid = get_pid("codebrowse")

if pid is None:
    # Already stopped.
    sys.exit(0)

if not process_exists(pid):
    print('Stale pid file; server is not running.')
    sys.exit(1)

print()
print('Shutting down previous server @ pid %d.' % (pid,))
print()

# A busy gunicorn can take a while to shut down.
two_stage_kill(pid, poll_interval=0.5, num_polls=120, get_status=False)
