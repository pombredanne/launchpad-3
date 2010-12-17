# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'StructuralSubscriptionMenuMixin',
    'StructuralSubscriptionTargetTraversalMixin',
    'StructuralSubscriptionView',
    'StructuralSubscribersPortletView',
    ]

from operator import attrgetter

from zope.component import getUtility
from zope.formlib import form
from zope.schema import (
    Choice,
    List,
    )
from zope.schema.vocabulary import (
    SimpleTerm,
    SimpleVocabulary,
    )

from canonical.launchpad.webapp import (
    canonical_url,
    LaunchpadView,
    stepthrough,
    )
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.menu import Link
from canonical.widgets import LabeledMultiCheckBoxWidget
from lp.app.browser.launchpadform import (
    action,
    custom_widget,
    LaunchpadFormView,
    )
from lp.bugs.browser.bugsubscription import AdvancedSubscriptionMixin
from lp.registry.enum import BugNotificationLevel
from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage,
    )
from lp.registry.interfaces.milestone import IProjectGroupMilestone
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.structuralsubscription import (
    IStructuralSubscriptionForm,
    IStructuralSubscriptionTarget,
    )
from lp.services.propertycache import cachedproperty


class StructuralSubscriptionView(LaunchpadFormView,
                                 AdvancedSubscriptionMixin):
    """View class for structural subscriptions."""

    schema = IStructuralSubscriptionForm

    custom_widget('subscriptions_team', LabeledMultiCheckBoxWidget)
    custom_widget('remove_other_subscriptions', LabeledMultiCheckBoxWidget)

    override_title_breadcrumbs = True

    @cachedproperty
    def _bug_notification_level_descriptions(self):
        return {
            BugNotificationLevel.LIFECYCLE: (
                "A bug in %s is fixed or re-opened." %
                self.context.displayname),
            BugNotificationLevel.METADATA: (
                "Any change is made to a bug in %s, other than a new "
                "comment being added." %
                self.context.displayname),
            BugNotificationLevel.COMMENTS: (
                "A change is made or a new comment is added to a bug in %s."
                % self.context.displayname),
            }

    @property
    def page_title(self):
        return 'Subscribe to Bugs in %s' % self.context.title

    @property
    def label(self):
        return self.page_title

    @property
    def next_url(self):
        return canonical_url(self.context)

    def setUpFields(self):
        """See LaunchpadFormView."""
        LaunchpadFormView.setUpFields(self)
        team_subscriptions = self._createTeamSubscriptionsField()
        if team_subscriptions:
            self.form_fields += form.Fields(team_subscriptions)
        if self.userIsDriver():
            add_other = form.Fields(self._createAddOtherSubscriptionsField())
            self.form_fields += add_other
            remove_other = self._createRemoveOtherSubscriptionsField()
            if remove_other:
                self.form_fields += form.Fields(remove_other)
        self._setUpBugNotificationLevelField()

    def _createTeamSubscriptionsField(self):
        """Create field with a list of the teams the user is a member of.

        Return a FormField instance, if the user is a member of at least
        one team, else return None.
        """
        teams = self.user_teams
        if not teams:
            return None
        teams.sort(key=attrgetter('displayname'))
        terms = [
            SimpleTerm(team, team.name, team.displayname)
            for team in teams]
        team_vocabulary = SimpleVocabulary(terms)
        team_subscriptions_field = List(
            __name__='subscriptions_team',
            title=u'Team subscriptions',
            description=(u'You can subscribe the teams of '
                          'which you are an administrator.'),
            value_type=Choice(vocabulary=team_vocabulary),
            required=False)
        return form.FormField(team_subscriptions_field)

    def _createRemoveOtherSubscriptionsField(self):
        """Create a field with a list of subscribers.

        Return a FormField instance, if subscriptions exist that can
        be removed, else return None.
        """
        teams = set(self.user_teams)
        other_subscriptions = set(
            subscription.subscriber
            for subscription
            in self.context.bug_subscriptions)

        # Teams and the current user have their own UI elements. Remove
        # them to avoid duplicates.
        other_subscriptions.difference_update(teams)
        other_subscriptions.discard(self.user)

        if not other_subscriptions:
            return None

        other_subscriptions = sorted(
            other_subscriptions, key=attrgetter('displayname'))

        terms = [
            SimpleTerm(subscriber, subscriber.name, subscriber.displayname)
            for subscriber in other_subscriptions]

        subscriptions_vocabulary = SimpleVocabulary(terms)
        other_subscriptions_field = List(
            __name__='remove_other_subscriptions',
            title=u'Unsubscribe',
            value_type=Choice(vocabulary=subscriptions_vocabulary),
            required=False)
        return form.FormField(other_subscriptions_field)

    def _createAddOtherSubscriptionsField(self):
        """Create a field for a new subscription."""
        new_subscription_field = Choice(
            __name__='new_subscription',
            title=u'Subscribe someone else',
            vocabulary='ValidPersonOrTeam',
            required=False)
        return form.FormField(new_subscription_field)

    @property
    def initial_values(self):
        """See `LaunchpadFormView`."""
        teams = set(self.user_teams)
        subscribed_teams = set(team
                               for team in teams
                               if self.isSubscribed(team))
        return {
            'subscribe_me': self.currentUserIsSubscribed(),
            'subscriptions_team': subscribed_teams,
            }

    def isSubscribed(self, person):
        """Is `person` subscribed to the context target?

        Returns True is the user is subscribed to bug notifications
        for the context target.
        """
        subscription = self.context.getSubscription(person)
        if subscription is not None:
            return (subscription.bug_notification_level >
                    BugNotificationLevel.NOTHING)
        else:
            return False

    def currentUserIsSubscribed(self):
        """Return True, if the current user is subscribed."""
        return self.isSubscribed(self.user)

    @cachedproperty
    def current_user_subscription(self):
        """Return the subscription of the current user."""
        return self.context.getSubscription(self.user)

    def userCanAlter(self):
        if self.context.userCanAlterBugSubscription(self.user, self.user):
            return True

    @action(u'Save these changes', name='save')
    def save_action(self, action, data):
        """Process the subscriptions submitted by the user."""
        self._handleUserSubscription(data)
        self._handleTeamSubscriptions(data)
        self._handleDriverChanges(data)

    def _handleUserSubscription(self, data):
        """Process the subscription for the user."""
        target = self.context
        # addSubscription raises an exception if called for an already
        # subscribed person, and removeBugSubscription raises an exception
        # for a non-subscriber, hence call these methods only, if the
        # subscription status changed.
        is_subscribed = self.isSubscribed(self.user)
        subscribe = data['subscribe_me']
        if (not is_subscribed) and subscribe:
            target.addBugSubscription(
                self.user, self.user,
                data.get('bug_notification_level', None))
            self.request.response.addNotification(
                'You have subscribed to "%s". You will now receive an '
                'e-mail each time someone reports or changes one of '
                'its public bugs.' % target.displayname)
        elif is_subscribed and not subscribe:
            target.removeBugSubscription(self.user, self.user)
            self.request.response.addNotification(
                'You have unsubscribed from "%s". You '
                'will no longer automatically receive e-mail about '
                'changes to its public bugs.'
                % target.displayname)
        else:
            # The subscription status did not change: nothing to do.
            pass

    def _handleTeamSubscriptions(self, data):
        """Process subscriptions for teams."""
        form_selected_teams = data.get('subscriptions_team', None)
        if form_selected_teams is None:
            return

        target = self.context
        teams = set(self.user_teams)
        form_selected_teams = teams & set(form_selected_teams)
        subscriptions = set(
            team for team in teams if self.isSubscribed(team))

        for team in form_selected_teams - subscriptions:
            target.addBugSubscription(
                team, self.user, data.get('bug_notification_level', None))
            self.request.response.addNotification(
                'The %s team will now receive an e-mail each time '
                'someone reports or changes a public bug in "%s".' % (
                team.displayname, self.context.displayname))

        for team in subscriptions - form_selected_teams:
            target.removeBugSubscription(team, self.user)
            self.request.response.addNotification(
                'The %s team will no longer automatically receive '
                'e-mail about changes to public bugs in "%s".' % (
                    team.displayname, self.context.displayname))

    def _handleDriverChanges(self, data):
        """Process subscriptions for other persons."""
        if not self.userIsDriver():
            return

        target = self.context
        new_subscription = data['new_subscription']
        if new_subscription is not None:
            target.addBugSubscription(new_subscription, self.user)
            self.request.response.addNotification(
                '%s will now receive an e-mail each time someone '
                'reports or changes a public bug in "%s".' % (
                new_subscription.displayname,
                target.displayname))

        subscriptions_to_remove = data.get('remove_other_subscriptions', [])
        for subscription in subscriptions_to_remove:
            target.removeBugSubscription(subscription, self.user)
            self.request.response.addNotification(
                '%s will no longer automatically receive e-mail about '
                'public bugs in "%s".' % (
                    subscription.displayname, target.displayname))

    def userIsDriver(self):
        """Has the current user driver permissions?"""
        # XXX Tom Berger 2008-01-30 spec=subscription-invitation:
        # The semantics of this method are actually a bit vague,
        # since when we talk about driver permissions, we're talking
        # about something different for each structure. For now,
        # we only want to look at this if the target is a
        # distribution source package, in order to maintain
        # compatibility with the bug contacts feature. We want
        # to enable this for other targets, but probably only
        # after implementing
        # https://launchpad.net/malone/+spec/subscription-invitation
        if IDistributionSourcePackage.providedBy(self.context):
            return check_permission(
                "launchpad.Driver", self.context.distribution)
        else:
            return False

    @cachedproperty
    def user_teams(self):
        """Return the teams that the current user is an administrator of."""
        return list(self.user.getAdministratedTeams())

    @property
    def show_details_portlet(self):
        """Show details portlet?

        Returns `True` if the portlet details is available
        and should be shown for the context.
        """
        return IDistributionSourcePackage.providedBy(self.context)


