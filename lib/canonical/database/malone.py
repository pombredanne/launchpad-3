# Copyright 2004 Canonical Ltd
#
# arch-tag: FA3333EC-E6E6-11D8-B7FE-000D9329A36C
"""Bug tables

"""

# Zope/Python standard libraries
from datetime import datetime
from email.Utils import make_msgid
from zope.interface import implements, Interface
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('canonical')

# Zope schema imports
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, TextLine

# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE
# TODO: Move this wrapper here
from canonical.database.sqlbase import SQLBase

from canonical.lp import dbschema

# Vocabularies
SubscriptionVocabulary = dbschema.vocabulary(dbschema.BugSubscription)
InfestationVocabulary = dbschema.vocabulary(dbschema.BugInfestationStatus)
BugStatusVocabulary = dbschema.vocabulary(dbschema.BugAssignmentStatus)
BugPriorityVocabulary = dbschema.vocabulary(dbschema.BugPriority)
BugSeverityVocabulary = dbschema.vocabulary(dbschema.BugSeverity)
BugRefVocabulary = dbschema.vocabulary(dbschema.BugExternalReferenceType)

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
            title=_('Title'), required=True,
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

class Bug(SQLBase):
    """A bug."""

    implements(IBug)

    _defaultOrder = '-id'
    _columns = [
        DateTimeCol('datecreated', dbName='datecreated', notNull=True),
        StringCol('name', dbName='name', unique=True, default=None),
        StringCol('title', notNull=True),
        StringCol('shortdesc', notNull=True),
        StringCol('description', notNull=True),
        ForeignKey(
                name='owner', dbName='owner', foreignKey='Person',
                notNull=True
                ),
        ForeignKey(name='duplicateof', foreignKey='Bug', dbName='duplicateof'),
        IntCol('communityscore', notNull=True, default=0),
        DateTimeCol('communitytimestamp', notNull=True),
        IntCol('hits', notNull=True, default=0),
        DateTimeCol('hitstimestamp', notNull=True),
        IntCol('activityscore', notNull=True, default=0),
        DateTimeCol('activitytimestamp', notNull=True),
    ]

    activity = MultipleJoin('BugActivity', joinColumn='bug')
    messages = MultipleJoin('BugMessage', joinColumn='bug')
    productassignment = MultipleJoin('ProductBugAssignment', joinColumn='bug')
    sourceassignment = MultipleJoin('SourcepackageBugAssignment',
                                    joinColumn='bug')

    def _set_title(self, value):
        # Record changes of title in activity log
        # TODO: We might want a 'Bug Created' log entry
        if hasattr(self, 'id'):
            now = datetime.utcnow()
            log = BugActivity(bug=self.id,
                            datechanged=now,
                            person=1, # should be the logged in user
                            whatchanged='title',
                            oldvalue=self.title,
                            newvalue=value,
                            message='Message here')
        self._SO_set_title(value)


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

class BugAttachment(SQLBase):
    """A bug attachment."""

    implements(IBugAttachment)

    _table = 'BugAttachment'
    _columns = [
        # TODO: This should be a foreign key
        IntCol('bug'),
        #ForeignKey(name='bug', foreignKey='Bug', dbName='bug', notNull=True),
        StringCol('title', notNull=True),
        StringCol('description', notNull=True)
    ]

    versions = MultipleJoin('BugAttachmentContent', joinColumn='bugattachment')


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

class BugAttachmentContent(SQLBase):
    """The actual content of a bug attachment (versioned)."""

    implements(IBugAttachmentContent)

    _table = 'BugAttachmentContent'
    _columns = [
        ForeignKey(
                name='bugattachment', foreignKey='BugAttachment',
                dbName='bugattachment'
                ),
        DateTimeCol('daterevised', notNull=True),
        StringCol('changecomment', notNull=True),
        # TODO: Evil binary in DB goes bye-bye. Just a placeholder.
        StringCol('content', notNull=True),
        StringCol('filename', notNull=True),
        StringCol('mimetype', default=None),
        ForeignKey(
                name='owner', foreignKey='Person',
                dbName='owner', default=None
                ),
    ]


class IBugActivity(Interface):
    """A log of all things that have happened to a bug."""

    bug = Int(title=_('Bug ID'))
    datechanged = Datetime(title=_('Date Changed'))
    person = Int(title=_('Person'))
    whatchanged = TextLine(title=_('What Changed'))
    oldvalue = TextLine(title=_('Old Value'))
    newvalue = TextLine(title=_('New Value'))
    message = Text(title=_('Message'))

class BugActivity(SQLBase):
    """Bug activity log entry."""

    implements(IBugActivity)

    _table = 'BugActivity'
    _columns = [
        ForeignKey(
                name='bug', foreignKey='BugActivity',
                dbName='bug', notNull=True
                ),
        DateTimeCol('datechanged', notNull=True),
        IntCol('person', notNull=True),
        StringCol('whatchanged', notNull=True),
        StringCol('oldvalue', notNull=True),
        StringCol('newvalue', notNull=True),
        StringCol('message', default=None)
    ]

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

