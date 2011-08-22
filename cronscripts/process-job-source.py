#!/usr/bin/python -S
#
# Copyright 2009, 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Handle jobs for a specified job source class."""

__metaclass__ = type

import sys

import _pythonpath
from twisted.python import log

from canonical.config import config
from lp.services.job import runner
from lp.services.job.runner import JobCronScript


class ProcessJobSource(JobCronScript):
    """Run jobs for a specified job source class."""
    usage = (
        "Usage: %prog [options] JOB_SOURCE\n\n"
        "For more help, run:\n"
        "    cronscripts/process-job-source-groups.py --help")

    def __init__(self):
        super(ProcessJobSource, self).__init__()
        # The fromlist argument is necessary so that __import__()
        # returns the bottom submodule instead of the top one.
        module = __import__(self.config_section.module,
                            fromlist=[self.job_source_name])
        self.source_interface = getattr(module, self.job_source_name)

    @property
    def config_name(self):
        return self.job_source_name

    @property
    def name(self):
        return 'process-job-source-%s' % self.job_source_name

    @property
    def runner_class(self):
        runner_class_name = getattr(
            self.config_section, 'runner_class', 'JobRunner')
        # Override attributes that are normally set in __init__().
        return getattr(runner, runner_class_name)

    def add_my_options(self):
        self.add_log_twisted_option()

    def handle_options(self):
        if len(self.args) != 1:
            self.parser.print_help()
            sys.exit(1)
        self.job_source_name = self.args[0]
        super(ProcessJobSource, self).handle_options()

    def main(self):
        if self.options.verbose:
            log.startLogging(sys.stdout)
        super(ProcessJobSource, self).main()


if __name__ == '__main__':
    script = ProcessJobSource()
    script.lock_and_run()
