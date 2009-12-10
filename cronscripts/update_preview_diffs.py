#!/usr/bin/python2.5
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0403

"""Update or create previews diffs for branch merge proposals."""

__metaclass__ = type

import _pythonpath

from lp.services.job.runner import JobCronScript, JobRunner, TwistedJobRunner
from lp.code.interfaces.branchmergeproposal import (
    IUpdatePreviewDiffJobSource,)


class RunUpdatePreviewDiffJobs(JobCronScript):
    """Run UpdatePreviewDiff jobs."""

    config_name = 'update_preview_diffs'
    source_interface = IUpdatePreviewDiffJobSource

    def __init__(self):
        super(JobCronScript, self).__init__()
        if self.options.twisted:
            self.runner_class = TwistedJobRunner
        else:
            self.runner_class = JobRunner

    def add_my_options(self):
        self.parser.add_option('--twisted', action='store_true')


if __name__ == '__main__':
    script = RunUpdatePreviewDiffJobs()
    script.lock_and_run()
