#!/usr/bin/python -S
#
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Synchronize packages."""

__metaclass__ = type

import _pythonpath

from lp.services.job.runner import JobCronScript
from lp.soyuz.interfaces.distributionjob import IPackageCopyJobSource


class RunPackageCopyJob(JobCronScript):
    """Run PackageCopyJob jobs."""

    config_name = 'sync_packages'
    source_interface = IPackageCopyJobSource


if __name__ == '__main__':
    script = RunPackageCopyJob()
    script.lock_and_run()
