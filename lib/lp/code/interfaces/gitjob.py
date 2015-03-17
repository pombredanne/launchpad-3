# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""GitJob interfaces."""

__metaclass__ = type

__all__ = [
    'IGitJob',
    'IGitRefScanJob',
    'IGitRefScanJobSource',
    ]

from lazr.restful.fields import Reference
from zope.interface import (
    Attribute,
    Interface,
    )

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
        schema=IGitRepository, required=True, readonly=True)

    metadata = Attribute(_("A dict of data about the job."))


class IGitRefScanJob(IRunnableJob):
    """A Job that scans a Git repository for its current list of references."""


class IGitRefScanJobSource(IJobSource):

    def create(repository):
        """Scan a repository for refs.

        :param repository: The database repository to scan.
        """
