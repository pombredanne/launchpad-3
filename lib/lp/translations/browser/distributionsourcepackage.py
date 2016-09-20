# Copyright 2009-2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Translations browser views for DistributionSourcePackages."""

__metaclass__ = type

__all__ = [
    'DistributionSourcePackageView',
    ]

import operator

from lp.registry.interfaces.series import SeriesStatus
from lp.services.propertycache import cachedproperty
from lp.services.webapp.publisher import LaunchpadView


class DistributionSourcePackageView(LaunchpadView):
    """Default DistributionSourcePackage translations view class."""

    @cachedproperty
    def translation_focus(self):
        """Return the ISourcePackage where the translators should work.

        If ther isn't a defined focus, we return latest series.
        """
        series = (
            self.context.distribution.translation_focus
            or self.context.distribution.currentseries)
        if series is not None:
            return series.getSourcePackage(self.context.sourcepackagename)

    def secondary_translatable_series(self):
        """Return a list of ISourcePackages that aren't the translation_focus.

        It only includes the ones that are still supported.
        """
        series = [
            series.getSourcePackage(self.context.sourcepackagename)
            for series in self.context.distribution.series
            if (series.status != SeriesStatus.OBSOLETE
                and (self.translation_focus is None or
                     self.translation_focus.distroseries != series))]

        return sorted(series, key=operator.attrgetter('distroseries.version'),
                      reverse=True)
