# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Bug subscription interfaces."""

__metaclass__ = type

__all__ = ['IBranchSubscription']

from zope.interface import Interface, Attribute
from zope.schema import Choice, Int
from canonical.launchpad import _

from canonical.lp.dbschema import (
    BranchSubscriptionNotificationLevel,
    BranchSubscriptionDiffSize)


class IBranchSubscription(Interface):
    """The relationship between a person and a branch."""

    person = Choice(
        title=_('Person'), required=True, vocabulary='ValidPersonOrTeam',
        readonly=True, description=_('Enter the launchpad id, or email '
        'address of the person you wish to subscribe to this branch. '
        'If you are unsure, use the "Choose..." option to find the '
        'person in Launchpad. You can only subscribe someone who is '
        'a registered user of the system.'))
    branch = Int(title=_('Branch ID'), required=True, readonly=True)
    notification_level = Choice(
        title=_('Notification Level'), required=True,
        vocabulary='BranchSubscriptionNotificationLevel',
        default=BranchSubscriptionNotificationLevel.ATTRIBUTEONLY,
        description=_(
            'Select the desired amount of email notifications.'))
    max_diff_lines = Choice(
        title=_('Generated Diff Size Limit'), required=True,
        vocabulary='BranchSubscriptionDiffSize',
        default=BranchSubscriptionDiffSize.ONEKLINES,
        description=_(
            'Diffs greater than the specified number of lines will not be '
            'sent to the subscriber.'))
