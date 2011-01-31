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
from lp.registry.enum import BugNotificationLevel
from lp.services.propertycache import cachedproperty
from lp.bugs.browser.widgets.bug import BugTagsFrozenSetWidget
from lp.bugs.browser.bugsubscription import AdvancedSubscriptionMixin
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


class BugSubscriptionFilterEditViewBase(LaunchpadEditFormView,
                                        AdvancedSubscriptionMixin):
    """Base class for edit or create views of `IBugSubscriptionFilter`."""

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

    target = None # Define in concrete subclass to be the target of the
    # structural subscription that we are modifying.

    # This is used by the AdvancedSubscriptionMixin.
    current_user_subscription = None

    @cachedproperty
    def _bug_notification_level_descriptions(self):
        displayname = self.target.displayname
        return {
            BugNotificationLevel.LIFECYCLE: (
                "A bug in %s is fixed or re-opened." % displayname),
            BugNotificationLevel.METADATA: (
                "Any change is made to a bug in %s, other than a new "
                "comment being added." % displayname),
            BugNotificationLevel.COMMENTS: (
                "A change is made or a new comment is added to a bug in %s."
                % displayname),
            }

    def setUpFields(self):
        """Set up fields for form.

        Overrides the usual implementation to also set up bug notification."""
        LaunchpadEditFormView.setUpFields(self)
        self._setUpBugNotificationLevelField()

    @property
    def next_url(self):
        """Return to the user's structural subscriptions page."""
        return canonical_url(
            self.user, view_name="+structural-subscriptions")

    cancel_url = next_url


class BugSubscriptionFilterEditView(
    BugSubscriptionFilterEditViewBase):
    """Edit view for `IBugSubscriptionFilter`.

    :ivar context: A provider of `IBugSubscriptionFilter`.
    """

    page_title = u"Edit filter"

    @action("Update", name="update")
    def update_action(self, action, data):
        """Update the bug filter with the form data."""
        self.updateContextFromData(data)

    @action("Delete", name="delete")
    def delete_action(self, action, data):
        """Delete the bug filter."""
        self.context.delete()

    @property
    def current_user_subscription(self):
        """Return an object that has the value for bug_notification_level."""
        return self.context

    @property
    def target(self):
        return self.context.structural_subscription.target


class BugSubscriptionFilterCreateView(
    BugSubscriptionFilterEditViewBase):
    """View to create a new `IBugSubscriptionFilter`.

    :ivar context: A provider of `IStructuralSubscription`.
    """

    page_title = u"Create new filter"

    # The context does not correspond to the thing we're creating - which,
    # somewhat obviously, doesn't exist yet - so don't even try to render it.
    render_context = False

    @action("Create", name="create")
    def create_action(self, action, data):
        """Create a new bug filter with the form data."""
        bug_filter = self.context.newBugFilter()
        self.updateContextFromData(data, context=bug_filter)

    @property
    def target(self):
        return self.context.target
