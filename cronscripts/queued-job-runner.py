#!/usr/bin/python -S
#
# Copyright 2009, 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Handle any jobs that have a configured job category and db id."""

__metaclass__ = type

import _pythonpath
import os
import sys

from twisted.python import log
from optparse import OptionParser

import lp.registry.model.person
from canonical.config import config
from canonical.launchpad.scripts.logger import (
    logger,
    logger_options,
    )

from lp.services.job.runner import (
    JobCronScript,
    JobRunner,
    )
from lp.services.job import runner


SCRIPT_NAME = 'queued-job-runner'


class RunJobs(JobCronScript):
    """Run jobs."""

    def __init__(self, job_source):
        print "Job source:", job_source
        self.config_name = job_source
        section = getattr(config, self.config_name)
        # The fromlist argument is necessary so that __import__()
        # returns the bottom submodule instead of the top one.
        module = __import__(section.module, fromlist=[job_source])
        self.source_interface = getattr(module, job_source)
        print 'source interface:', self.source_interface
        if getattr(section, 'runner_class', None) is None:
            runner_class = JobRunner
        else:
            runner_class = getattr(runner, section.runner_class, JobRunner)
        super(RunJobs, self).__init__(
            runner_class=runner_class,
            script_name='%s-%s' % (SCRIPT_NAME, job_source))


class RunJobsLauncher:

    def __init__(self):
        pass

    def parse_options(self):
        parser = OptionParser()
        logger_options(parser)
        parser.add_option(
            '-e', '--exclude', action='append', dest='excluded_job_sources',
            default=[], help="Exclude a specific job class. Can be repeated.")

        self.options, self.args = parser.parse_args()
        self.logger = logger(self.options, SCRIPT_NAME)

        for job_source in self.options.excluded_job_sources:
            if job_source not in self.all_job_sources:
                self.logger.warn('%r is not a valid job source class'
                                 % job_source)

    def main(self):
        self.parse_options()
        if self.options.verbose:
            log.startLogging(sys.stdout)

        children = set()
        for job_source in self.all_job_sources:
            if job_source in self.options.excluded_job_sources:
                continue
            pid = os.fork()
            # Run the script in a child process. Continue the loop in the
            # parent.
            if pid == 0:
                script = RunJobs(job_source)
                script.lock_and_run()
                # The child process should not run the rest of the program.
                sys.exit()
            else:
                children.add(pid)

        # Wait till all child processes finish.
        while len(children) > 0:
            pid, status = os.wait()
            children.remove(pid)

    @property
    def all_job_sources(self):
        job_sources = config['queued-job-runner'].job_sources
        return [job_source.strip() for job_source in job_sources.split(',')]


if __name__ == '__main__':
    script = RunJobsLauncher()
    script.main()
