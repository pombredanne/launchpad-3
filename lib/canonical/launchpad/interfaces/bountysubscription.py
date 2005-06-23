from zope.interface import Interface, Attribute
from zope.schema import Bool, Bytes, Choice, Datetime, \
    Int, Text, TextLine
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

class IBountySubscription(Interface):
    """The relationship between a person and a bounty."""

    id = Int(title=_('ID'), readonly=True, required=True)
    person = Choice(
            title=_('Person ID'), required=True, vocabulary='ValidPersonOrTeam',
            readonly=True,
            )
    bounty = Int(title=_('Bounty ID'), required=True, readonly=True)
    subscription = Choice(
            title=_('Subscription'), required=True, readonly=False,
            description=_("""Your subscription to a bounty can be one of
            "watch", "cc" or "none". If you "watch" a bounty then it will
            show up on your reports, but you won't normally receive bounty
            mail. If you "cc" yourself on a bounty you will receive a copy of
            all bounty update notifications by email.
            """),
            vocabulary='Subscription')


class IBountySubscriptionSet(Interface):
    """A set for IBountySubscription objects."""

    title = Attribute('Title')

    def __getitem__(key):
        """Get a BountySubscription object."""

    def __iter__():
        """Iterate over all bounty subscriptions."""

    def delete(id):
        """Delete a bounty subscription."""

