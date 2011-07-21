#!/usr/bin/python -S
#
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Run jobs specified by a config section."""

__metaclass__ = type

import _pythonpath

from lp.services.job.runner import JobCronScript

if __name__ == '__main__':
    script = JobCronScript(commandline_config=True)
    script.lock_and_run()
