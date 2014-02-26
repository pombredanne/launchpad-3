# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Browser views for LaunchpadStatisticSet."""

__metaclass__ = type

__all__ = [
    'LaunchpadStatisticSet',
    ]

from lp.services.webapp import LaunchpadView


class LaunchpadStatisticSet(LaunchpadView):
    label = page_title = "Launchpad statistics"
