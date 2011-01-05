# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""View classes for bug subscription filters."""

__metaclass__ = type
__all__ = [
    "BugSubscriptionFilterView",
    ]


from canonical.launchpad.webapp.publisher import LaunchpadView


class BugSubscriptionFilterView(LaunchpadView):

    page_title = u"Bug subscription filter"
