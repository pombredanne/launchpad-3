# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Bug subscription interfaces."""

__metaclass__ = type

__all__ = [
    'BranchSubscriptionDiffSize',
    'BranchSubscriptionNotificationLevel',
    'CodeReviewNotificationLevel',
    'IBranchSubscription',
    ]

from zope.interface import Interface
from zope.schema import Choice, Int
from canonical.launchpad import _
from canonical.launchpad.fields import PublicPersonChoice
from canonical.lazr import DBEnumeratedType, DBItem


class BranchSubscriptionDiffSize(DBEnumeratedType):
    """Branch Subscription Diff Size

    When getting branch revision notifications, the person can set a size
    limit of the diff to send out. If the generated diff is greater than
    the specified number of lines, then it is omitted from the email.
    This enumerated type defines the number of lines as a choice
    so we can sensibly limit the user to a number of size choices.
    """

    NODIFF = DBItem(0, """
        Don't send diffs

        Don't send generated diffs with the revision notifications.
        """)

    HALFKLINES = DBItem(500, """
        500 lines

        Limit the generated diff to 500 lines.
        """)

    ONEKLINES  = DBItem(1000, """
        1000 lines

        Limit the generated diff to 1000 lines.
        """)

    FIVEKLINES = DBItem(5000, """
        5000 lines

        Limit the generated diff to 5000 lines.
        """)

    WHOLEDIFF  = DBItem(-1, """
        Send entire diff

        Don't limit the size of the diff.
        """)


class BranchSubscriptionNotificationLevel(DBEnumeratedType):
    """Branch Subscription Notification Level

    The notification level is used to control the amount and content
    of the email notifications send with respect to modifications
    to branches whether it be to branch attributes in the UI, or
    to the contents of the branch found by the branch scanner.
    """

    NOEMAIL = DBItem(0, """
        No email

        Do not send any email about changes to this branch.
        """)

    ATTRIBUTEONLY = DBItem(1, """
        Branch attribute notifications only

        Only send notifications for branch attribute changes such
        as name, description and whiteboard.
        """)

    DIFFSONLY = DBItem(2, """
        Branch revision notifications only

        Only send notifications about new revisions added to this
        branch.
        """)

    FULL = DBItem(3, """
        Branch attribute and revision notifications

        Send notifications for both branch attribute updates
        and new revisions added to the branch.
        """)


class CodeReviewNotificationLevel(DBEnumeratedType):
    """Code Review Notification Level

    The notification level is used to control the amount and content
    of the email notifications send with respect to code reviews related
    to this branch.
    """

    NOEMAIL = DBItem(0, """
        No email

        Do not send any email about code review for this branch.
        """)

    STATUS = DBItem(1, """
        Status changes only

        Send email when votes are cast or status is changed.
        """)

    FULL = DBItem(2, """
        Email about all changes

        Send email about any code review activity for this branch.
        """)


class IBranchSubscription(Interface):
    """The relationship between a person and a branch."""

    id = Int(title=_('ID'), readonly=True, required=True)
    person = PublicPersonChoice(
        title=_('Person'), required=True, vocabulary='ValidPersonOrTeam',
        readonly=True, description=_('Enter the launchpad id, or email '
        'address of the person you wish to subscribe to this branch. '
        'If you are unsure, use the "Choose..." option to find the '
        'person in Launchpad. You can only subscribe someone who is '
        'a registered user of the system.'))
    branch = Int(title=_('Branch ID'), required=True, readonly=True)
    notification_level = Choice(
        title=_('Notification Level'), required=True,
        vocabulary=BranchSubscriptionNotificationLevel,
        default=BranchSubscriptionNotificationLevel.ATTRIBUTEONLY,
        description=_(
            'Attribute notifications are sent when branch details are changed'
            ' such as lifecycle status and name.  Revision notifications are '
            'generated when new branch revisions are found due to the branch '
            'being updated through either pushes to the hosted branches or '
            'the mirrored branches being updated.'))
    max_diff_lines = Choice(
        title=_('Generated Diff Size Limit'), required=True,
        vocabulary=BranchSubscriptionDiffSize,
        default=BranchSubscriptionDiffSize.ONEKLINES,
        description=_(
            'Diffs greater than the specified number of lines will not be '
            'sent to the subscriber.  The subscriber will still receive '
            'an email with the new revision details even if the diff '
            'is larger than the specified number of lines.'))
    review_level = Choice(
        title=_('Code review Level'), required=True,
        vocabulary=CodeReviewNotificationLevel,
        default=CodeReviewNotificationLevel.FULL,
        description=_(
            'Control the kind of review activity that triggers notifications.'
            ))

