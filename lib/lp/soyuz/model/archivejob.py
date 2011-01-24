# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = object

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
from lp.services.job.model.job import Job
from lp.services.job.runner import BaseRunnableJob
from lp.services.database.stormbase import StormBase
from lp.soyuz.enums import ArchiveJobType
from lp.soyuz.interfaces.archivejob import (
    IArchiveJob,
    IArchiveJobSource,
    )
from lp.soyuz.model.archive import Archive


class ArchiveJob(StormBase):
    """Base class for jobs related to Archives."""

    implements(IArchiveJob)

    __storm_table__ = 'archivejob'

    id = Int(primary=True)

    job_id = Int(name='job')
    job = Reference(job_id, Job.id)

    archive_id = Int(name='archive')
    archive = Reference(archive_id, Archive.id)

    job_type = EnumCol(enum=ArchiveJobType, notNull=True)

    _json_data = Unicode('json_data')

    @property
    def metadata(self):
        return simplejson.loads(self._json_data)

    def __init__(self, archive, job_type, metadata):
        """Create an ArchiveJob.

        :param archive: the archive this job relates to.
        :param job_type: the bugjobtype of this job.
        :param metadata: the type-specific variables, as a json-compatible
            dict.
        """
        super(ArchiveJob, self).__init__()
        json_data = simplejson.dumps(metadata)
        self.job = Job()
        self.archive = archive
        self.job_type = job_type
        # XXX AaronBentley 2009-01-29 bug=322819: This should be a bytestring,
        # but the db representation is unicode.
        self._json_data = json_data.decode('utf-8')

    @classmethod
    def get(cls, key):
        """Return the instance of this class whose key is supplied."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        instance = store.get(cls, key)
        if instance is None:
            raise SQLObjectNotFound(
                'No occurence of %s has key %s' % (cls.__name__, key))
        return instance


class ArchiveJobDerived(BaseRunnableJob):
    """Intermediate class for deriving from ArchiveJob."""
    delegates(IArchiveJob)
    classProvides(IArchiveJobSource)

    def __init__(self, job):
        self.context = job

    @classmethod
    def create(cls, archive, metadata=None):
        """See `IArchiveJob`."""
        if metadata is None:
            metadata = {}
        job = ArchiveJob(archive, cls.class_job_type, metadata)
        return cls(job)

    @classmethod
    def get(cls, job_id):
        """Get a job by id.

        :return: the ArchiveJob with the specified id, as the current
                 BugJobDerived subclass.
        :raises: SQLObjectNotFound if there is no job with the specified id,
                 or its job_type does not match the desired subclass.
        """
        job = ArchiveJob.get(job_id)
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
            ArchiveJob,
            And(ArchiveJob.job_type == cls.class_job_type,
                ArchiveJob.job == Job.id,
                Job.id.is_in(Job.ready_jobs),
                ArchiveJob.archive == Archive.id))
        return (cls(job) for job in jobs)

    def getOopsVars(self):
        """See `IRunnableJob`."""
        vars = BaseRunnableJob.getOopsVars(self)
        vars.extend([
            ('archive_id', self.context.archive.id),
            ('archive_job_id', self.context.id),
            ('archive_job_type', self.context.job_type.title),
            ])
        return vars
