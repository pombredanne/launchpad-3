# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'BranchSubscriptionAddView',
    'BranchSubscriptionEditView'
    ]

from canonical.lp.dbschema import BranchSubscriptionNotificationLevel

from canonical.launchpad.interfaces import IBranchSubscription
from canonical.launchpad.webapp import (
    LaunchpadFormView, LaunchpadEditFormView,
    action, canonical_url, custom_widget)
from canonical.widgets import LaunchpadDropdownWidget


class _BranchSubscriptionView(LaunchpadFormView):

    """Contains the common functionality of the Add and Edit views."""
    
    schema = IBranchSubscription
    field_names = ['notification_level', 'max_diff_lines']

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
                                 notification_level, max_diff_lines):
        if notification_level in self.LEVELS_REQUIRING_LINES_SPECIFICATION:
            lines_message = '<li>%s</li>' % max_diff_lines.description
        else:
            lines_message = ''
            
        message = ('%s<ul><li>%s</li>%s</ul>' % (
                   initial, notification_level.description, lines_message))
        self.request.response.addNotification(message)

    def optional_max_diff_lines(self, notification_level, max_diff_lines):
        if notification_level in self.LEVELS_REQUIRING_LINES_SPECIFICATION:
            return max_diff_lines
        else:
            return None

class BranchSubscriptionAddView(_BranchSubscriptionView):

    @action("Subscribe")
    def subscribe(self, action, data):
        notification_level = data['notification_level']
        max_diff_lines = self.optional_max_diff_lines(
            notification_level, data['max_diff_lines'])

        self.context.subscribe(self.user, notification_level, max_diff_lines)
        
        self.add_notification_message(
            'You have subscribed to this branch with: ',
            notification_level, max_diff_lines)

    @action("Cancel")
    def cancel_edit(self, action, data):
        "Cancel the request, and take user back to branch page."
    
    
class BranchSubscriptionEditView(_BranchSubscriptionView):

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
        self.context.unsubscribe(self.user)
        self.request.response.addNotification(
            "You have unsubscribed from this branch.")
                
    @action("Change")
    def change_details(self, action, data):
        subscription = self.context.getSubscription(self.user)
        subscription.notification_level = data['notification_level']
        subscription.max_diff_lines = self.optional_max_diff_lines(
            subscription.notification_level,
            data['max_diff_lines'])
        
        self.add_notification_message(
            'Subscription updated to: ',
            subscription.notification_level,
            subscription.max_diff_lines)

    @action("Cancel")
    def cancel_edit(self, action, data):
        "Cancel the request, and take user back to branch page."
    
