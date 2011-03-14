# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""`IDistroSeriesDifferenceJob`."""

__metaclass__ = type
__all__ = [
    'IDistroSeriesDifferenceJobSource',
    ]

from lp.services.job.interfaces.job import IJobSource


class IDistroSeriesDifferenceJobSource(IJobSource):
    """An `IJob` for creating `DistroSeriesDifference`s."""

    def createForPackagePublication(distroseries, sourcepackagename):
        """Create jobs as appropriate for a given status publication.

        :param distroseries: A `DistroSeries` that is assumed to be
            derived from another one.
        :param sourcepackagename: A `SourcePackageName` that is being
            published in `distroseries`.
        """
