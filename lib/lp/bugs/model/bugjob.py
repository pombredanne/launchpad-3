# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Job classes related to BugJobs are in here."""

__metaclass__ = type
__all__ = [
    'BugJob',
    ]

import simplejson

from sqlobject import SQLObjectNotFound
from storm.base import Storm
from storm.expr import And
from storm.locals import Int, Reference, Unicode
from storm.store import Store

from zope.component import getUtility
from zope.interface import classProvides, implements
from zope.security.proxy import removeSecurityProxy

from canonical.database.enumcol import EnumCol
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR, IStoreSelector, MAIN_STORE, MASTER_FLAVOR)

from lazr.delegates import delegates

from lp.bugs.interfaces.bugjob import (
    BugJobType, IBugJob, ICalculateBugHeatJob, ICalculateBugHeatJobSource)
from lp.bugs.model.bug import Bug
from lp.bugs.scripts.bugheat import BugHeatCalculator
from lp.services.job.model.job import Job
from lp.services.job.runner import BaseRunnableJob


class BugJob(Storm):
    """Base class for jobs related to Bugs."""

    implements(IBugJob)

    __storm_table__ = 'BugJob'

    id = Int(primary=True)

    job_id = Int(name='job')
    job = Reference(job_id, Job.id)

    bug_id = Int(name='bug')
    bug = Reference(bug_id, Bug.id)

    job_type = EnumCol(enum=BugJobType, notNull=True)

    _json_data = Unicode('json_data')

    @property
    def metadata(self):
        return simplejson.loads(self._json_data)

    def __init__(self, bug, job_type, metadata):
        """Constructor.

        :param bug: The proposal this job relates to.
        :param job_type: The BugJobType of this job.
        :param metadata: The type-specific variables, as a JSON-compatible
            dict.
        """
        Storm.__init__(self)
        json_data = simplejson.dumps(metadata)
        self.job = Job()
        self.bug = bug
        self.job_type = job_type
        # XXX AaronBentley 2009-01-29 bug=322819: This should be a bytestring,
        # but the DB representation is unicode.
        self._json_data = json_data.decode('utf-8')

    def sync(self):
        store = Store.of(self)
        store.flush()
        store.autoreload(self)

    def destroySelf(self):
        Store.of(self).remove(self)

    @classmethod
    def selectBy(cls, **kwargs):
        """Return selected instances of this class.

        At least one pair of keyword arguments must be supplied.
        foo=bar is interpreted as 'select all instances of
        BugJob whose property "foo" is equal to "bar"'.
        """
        assert len(kwargs) > 0
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.find(cls, **kwargs)

    @classmethod
    def get(cls, key):
        """Return the instance of this class whose key is supplied."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        instance = store.get(cls, key)
        if instance is None:
            raise SQLObjectNotFound(
                'No occurrence of %s has key %s' % (cls.__name__, key))
        return instance


class BugJobDerived(BaseRunnableJob):
    """Intermediate class for deriving from BugJob."""
    delegates(IBugJob)

    def __init__(self, job):
        self.context = job

    def __eq__(self, job):
        return (
            self.__class__ is removeSecurityProxy(job.__class__)
            and self.job == job.job)

    def __ne__(self, job):
        return not (self == job)

    @classmethod
    def create(cls, bug):
        """See `XXX`."""
        job = BugJob(bug, cls.class_job_type, {})
        return cls(job)

    @classmethod
    def get(cls, job_id):
        """Get a job by id.

        :return: the BugJob with the specified id, as the current
                 BugJobDerived subclass.
        :raises: SQLObjectNotFound if there is no job with the specified id,
                 or its job_type does not match the desired subclass.
        """
        job = BugJob.get(job_id)
        if job.job_type != cls.class_job_type:
            raise SQLObjectNotFound(
                'No object found with id %d and type %s' % (job_id,
                cls.class_job_type.title))
        return cls(job)

    @classmethod
    def iterReady(cls):
        """Iterate through all ready BugJobs."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)
        jobs = store.find(
            BugJob,
            And(BugJob.job_type == cls.class_job_type,
                BugJob.job == Job.id,
                Job.id.is_in(Job.ready_jobs),
                BugJob.bug == Bug.id))
        return (cls(job) for job in jobs)

    def getOopsVars(self):
        """See `IRunnableJob`."""
        vars =  BaseRunnableJob.getOopsVars(self)
        bmp = self.context.branch_merge_proposal
        vars.extend([
            ('bug_job_id', self.context.id),
            ('bug_job_type', self.context.job_type.title),
            ])
        return vars


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
