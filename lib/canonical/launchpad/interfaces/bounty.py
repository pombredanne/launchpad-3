
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from zope.interface import Interface, Attribute, classImplements

from zope.schema import Choice, Datetime, Int, Text, TextLine, Float
from zope.schema.interfaces import IText, ITextLine
from zope.app.form.browser.interfaces import IAddFormCustomization

from canonical.launchpad.fields import Summary, Title, TimeInterval
from canonical.launchpad.validators.name import valid_name
from canonical.launchpad.interfaces import IHasOwner


class IBounty(IHasOwner):
    """The core bounty description."""

    id = Int(
            title=_('Bounty ID'), required=True, readonly=True,
            )
    name = TextLine(
            title=_('Bounty name'), required=True,
            description=_("""A short and unique name for this bounty. 
                This allows us to refer to the bounty directly in a url,
                so it needs to be distinct and descriptive. For example:
                mozilla-type-ahead-find and
                postgres-smart-serial."""),
            constraint=valid_name,
            )
    title = Title(
            title=_('Bounty title'), required=True,
            description=_("""The title of the bounty should be no more than 70
            characters long, and is displayed in every list or report of bounties. It
            should be as clear as possible in the space allotted what the
            bounty is for."""),
            )
    summary = Summary(
            title=_('Summary'), required=True,
            description=_("""The bounty summary is a single paragraph
            description of the bounty. This will also be desplayed in most
            bounty listings."""),
            )
    description = Text(
            title=_('Description'), required=True,
            description=_("""The bounty description should be a detailed
            description of the bounty, aimed ad specifying the exact results
            that will be acceptable to the bounty owner and reviewer.""")
            )
    usdvalue = Float(
            title=_('Estimated USD Value'),
            required=True, description=_("""The value of this bounty, in
            USD. Note that in some cases the bounty may have been offered in
            a variety of currencies, so this USD value is an estimate based
            on recent currency rates.""")
            )
    difficulty = Int(
            title=_('Difficulty'),
            required=True, description=_("""The difficulty of this bounty,
            rated from 1 to 100 where 100 is most difficult. An example of
            an extremely difficult bounty would be something that requires
            extensive and rare knowledge, such as a kernel memory management
            subsystem.""")
            )
    duration = TimeInterval(
            title=_('Duration'),
            required=True, description=_("""The expected time required to
            complete this bounty work, given the necessary skills.""")
            )
    reviewer = Attribute('The reviewer.')
    reviewerID = Int(title=_('Reviewer'), required=True)
    datecreated = Datetime(
            title=_('Date Created'), required=True, readonly=True,
            )
    ownerID = Int(
            title=_('Owner'), required=True, readonly=True
            )
    owner = Attribute("The owner's IPerson")
    # joins
    subscriptions = Attribute('The set of subscriptions to this bounty.')
    projects = Attribute('The projects which this bounty is related to.')
    products = Attribute('The products to which this bounty is related.')
    distributions = Attribute('The distributions to which this bounty is related.')

    # subscription-related methods
    def subscribe(person, subscription):
        """Subscribe this person to the bounty, using the given level of
        subscription. Returns the BountySubscription that this would have
        created or updated."""

    def unsubscribe(person):
        """Remove this person's subscription to this bounty."""


# Interfaces for containers
class IBountySet(IAddFormCustomization):
    """A container for bounties."""

    title = Attribute('Title')

    def __getitem__(key):
        """Get a bounty."""

    def __iter__():
        """Iterate through the bounties in this set."""

