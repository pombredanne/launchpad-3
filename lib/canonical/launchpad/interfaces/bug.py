# arch-tag: 2C926820-E0AE-11D8-A7D9-000D9329A36C

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('malone')
from zope.interface import Interface, Attribute

from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, TextLine
from zope.app.form.browser.interfaces import IAddFormCustomization

from canonical.lp import dbschema

# Vocabularies
SubscriptionVocabulary = dbschema.vocabulary(dbschema.BugSubscription)
InfestationVocabulary = dbschema.vocabulary(dbschema.BugInfestationStatus)
BugStatusVocabulary = dbschema.vocabulary(dbschema.BugAssignmentStatus)
BugPriorityVocabulary = dbschema.vocabulary(dbschema.BugPriority)
BugSeverityVocabulary = dbschema.vocabulary(dbschema.BugSeverity)
BugRefVocabulary = dbschema.vocabulary(dbschema.BugExternalReferenceType)
#RemoteBugStatusVocabulary = dbschema.vocabulary(dbschema.RemoteBugStatus)


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
            'SQLObject.Multijoin of ISourcepackageBugAssignment'
            )
    productinfestations = Attribute('List of product release infestations.')
    packageinfestations = Attribute('List of package release infestations.')
    watches = Attribute('SQLObject.Multijoin of IBugWatch')
    externalrefs = Attribute('SQLObject.Multijoin of IBugExternalRef')
    subscriptions = Attribute('SQLObject.Multijoin of IBugSubscription')

    url = Attribute('Generated URL based on data and reference type')


class IBugTrackerSet(Interface):
    """An interface for the BugTrackerSet. This models a set of BugTracker's
    (either the full set in the db or a subset). Each BugTracker is a
    distinct instance of a bug tracking tool. For example,
    bugzilla.mozilla.org is distinct from bugzilla.gnome.org.
    """
    def __getitem__(name):
        """Get a BugTracker by its name in the database. NB! We do not want to
        expose the BugTracker.id to the world so we use its name.
        """

    def __iter__():
        """Iterate through BugTrackers."""


class IBugAttachment(Interface):
    """A file attachment to an IBugMessage."""

    id = Int(
            title=_('ID'), required=True, readonly=True,
            )
    bugmessageID = Int(
            title=_('Bug Message ID'), required=True, readonly=True,
            )
    bugmessage = Attribute('Bug Message')
    name = TextLine(
            title=_('Name'), required=False, readonly=False,
            )
    description = Text(
            title=_('Description'), required=True, readonly=False,
            )
    libraryfile = Int(
            title=_('Library File'), required=True, readonly=False,
            )
    datedeactivated = Datetime(
            title=_('Date deactivated'), required=False, readonly=False,
            )

class IMaloneApplication(Interface):
    """Malone application class."""

class IMaloneBug(IBug, IAddFormCustomization):
    pass

class IMaloneBugAttachment(IBugAttachment, IAddFormCustomization):
    pass

# Interfaces for containers

class IBugContainer(IAddFormCustomization):
    """A container for bugs."""

    def __getitem__(key):
        """Get a Bug."""

    def __iter__():
        """Iterate through Bugs."""

class IBugAttachmentContainer(IAddFormCustomization):
    """A container for IBugAttachment objects."""

    bug = Int(title=_("Bug id"), readonly=True)

    def __getitem__(key):
        """Get an Attachment."""

    def __iter__():
        """Iterate through BugAttachments for a given bug."""

class IBugExternalRefContainer(Interface):
    """A container for IBugExternalRef objects."""

    bug = Int(title=_("Bug id"), readonly=True)

    def __getitem__(key):
        """Get a BugExternalRef."""

    def __iter__():
        """Iterate through BugExternalRefs for a given bug."""

class IProductBugAssignmentContainer(Interface):
    """A container for IProductBugAssignment objects."""

    bug = Int(title=_("Bug id"), readonly=True)

    def __getitem__(key):
        """Get a ProductBugAssignment"""

    def __iter__():
        """Iterate through ProductBugAssignments for a given bug."""

class ISourcepackageBugAssignmentContainer(Interface):
    """A container for ISourcepackageBugAssignment objects."""

    bug = Int(title=_("Bug id"), readonly=True)

    def __getitem__(key):
        """Get a SourcepackageBugAssignment"""

    def __iter__():
        """Iterate through SourcepackageBugAssignments for a given bug."""

class IBugProductInfestationContainer(Interface):
    """A container for IBugProductInfestations."""

    bug = Int(title=_("Bug id"), readonly=True)

    def __getitem__(key):
        """Get a BugProductInfestation."""

    def __iter__():
        """Iterate through BugProductInfestations for a given bug."""

