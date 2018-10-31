# Copyright 2015-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'GitRepositoryPortletSubscribersContent',
    'GitSubscriptionAddOtherView',
    'GitSubscriptionAddView',
    'GitSubscriptionEditOwnView',
    'GitSubscriptionEditView',
    ]

from zope.component import getUtility

from lp.app.browser.launchpadform import (
    action,
    LaunchpadEditFormView,
    LaunchpadFormView,
    )
from lp.app.interfaces.services import IService
from lp.code.enums import BranchSubscriptionNotificationLevel
from lp.code.interfaces.gitsubscription import IGitSubscription
from lp.registry.interfaces.person import IPersonSet
from lp.services.webapp import (
    canonical_url,
    LaunchpadView,
    )
from lp.services.webapp.authorization import (
    check_permission,
    precache_permission_for_objects,
    )
from lp.services.webapp.escaping import structured


class GitRepositoryPortletSubscribersContent(LaunchpadView):
    """View for the contents for the subscribers portlet."""

    def subscriptions(self):
        """Return a decorated list of Git repository subscriptions."""

        # Cache permissions so private subscribers can be rendered.
        # The security adaptor will do the job also but we don't want or
        # need the expense of running several complex SQL queries.
        subscriptions = list(self.context.subscriptions)
        person_ids = [sub.person_id for sub in subscriptions]
        list(getUtility(IPersonSet).getPrecachedPersonsFromIDs(
            person_ids, need_validity=True))
        if self.user is not None:
            subscribers = [
                subscription.person for subscription in subscriptions]
            precache_permission_for_objects(
                self.request, "launchpad.LimitedView", subscribers)

        visible_subscriptions = [
            subscription for subscription in subscriptions
            if check_permission("launchpad.LimitedView", subscription.person)]
        return sorted(
            visible_subscriptions,
            key=lambda subscription: subscription.person.displayname)


class _GitSubscriptionView(LaunchpadFormView):
    """Contains the common functionality of the Add and Edit views."""

    schema = IGitSubscription
    field_names = ['notification_level', 'max_diff_lines', 'review_level']

    LEVELS_REQUIRING_LINES_SPECIFICATION = (
        BranchSubscriptionNotificationLevel.DIFFSONLY,
        BranchSubscriptionNotificationLevel.FULL)

    @property
    def user_is_subscribed(self):
        # Since it is technically possible to get to this page when
        # the user is not subscribed by hacking the URL, we should
        # handle the case nicely.
        return self.context.getSubscription(self.user) is not None

    @property
    def next_url(self):
        return canonical_url(self.context)

    cancel_url = next_url

    def add_notification_message(self, initial, notification_level,
                                 max_diff_lines, review_level):
        if notification_level in self.LEVELS_REQUIRING_LINES_SPECIFICATION:
            lines_message = "<li>%s</li>" % max_diff_lines.description
        else:
            lines_message = ""

        format_str = "%%s<ul><li>%%s</li>%s<li>%%s</li></ul>" % lines_message
        message = structured(
            format_str, initial, notification_level.description,
            review_level.description)
        self.request.response.addNotification(message)

    def optional_max_diff_lines(self, notification_level, max_diff_lines):
        if notification_level in self.LEVELS_REQUIRING_LINES_SPECIFICATION:
            return max_diff_lines
        else:
            return None


class GitSubscriptionAddView(_GitSubscriptionView):

    page_title = label = "Subscribe to repository"

    @action("Subscribe")
    def subscribe(self, action, data):
        # To catch the stale post problem, check that the user is not
        # subscribed before continuing.
        if self.context.hasSubscription(self.user):
            self.request.response.addNotification(
                "You are already subscribed to this repository.")
        else:
            notification_level = data["notification_level"]
            max_diff_lines = self.optional_max_diff_lines(
                notification_level, data["max_diff_lines"])
            review_level = data["review_level"]

            self.context.subscribe(
                self.user, notification_level, max_diff_lines, review_level,
                self.user)

            self.add_notification_message(
                "You have subscribed to this repository with: ",
                notification_level, max_diff_lines, review_level)


