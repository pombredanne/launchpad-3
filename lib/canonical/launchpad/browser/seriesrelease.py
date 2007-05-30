# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Presentation code that pertains to both product series and distro releases.
"""

__metaclass__ = type
__all__ = [
    'SeriesOrReleasesMixinDynMenu',
    ]


class SeriesOrReleasesMixinDynMenu:

    MAX_SERIES = 8
    MAX_RELEASES = 8

    def seriesMenu(self):
        for link in self._seriesOrReleaseMenu(
            self.context.serieses,
            self.MAX_SERIES,
            self.makeLink('Show all series...', page='+series')
            ):
            yield link

    def releasesMenu(self):
        for link in self._seriesOrReleaseMenu(
            self.context.releases,
            self.MAX_RELEASES,
            self.makeLink('Show all releases...', page='+releases')
            ):
            yield link

    def _seriesOrReleaseMenu(self, iterator, maxitems, show_all_link):
        # This is written from the point of view of series, even
        # though it is used for series or for releases.
        series_iter = iter(iterator)
        for idx, series in enumerate(series_iter):
            yield self.makeBreadcrumbLink(series)
            if idx + 1 >= maxitems:
                break
        # If there are any more, then offer a link to all series.
        try:
            series_iter.next()
        except StopIteration:
            pass
        else:
            yield show_all_link

