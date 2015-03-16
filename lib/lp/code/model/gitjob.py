# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'GitJob',
    'GitRefScanJob',
    ]

from lazr.delegates import delegates
from lazr.enum import (
    DBEnumeratedType,
    DBItem,
    )
from storm.exceptions import LostObjectError
from storm.locals import (
    Int,
    JSON,
    Reference,
    )
from zope.interface import (
    classProvides,
    implements,
    )

from lp.app.errors import NotFoundError
from lp.code.githosting import GitHostingClient
from lp.code.interfaces.gitjob import (
    IGitJob,
    IGitRefScanJob,
    IGitRefScanJobSource,
    )
from lp.services.config import config
from lp.services.database.enumcol import EnumCol
from lp.services.database.interfaces import (
    IMasterStore,
    IStore,
    )
from lp.services.database.stormbase import StormBase
from lp.services.job.model.job import (
    EnumeratedSubclass,
    Job,
    )
from lp.services.job.runner import BaseRunnableJob
from lp.services.mail.sendmail import format_address_for_person
from lp.services.scripts import log


class GitJobType(DBEnumeratedType):
    """Values that `IGitJob.job_type` can take."""

    REF_SCAN = DBItem(0, """
        Ref scan

        This job scans a repository for its current list of references.
        """)


class GitJob(StormBase):
    """See `IGitJob`."""

    __storm_table__ = 'GitJob'

    implements(IGitJob)

    job_id = Int(name='job', primary=True, allow_none=False)
    job = Reference(job_id, 'Job.id')

    repository_id = Int(name='repository', allow_none=False)
    repository = Reference(repository_id, 'GitRepository.id')

    job_type = EnumCol(enum=GitJobType, notNull=True)

    metadata = JSON('json_data')

    def __init__(self, repository, job_type, metadata, **job_args):
        """Constructor.

        Extra keyword arguments are used to construct the underlying Job
        object.

        :param repository: The database repository this job relates to.
        :param job_type: The `GitJobType` of this job.
        :param metadata: The type-specific variables, as a JSON-compatible
            dict.
        """
        super(GitJob, self).__init__()
        self.job = Job(**job_args)
        self.repository = repository
        self.job_type = job_type
        self.metadata = metadata

    def makeDerived(self):
        return GitJobDerived.makeSubclass(self)


class GitJobDerived(BaseRunnableJob):

    __metaclass__ = EnumeratedSubclass

    delegates(IGitJob)

    def __init__(self, git_job):
        self.context = git_job

    @classmethod
    def get(cls, job_id):
        """Get a job by id.

        :return: The `GitJob` with the specified id, as the current
            `GitJobDerived` subclass.
        :raises: `NotFoundError` if there is no job with the specified id,
            or its `job_type` does not match the desired subclass.
        """
        git_job = IStore(GitJob).get(GitJob, job_id)
        if git_job.job_type != cls.class_job_type:
            raise NotFoundError(
                "No object found with id %d and type %s" %
                (job_id, cls.class_job_type.title))
        return cls(git_job)

    @classmethod
    def iterReady(cls):
        """See `IJobSource`."""
        jobs = IMasterStore(GitJob).find(
            GitJob,
            GitJob.job_type == cls.class_job_type,
            GitJob.job == Job.id,
            Job.id.is_in(Job.ready_jobs))
        return (cls(job) for job in jobs)

    def getOopsVars(self):
        """See `IRunnableJob`."""
        oops_vars = super(GitJobDerived, self).getOopsVars()
        oops_vars.extend([
            ('git_job_id', self.context.job.id),
            ('git_job_type', self.context.job_type.title),
            ('git_repository_id', self.context.repository.id),
            ('git_repository_name', self.context.repository.unique_name)])
        return oops_vars

    def getErrorRecipients(self):
        if self.requester is None:
            return []
        return [format_address_for_person(self.requester)]


class GitRefScanJob(GitJobDerived):
    """A Job that scans a Git repository for its current list of references."""

    implements(IGitRefScanJob)

    classProvides(IGitRefScanJobSource)
    class_job_type = GitJobType.REF_SCAN

    config = config.IGitRefScanJobSource

    @classmethod
    def create(cls, repository):
        """See `IGitRefScanJobSource`."""
        git_job = GitJob(
            repository, cls.class_job_type,
            {"repository_name": repository.unique_name})
        job = cls(git_job)
        job.celeryRunOnCommit()
        return job

    def __init__(self, git_job):
        super(GitRefScanJob, self).__init__(git_job)
        self._cached_repository_name = self.metadata["repository_name"]
        self._hosting_client = GitHostingClient(
            config.codehosting.internal_git_api_endpoint)

    def run(self):
        """See `IGitRefScanJob`."""
        try:
            hosting_path = self.repository.getInternalPath()
        except LostObjectError:
            log.warning(
                "Skipping repository %s because it has been deleted." %
                self._cached_repository_name)
            return
        new_refs = {}
        for path, info in self._hosting_client.get_refs(hosting_path).items():
            try:
                new_refs[path] = self.repository.convertRefInfo(info)
            except ValueError:
                pass
        current_refs = dict((ref.path, ref) for ref in self.repository.refs)
        refs_to_insert = dict(
            (path, info) for path, info in new_refs.items()
            if path not in current_refs)
        self.repository.createRefs(refs_to_insert)
        self.repository.removeRefs(set(current_refs) - set(new_refs))
        for path in set(new_refs) & set(current_refs):
            new_ref = new_refs[path]
            current_ref = current_refs[path]
            if (new_ref["sha1"] != current_ref.commit_sha1 or
                new_ref["type"] != current_ref.object_type):
                self.repository.updateRef(current_ref, new_ref)