class BugExternalRef(SQLBase):
    """An external reference for a bug, not supported remote bug systems."""

    implements(IBugExternalRef)

    _table = 'BugExternalRef'
    _columns = [
        # TODO: Should be foreignkey
        IntCol('bug', notNull=True),
        #ForeignKey(name='bug', foreignKey='Bug', dbName='bug', notNull=True),
        IntCol('bugreftype', notNull=True),
        StringCol('data', notNull=True),
        StringCol('description', notNull=True),
        DateTimeCol('datecreated', notNull=True),
        ForeignKey(
                name='owner', foreignKey='Person', dbName='owner',
                notNull=True,
                ),
    ]

    def url(self):
        """Return the URL for this external reference.

        1: If a CVE number link to the CVE site
        2: If a URL link to that URL
        """

        if self.bugreftype == 1:
             return 'http://www.cve.mitre.org/cgi-bin/cvename.cgi?name=%s' % (
                                                                    self.data)
        else:
            return self.data


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

class BugMessage(SQLBase):
    """A message for a bug."""

    implements(IBugMessage)

    # XXX: time of datecreated is being set to midnight in forms.
    _table = 'BugMessage'
    _defaultOrder = '-id'
    _columns = [
        ForeignKey(name='bug', foreignKey='Bug', dbName='bug', notNull=True),
        DateTimeCol('datecreated', notNull=True),
        StringCol('title', notNull=True),
        StringCol('contents', notNull=True),
        ForeignKey(
                name='owner', foreignKey='Person', dbName='owner', notNull=True
                ),
        ForeignKey(
                name='parent', foreignKey='BugMessage', dbName='parent',
                notNull=True
                ),
        ForeignKey(
                name='distribution', foreignKey='Distribution',
                dbName='distribution', notNull=False, default=None
                ),
        StringCol('rfc822msgid', unique=True, notNull=True),
    ]

class IBugSubscription(Interface):
    """The relationship between a person and a bug."""

    id = Int(title=_('ID'),
             readonly=True)
    person = Int(title=_('Person ID'))
    bug = Int(title=_('Bug ID'))
    subscription = Choice(title=_('Subscription'),
                          vocabulary=SubscriptionVocabulary)

class BugSubscription(SQLBase):
    """A relationship between a person and a bug."""

    implements(IBugSubscription)

    _table='BugSubscription'
    _columns = [
        ForeignKey(
                name='person', dbName='person', foreignKey='Person',
                notNull=True
                ),
        # TODO: This Forgeign Key breaks the BugSubscriptionContainer
        # ForeignKey(name='bug', dbName='bug', foreignKey='Bug'),
        IntCol('bug'),
        #ForeignKey(name='bug', dbName='bug', foreignKey='Bug', notNull=True),
        IntCol('subscription', notNull=True)
    ]

  
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

class ProductBugAssignment(SQLBase):
    """A relationship between a Product and a Bug."""

    implements(IProductBugAssignment)

    _table = 'ProductBugAssignment'
    _columns = [
        ForeignKey(name='bug', dbName='bug', foreignKey='Bug'),
        ForeignKey(name='product', dbName='product', foreignKey='Product'),
        IntCol('bugstatus', notNull=True,
                default=int(dbschema.BugAssignmentStatus.NEW),
                ),
        IntCol('priority', notNull=True,
                default=int(dbschema.BugPriority.MEDIUM),
                ),
        IntCol('severity', notNull=True,
                default=int(dbschema.BugSeverity.NORMAL),
                )
    ]


class ISourcepackageBugAssignment(Interface):
    """The status of a bug with regard to a source package."""

    bug = Int(
            title=_('Bug ID'), required=True,
            )
    sourcepackage = Int(
            title=_('Source Package'), required=True,
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
    binarypackage = Int(title=_('Binary Package'), required=False,)

class SourcepackageBugAssignment(SQLBase):
    """A relationship between a Sourcepackage and a Bug."""

    implements(ISourcepackageBugAssignment)

    _table = 'SourcepackageBugAssignment'
    _columns = [
        ForeignKey(name='bug', dbName='bug', foreignKey='Bug'),
        ForeignKey(name='sourcepackage', dbName='sourcepackage',
                   foreignKey='Sourcepackage'),
        IntCol('bugstatus', default=int(dbschema.BugAssignmentStatus.NEW)),
        IntCol('priority', default=int(dbschema.BugPriority.MEDIUM)),
        IntCol('severity', default=int(dbschema.BugSeverity.NORMAL)),
        ForeignKey(name='binarypackage', dbName='binarypackage',
                foreignKey='Binarypackage'),
    ]

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

class IBugProductRelationship(Interface):
    """A relationship between a Product and a Bug."""

    bug = Int(title=_('Bug'))
    product = Int(title=_('Product'))
    bugstatus = Int(title=_('Bug Status'))
    priority = Int(title=_('Priority'))
    severity = Int(title=_('Severity'))


