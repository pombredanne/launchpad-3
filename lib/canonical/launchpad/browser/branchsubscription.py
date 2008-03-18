# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'BranchSubscriptionSOP',
    'BranchSubscriptionAddView',
    'BranchSubscriptionEditView',
    'BranchSubscriptionEditOwnView',
    'BranchSubscriptionAddOtherView',
    ]

from zope.component import getUtility

from canonical.launchpad.browser.launchpad import StructuralObjectPresentation
from canonical.launchpad.interfaces import (
    BranchSubscriptionNotificationLevel, IBranchSubscription,
    ILaunchpadCelebrities)
from canonical.launchpad.webapp import (
    action, canonical_url, LaunchpadEditFormView, LaunchpadFormView)
from canonical.launchpad.webapp.menu import structured


class BranchSubscriptionSOP(StructuralObjectPresentation):
    """Provides the structural heading for IBranchSubscription."""

    def getMainHeading(self):
        """See IStructuralHeaderPresentation."""
        return self.context.branch.owner.browsername


class _BranchSubscriptionView(LaunchpadFormView):

    """Contains the common functionality of the Add and Edit views."""

    schema = IBranchSubscription
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

    def add_notification_message(self, initial,
                                 notification_level, max_diff_lines,
                                 review_level):
        if notification_level in self.LEVELS_REQUIRING_LINES_SPECIFICATION:
            lines_message = '<li>%s</li>' % max_diff_lines.description
        else:
            lines_message = ''

        format_str = '%%s<ul><li>%%s</li>%s<li>%%s</li></ul>' % lines_message
        message = structured(format_str, initial,
                             notification_level.description,
                             review_level.description)
        self.request.response.addNotification(message)

    def optional_max_diff_lines(self, notification_level, max_diff_lines):
        if notification_level in self.LEVELS_REQUIRING_LINES_SPECIFICATION:
            return max_diff_lines
        else:
            return None


class BranchSubscriptionAddView(_BranchSubscriptionView):

    subscribing_self = True

    @action("Subscribe")
    def subscribe(self, action, data):
        # To catch the stale post problem, check that the user is not
        # subscribed before continuing.
        if self.context.hasSubscription(self.user):
            self.request.response.addNotification(
                'You are already subscribed to this branch.')
        else:
            notification_level = data['notification_level']
            max_diff_lines = self.optional_max_diff_lines(
                notification_level, data['max_diff_lines'])
            review_level = data['review_level']

            self.context.subscribe(
                self.user, notification_level, max_diff_lines, review_level)

            self.add_notification_message(
                'You have subscribed to this branch with: ',
                notification_level, max_diff_lines, review_level)


class BranchSubscriptionEditOwnView(_BranchSubscriptionView):

    @property
    def initial_values(self):
        subscription = self.context.getSubscription(self.user)
        if subscription is None:
            # This is the case of URL hacking or stale page.
            return {}
        else:
            return {'notification_level' : subscription.notification_level,
                    'max_diff_lines' : subscription.max_diff_lines}

    @action("Unsubscribe")
    def unsubscribe(self, action, data):
        # Be proactive in the checking to catch the stale post problem.
        if self.context.hasSubscription(self.user):
            self.context.unsubscribe(self.user)
            self.request.response.addNotification(
                "You have unsubscribed from this branch.")
        else:
            self.request.response.addNotification(
                'You are not subscribed to this branch.')

    @action("Change")
    def change_details(self, action, data):
        # Be proactive in the checking to catch the stale post problem.
        if self.context.hasSubscription(self.user):
            subscription = self.context.getSubscription(self.user)
            subscription.notification_level = data['notification_level']
            subscription.max_diff_lines = self.optional_max_diff_lines(
                subscription.notification_level,
                data['max_diff_lines'])

            self.add_notification_message(
                'Subscription updated to: ',
                subscription.notification_level,
                subscription.max_diff_lines,
                subscription.review_level)
        else:
            self.request.response.addNotification(
                'You are not subscribed to this branch.')


class BranchSubscriptionAddOtherView(_BranchSubscriptionView):
    """View used to subscribe someone other than the current user."""

    field_names = [
        'person', 'notification_level', 'max_diff_lines', 'review_level']
    for_input = True

    # Since we are subscribing other people, the current user
    # is never considered subscribed.
    user_is_subscribed = False
    subscribing_self = False
    # Override the inherited property for next_url
    next_url = None

    @action("Subscribe", name="subscribe_action")
    def subscribe_action(self, action, data):
        """Subscribe the specified user to the branch.

        The user must be a member of a team in order to subscribe that team to
        the branch.  Launchpad Admins are special and they can subscribe any
        team.
        """
        notification_level = data['notification_level']
        max_diff_lines = self.optional_max_diff_lines(
            notification_level, data['max_diff_lines'])
        review_level = data['review_level']
        person = data['person']
        subscription = self.context.getSubscription(person)
        self.next_url = canonical_url(self.context)
        if subscription is None:
            # XXX thumper 2007-06-14 bug=117980:
            # Restrictive policy is being enforced in the view
            # rather than the model.
            admins = getUtility(ILaunchpadCelebrities).admin
            if (person.isTeam() and not self.user.inTeam(person)
                and not self.user.inTeam(admins)):
                # A person can only subscribe a team if they are members
                # of that team (or a Launchpad Admin).
                self.setFieldError(
                    'person',
                    "You can only subscribe teams that you are a member of.")
                self.next_url = None
                return

            self.context.subscribe(
                person, notification_level, max_diff_lines, review_level)

            self.add_notification_message(
                '%s has been subscribed to this branch with: '
                % person.displayname, notification_level, max_diff_lines,
                review_level)
        else:
            self.add_notification_message(
                '%s was already subscribed to this branch with: '
                % person.displayname,
                subscription.notification_level, subscription.max_diff_lines,
                review_level)


class BranchSubscriptionEditView(LaunchpadEditFormView):
    """The view for editting branch subscriptions.

    Used when traversed to the branch subscription itself rather than
    through the branch action item to edit the user's own subscription.
    This is the only current way to edit a team branch subscription.
    """
    schema = IBranchSubscription
    field_names = ['notification_level', 'max_diff_lines', 'review_level']

    def initialize(self):
        self.branch = self.context.branch
        self.person = self.context.person
        LaunchpadEditFormView.initialize(self)

    @action("Unsubscribe", name="unsubscribe")
    def unsubscribe_action(self, action, data):
        """Unsubscribe the team from the branch."""
        self.branch.unsubscribe(self.person)
        self.request.response.addNotification(
            "%s has been unsubscribed from this branch."
            % self.person.displayname)

    @action("Change", name="change")
    def change_action(self, action, data):
        """Update the branch subscription."""
        self.updateContextFromData(data)

    @property
    def next_url(self):
        return canonical_url(self.branch)
