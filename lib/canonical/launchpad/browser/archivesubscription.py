# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Browser views related to archive subscriptions."""

__metaclass__ = type

__all__ = [
    'ArchiveSubscribersView',
    'PersonArchiveSubscriptionsView',
    ]

import datetime

from zope.app.form.browser import TextWidget
from zope.component import getUtility
from zope.formlib import form

from canonical.cachedproperty import cachedproperty
from canonical.launchpad.browser.archive import ArchiveViewBase
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

    @property
    def subscriptions(self):
        """Return all the persons archive subscriptions."""
        # TODO: This will change to current_subscriptions
        return getUtility(IArchiveSubscriberSet).getBySubscriber(
            self.context)

    @cachedproperty
    def has_subscriptions(self):
        """Return whether this person has any subscriptions."""
        # XXX noodles 20090224 bug=246200: use bool() when it gets fixed
        # in storm.
        return self.subscriptions.count() > 0

