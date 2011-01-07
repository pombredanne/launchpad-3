# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""View classes for bug subscription filters."""

__metaclass__ = type
__all__ = [
    "BugSubscriptionFilterView",
    ]


from zope.app.form.browser import TextWidget

from canonical.launchpad.helpers import english_list
from canonical.launchpad.webapp.publisher import LaunchpadView
from canonical.widgets.bug import BugTagsWidget
from canonical.widgets.itemswidgets import LabeledMultiCheckBoxWidget
from lp.app.browser.launchpadform import (
    action,
    custom_widget,
    LaunchpadFormView,
    )
from lp.bugs.interfaces.bugsubscriptionfilter import IBugSubscriptionFilter


class BugSubscriptionFilterView(LaunchpadView):
    """View for `IBugSubscriptionFilter`.

    The properties and methods herein are intended to construct a view
    something like:

      Bug mail filter "A filter description"
        Matches when status is New, Confirmed, or Triaged
        *and* importance is High, Medium, or Low
        *and* the bug is tagged with bar or foo.

    """

    @property
    def description(self):
        """Return the bug filter description.

        Leading and trailing whitespace is trimmed. If the description is not
        set the empty string is returned.
        """
        description = self.context.description
        return u"" if description is None else description.strip()

    @property
    def conditions(self):
        """Descriptions of the bug filter's conditions."""
        conditions = []
        statuses = self.context.statuses
        if len(statuses) > 0:
            conditions.append(
                u"the status is %s" % english_list(
                    (status.title for status in sorted(statuses)),
                    conjunction=u"or"))
        importances = self.context.importances
        if len(importances) > 0:
            conditions.append(
                u"the importance is %s" % english_list(
                    (importance.title for importance in sorted(importances)),
                    conjunction=u"or"))
        tags = self.context.tags
        if len(tags) > 0:
            conditions.append(
                u"the bug is tagged with %s" % english_list(
                    sorted(tags), conjunction=(
                        u"and" if self.context.find_all_tags else u"or")))
        return conditions


class BugSubscriptionFilterEditView(LaunchpadFormView):
    """View for `IBugSubscriptionFilter`.

    The properties and methods herein are intended to construct a view
    something like:

      Bug mail filter "A filter description"
        Matches when status is New, Confirmed, or Triaged
        *and* importance is High, Medium, or Low
        *and* the bug is tagged with bar or foo.

    """

    page_title = u"Edit filter"
    schema = IBugSubscriptionFilter
    field_names = (
        "description",
        "statuses",
        "importances",
        "tags",
        "find_all_tags",
        )

    custom_widget("description", TextWidget)
    custom_widget("statuses", LabeledMultiCheckBoxWidget)
    custom_widget("importances", LabeledMultiCheckBoxWidget)
    custom_widget("tags", BugTagsWidget)

    def setUpWidgets(self, context=None):
        super(BugSubscriptionFilterEditView, self).setUpWidgets(context)
        self.widgets["description"].displayWidth = 50
        self.widgets["tags"].displayWidth = 35

    @action('Update filter', name='update')
    def update_action(self, action, data):
        """Update the bug filter with the form data."""
        self.updateContextFromData(data)