class GitSubscriptionEditOwnView(_GitSubscriptionView):

    @property
    def label(self):
        return "Edit subscription to repository"

    @property
    def page_title(self):
        return "Edit subscription to repository %s" % self.context.displayname

    @property
    def initial_values(self):
        subscription = self.context.getSubscription(self.user)
        if subscription is None:
            # This is the case of URL hacking or stale page.
            return {}
        else:
            return {"notification_level": subscription.notification_level,
                    "max_diff_lines": subscription.max_diff_lines,
                    "review_level": subscription.review_level}

    @action("Change")
    def change_details(self, action, data):
        # Be proactive in the checking to catch the stale post problem.
        if self.context.hasSubscription(self.user):
            subscription = self.context.getSubscription(self.user)
            subscription.notification_level = data["notification_level"]
            subscription.max_diff_lines = self.optional_max_diff_lines(
                subscription.notification_level,
                data["max_diff_lines"])
            subscription.review_level = data["review_level"]

            self.add_notification_message(
                "Subscription updated to: ",
                subscription.notification_level,
                subscription.max_diff_lines,
                subscription.review_level)
        else:
            self.request.response.addNotification(
                "You are not subscribed to this repository.")

    @action("Unsubscribe")
    def unsubscribe(self, action, data):
        # Be proactive in the checking to catch the stale post problem.
        if self.context.hasSubscription(self.user):
            self.context.unsubscribe(self.user, self.user)
            self.request.response.addNotification(
                "You have unsubscribed from this repository.")
        else:
            self.request.response.addNotification(
                "You are not subscribed to this repository.")


class GitSubscriptionAddOtherView(_GitSubscriptionView):
    """View used to subscribe someone other than the current user."""

    field_names = [
        "person", "notification_level", "max_diff_lines", "review_level"]
    for_input = True

    # Since we are subscribing other people, the current user
    # is never considered subscribed.
    user_is_subscribed = False

    page_title = label = "Subscribe to repository"

    def validate(self, data):
        if "person" in data:
            person = data["person"]
            subscription = self.context.getSubscription(person)
            if subscription is None and not self.context.userCanBeSubscribed(
                person):
                self.setFieldError(
                    "person",
                    "Open and delegated teams cannot be subscribed to "
                    "private repositories.")

    @action("Subscribe", name="subscribe_action")
    def subscribe_action(self, action, data):
        """Subscribe the specified user to the repository.

        The user must be a member of a team in order to subscribe that team
        to the repository.  Launchpad Admins are special and they can
        subscribe any team.
        """
        notification_level = data["notification_level"]
        max_diff_lines = self.optional_max_diff_lines(
            notification_level, data["max_diff_lines"])
        review_level = data["review_level"]
        person = data["person"]
        subscription = self.context.getSubscription(person)
        if subscription is None:
            self.context.subscribe(
                person, notification_level, max_diff_lines, review_level,
                self.user)
            self.add_notification_message(
                "%s has been subscribed to this repository with: "
                % person.displayname, notification_level, max_diff_lines,
                review_level)
        else:
            self.add_notification_message(
                "%s was already subscribed to this repository with: "
                % person.displayname,
                subscription.notification_level, subscription.max_diff_lines,
                review_level)


class GitSubscriptionEditView(LaunchpadEditFormView):
    """The view for editing repository subscriptions.

    Used when traversed to the repository subscription itself rather than
    through the repository action item to edit the user's own subscription.
    This is the only current way to edit a team repository subscription.
    """
    schema = IGitSubscription
    field_names = ["notification_level", "max_diff_lines", "review_level"]

    @property
    def page_title(self):
        return (
            "Edit subscription to repository %s" % self.repository.displayname)

    @property
    def label(self):
        return (
            "Edit subscription to repository for %s" % self.person.displayname)

    def initialize(self):
        self.repository = self.context.repository
        self.person = self.context.person
        super(GitSubscriptionEditView, self).initialize()

    @action("Change", name="change")
    def change_action(self, action, data):
        """Update the repository subscription."""
        self.updateContextFromData(data)

    @action("Unsubscribe", name="unsubscribe")
    def unsubscribe_action(self, action, data):
        """Unsubscribe the team from the repository."""
        self.repository.unsubscribe(self.person, self.user)
        self.request.response.addNotification(
            "%s has been unsubscribed from this repository."
            % self.person.displayname)

    @property
    def next_url(self):
        url = canonical_url(self.repository)
        # If the subscriber can no longer see the repository, redirect them
        # away.
        service = getUtility(IService, "sharing")
        _, _, repositories, _ = service.getVisibleArtifacts(
            self.person, gitrepositories=[self.repository],
            ignore_permissions=True)
        if not repositories:
            url = canonical_url(self.repository.target)
        return url

    cancel_url = next_url
