from zope.interface import Interface, Attribute
from zope.schema import Bool, Bytes, Choice, Datetime, \
    Int, Text, TextLine
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

class IBugSubscription(Interface):
    """The relationship between a person and a bug."""

    id = Int(title=_('ID'), readonly=True, required=True)
    person = Choice(
            title=_('Person ID'), required=True, vocabulary='ValidPersonOrTeam',
            readonly=True,
            )
    bug = Int(title=_('Bug ID'), required=True, readonly=True)
    subscription = Choice(
            title=_('Subscription'), required=True, readonly=False,
            description=_("""Your subscription to a bug can be one of
            "watch", "cc" or "ignore". If you "watch" a bug then it will
            show up on your reports, but you won't normally receive bug
            mail. If you "cc" yourself on a bug you will receive a copy of
            all bug update notifications by email. If you "ignore" a bug
            then you will not receive notifications from that bug even if
            they are directly addressed to you as a maintainer or assignee."""),
            vocabulary='Subscription')


class IBugSubscriptionSet(Interface):
    """A set for IBugSubscription objects."""

    title = Attribute('Title')
    bug = Attribute('the bug')

    def __getitem__(key):
        """Get a BugSubscription object."""

    def __iter__():
        """Iterate through the bug subscriptions in this set."""

    def delete(id):
        """Delete a subscription."""
