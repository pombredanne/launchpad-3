# arch-tag: 2C926820-E0AE-11D8-A7D9-000D9329A36C

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')
from zope.interface import Interface, Attribute

from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, TextLine
from zope.app.form.browser.interfaces import IAddFormCustomization



class IBug(Interface):
    """The core bug entry."""

    id = Int(
            title=_('Bug ID'), required=True, readonly=True,
            )
    datecreated = Datetime(
            title=_('Date Created'), required=True, readonly=True,
            )
    name = TextLine(
            title=_('Nickname'), required=False,
            )
    title = TextLine(
            title=_('Bug Title'), required=True,
            )
    shortdesc = Text(
            title=_('Short Description'), required=True,
            )
    description = Text(
            title=_('Description'), required=True,
            )
    ownerID = Int(
            title=_('Owner'), required=True, readonly=True
            )
    owner = Attribute("The owner's IPerson")
    duplicateof = Int(
            title=_('Duplicate Of'), required=False,
            )
    communityscore = Int(
            title=_('Community Score'), required=True, readonly=True,
            default=0,
            )
    communitytimestamp = Datetime(
            title=_('Community Timestamp'), required=True, readonly=True,
            #default=datetime.utcnow,
            )
    hits = Int(
            title=_('Hits'), required=True, readonly=True,
            default=0,
            )
    hitstimestamp = Datetime(
            title=_('Hits Timestamp'), required=True, readonly=True,
            #default=datetime.utcnow,
            )
    activityscore = Int(
            title=_('Activity Score'), required=True, readonly=True,
            default=0,
            )
    activitytimestamp = Datetime(
            title=_('Activity Timestamp'), required=True, readonly=True,
            #default=datetime.utcnow,
            )

    activity = Attribute('SQLObject.Multijoin of IBugActivity')
    messages = Attribute('SQLObject.Multijoin of IBugMessages')
    people = Attribute('SQLObject.Multijoin of IPerson')
    productassignment = Attribute('SQLObject.Multijoin of IProductBugAssigment')
    sourceassignment = Attribute(
            'SQLObject.Multijoin of ISourcePackageBugAssignment'
            )
    productinfestations = Attribute('List of product release infestations.')
    packageinfestations = Attribute('List of package release infestations.')
    watches = Attribute('SQLObject.Multijoin of IBugWatch')
    externalrefs = Attribute('SQLObject.Multijoin of IBugExternalRef')
    subscriptions = Attribute('SQLObject.Multijoin of IBugSubscription')

    url = Attribute('Generated URL based on data and reference type')

# XXX Mark Shuttleworth comments: we can probably get rid of this and
# consolidate around IBug
class IMaloneBug(IBug, IAddFormCustomization):
    pass


class IMaloneBugAddForm(IMaloneBug):
    ''' Information we need to create a bug '''
    #email = TextLine(title=_("Your Email Address"))
    product = Choice(
            title=_("Product"), required=False,
            vocabulary="Product",
            )
    sourcepackage = Choice(
            title=_("Source Package"), required=False,
            vocabulary="SourcePackage",
            )
    binarypackage = Choice(
            title=_("Binary Package"), required=False,
            vocabulary="BinaryPackage"
            )
    owner = Int(title=_("Owner"), required=True)


# Interfaces for containers

class IBugContainer(IAddFormCustomization):
    """A container for bugs."""

    def __getitem__(key):
        """Get a Bug."""

    def __iter__():
        """Iterate through Bugs."""

#
# Bug Report Objects
#


class IBugsAssignedReport(Interface):

    user = Attribute("The user for whom this report will be generated")

    def assignedBugs():
        """An iterator over ALL the bugs directly or indirectly assigned
        to the person."""
