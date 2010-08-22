# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    "InitialiseDistroSeriesJob",
    "InitialiseDistroSeriesJobDerived",
]

import simplejson

from sqlobject import SQLObjectNotFound
from storm.base import Storm
from storm.locals import And, Int, Reference, Unicode

from zope.component import getUtility
from zope.interface import classProvides, implements

from canonical.database.enumcol import EnumCol
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR, IStoreSelector, MAIN_STORE, MASTER_FLAVOR)

from lazr.delegates import delegates
 
from lp.registry.model.distroseries import DistroSeries
from lp.soyuz.interfaces.initialisedistroseriesjob import (
    IInitialiseDistroSeriesJob,
    IInitialiseDistroSeriesJobSource)
    
from lp.services.job.model.job import Job
from lp.services.job.runner import BaseRunnableJob


class InitialiseDistroSeriesJob(Storm):
    """Base class for jobs related to InitialiseDistroSeriess."""

    implements(IInitialiseDistroSeriesJob)

    __storm_table__ = 'InitialiseDistroSeriesJob'

    id = Int(primary=True)

    job_id = Int(name='job')
    job = Reference(job_id, Job.id)

    distroseries_id = Int(name='distroseries')
    distroseries = Reference(distroseries_id, DistroSeries.id)

    _json_data = Unicode('json_data')

    def __init__(self, distroseries, metadata):
        super(InitialiseDistroSeriesJob, self).__init__()
        json_data = simplejson.dumps(metadata)
        self.job = Job()
        self.distroseries = distroseries
        self._json_data = json_data.decode('utf-8')

    @property
    def metadata(self):
        return simplejson.loads(self._json_data)

    @classmethod
    def get(cls, key):
        """Return the instance of this class whose key is supplied."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        instance = store.get(cls, key)
        if instance is None:
            raise SQLObjectNotFound(
                'No occurence of %s has key %s' % (cls.__name__, key))
        return instance


class InitialiseDistroSeriesJobDerived(BaseRunnableJob):
    """Intermediate class for deriving from InitialiseDistroSeriesJob."""
    delegates(IInitialiseDistroSeriesJob)
    classProvides(IInitialiseDistroSeriesJobSource)

    def __init__(self, job):
        self.context = job

    @classmethod
    def create(cls, distroseries):
        """See `IInitialiseDistroSeriesJob`."""
        # If there's already a job, don't create a new one.
        job = InitialiseDistroSeriesJob(
            distroseries, {})
        return cls(job)

    @classmethod
    def get(cls, job_id):
        """Get a job by id.

        :return: the InitialiseDistroSeriesJob with the specified id, as
                 the current InitialiseDistroSeriesJobDerived subclass.
        :raises: SQLObjectNotFound if there is no job with the specified id.
        """
        job = InitialiseDistroSeriesJob.get(job_id)
        return cls(job)

    @classmethod
    def iterReady(cls):
        """Iterate through all ready InitialiseDistroSeriesJobs."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)
        jobs = store.find(
            InitialiseDistroSeriesJob,
            And(InitialiseDistroSeriesJob.job == Job.id,
                Job.id.is_in(Job.ready_jobs),
                InitialiseDistroSeriesJob.distroseries == DistroSeries.id))
        return (cls(job) for job in jobs)

    def getOopsVars(self):
        """See `IRunnableJob`."""
        vars = BaseRunnableJob.getOopsVars(self)
        vars.extend([
            ('distroseries_id', self.context.distroseries.id),
            ('distroseries_job_id', self.context.id),
            ])
        return vars

