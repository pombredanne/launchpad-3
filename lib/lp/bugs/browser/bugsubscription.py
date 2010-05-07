# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Views for BugSubscription."""

__metaclass__ = type
__all__ = [
    'BugPortletDuplicateSubcribersContents',
    'BugPortletSubcribersContents',
    'BugSubscriptionAddView',
    ]

from simplejson import dumps

from lazr.delegates import delegates

from lp.bugs.browser.bug import BugViewMixin
from lp.bugs.interfaces.bugsubscription import IBugSubscription
from canonical.launchpad.webapp import (
    action, canonical_url, LaunchpadFormView, LaunchpadView)
from canonical.launchpad.webapp.authorization import check_permission


class BugSubscriptionAddView(LaunchpadFormView):
    """Browser view class for subscribing someone else to a bug."""

    schema = IBugSubscription

    field_names = ['person']

    def setUpFields(self):
        """Set up 'person' as an input field."""
        super(BugSubscriptionAddView, self).setUpFields()
        self.form_fields['person'].for_input = True

    @action('Subscribe user', name='add')
    def add_action(self, action, data):
        person = data['person']
        self.context.bug.subscribe(person, self.user, suppress_notify=False)
        if person.isTeam():
            message = '%s team has been subscribed to this bug.'
        else:
            message = '%s has been subscribed to this bug.'
        self.request.response.addInfoNotification(message %
                                                  person.displayname)

    @property
    def next_url(self):
        return canonical_url(self.context)

    cancel_url = next_url

    @property
    def label(self):
        return 'Subscribe someone else to bug #%i' % self.context.bug.id

    page_title = label


class BugPortletSubcribersContents(LaunchpadView, BugViewMixin):
    """View for the contents for the subscribers portlet."""

    @property
    def sorted_direct_subscriptions(self):
        """Get the list of direct subscriptions to the bug.

        The list is sorted such that subscriptions you can unsubscribe appear
        before all other subscriptions.
        """
        direct_subscriptions = [
            SubscriptionAttrDecorator(subscription)
            for subscription in self.context.getDirectSubscriptions()]
        can_unsubscribe = []
        cannot_unsubscribe = []
        for subscription in direct_subscriptions:
            if not check_permission('launchpad.View', subscription.person):
                continue
            if subscription.person == self.user:
                can_unsubscribe = [subscription] + can_unsubscribe
            elif subscription.canBeUnsubscribedByUser(self.user):
                can_unsubscribe.append(subscription)
            else:
                cannot_unsubscribe.append(subscription)
        return can_unsubscribe + cannot_unsubscribe


class BugPortletDuplicateSubcribersContents(LaunchpadView, BugViewMixin):
    """View for the contents for the subscribers-from-dupes portlet block."""

    @property
    def sorted_subscriptions_from_dupes(self):
        """Get the list of subscriptions to duplicates of this bug."""
        return [
            SubscriptionAttrDecorator(subscription)
            for subscription in self.context.getSubscriptionsFromDuplicates()]


class BugPortletSubcribersIds(LaunchpadView, BugViewMixin):
    """A view that returns a JSON dump of the subscriber IDs for a bug."""

    @property
    def subscriber_ids_js(self):
        """Return subscriber_ids in a form suitable for JavaScript use."""
        return dumps(self.subscriber_ids)

    def render(self):
        """Override the default render() to return only JSON."""
        return self.subscriber_ids_js


class SubscriptionAttrDecorator:
    """A BugSubscription with added attributes for HTML/JS."""
    delegates(IBugSubscription, 'subscription')

    def __init__(self, subscription):
        self.subscription = subscription

    @property
    def css_name(self):
        return 'subscriber-%s' % self.subscription.person.id
