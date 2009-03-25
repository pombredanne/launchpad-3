# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Browser views related to archive subscriptions."""

__metaclass__ = type

__all__ = [
    'ArchiveSubscribersView',
    'PersonArchiveSubscriptionsView',
    'traverse_archive_subscription_for_subscriber'
    ]

import datetime

import pytz

from zope.app.form import CustomWidgetFactory
from zope.app.form.browser import TextWidget
from zope.component import getUtility
from zope.formlib import form
from zope.interface import alsoProvides
from zope.security.proxy import removeSecurityProxy

from canonical.cachedproperty import cachedproperty
from canonical.launchpad.components.decoratedresultset import (
    DecoratedResultSet)
from canonical.launchpad.interfaces.archive import IArchiveSet
from canonical.launchpad.interfaces.archiveauthtoken import (
    IArchiveAuthTokenSet)
from canonical.launchpad.interfaces.archivesubscriber import (
    IArchiveSubscriberSet, IArchiveSubscriberUI,
    IArchiveSubscriptionForOwner, IArchiveSubscriptionForSubscriber)
from canonical.launchpad.webapp.launchpadform import (
    action, custom_widget, LaunchpadFormView, LaunchpadEditFormView)
from canonical.launchpad.webapp.menu import structured
from canonical.launchpad.webapp.publisher import (
    canonical_url, LaunchpadView)
from canonical.widgets import DateWidget


def archive_subscription_ui_adapter(archive_subscription):
    """Adapt an archive subscriber to the UI interface.

    Since we are only modifying the type of fields that already exist
    on IArchiveSubscriber, we simply return the archive_subscriber record.
    """
    return archive_subscription

def archive_subscription_for_owner_adapter(archive_subscription):
    """Adapt an archive subscriber into an IArchiveSubscriptionForOwner

    Adds IArchiveSubscriptionForOwner as an interface provided by the object.
    """
    # removeSecurityProxy is required only for alsoProvides(), the proxied
    # object is still returned.
    alsoProvides(
        removeSecurityProxy(archive_subscription),
        IArchiveSubscriptionForOwner)

    return archive_subscription

def archive_subscription_for_subscriber_adapter(archive_subscription):
    """Adapt an archive subscriber into an IArchiveSubscriptionForSubscriber

    Adds IArchiveSubscriptionForSubscriber as an interface provided by the
    object.
    """
    # removeSecurityProxy is required only for alsoProvides(), the proxied
    # object is still returned.
    alsoProvides(
        removeSecurityProxy(archive_subscription),
        IArchiveSubscriptionForSubscriber)

    return archive_subscription

def traverse_archive_subscription_for_subscriber(subscriber, archive_id):
    """Return the subscription for a subscriber to an archive."""
    subscription = None
    archive = getUtility(IArchiveSet).get(archive_id)
    if archive:
        subscription = getUtility(IArchiveSubscriberSet).getBySubscriber(
            subscriber, archive=archive).first()

    return subscription


class ArchiveSubscribersView(LaunchpadFormView):
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

    @property
    def subscriptions(self):
        """Return all the subscriptions for this archive.

        A decorated result set is used to adapt the subscriptions to
        IArchiveSubscriptionForOwner so that the correct URL is used
        in templates.
        """
        result_set = getUtility(IArchiveSubscriberSet).getByArchive(
            self.context)

        def adapt_for_owner(subscription):
            return IArchiveSubscriptionForOwner(subscription)

        return DecoratedResultSet(result_set, adapt_for_owner)

    @cachedproperty
    def has_subscriptions(self):
        """Return whether this archive has any subscribers."""
        # XXX noodles 20090212 bug=246200: use bool() when it gets fixed
        # in storm.
        return getUtility(IArchiveSubscriberSet).getByArchive(
            self.context).count() > 0

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

    @action(u'Cancel subscription', name='cancel')
    def cancel_subscription(self, action, data):
        """Cancel the context subscription."""
        self.context.cancel(self.user)

        notification = "The subscription for %s has been canceled." % (
            self.context.subscriber.displayname)
        self.request.response.addNotification(structured(notification))

    @property
    def next_url(self):
        """Calculate and return the url to which we want to redirect."""
        return canonical_url(self.context.archive) + "/+subscriptions"


class PersonArchiveSubscriptionsView(LaunchpadView):
    """A view for displaying a persons archive subscriptions."""

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
        # Note to reviewer: Unsure how to best format this??
        return [
            {
                "subscription": IArchiveSubscriptionForSubscriber(
                    subscription),
                "token": token
            } for subscription, token in subs_with_tokens]


class PersonArchiveSubscriptionView(LaunchpadView):
    """Display a users archive subscription and relevant info.

    This includes the current sources.list entries (if the subscription
    has a current token), and the ability to generate and re-generate
    tokens.
    """

    def initialize(self):
        """Process any posted actions."""
        super(PersonArchiveSubscriptionView, self).initialize()

        # If an activation was requested and there isn't a currently
        # active token, then create a token, provided a notification
        # and redirect.
        if self.request.form.get('activate') and not self.active_token:
            token = self.context.archive.newAuthToken(self.context.subscriber)

            self.request.response.addNotification(structured(
                "Your personal subscription to '%s' has been confirmed. "
                "Please update your custom sources.list as "
                "described below." % self.context.archive.displayname))

            self.request.response.redirect(self.request.getURL())

        # Otherwise, if a regeneration was requested and there is an
        # active token, then cancel the old token, create a new one,
        # provide a notification and redirect.
        elif self.request.form.get('regenerate') and self.active_token:
            self.active_token.deactivate()

            token = self.context.archive.newAuthToken(self.context.subscriber)

            self.request.response.addNotification(structured(
                "Your personal subscription to '%s' has been regenerated. "
                "Please update your custom sources.list as "
                "described below." % self.context.archive.displayname))

            self.request.response.redirect(self.request.getURL())

    @cachedproperty
    def active_token(self):
        """Returns the corresponding current token for this subscription."""
        token_set = getUtility(IArchiveAuthTokenSet)
        return token_set.getActiveTokenForArchiveAndPerson(
            self.context.archive, self.context.subscriber)


    @property
    def private_ppa_sources_list(self):
        """Return the private ppa sources.list entries as a string."""

        if self.active_token is None:
            return ""

        token = self.active_token
        archive = self.context.archive
        series_name = archive.distribution.currentseries.name
        return (
            "# %(title)s\n"
            "deb %(archive_url)s %(series_name)s main\n"
            "deb-src %(archive_url)s %(series_name)s main" % {
                'title': "Personal subscription of %s to %s" % (
                    self.context.subscriber.displayname, archive.displayname),
                'archive_url': token.archive_url,
                'series_name': series_name})



