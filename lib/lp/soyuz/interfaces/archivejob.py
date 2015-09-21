# Copyright 2010-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""ArchiveJob interfaces."""

__metaclass__ = type

__all__ = [
    'IArchiveJob',
    'IArchiveJobSource',
    'IPackageUploadNotificationJob',
    'IPackageUploadNotificationJobSource',
    ]


from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Int,
    Object,
    )

from lp import _
from lp.services.job.interfaces.job import (
    IJob,
    IJobSource,
    IRunnableJob,
    )
from lp.soyuz.interfaces.archive import IArchive


class IArchiveJob(Interface):
    """A Job related to an Archive."""

    id = Int(
        title=_('DB ID'), required=True, readonly=True,
        description=_("The tracking number for this job."))

    archive = Object(
        title=_('The archive this job is about.'), schema=IArchive,
        required=True)

    job = Object(
        title=_('The common Job attributes'), schema=IJob, required=True)

    metadata = Attribute('A dict of data about the job.')

    def destroySelf():
        """Destroy this object."""


class IArchiveJobSource(IJobSource):
    """An interface for acquiring IArchiveJobs."""

    def create(archive):
        """Create a new IArchiveJob for an archive."""


class IPackageUploadNotificationJob(IRunnableJob):
    """A Job to send package upload notifications."""


class IPackageUploadNotificationJobSource(IArchiveJobSource):
    """Interface for acquiring PackageUploadNotificationJobs."""
