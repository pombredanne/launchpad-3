#!/usr/bin/python -S
#
# Copyright 2009, 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Handle any jobs that have a configured job category and db id."""

__metaclass__ = type

import _pythonpath
import os
import sys
import textwrap

from twisted.python import log
from optparse import (
    OptionParser,
    IndentedHelpFormatter,
    )

from lp.services.propertycache import cachedproperty
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


class ProcessJobSource(JobCronScript):
    """Run jobs."""

    def __init__(self, job_source):
        self.config_name = job_source
        section = getattr(config, self.config_name)
        # The fromlist argument is necessary so that __import__()
        # returns the bottom submodule instead of the top one.
        module = __import__(section.module, fromlist=[job_source])
        self.source_interface = getattr(module, job_source)
        if getattr(section, 'runner_class', None) is None:
            runner_class = JobRunner
        else:
            runner_class = getattr(runner, section.runner_class, JobRunner)
        super(ProcessJobSource, self).__init__(
            runner_class=runner_class,
            script_name='%s-%s' % (SCRIPT_NAME, job_source))


class LongEpilogHelpFormatter(IndentedHelpFormatter):
    """Preserve newlines in epilog."""

    def format_epilog(self, epilog):
        if epilog:
            return '\n%s\n' % epilog
        else:
            return ""


class SpawnScripts:
    """Handle each job source in a separate process with ProcessJobSource."""

    def parse_options(self):
        usage = "%prog -g GROUP | -i JOB_SOURCE [ -e JOB_SOURCE ]"
        epilog = (
            textwrap.fill(
            "At least one group or one included job source must be "
            "specified. Excluding job sources is useful when you want to "
            "run all the other job sources in a group.")
            + "\n\n" + self.group_help)

        parser = OptionParser(usage, add_help_option=True, epilog=epilog,
                              formatter=LongEpilogHelpFormatter())
        logger_options(parser)
        parser.add_option(
            '-g', '--group', dest='groups',
            metavar='GROUP', default=[], action='append',
            help="Include all job sources from the specified groups.")
        parser.add_option(
            '-i', '--include', dest='included_job_sources',
            metavar="JOB_SOURCE", default=[], action='append',
            help="Include specific job sources.")
        parser.add_option(
            '-e', '--exclude', dest='excluded_job_sources',
            metavar="JOB_SOURCE", default=[], action='append',
            help="Exclude specific job sources.")

        self.options, self.args = parser.parse_args()
        if (len(self.options.groups) == 0
            and len(self.options.included_job_sources) == 0):
            parser.print_help()
            sys.exit(1)

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
                script = ProcessJobSource(job_source)
                script.lock_and_run()
                # The child process should not run the rest of the program.
                sys.exit()
            else:
                children.add(pid)

        # Wait till all child processes finish.
        while len(children) > 0:
            pid, status = os.wait()
            children.remove(pid)

    @cachedproperty
    def all_job_sources(self):
        job_sources = config['queued-job-runner'].job_sources
        return [job_source.strip() for job_source in job_sources.split(',')]

    @cachedproperty
    def groups(self):
        groups = {}
        for source in self.all_job_sources:
            if source not in config:
                continue
            section = config[source]
            group = groups.setdefault(section.crontab_group, [])
            group.append(source)
        return groups

    @cachedproperty
    def group_help(self):
        return '\n\n'.join(
            'Group: %s\n    %s' % (group, '\n    '.join(sources))
            for group, sources in sorted(self.groups.items()))


if __name__ == '__main__':
    script = SpawnScripts()
    script.main()
