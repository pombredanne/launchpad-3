# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""View classes for bug subscription filters."""

__metaclass__ = type
__all__ = [
    "BugSubscriptionFilterView",
    ]


from canonical.launchpad.helpers import english_list
from canonical.launchpad.webapp.publisher import LaunchpadView


class BugSubscriptionFilterView(LaunchpadView):

    page_title = u"Bug subscription filter"

    @property
    def description(self):
        description = self.context.description
        if description is None:
            description = u""
        else:
            description = description.strip()
        if len(description) == 0:
            return u"\u2014"
        else:
            return english_list(
                (status.title for status in sorted(description)),
                conjunction=u"or")

    @property
    def statuses(self):
        statuses = self.context.statuses
        if len(statuses) == 0:
            return u"\u2014"
        else:
            return english_list(
                (status.title for status in sorted(statuses)),
                conjunction=u"or")

    @property
    def importances(self):
        importances = self.context.importances
        if len(importances) == 0:
            return u"\u2014"
        else:
            return english_list(
                (importance.title for importance in sorted(importances)),
                conjunction=u"or")

    @property
    def tags(self):
        tags = self.context.tags
        if len(tags) == 0:
            return u"\u2014"
        elif self.context.find_all_tags:
            return english_list(sorted(tags), u"and")
        else:
            return english_list(sorted(tags), u"or")
