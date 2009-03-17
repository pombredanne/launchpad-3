# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Browser views related to archive subscriptions."""

__metaclass__ = type

__all__ = [
    'ArchiveSubscribersView',
    'PersonArchiveSubscriptionsView',
    ]

import datetime

import pytz

from sqlobject import SQLObjectNotFound

from zope.app.form import CustomWidgetFactory
from zope.app.form.browser import TextWidget
from zope.component import getUtility
from zope.formlib import form

from canonical.cachedproperty import cachedproperty
from canonical.launchpad.browser.archive import ArchiveViewBase
from canonical.launchpad.interfaces.archive import IArchiveSet
from canonical.launchpad.interfaces.archivesubscriber import (
    IArchiveSubscriberUI, IArchiveSubscriberSet)
from canonical.launchpad.webapp.launchpadform import (
    action, custom_widget, LaunchpadFormView, LaunchpadEditFormView)
from canonical.launchpad.webapp.menu import structured
from canonical.launchpad.webapp.publisher import (
    canonical_url, LaunchpadView)
from canonical.widgets import DateWidget


class ArchiveSubscribersView(ArchiveViewBase, LaunchpadFormView):
    """A view for listing and creating archive subscribers."""

    schema = IArchiveSubscriberUI
    field_names = ['subscriber', 'date_expires', 'description']
    custom_widget('description', TextWidget, displayWidth=40)
    custom_widget('date_expires', CustomWidgetFactory(DateWidget))

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
            if date_expires < datetime.date.today():
                self.setFieldError('date_expires',
                    "The expiry date must be in the future.")

    @action(u"Add", name="add",
            validator="validate_new_subscription")
    def create_subscription(self, action, data):
        """Create a subscription for the supplied user."""
        # As we present a date selection to the user for expiry, we
        # need to convert the value into a datetime with UTC:
        date_expires = data['date_expires']
        if date_expires:
            date_expires = datetime.datetime(
                date_expires.year,
                date_expires.month,
                date_expires.day,
                tzinfo=pytz.timezone('UTC'))
        self.context.newSubscription(
            data['subscriber'],
            self.user,
            description=data['description'],
            date_expires=date_expires)

        notification = "%s has been added as a subscriber." % (
            data['subscriber'].displayname)
        self.request.response.addNotification(structured(notification))

        # Just ensure a redirect happens (back to ourselves).
        self.next_url = str(self.request.URL)

class ArchiveSubscriptionEditView(LaunchpadEditFormView):
    """A view for editing and canceling an archive subscriber."""

    schema = IArchiveSubscriberUI
    field_names = ['date_expires', 'description']
    custom_widget('description', TextWidget, displayWidth=40)
    custom_widget('date_expires', CustomWidgetFactory(DateWidget))

    def validate_update_subscription(self, action, data):
        """Ensure that the date of expiry is not in the past."""
        form.getWidgetsData(self.widgets, 'field', data)
        date_expires = data.get('date_expires')

        if date_expires:
            if date_expires < datetime.date.today():
                self.setFieldError('date_expires',
                    "The expiry date must be in the future.")

    @action(
        u'Update', name='update', validator="validate_update_subscription")
    def update_subscription(self, action, data):
        """Update the context subscription with the new data."""
        # As we present a date selection to the user for expiry, we
        # need to convert the value into a datetime with UTC:
        date_expires = data['date_expires']

        if date_expires:
            data['date_expires'] = datetime.datetime(
                date_expires.year,
                date_expires.month,
                date_expires.day,
                tzinfo=pytz.timezone('UTC'))

        self.updateContextFromData(data)

        notification = "The subscription for %s has been updated." % (
            self.context.subscriber.displayname)
        self.request.response.addNotification(structured(notification))

        # Redirect back to the subscriptions page.
        # Note to reviewer: is there a better way to do this??
        self.next_url = canonical_url(self.context.archive) + (
            "/+subscriptions")

    @action(u'Cancel subscription', name='cancel')
    def cancel_subscription(self, action, data):
        """Cancel the context subscription."""
        self.context.cancel(self.user)

        notification = "The subscription for %s has been canceled." % (
            self.context.subscriber.displayname)
        self.request.response.addNotification(structured(notification))

        # Redirect back to the subscriptions page.
        # Note to reviewer: is there a better way to do this??
        self.next_url = canonical_url(self.context.archive) + (
            "/+subscriptions")

class PersonArchiveSubscriptionsView(LaunchpadView):
    """A view for managing a persons archive subscriptions."""

    def initialize(self):
        """Check for any POSTed subscription activations."""
        super(PersonArchiveSubscriptionsView, self).initialize()

        if self.request.method == "POST":
            self.processSubscriptionActivation()

    @cachedproperty
    def subscriptions_with_tokens(self):
        """Return all the persons archive subscriptions with the token
        for each.

        The result is formatted as a list of dicts to make the TALS code
        cleaner.
        """
        subscriber_set = getUtility(IArchiveSubscriberSet)
        subs_with_tokens = subscriber_set.getBySubscriberWithActiveToken(
            self.context)

        # Turn the result set into a list of dicts so it can be easily
        # accessed in TAL:
        return [
            {"subscription": subscription, "token": token}
                for subscription, token in subs_with_tokens]

    @cachedproperty
    def active_subscriptions_with_tokens(self):
        """Return the active subscriptions, each with it's token.

        The result is formatted as a list of dicts to make the TALS code
        cleaner.
        """
        return [
            subs_with_token
                for subs_with_token in self.subscriptions_with_tokens
                    if subs_with_token["token"] is not None]

    @cachedproperty
    def pending_subscriptions(self):
        """Return the pending subscriptions for this user.

        This is all subscriptions for the user, for which they do not have
        an active token.
        """
        return [
            subs_with_token["subscription"]
                for subs_with_token in self.subscriptions_with_tokens
                    if subs_with_token["token"] is None]

    @property
    def private_ppa_sources_list(self):
        """Return all the private ppa sources.list entries as a string."""
        sources_list_text = "# Personal subscriptions for private PPAs\n\n"
        active_sources_entries = []
        for subs_with_token in self.active_subscriptions_with_tokens:
            subscription = subs_with_token['subscription']
            token = subs_with_token['token']
            archive = subscription.archive
            series_name = archive.distribution.currentseries.name
            active_sources_entries.append(
                "# %(title)s\n"
                "deb %(archive_url)s %(series_name)s main\n"
                "deb-src %(archive_url)s %(series_name)s main\n" % {
                    'title': archive.title,
                    'archive_url': token.archive_url,
                    'series_name': series_name})

        sources_list_text += "\n".join(active_sources_entries)
        return sources_list_text

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
                "Please update your custom sources.list as "
                "described below." % archive.title))
            redirectToSelf()
