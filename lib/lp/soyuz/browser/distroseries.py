# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'DistroSeriesBuildsView',
    'DistroSeriesQueueView',
    ]

from lp.registry.browser.distroseries import DistroSeriesView


class DistroSeriesBuildsView(DistroSeriesView):
    """A View to show an `IDistroSeries` object's builds."""

    label = 'Builds'
    page_title = label


class DistroSeriesQueueView(DistroSeriesView):
    """A View to show an `IDistroSeries` object's uploads."""

    label = 'Upload queue'
    page_title = label
