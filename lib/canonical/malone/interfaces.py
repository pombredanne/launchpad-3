# arch-tag: 2C926820-E0AE-11D8-A7D9-000D9329A36C

from zope.interface import Interface
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, TextLine
from zope.schema import Password

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('malone')

from vocabularies import SubscriptionVocabulary, InfestationVocabulary
from vocabularies import BugStatusVocabulary, BugPriorityVocabulary
from vocabularies import BugSeverityVocabulary, BugRefVocabulary

def is_allowed_filename(value):
    if '/' in value: # Path seperator
        return False
    if '\\' in value: # Path seperator
        return False
    if '?' in value: # Wildcard
        return False
    if '*' in value: # Wildcard
        return False
    if ':' in value: # Mac Path seperator, DOS drive indicator
        return False
    return True

def is_allowed_filename(value):
    if '/' in value: # Path seperator
        return False
    if '\\' in value: # Path seperator
        return False
    if '?' in value: # Wildcard
        return False
    if '*' in value: # Wildcard
        return False
    if ':' in value: # Mac Path seperator, DOS drive indicator
        return False
    return True

class IMaloneApplication(Interface):
    """Malone application class."""


# Interfaces for each table in the database

class IBug(Interface):
    """The core bug entry."""

    id = Int(
            title=_('Bug ID'), required=True, readonly=True,
            )
    datecreated = Datetime(
            title=_('Date Created'), required=True, readonly=True,
            )
    nickname = TextLine(
            title=_('Nickname'), required=False,
            )
    title = TextLine(
            title=_('Title'), required=True,
            )
    description = Text(
            title=_('Description'), required=True,
            )
    ownerID = Int(
            title=_('Owner'), required=True, readonly=True
            )
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

    def activity():
        """Return a list of IBugActivity."""

    def messages():
        """Return a list of IBugMessage"""

    def people():
        """Returns a list IPerson"""

    def productassignment():
        """Product assignments for this bug."""

    def sourceassignment():
        """Source package assignments for this bug."""

    def owner():
        """Return a Person object for the owner."""


class IBugSubscription(Interface):
    """The relationship between a person and a bug."""

    id = Int(title=_('ID'),
             readonly=True)
    person = Int(title=_('Person ID'))
    bug = Int(title=_('Bug ID'))
    subscription = Choice(title=_('Subscription'),
                          vocabulary=SubscriptionVocabulary)
 

class IBugInfestation(Interface):
    """The bug status scorecard."""

    bug = Int(title=_('Bug ID'))
    coderelease = Int(title=_('Code Release'))
    explicit = Bool(title=_('Explicitly Created by a Human'))
    infestation = Choice(title=_('Infestation'),
                         vocabulary=InfestationVocabulary)
    datecreated = Datetime(title=_('Date Created'))
    creator = Int(title=_('Creator'))
    dateverified = Datetime(title=_('Date Verified'))
    verifiedby = Int(title=_('Verified By'))
    lastmodified = Datetime(title=_('Last Modified'))
    lastmodifiedby = Int(title=_('Last Modified By'))


class ISourcepackageBugAssignment(Interface):
    """The status of a bug with regard to a source package."""

    bug = Int(title=_('Bug ID'))
    sourcepackage = Int(title=_('Source Package'))
    bugstatus = Choice(title=_('Bug Status'),
                       vocabulary=BugStatusVocabulary)
    priority = Choice(title=_('Priority'),
                      vocabulary=BugPriorityVocabulary)
    severity = Choice(title=_('Severity'),
                      vocabulary=BugSeverityVocabulary)
    binarypackage = Int(title=_('Binary Package'))


class IProductBugAssignment(Interface):
    """The status of a bug with regard to a product."""

    bug = Int(title=_('Bug ID'))
    product = Int(title=_('Product'))
    bugstatus = Choice(title=_('Bug Status'),
                       vocabulary=BugStatusVocabulary)
    priority = Choice(title=_('Priority'),
                      vocabulary=BugPriorityVocabulary)
    severity = Choice(title=_('Severity'),
                      vocabulary=BugSeverityVocabulary)


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
            title=_('Owner'), required=False, readonly=False,
            )

    def url():
        """Return the url of the external resource."""


class IBugSystemType(Interface):
    """A type of supported remote bug system, eg Bugzilla."""

    id = Int(title=_('ID'))
    name = TextLine(title=_('Name'))
    title = TextLine(title=_('Title'))
    description = Text(title=_('Description'))
    homepage = TextLine(title=_('Homepage'))
    owner = Int(title=_('Owner'))


class IBugSystem(Interface):
    """A remote a bug system."""

    id = Int(title=_('ID'))
    bugsystemtype = Int(title=_('Bug System Type'))
    name = TextLine(title=_('Name'))
    title = TextLine(title=_('Title'))
    description = Text(title=_('Description'))
    baseurl = TextLine(title=_('Base URL'))
    owner = Int(title=_('Owner'))
    

class IBugWatch(Interface):
    """A bug on a remote system."""

    id = Int(title=_('ID'))
    bug = Int(title=_('Bug ID'))
    bugsystem = Int(title=_('Bug System'))
    remotebug = Int(title=_('Remote Bug'))
    remotestatus = Int(title=_('Remote Status'))
    lastchanged = Datetime(title=_('Last Changed'))
    lastchecked = Datetime(title=_('Last Checked'))
    datecreated = Datetime(title=_('Date Created'))
    owner = Int(title=_('Owner'))


