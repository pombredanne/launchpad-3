# arch-tag: 2C926820-E0AE-11D8-A7D9-000D9329A36C

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')
from zope.interface import Interface, Attribute

from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, TextLine
from zope.schema.interfaces import IText, ITextLine
from zope.app.form.browser.interfaces import IAddFormCustomization

from canonical.launchpad.validators.name import valid_name
from canonical.launchpad.fields import Title, Summary


# CONTENT
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
            description=_("""A short and unique name for this bug. Very few
                bugs have a nickname, they are just bugs that are so
                significant that people will actually remember the
                name. Please don't set a nickname for the bug unless you
                are certain that this is the sort of bug that the entire
                community, upstream and all distro's, will phear."""),
            constraint=valid_name,
            )
    title = Title(
            title=_('Bug Title'), required=True,
            description=_("""The title of the bug should be no more than 70
            characters, and is displayed in every bug list or report. It
            should be as clear as possible in the space allotted."""),
            )
    shortdesc = Summary(
            title=_('Summary'), required=True,
            description=_("""The bug summary is a single paragraph
            description that should capture the essence of the bug, where it
            has been observed, and what triggers it."""),
            )
    description = Text(
            title=_('Description'), required=True,
            description=_("""The bug description should be a detailed
            description of this bug, including the steps required to
            reproduce the bug if it is reproducable, and the platforms on which
            it is found if it is platform specific.""")
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
    productassignment = Attribute('SQLObject.Multijoin of IProductBugAssigment')
    packageassignment = Attribute(
            'SQLObject.Multijoin of ISourcePackageBugAssignment'
            )
    productinfestations = Attribute('List of product release infestations.')
    packageinfestations = Attribute('List of package release infestations.')
    watches = Attribute('SQLObject.Multijoin of IBugWatch')
    externalrefs = Attribute('SQLObject.Multijoin of IBugExternalRef')
    subscriptions = Attribute('SQLObject.Multijoin of IBugSubscription')

# XXX Mark Shuttleworth comments: we can probably get rid of this and
# consolidate around IBug
class IMaloneBug(IBug, IAddFormCustomization):
    pass


class IBugAddForm(IMaloneBug):
    """Information we need to create a bug"""
    id = Int(title=_("Bug #"), required=False)
    product = Choice(
            title=_("Product"), required=False,
            vocabulary="Product",
            )
    sourcepackage = Choice(
            title=_("Source Package"), required=False,
            description=_("""The distro package in which this bug exists and
            needs to be fixed. Bugs might be related to distribution
            packaging of the upstream software, or they might be upstream
            bugs that affect that source package."""),
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