class IBugPackageInfestationContainer(Interface):
    """A container for IBugPackageInfestations."""

    bug = Int(title=_("Bug id"), readonly=True)

    def __getitem__(key):
        """Get a BugPackageInfestation."""

    def __iter__():
        """Iterate through BugPackageInfestations for a given bug."""

class IBugWatchContainer(Interface):
    """A container for IBugWatch objects."""

    bug = Int(title=_("Bug id"), readonly=True)

    def __getitem__(key):
        """Get a BugWatch"""

    def __iter__():
        """Iterate through BugWatches for a given bug."""

class ISourcepackageContainer(Interface):
    """A container for ISourcepackage objects."""

    def __getitem__(key):
        """Get an ISourcepackage by name"""

    def __iter__():
        """Iterate through Sourcepackages."""

    def bugassignments(self, orderby='-id'):
        """Sequence of SourcepackageBugAssignment, in order"""

    def withBugs(self):
        """Return a sequence of Sourcepackage, that have bugs assigned to
        them. In future, we might pass qualifiers to further limit the list
        that is returned, such as a name filter."""

class IBugSubscriptionContainer(Interface):
    """A container for IBugSubscription objects."""

    bug = Int(title=_("Bug id"), readonly=True)

    def __getitem__(key):
        """Get a BugSubscription object."""

    def __iter__():
        """Iterate through bug subscribers for this bug."""

    def delete(id):
        """Delete a subscription."""

class IBugMessagesView(IAddFormCustomization):
    """BugMessage views"""

class IBugExternalRefsView(IAddFormCustomization):
    """BugExternalRef views"""

class IBugActivity(Interface):
    """A log of all things that have happened to a bug."""

    bug = Int(title=_('Bug ID'))
    datechanged = Datetime(title=_('Date Changed'))
    person = Int(title=_('Person'))
    whatchanged = TextLine(title=_('What Changed'))
    oldvalue = TextLine(title=_('Old Value'))
    newvalue = TextLine(title=_('New Value'))
    message = Text(title=_('Message'))

class IBugExternalRef(Interface):
    """An external reference for a bug, not supported remote bug systems."""

    id = Int(
            title=_('ID'), required=True, readonly=True
            )
    bug = Int(
            title=_('Bug ID'), required=True, readonly=True,
            )
    bugreftype = Choice(
            title=_('Bug Ref Type'), required=True, readonly=False,
            vocabulary=BugRefVocabulary
            )
    data = TextLine(
            title=_('Data'), required=True, readonly=False,
            )
    description = Text(
            title=_('Description'), required=True, readonly=False,
            )
    datecreated = Datetime(
            title=_('Date Created'), required=True, readonly=True,
            )
    owner = Int(
            title=_('Owner'), required=False, readonly=True,
            )

    def url():
        """Return the url of the external resource."""

class IBugMessage(Interface):
    """A message about a bug."""

    id = Int(
            title=_('ID'), required=True, readonly=True,
            )
    bug = Int(
            title=_('Bug ID'), required=True, readonly=True,
            )
    datecreated = Datetime(
            title=_('Date Created'), required=True, readonly=True,
            )
    title = TextLine(
            title=_('Title'), required=True, readonly=True,
            )
    contents = Text(
            title=_('Contents'), required=True, readonly=True,
            )
    personmsg = Int(
            title=_('Person'), required=False, readonly=True,
            )
    parent = Int(
            title=_('Parent'), required=False, readonly=True,
            )
    distribution = Int(
            title=_('Distribution'), required=False, readonly=True,
            )
    rfc822msgid = TextLine(
            title=_('RFC822 Msg ID'), required=True, readonly=True,
            )
    attachments = Attribute('Bug Attachments')

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
            vocabulary=SubscriptionVocabulary
            )
class IProductBugAssignment(Interface):
    """The status of a bug with regard to a product."""

    id = Int(title=_('ID'), required=True, readonly=True)
    bug = Int(title=_('Bug ID'), required=True, readonly=True)
    product = Choice(
            title=_('Product'), required=True,
            vocabulary='Product'
            )
    bugstatus = Choice(title=_('Bug Status'),
                       vocabulary=BugStatusVocabulary)
    priority = Choice(title=_('Priority'),
                      vocabulary=BugPriorityVocabulary)
    severity = Choice(title=_('Severity'),
                      vocabulary=BugSeverityVocabulary)
    assignee = Choice(title=_('Assignee'), required=False, vocabulary='Person')

