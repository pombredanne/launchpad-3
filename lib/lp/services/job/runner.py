# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Facilities for running Jobs."""


__all__ = ['JobRunner']


import sys

import transaction

from lp.services.job.interfaces.job import LeaseHeld
from canonical.launchpad.webapp import errorlog


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
        # Commit transaction to clear the row lock.
        transaction.commit()
        try:
            job.job.start()
            transaction.commit()
            job.run()
        except Exception:
            # Commit transaction to update the DB time.
            transaction.commit()
            job.job.fail()
            self.incomplete_jobs.append(job)
            raise
        else:
            # Commit transaction to update the DB time.
            transaction.commit()
            job.job.complete()
            self.completed_jobs.append(job)
        # Commit transaction to update job status.
        transaction.commit()

    def runAll(self):
        """Run all the Jobs for this JobRunner."""
        for job in self.jobs:
            try:
                self.runJob(job)
            except LeaseHeld:
                self.incomplete_jobs.append(job)
            except Exception:
                info = sys.exc_info()
                errorlog.globalErrorUtility.raising(info)
