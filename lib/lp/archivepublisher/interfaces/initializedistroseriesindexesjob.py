# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""`IJobSource` for `InitializeDistroSeriesIndexesJob`."""

__metaclass__ = type
__all__ = [
    'IInitializeDistroSeriesIndexesJobSource',
    ]

from lp.services.job.interfaces.job import IJobSource


class IInitializeDistroSeriesIndexesJobSource(IJobSource):
    """Create and manage `IInitializeDistroSeriesIndexesJob`s."""

    def makeFor(distroseries):
        """Create `IInitializeDistroSeriesIndexesJob` if appropriate.

        If the `Distribution` that `distroseries` belongs to has no
        publisher configuration, no job will be returned.

        :param distroseries: A newly created `DistroSeries` that needs
            its archive indexes initialized.
        :return: An `IInitializeDistroSeriesIndexesJob`, or None.
        """