class ISourcepackageBugAssignment(Interface):
    """The status of a bug with regard to a source package."""

    id = Int(title=_('ID'), required=True, readonly=True)
    bug = Int(title=_('Bug ID'), required=True, readonly=True)
    sourcepackage = Choice(
            title=_('Source Package'), required=True, readonly=True,
            vocabulary='Sourcepackage'
            )
    bugstatus = Choice(
            title=_('Bug Status'), vocabulary=BugStatusVocabulary,
            required=True, default=int(dbschema.BugAssignmentStatus.NEW),
            )
    priority = Choice(
            title=_('Priority'), vocabulary=BugPriorityVocabulary,
            required=True, default=int(dbschema.BugPriority.MEDIUM),
            )
    severity = Choice(
            title=_('Severity'), vocabulary=BugSeverityVocabulary,
            required=True, default=int(dbschema.BugSeverity.NORMAL),
            )
    binarypackagename = Choice(
            title=_('Binary PackageName'), required=False,
            vocabulary='BinarypackageName'
            )
    assignee = Choice(title=_('Assignee'), required=False, vocabulary='Person')

class IBugProductInfestation(Interface):
    """A bug that shows up in a product release as a result of having
    first been reported in a code release from which the product release
    was derived."""

    id = Int(title=_("Bug Product Infestation ID"), required=True, readonly=True)
    bug = Int(title=_('Bug ID'))
    explicit = Bool(title=_('Explicitly Created by a Human'))
    productrelease = Choice(title=_('Product Release'),
                            vocabulary='ProductRelease')
    infestation = Choice(title=_('Infestation'),
                         vocabulary=InfestationVocabulary)
    datecreated = Datetime(title=_('Date Created'))
    creator = Int(title=_('Creator'))
    dateverified = Datetime(title=_('Date Verified'))
    verifiedby = Int(title=_('Verified By'))
    lastmodified = Datetime(title=_('Last Modified'))
    lastmodifiedby = Int(title=_('Last Modified By'))

class IBugPackageInfestation(Interface):
    """A bug that shows up in a source package release as a result of
    having first been reported in a code release from which the
    source package release was derived."""

    bug = Int(title=_('Bug ID'))
    sourcepackagerelease = Int(title=_('Source Package Release'))
    explicit = Bool(title=_('Explicitly Created by a Human'))
    infestation = Choice(title=_('Infestation'),
                         vocabulary=InfestationVocabulary)
    datecreated = Datetime(title=_('Date Created'))
    creator = Int(title=_('Creator'))
    dateverified = Datetime(title=_('Date Verified'))
    verifiedby = Int(title=_('Verified By'))
    lastmodified = Datetime(title=_('Last Modified'))
    lastmodifiedby = Int(title=_('Last Modified By'))

class IBugTrackerType(Interface):
    """A type of supported remote bug system, eg Bugzilla."""

    id = Int(title=_('ID'))
    name = TextLine(title=_('Name'))
    title = TextLine(title=_('Title'))
    description = Text(title=_('Description'))
    homepage = TextLine(title=_('Homepage'))
    owner = Int(title=_('Owner'))

class IBugTracker(Interface):
    """A remote a bug system."""

    id = Int(title=_('ID'))
    bugtrackertype = Int(title=_('Bug System Type'))
    name = TextLine(title=_('Name'))
    title = TextLine(title=_('Title'))
    shortdesc = Text(title=_('Short Description'))
    baseurl = TextLine(title=_('Base URL'))
    owner = Int(title=_('Owner'))
    contactdetails = Text(title=_('Contact details'))

class IBugWatch(Interface):
    """A bug on a remote system."""

    id = Int(title=_('ID'), required=True, readonly=True)
    bug = Int(title=_('Bug ID'), required=True, readonly=True)
    bugtracker = Choice(title=_('Bug System'), required=True,
            vocabulary='BugTracker')
    remotebug = TextLine(title=_('Remote Bug'), required=True, readonly=False)
    # TODO: default should be NULL, but column is NOT NULL
    remotestatus = TextLine(
            title=_('Remote Status'), required=True, readonly=True, default=u''
            )
    lastchanged = Datetime(
            title=_('Last Changed'), required=True, readonly=True
            )
    lastchecked = Datetime(
            title=_('Last Checked'), required=True, readonly=True
            )
    datecreated = Datetime(
            title=_('Date Created'), required=True, readonly=True
            )
    owner = Int(
            title=_('Owner'), required=True, readonly=True
            )

class IBugProductRelationship(Interface):
    """A relationship between a Product and a Bug."""

    bug = Int(title=_('Bug'))
    product = Int(title=_('Product'))
    bugstatus = Int(title=_('Bug Status'))
    priority = Int(title=_('Priority'))
    severity = Int(title=_('Severity'))


#
# Bug Report Objects
#


class IBugsAssignedReport(Interface):

    user = Attribute("The user for whom this report will be generated")

    def directAssignments():
        """An iterator over the bugs directly assigned to the person."""

    def sourcepackageAssignments():
        """An iterator over bugs assigned to the person's source
        packages."""


    
