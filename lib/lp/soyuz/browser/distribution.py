# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'DistributionBuildsView',
    ]

from lp.registry.browser.distribution import DistributionView


class DistributionBuildsView(DistributionView):
    """A View to show an `IDistribution` object's builds."""

    label = 'Builds'
    page_title = label
