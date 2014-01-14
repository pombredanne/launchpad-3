# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    "IPackageTranslationsUploadJob",
    "IPackageTranslationsUploadJobSource",
    ]

from lp.services.job.interfaces.job import (
    IJobSource,
    IRunnableJob,
    )


class IPackageTranslationsUploadJobSource(IJobSource):
    """An interface for acquiring IPackageTranslationsUploadJob."""

    def create(distroseries, libraryfilealias, sourcepackagename, requester):
        """Create new translations upload job for a source package release."""


class IPackageTranslationsUploadJob(IRunnableJob):
    """A `Job` that uploads/attaches files to a `ITranslationsImportQueue`."""

    def getErrorRecipients():
        """Return a list of email-ids to notify about upload errors."""

    def attachTranslationFiles(by_maintainer):
        """Attach a tarball with translations to be imported into Rosetta.

        :by_maintainer: indicates if the imported files where uploaded by
            the maintainer of the project or package.

        raise DownloadFailed if we are not able to fetch the file from
            :tarball_alias:.
        """
