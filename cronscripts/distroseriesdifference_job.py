#!/usr/bin/python -S
#
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Process DistroSeriesDifferences."""

__metaclass__ = type

import _pythonpath

from lp.services.job.runner import JobCronScript
from lp.soyuz.interfaces.distributionjob import (
    IDistroSeriesDifferenceJobSource,
    )


class RunDistroSeriesDifferenceJob(JobCronScript):
    """Run DistroSeriesDifferenceJob jobs."""

    config_name = 'distroseriesdifferencejob'
    source_interface = IDistroSeriesDifferenceJobSource


if __name__ == '__main__':
    script = RunDistroSeriesDifferenceJob()
    script.lock_and_run()
