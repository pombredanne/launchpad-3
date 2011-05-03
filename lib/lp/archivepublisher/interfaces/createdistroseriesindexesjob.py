# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""`IJobSource` for `CreateDistroSeriesIndexesJob`."""

__metaclass__ = type
__all__ = [
    'ICreateDistroSeriesIndexesJobSource',
    ]

from lp.services.job.interfaces.job import IJobSource


class ICreateDistroSeriesIndexesJobSource(IJobSource):
    """Create and manage `ICreateDistroSeriesIndexesJob`s."""

    def makeFor(distroseries):
        """Create `ICreateDistroSeriesIndexesJob` if appropriate.

        If the `Distribution` that `distroseries` belongs to has no
        publisher configuration, no job will be returned.

        :param distroseries: A `DistroSeries` that needs its archive
            indexes created.
        :return: An `ICreateDistroSeriesIndexesJob`, or None.
        """
