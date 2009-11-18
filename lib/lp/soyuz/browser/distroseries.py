# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'DistroSeriesBuildsView',
    ]

from lp.registry.browser.distroseries import DistroSeriesView


class DistroSeriesBuildsView(DistroSeriesView):
    """A View to show an `IDistroSeries` object's builds."""

    @property
    def page_title(self):
        """Return the HTML page title."""
        return '%s builds' % self.context.title
