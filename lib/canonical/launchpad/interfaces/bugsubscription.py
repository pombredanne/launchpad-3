from zope.interface import Interface
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, TextLine
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

class IBugSubscription(Interface):
    """The relationship between a person and a bug."""

    id = Int(title=_('ID'), readonly=True, required=True)
    person = Choice(
            title=_('Person ID'), required=True, vocabulary='Person',
            readonly=True,
            )
    bug = Int(title=_('Bug ID'), required=True, readonly=True)
    subscription = Choice(
            title=_('Subscription'), required=True, readonly=False,
            vocabulary='Subscription')


class IBugSubscriptionContainer(Interface):
    """A container for IBugSubscription objects."""

    bug = Int(title=_("Bug id"), readonly=True)

    def __getitem__(key):
        """Get a BugSubscription object."""

    def __iter__():
        """Iterate through bug subscribers for this bug."""

    def delete(id):
        """Delete a subscription."""

