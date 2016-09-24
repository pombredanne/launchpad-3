# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Widgets related to `TranslationImportQueueEntry`."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    "TranslationImportQueueEntrySourcePackageNameWidget",
    ]

from lp.app.widgets.popup import SourcePackageNameWidgetBase


class TranslationImportQueueEntrySourcePackageNameWidget(
    SourcePackageNameWidgetBase):
    """A widget for associating a TranslationImportQueueEntry with an SPN."""

    @property
    def distribution_name(self):
        distribution = self.getDistribution()
        if distribution is not None:
            return distribution.name
        else:
            return ''

    def getDistribution(self):
        """See `SourcePackageNameWidgetBase`."""
        distroseries = self.context.context.distroseries
        if distroseries is not None:
            return distroseries.distribution
        else:
            return None
