# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Job classes related to BugJobs are in here."""

__metaclass__ = type
__all__ = [
    'CalculateBugHeatJob',
    ]

from zope.interface import classProvides, implements

from lp.bugs.interfaces.bugjob import (
    BugJobType, ICalculateBugHeatJob, ICalculateBugHeatJobSource)
from lp.bugs.model.bugjob import BugJobDerived
from lp.bugs.scripts.bugheat import BugHeatCalculator


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
