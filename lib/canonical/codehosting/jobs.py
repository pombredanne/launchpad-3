# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Facilities for running Jobs."""


__all__ = 'JobRunner'


import sys

from zope.component import getUtility
from zope.error.interfaces import IErrorReportingUtility

from canonical.launchpad.interfaces.job import LeaseHeld


class JobRunner(object):
    """Runner of Jobs."""

    def __init__(self, jobs):
        self.jobs = jobs
        self.completed_jobs = []
        self.incomplete_jobs = []

    @classmethod
    def fromReady(klass, job_class):
        """Return a job runner for all ready jobs of a given class."""
        return klass(job_class.iterReady())

    def runJob(self, job):
        """Attempt to run a job, updating its status as appropriate."""
        job.job.acquireLease()
        try:
            job.job.start()
            job.run()
        except Exception:
            job.job.fail()
            self.incomplete_jobs.append(job)
            raise
        else:
            job.job.complete()
            self.completed_jobs.append(job)

    def runAll(self):
        """Run all the Jobs for this JobRunner."""
        for job in self.jobs:
            try:
                self.runJob(job)
            except LeaseHeld:
                self.incomplete_jobs.append(job)
            except Exception:
                info = sys.exc_info()
                reporter = getUtility(IErrorReportingUtility)
                reporter.raising(info)
