#!/usr/bin/python -S
#
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Initialise new distroseries."""

__metaclass__ = type

import _pythonpath

from lp.services.job.runner import JobCronScript
from lp.soyuz.interfaces.distributionjob import (
    IInitialiseDistroSeriesJobSource,
    )


class RunInitialiseDistroSeriesJob(JobCronScript):
    """Run InitialiseDistroSeriesJob jobs."""

    config_name = 'initialisedistroseries'
    source_interface = IInitialiseDistroSeriesJobSource


if __name__ == '__main__':
    script = RunInitialiseDistroSeriesJob()
    script.lock_and_run()
