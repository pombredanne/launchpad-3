# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Browser views for DistroSeriesDifferences."""

__metaclass__ = type
__all__ = [
    'DistroSeriesDifferenceView',
    ]

from canonical.launchpad.webapp.publisher import LaunchpadView


class DistroSeriesDifferenceView(LaunchpadView):

    @property
    def summary(self):
        """Return the summary of the related source package."""
        source_pub = None
        if self.context.source_pub is not None:
            source_pub = self.context.source_pub
        elif self.context.parent_source_pub is not None:
            source_pub = self.context.parent_source_pub

        if source_pub is not None:
            return source_pub.meta_sourcepackage.summary
        else:
            return None

