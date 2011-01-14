# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""View classes for bug subscription filters."""

__metaclass__ = type
__all__ = [
    "BugSubscriptionFilterView",
    ]


from zope.app.form.browser import TextWidget

from canonical.launchpad.helpers import english_list
from canonical.launchpad.webapp.publisher import (
    canonical_url,
    LaunchpadView,
    )
from canonical.widgets.itemswidgets import LabeledMultiCheckBoxWidget
from lp.app.browser.launchpadform import (
    action,
    custom_widget,
    LaunchpadEditFormView,
    )
from lp.bugs.browser.widgets.bug import BugTagsFrozenSetWidget
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


class BugSubscriptionFilterEditView(LaunchpadEditFormView):
    """Edit view for `IBugSubscriptionFilter`."""

    page_title = u"Edit filter"
    schema = IBugSubscriptionFilter
    field_names = (
        "description",
        "statuses",
        "importances",
        "tags",
        "find_all_tags",
        )

    custom_widget("description", TextWidget, displayWidth=50)
    custom_widget("statuses", LabeledMultiCheckBoxWidget)
    custom_widget("importances", LabeledMultiCheckBoxWidget)
    custom_widget("tags", BugTagsFrozenSetWidget, displayWidth=35)

    @action("Update", name="update")
    def update_action(self, action, data):
        """Update the bug filter with the form data."""
        self.updateContextFromData(data)

    @property
    def next_url(self):
        """Return to the user's structural subscriptions page."""
        return canonical_url(
            self.user, view_name="+structural-subscriptions")

    cancel_url = next_url


class BugSubscriptionFilterCreateView(BugSubscriptionFilterEditView):

    page_title = u"Create new filter"

    # The context does not correspond to the thing we're creating - which,
    # somewhat obviously, doesn't exist yet - so don't even try to render it.
    render_context = False

    @action("Create", name="create")
    def create_action(self, action, data):
        """Create a new bug filter with the form data."""
        bug_filter = self.context.newBugFilter()
        self.updateContextFromData(data, context=bug_filter)
