#!/usr/bin/python -S
#
# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=C0103,W0403
"""Retrying build in MANUALDEPWAIT state.

This procedure aims to retry builds in all supported series and architectures
in the given distribution which have failed due to unsatisfied
build-dependencies.

It checks every build in this state, including PPA and PARTNER ones, and
retries the ones which got their dependencies published after they were tried.

Unlike the other buildd-cronscripts, this one it targeted to run via cron
in parallel with other tasks happening in build farm.

As an optimization, distroseries from the selected distribution which are not
supported anymore (OBSOLETE status) are skipped.
"""

__metaclass__ = type

import _pythonpath

from lp.soyuz.scripts.buildd import RetryDepwait

if __name__ == '__main__':
    script = RetryDepwait('retry-depwait', dbuser='retry_depwait')
    script.lock_or_quit()
    try:
        script.run()
    finally:
        script.unlock()
