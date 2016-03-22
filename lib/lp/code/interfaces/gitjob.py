# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""GitJob interfaces."""

__metaclass__ = type

__all__ = [
    'IGitJob',
    'IGitRefScanJob',
    'IGitRefScanJobSource',
    'IGitRepositoryModifiedMailJob',
    'IGitRepositoryModifiedMailJobSource',
    'IReclaimGitRepositorySpaceJob',
    'IReclaimGitRepositorySpaceJobSource',
    ]

from lazr.restful.fields import Reference
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import Text

from lp import _
from lp.code.interfaces.gitrepository import IGitRepository
from lp.services.job.interfaces.job import (
    IJob,
    IJobSource,
    IRunnableJob,
    )


class IGitJob(Interface):
    """A job related to a Git repository."""

    job = Reference(
        title=_("The common Job attributes."), schema=IJob,
        required=True, readonly=True)

    repository = Reference(
        title=_("The Git repository to use for this job."),
        schema=IGitRepository, required=False, readonly=True)

    metadata = Attribute(_("A dict of data about the job."))


class IGitRefScanJob(IRunnableJob):
    """A Job that scans a Git repository for its current list of references."""


class IGitRefScanJobSource(IJobSource):

    def create(repository):
        """Scan a repository for refs.

        :param repository: The database repository to scan.
        """


class IReclaimGitRepositorySpaceJob(IRunnableJob):
    """A Job that deletes a repository from storage after it has been
    deleted from the database."""

    repository_path = Text(
        title=_("The storage path of the now-deleted repository."))


class IReclaimGitRepositorySpaceJobSource(IJobSource):

    def create(repository_name, repository_path):
        """Construct a new object that implements
        IReclaimGitRepositorySpaceJob.

        :param repository_name: The unique name of the repository to remove
            from storage.
        :param repository_path: The storage path of the repository to remove
            from storage.
        """


class IGitRepositoryModifiedMailJob(IRunnableJob):
    """A Job to send email about repository modifications."""


class IGitRepositoryModifiedMailJobSource(IJobSource):

    def create(repository, user, repository_delta):
        """Send email about repository modifications.

        :param repository: The `IGitRepository` that was modified.
        :param user: The `IPerson` who modified the repository.
        :param repository_delta: An `IGitRepositoryDelta` describing the
            changes.
        """
