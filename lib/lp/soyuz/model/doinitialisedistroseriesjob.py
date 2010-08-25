# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    "DoInitialiseDistroSeriesJob",
]

from zope.component import getUtility
from zope.interface import classProvides, implements

from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR, IStoreSelector, MAIN_STORE)

from lp.services.job.model.job import Job
from lp.soyuz.interfaces.initialisedistroseriesjob import (
    InitialiseDistroSeriesJobType, IDoInitialiseDistroSeriesJob,
    IDoInitialiseDistroSeriesJobSource)
from lp.soyuz.model.initialisedistroseriesjob import (
    InitialiseDistroSeriesJob, InitialiseDistroSeriesJobDerived)


class DoInitialiseDistroSeriesJob(InitialiseDistroSeriesJobDerived):

    implements(IDoInitialiseDistroSeriesJob)

    class_job_type = InitialiseDistroSeriesJobType.DO_INITIALISE
    classProvides(IDoInitialiseDistroSeriesJobSource)

    @classmethod
    def create(cls, distroseries):
        """See `IDoInitialiseDistroSeriesJob`."""
        # If there's already a job, don't create a new one.
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        existing_job = store.find(
            InitialiseDistroSeriesJob,
            InitialiseDistroSeriesJob.distroseries == distroseries,
            InitialiseDistroSeriesJob.job_type == cls.class_job_type,
            InitialiseDistroSeriesJob.job == Job.id,
            Job.id.is_in(Job.ready_jobs)
            ).any()

        if existing_job is not None:
            return cls(existing_job)
        else:
            return super(
                DoInitialiseDistroSeriesJob, cls).create(distroseries)

    def run(self):
        """See `IRunnableJob`."""
        self.distroseries.initialiseFromParent()

