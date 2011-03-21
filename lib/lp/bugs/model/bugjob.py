# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Job classes related to BugJobs are in here."""

__metaclass__ = type
__all__ = [
    'BugJob',
    'BugJobDerived',
    ]

from lazr.delegates import delegates
import simplejson
from sqlobject import SQLObjectNotFound
from storm.expr import And
from storm.locals import (
    Int,
    Reference,
    Unicode,
    )
from zope.component import getUtility
from zope.interface import (
    classProvides,
    implements,
    )

from canonical.database.enumcol import EnumCol
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    MASTER_FLAVOR,
    )
from lp.bugs.interfaces.bugjob import (
    BugJobType,
    IBugJob,
    IBugJobSource,
    )
from lp.bugs.model.bug import Bug
from lp.services.job.model.job import Job
from lp.services.job.runner import BaseRunnableJob
from lp.services.database.stormbase import StormBase


class BugJob(StormBase):
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
        super(BugJob, self).__init__()
        json_data = simplejson.dumps(metadata)
        self.job = Job()
        self.bug = bug
        self.job_type = job_type
        # XXX AaronBentley 2009-01-29 bug=322819: This should be a bytestring,
        # but the DB representation is unicode.
        self._json_data = json_data.decode('utf-8')

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
    classProvides(IBugJobSource)

    def __init__(self, job):
        self.context = job

    @classmethod
    def create(cls, bug):
        """See `IBugJob`."""
        # If there's already a job for the bug, don't create a new one.
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
        vars = BaseRunnableJob.getOopsVars(self)
        vars.extend([
            ('bug_id', self.context.bug.id),
            ('bug_job_id', self.context.id),
            ('bug_job_type', self.context.job_type.title),
            ])
        return vars
