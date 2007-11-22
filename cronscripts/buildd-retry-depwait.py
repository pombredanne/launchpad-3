#!/usr/bin/python2.4
# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0403
"""Retrying build in MANUALDEPWAIT state.

This procedure aims to retry builds in all supported series and architectures
in the given distribution which have failed due to unsatisfied
build-dependencies.

It checks every build in this state, including PPA and PARTNER ones, and
retry the ones which got their dependencies published after they were tried.

Different than the other buildd-cronscripts, this one it targeted to run via
cron in parallel with other tasks happen in build farm.

As a optimization, distroseries from the selected distribution which are not
supported anymore (OBSOLETE status) are skipped from the iteration.
"""

__metaclass__ = type

import _pythonpath

from canonical.config import config
from canonical.launchpad.scripts.buildd import RetryDepwait

if __name__ == '__main__':
    script = RetryDepwait(
        'retry-depwait', dbuser=config.builddmaster.dbuser)
    script.lock_or_quit()
    try:
        script.run()
    finally:
        script.unlock()