class IBugAttachment(Interface):
    """A file attachment to a bug."""

    id = Int(
            title=_('ID'), required=True, readonly=True,
            )
    bug = Int(
            title=_('Bug ID'), required=True, readonly=True,
            )
    title = TextLine(
            title=_('Title'), required=True, readonly=False,
            )
    description = Text(
            title=_('Description'), required=True, readonly=False,
            )

    def versions(self):
        """Return BugAttachmentContent for this attachment."""


class IBugAttachmentContent(Interface):
    """The actual content of a bug attachment (versioned)."""

    id = Int(
            title=_('Bug Attachment Content ID'), required=True, readonly=True,
            )
    bugattachment = Int(
            title=_('Bug Attachment ID'), required=True, readonly=True
            )
    daterevised = Datetime(
            title=_('Date Revised'), required=True, readonly=True,
            )
    changecomment = Text(
            title=_('Change Comment'), required=True, readonly=False,
            )
    # TODO: Use a file type when we can handle binarys
    content = Text(
            title=_('Content'), required=True, readonly=True,
            default=_(
                "Using textarea as placeholder as SQLObject doesn't do binarys"
                )
            )
    filename = TextLine(
            title=_('Filename'), required=True, readonly=False,
            constraint=is_allowed_filename,
            )
    mimetype = TextLine(
            title=_('MIME Type'), required=False, readonly=False,
            )
    owner = Int(
            title=_('Owner'), required=False, readonly=False,
            )


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

class IPerson(Interface):
    """A Person."""

    id = Int(
            title=_('ID'), required=True, readonly=True,
            )
    presentationname = TextLine(
            title=_('Presentation Name'), required=False, readonly=False,
            )
    givenname = TextLine(
            title=_('Given Name'), required=False, readonly=False,
            )
    familyname = TextLine(
            title=_('Family Name'), required=False, readonly=False,
            )
    password = Password(
            title=_('Password'), required=False, readonly=False,
            )
    teamowner = Int(
            title=_('Team Owner'), required=False, readonly=False,
            )
    teamdescription = TextLine(
            title=_('Team Description'), required=False, readonly=False,
            )
    # TODO: This should be required in the DB, defaulting to something
    karma = Int(
            title=_('Karma'), required=False, readonly=True,
            )
    # TODO: This should be required in the DB, defaulting to something
    karmatimestamp = Datetime(
            title=_('Karma Timestamp'), required=False, readonly=True,
            )

class IBugProductRelationship(Interface):
    """A relationship between a Product and a Bug."""

    bug = Int(title=_('Bug'))
    product = Int(title=_('Product'))
    bugstatus = Int(title=_('Bug Status'))
    priority = Int(title=_('Priority'))
    severity = Int(title=_('Severity'))

class IProduct(Interface):
    """A Product."""

    project = Int(title=_('Project'))
    owner = Int(title=_('Owner'))
    title = TextLine(title=_('Title'))
    description = Text(title=_('Description'))
    homepageurl = TextLine(title=_('Homepage URL'))
    manifest = TextLine(title=_('Manifest'))

    def bugs():
        """Return ProductBugAssignments for this Product."""


class ISourcepackage(Interface):
    """A Sourcepackage."""

    maintainer = Int(title=_('Maintainer'))
    name = TextLine(title=_('Name'))
    title = TextLine(title=_('Title'))
    description = Text(title=_('Description'))
    manifest = Int(title=_('Manifest'))


class IProject(Interface):
    """A Project."""

    id = Int(title=_('ID'))
    owner = Int(title=_('Owner'))
    name = TextLine(title=_('Name'))
    title = TextLine(title=_('Title'))
    description = Text(title=_('Description'))
    homepageurl = TextLine(title=_('Homepage URL'))

    def products():
        """Return Products for this Project."""

class IBugProductRelationship(Interface):
    """A relationship between a Product and a Bug."""

    bug = Int(title=_('Bug'))
    product = Int(title=_('Product'))
    bugstatus = Int(title=_('Bug Status'))
    priority = Int(title=_('Priority'))
    severity = Int(title=_('Severity'))


# Interfaces for containers

class IUsesAddForm(Interface):
    """Hooks required for the default Zope3 addform to work.

    nextURL() is justifiable, but we should probably customize
    the addform machinery to play nicer with sqlos and make the
    add dead-chicken unnecessary
    """
    def add(ob):
        """Add the object, if necessary. Return it."""

    def nextURL():
        """Return the URL to go to after adding"""

class IBugContainer(IUsesAddForm):
    """A container for bugs."""

    def __getitem__(key):
        """Get a Bug."""

    def __iter__():
        """Iterate through Bugs."""

class IBugAttachmentContainer(IUsesAddForm):
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


class IProjectContainer(Interface):
    """A container for IProject objects."""

    def __getitem__(key):
        """Get a Project."""

    def __iter__():
        """Iterate through Projects."""

    def search(name, title):
        """Search through Projects."""


class IBugSubscriptionContainer(Interface):
    """A container for IBugSubscription objects."""

    bug = Int(title=_("Bug id"), readonly=True)

    def __getitem__(key):
        """Get a BugSubscription object."""

    def __iter__():
        """Iterate through bug subscribers for this bug."""

    def delete(id):
        """Delete a subscription."""


class IBugMessagesView(IUsesAddForm):
    """BugMessage views"""

class IBugExternalRefsView(IUsesAddForm):
    """BugExternalRef views"""

