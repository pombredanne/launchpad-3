#!/usr/bin/python -S
#
# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Run `CreateDistroSeriesIndexesJob`s.

The jobs write to the file system.  This script should be run _only_ on
a server that holds the distributions archives.
"""

__metaclass__ = type

import _pythonpath

from lp.archivepublisher.interfaces.createdistroseriesindexesjob import (
    ICreateDistroSeriesIndexesJobSource,
    )
from lp.services.job.runner import JobCronScript


class RunCreateDistroSeriesIndexesJobs(JobCronScript):
    """Run `CreateDistroSeriesIndexesJobs`s."""

    config_name = 'create_distroseries_indexes'
    source_interface = ICreateDistroSeriesIndexesJobSource


if __name__ == '__main__':
    RunCreateDistroSeriesIndexesJobs().lock_and_run()