class StructuralSubscriptionTargetTraversalMixin:
    """Mix-in class that provides +subscription/<SUBSCRIBER> traversal."""

    @stepthrough('+subscription')
    def traverse_structuralsubscription(self, name):
        """Traverses +subscription portions of URLs."""
        person = getUtility(IPersonSet).getByName(name)
        return self.context.getSubscription(person)


class StructuralSubscriptionMenuMixin:
    """Mix-in class providing the subscription add/edit menu link."""

    def subscribe(self):
        """The subscribe menu link.

        If the user, or any of the teams he's a member of, already has a
        subscription to the context, the link offer to edit the subscriptions
        and displays the edit icon. Otherwise, the link offers to subscribe
        and displays the add icon.
        """
        if IStructuralSubscriptionTarget.providedBy(self.context):
            sst = self.context
        else:
            # self.context is a view, and the target is its context
            sst = self.context.context

        # ProjectGroup milestones aren't really structural subscription
        # targets as they're not real milestones, so you can't subscribe to
        # them.
        enabled = not IProjectGroupMilestone.providedBy(sst)

        if sst.userHasBugSubscriptions(self.user):
            text = 'Edit bug mail subscription'
            icon = 'edit'
        else:
            text = 'Subscribe to bug mail'
            icon = 'add'
        if enabled == False or (
            not sst.userCanAlterBugSubscription(self.user, self.user)):
            return Link('+subscribe', text, icon=icon, enabled=False)
        else:
            return Link('+subscribe', text, icon=icon, enabled=enabled)


class StructuralSubscribersPortletView(LaunchpadView):
    """A simple view for displaying the subscribers portlet."""

    @property
    def target_label(self):
        """Return the target label for the portlet."""
        if IDistributionSourcePackage.providedBy(self.context):
            return "To all bugs in %s" % self.context.displayname
        else:
            return "To all %s bugs" % self.context.title

    @property
    def parent_target_label(self):
        """Return the target label for the portlet."""
        return (
            "To all %s bugs" % self.context.parent_subscription_target.title)
