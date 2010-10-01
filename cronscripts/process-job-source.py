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
        if len(self.args) != 1:
            self.parser.print_help()
            sys.exit(1)
        job_source = self.args[0]
        # The dbuser is grabbed from the section matching config_name.
        section = getattr(config, job_source)
        # The fromlist argument is necessary so that __import__()
        # returns the bottom submodule instead of the top one.
        module = __import__(section.module, fromlist=[job_source])
        self.source_interface = getattr(module, job_source)
        runner_class_name = getattr(section, 'runner_class', 'JobRunner')
        # Override attributes that are normally set in __init__().
        self.name = 'process-job-source-%s' % job_source
        self.config_name = job_source
        self.runner_class = getattr(runner, runner_class_name)

    def main(self):
        if self.options.verbose:
            log.startLogging(sys.stdout)
        super(ProcessJobSource, self).main()


if __name__ == '__main__':
    script = ProcessJobSource()
    script.lock_and_run()
