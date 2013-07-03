# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    "IPackageDiffJob",
    "IPackageDiffJobSource",
    ]

from lp.services.job.interfaces.job import (
    IJobSource,
    IRunnableJob,
    )


class IPackageDiffJobSource(IJobSource):
    """An interface for acquring IPackageDiffJobs."""

    def create(packagediff):
        """Create a new diff generation job for a package diff."""

    def get(packagediff):
        """Retrieve the diff generation job for a package diff.

        :return: `None` or an `IPackageDiffJob`.
        """ 


class IPackageDiffJob(IRunnableJob):
    """A `Job` that generates diffs for a given `IPackageDiff`s."""
