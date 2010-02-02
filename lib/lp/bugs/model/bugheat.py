# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Job classes related to BugJobs are in here."""

__metaclass__ = type
__all__ = [
    'CalculateBugHeatJob',
    ]

from zope.component import getUtility
from zope.interface import classProvides, implements

from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR, IStoreSelector, MAIN_STORE)

from lp.bugs.interfaces.bugjob import (
    BugJobType, ICalculateBugHeatJob, ICalculateBugHeatJobSource)
from lp.bugs.model.bugjob import BugJob, BugJobDerived
from lp.bugs.scripts.bugheat import BugHeatCalculator
from lp.services.job.model.job import Job


class CalculateBugHeatJob(BugJobDerived):
    """A Job to calculate bug heat."""
    implements(ICalculateBugHeatJob)

    class_job_type = BugJobType.UPDATE_HEAT
    classProvides(ICalculateBugHeatJobSource)

    def run(self):
        """See `IRunnableJob`."""
        calculator = BugHeatCalculator(self.bug)
        calculated_heat = calculator.getBugHeat()
        self.bug.setHeat(calculated_heat)

    @classmethod
    def create(cls, bug):
        """See `ICalculateBugHeatJobSource`."""
        # If there's already a job for the bug, don't create a new one.
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        job_for_bug = store.find(
            BugJob,
            BugJob.bug == bug,
            BugJob.job_type == cls.class_job_type,
            BugJob.job == Job.id,
            Job.id.is_in(Job.ready_jobs)
            ).any()

        if job_for_bug is not None:
            return cls(job_for_bug)
        else:
            return super(CalculateBugHeatJob, cls).create(bug)

