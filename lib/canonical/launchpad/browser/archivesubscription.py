# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Browser views related to archive subscriptions."""

__metaclass__ = type

__all__ = [
    'ArchiveSubscribersView',
    'PersonArchiveSubscriptionsView',
    ]

import datetime

from sqlobject import SQLObjectNotFound

from zope.app.form.browser import TextWidget
from zope.component import getUtility
from zope.formlib import form

from canonical.cachedproperty import cachedproperty
from canonical.launchpad.browser.archive import ArchiveViewBase
from canonical.launchpad.interfaces.archive import IArchiveSet
from canonical.launchpad.interfaces.archivesubscriber import (
    IArchiveSubscriber, IArchiveSubscriberSet)
from canonical.launchpad.webapp.launchpadform import (
    action, custom_widget, LaunchpadFormView)
from canonical.launchpad.webapp.menu import structured
from canonical.launchpad.webapp.publisher import (
    canonical_url, LaunchpadView)


class ArchiveSubscribersView(ArchiveViewBase, LaunchpadFormView):
    """A view for listing and creating archive subscribers."""

    schema = IArchiveSubscriber
    field_names = ['subscriber', 'date_expires', 'description']
    custom_widget('description', TextWidget, displayWidth=40)

    def initialize(self):
        """Ensure that we are dealing with a private archive."""
        # If this archive is not private, then we should not be
        # managing the subscribers.
        if not self.context.private:
            self.request.response.addNotification(structured(
                "Only private archives can have subscribers."))
            self.request.response.redirect(
                canonical_url(self.context))
            return

        super(ArchiveSubscribersView, self).initialize()

    @cachedproperty
    def subscriptions(self):
        """Return all the subscriptions for this archive."""
        return getUtility(IArchiveSubscriberSet).getByArchive(self.context)

    @cachedproperty
    def has_subscriptions(self):
        """Return whether this archive has any subscribers."""
        # XXX noodles 20090212 bug=246200: use bool() when it gets fixed
        # in storm.
        return self.subscriptions.count() > 0

    def validate_new_subscription(self, action, data):
        """Ensure the subscriber isn't already subscribed.

        Also ensures that the expiry date is in the future.
        """
        form.getWidgetsData(self.widgets, 'field', data)
        subscriber = data.get('subscriber')
        date_expires = data.get('date_expires')

        if subscriber is not None:
            subscriber_set = getUtility(IArchiveSubscriberSet)
            current_subscription = subscriber_set.getBySubscriber(
                subscriber, archive=self.context)

            # XXX noodles 20090212 bug=246200: use bool() when it gets fixed
            # in storm.
            if current_subscription.count() > 0:
                self.setFieldError('subscriber',
                    "%s is already subscribed." % subscriber.displayname)

        if date_expires:
            # date_expires includes tzinfo, and is only comparable with
            # other datetime objects that include tzinfo.
            now = datetime.datetime.now().replace(tzinfo=date_expires.tzinfo)
            if date_expires < now:
                self.setFieldError('date_expires',
                    "The expiry date must be in the future.")

    @action(u"Add", name="add",
            validator="validate_new_subscription")
    def create_subscription(self, action, data):
        """Create a subscription for the supplied user."""
        self.context.newSubscription(
            data['subscriber'],
            self.user,
            description=data['description'],
            date_expires=data['date_expires'])

        notification = "%s has been added as a subscriber." % (
            data['subscriber'].displayname)
        self.request.response.addNotification(structured(notification))

        # Just ensure a redirect happens (back to ourselves).
        self.next_url = str(self.request.URL)


class PersonArchiveSubscriptionsView(LaunchpadView):
    """A view for managing a persons archive subscriptions."""

    def initialize(self):
        """Check for any POSTed subscription activations."""
        super(PersonArchiveSubscriptionsView, self).initialize()

        if self.request.method == "POST":
            self.processSubscriptionActivation()

    @property
    def subscriptions_with_tokens(self):
        """Return all the persons archive subscriptions with the token
        for each."""
        subscriber_set = getUtility(IArchiveSubscriberSet)
        return subscriber_set.getBySubscriberWithActiveToken(
            self.context)

    @cachedproperty
    def has_subscriptions(self):
        """Return whether this person has any subscriptions."""
        # XXX noodles 20090224 bug=246200: use bool() when it gets fixed
        # in storm.
        return getUtility(
            IArchiveSubscriberSet).getBySubscriber(self.context).count() > 0

    def processSubscriptionActivation(self):
        """Process any posted data that activates a subscription."""
        # Just for clarity, define a redirectToSelf() helper.
        def redirectToSelf():
            self.request.response.redirect(self.request.getURL())

        # NOTE: as there isn't any form input to validate, but just simple
        # buttons, any bad data here should only be the result of either
        # (1) users fiddling with form post data, or (2) timing issues between
        # subscription expiries/cancellations and activations, so in all
        # cases below, we just redirect to a normal GET request in the event
        # of bad data.

        # Check first for a valid archive_id in the post data - if none
        # is found simply redirect to a normal GET request.
        archive_id = self.request.form.get('archive_id')
        if archive_id:
            try:
                archive_id = int(archive_id)
            except ValueError:
                redirectToSelf()
                return
        else:
            redirectToSelf()
            return

        # Next, try to grab the corresponding archive. Again, if none
        # is found, redirect to a normal GET request.
        try:
            archive = getUtility(IArchiveSet).get(archive_id)
        except SQLObjectNotFound:
            # Just ignore as it should only happen if the user
            # is fiddling with POST params.
            redirectToSelf()
            return

        # Grab the current user's subscriptions for this
        # particular archive, as well as any token that already
        # exists:
        subscriber_set = getUtility(IArchiveSubscriberSet)
        subscriptions_with_token = \
            subscriber_set.getBySubscriberWithActiveToken(
                self.context, archive=archive)

        if subscriptions_with_token.count() == 0:
            # The user does not have a current subscription, so no token.
            redirectToSelf()
            return

        # Note: there may be multiple subscriptions for a user (through
        # teams), but there should only ever be one token generated.
        subscription, token = subscriptions_with_token[0]
        if token is None:
            token = archive.newAuthToken(self.context)
            # Message the user and redirect:
            self.request.response.addNotification(structured(
                "Your subscription to '%s' has been activated. "
                "Please update your private_ppa_sources.list as "
                "displayed below." % archive.title))
            redirectToSelf()


