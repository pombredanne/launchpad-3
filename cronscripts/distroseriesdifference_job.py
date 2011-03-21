#!/usr/bin/python -S
#
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Process DistroSeriesDifferences."""

__metaclass__ = type

import _pythonpath

from lp.services.features import getFeatureFlag
from lp.services.job.runner import JobCronScript
from lp.soyuz.model.distroseriesdifferencejob import (
    FEATURE_FLAG_ENABLE_MODULE,
    )
from lp.soyuz.interfaces.distributionjob import (
    IDistroSeriesDifferenceJobSource,
    )


class RunDistroSeriesDifferenceJob(JobCronScript):
    """Run DistroSeriesDifferenceJob jobs."""

    config_name = 'distroseriesdifferencejob'
    source_interface = IDistroSeriesDifferenceJobSource

    def main(self):
        if not getFeatureFlag(FEATURE_FLAG_ENABLE_MODULE):
            self.logger.info("Feature flag is not enabled.")
            return
        super(RunDistroSeriesDifferenceJob, self).main()


if __name__ == '__main__':
    script = RunDistroSeriesDifferenceJob()
    script.lock_and_run()
