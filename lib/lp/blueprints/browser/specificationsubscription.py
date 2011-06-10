# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Views for SpecificationSubscription."""

__metaclass__ = type
__all__ = [
    'SpecificationSubscriptionAddView',
    'SpecificationSubscriptionEditView',
    ]

from simplejson import dumps
from zope.component import getUtility

from lazr.delegates import delegates

from canonical.launchpad import _
from canonical.launchpad.webapp import (
    canonical_url,
    )
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.interfaces import ILaunchBag
from canonical.launchpad.webapp.publisher import LaunchpadView
from lp.app.browser.launchpadform import (
    action,
    LaunchpadEditFormView,
    LaunchpadFormView,
    )
from lp.blueprints.interfaces.specificationsubscription import (
    ISpecificationSubscription,
    )
from lp.registry.model.person import person_sort_key
from lp.services.propertycache import cachedproperty


class SpecificationSubscriptionAddView(LaunchpadFormView):

    schema = ISpecificationSubscription
    field_names = ['person', 'essential']
    label = 'Subscribe someone else'
    for_input = True

    @action(_('Continue'), name='continue')
    def continue_action(self, action, data):
        self.context.subscribe(data['person'], self.user, data['essential'])
        self.next_url = canonical_url(self.context)

    @property
    def cancel_url(self):
        return canonical_url(self.context)


class SpecificationSubscriptionEditView(LaunchpadEditFormView):

    schema = ISpecificationSubscription
    field_names = ['essential']
    label = 'Edit subscription'

    @action(_('Change'), name='change')
    def change_action(self, action, data):
        self.updateContextFromData(data)
        self.next_url = canonical_url(self.context.specification)

    @property
    def cancel_url(self):
        return canonical_url(self.context.specification)


class SpecificationPortletSubcribersContents(LaunchpadView):
    """View for the contents for the subscribers portlet."""

    @property
    def subscription(self):
        """Return a decorated subscription with added attributes."""
        return SubscriptionAttrDecorator(self.context)

    @property
    def sorted_subscriptions(self):
        """Get the list of subscriptions to the specification.

        The list is sorted such that subscriptions you can unsubscribe appear
        before all other subscriptions.
        """
        sort_key = lambda sub: person_sort_key(sub.person)
        subscriptions = sorted(self.context.subscriptions, key=sort_key)

        can_unsubscribe = []
        cannot_unsubscribe = []
        for subscription in subscriptions:
            if not check_permission('launchpad.View', subscription.person):
                continue
            if subscription.person == self.user:
                can_unsubscribe = [subscription] + can_unsubscribe
            elif subscription.canBeUnsubscribedByUser(self.user):
                can_unsubscribe.append(subscription)
            else:
                cannot_unsubscribe.append(subscription)

        sorted_subscriptions = can_unsubscribe + cannot_unsubscribe
        return sorted_subscriptions

    @property
    def current_user_subscription_class(self):
        is_subscribed = self.context.isSubscribed(self.user)
        if is_subscribed:
            return 'subscribed-true'
        else:
            return 'subscribed-false'


class SpecificationPortletSubcribersIds(LaunchpadView):
    """A view returning a JSON dump of the subscriber IDs for a blueprint."""

    @cachedproperty
    def subscriber_ids(self):
        """Return a dictionary mapping a css_name to user name."""
        subscribers = set(self.context.subscribers)

        # The current user has to be in subscribers_id so
        # in case the id is needed for a new subscription.
        user = getUtility(ILaunchBag).user
        if user is not None:
            subscribers.add(user)

        ids = {}
        for sub in subscribers:
            ids[sub.name] = 'subscriber-%s' % sub.id
        return ids

    @property
    def subscriber_ids_js(self):
        """Return subscriber_ids in a form suitable for JavaScript use."""
        return dumps(self.subscriber_ids)

    def render(self):
        """Override the default render() to return only JSON."""
        self.request.response.setHeader('content-type', 'application/json')
        return self.subscriber_ids_js


class SubscriptionAttrDecorator:
    """A SpecificationSubscription with added attributes for HTML/JS."""
    delegates(ISpecificationSubscription, 'subscription')

    def __init__(self, subscription):
        self.subscription = subscription

    @property
    def css_name(self):
        return 'subscriber-%s' % self.subscription.person.id
