#!/usr/bin/python -S
#
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0403

"""Process uploaded Apport BLOBs."""

__metaclass__ = type

import _pythonpath

from canonical.launchpad.webapp import errorlog

from lp.services.job.runner import JobCronScript
from lp.bugs.interfaces.apportjob import IProcessApportBlobJobSource


class RunProcessApportBlobs(JobCronScript):
    """Run ProcessApportBlobJobs."""

    config_name = 'process_apport_blobs'
    source_interface = IProcessApportBlobJobSource

    def main(self):
        errorlog.globalErrorUtility.configure(self.config_name)
        return super(RunProcessApportBlobs, self).main()


if __name__ == '__main__':
    script = RunProcessApportBlobs()
    script.lock_and_run()
