"""Launchpad Bug-related Database Table Objects

Part of the Launchpad system.

(c) 2004 Canonical, Ltd.
"""

# Zope
from zope.interface import implements
# SQL imports
from canonical.database.sqlbase import SQLBase
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE

from canonical.launchpad.interfaces import *

class Bug(SQLBase):
    """A bug."""

    implements(IBug)

    _defaultOrder = '-id'

    datecreated = DateTimeCol(notNull=True)
    name = StringCol(unique=True, default=None)
    title = StringCol(notNull=True)
    shortdesc = StringCol(notNull=True)
    description = StringCol(notNull=True)
    owner = ForeignKey(foreignKey='Person', notNull=True, dbName='owner')
    duplicateof = ForeignKey(foreignKey='Bug', dbName='duplicateof')
    communityscore = IntCol(notNull=True, default=0)
    communitytimestamp = DateTimeCol(notNull=True)
    hits = IntCol(notNull=True, default=0)
    hitstimestamp = DateTimeCol(notNull=True)
    activityscore = IntCol(notNull=True, default=0)
    activitytimestamp = DateTimeCol(notNull = True)

    activity = MultipleJoin('BugActivity', joinColumn='bug')
    messages = MultipleJoin('BugMessage', joinColumn='bug')
    # TODO: Standardize on pluralization and naming for table relationships
    productassignment = MultipleJoin('ProductBugAssignment', joinColumn='bug')
    sourceassignment = MultipleJoin('SourcepackageBugAssignment',
                                    joinColumn='bug')
    watches = MultipleJoin('BugWatch', joinColumn='bug')
    externalrefs = MultipleJoin('BugExternalRef', joinColumn='bug')
    subscriptions = MultipleJoin('BugSubscription', joinColumn='bug')

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

    def _url(self):
        if int(self.bugreftype) == int(dbschema.BugExternalReferenceType.CVE):
            return 'http://www.cve.mitre.org/cgi-bin/cvename.cgi?name=%s' % (
                    urlquote(self.data)
                    )
        else:
            return self.data
    url = property(_url, None)

class BugAttachment(SQLBase):
    """A bug attachment."""

    implements(IBugAttachment)

    _table = 'BugAttachment'
    _columns = [
        ForeignKey(
                name='bugmessage', foreignKey='BugMessage',
                dbName='bugmessage', notNull=True,
                ),
        StringCol('name', notNull=False, default=None),
        StringCol('description', notNull=False, default=None),
        ForeignKey(
                name='libraryfile', foreignKey='LibraryFileAlias',
                dbName='libraryfile', notNull=False,
                ),
        DateTimeCol('datedeactivated', notNull=False, default=None),
    ]

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

    attachments = MultipleJoin('BugAttachment', joinColumn='bugmessage')

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

class ProductBugAssignment(SQLBase):
    """A relationship between a Product and a Bug."""

    implements(IProductBugAssignment)

    _table = 'ProductBugAssignment'

    _columns = [
        ForeignKey(name='bug', dbName='bug', foreignKey='Bug'),
        ForeignKey(name='product', dbName='product', foreignKey='Product'),
        IntCol(name='bugstatus',
            notNull=True, default=int(dbschema.BugAssignmentStatus.NEW)
            ),
        IntCol(name='priority',
            notNull=True, default=int(dbschema.BugPriority.MEDIUM),
            ),
        IntCol(name='severity',
            notNull=True, default=int(dbschema.BugSeverity.NORMAL),
            ),
        ForeignKey(name='assignee', dbName='assignee', foreignKey='Person', default=None)
        ]


class SourcepackageBugAssignment(SQLBase):
    """A relationship between a Sourcepackage and a Bug."""

    implements(ISourcepackageBugAssignment)

    _table = 'SourcepackageBugAssignment'

    _columns = [
        ForeignKey(name='bug', dbName='bug', foreignKey='Bug'),
        ForeignKey(name='sourcepackage', 
            dbName='sourcepackage', foreignKey='Sourcepackage'),
        IntCol('bugstatus', default=int(dbschema.BugAssignmentStatus.NEW)),
        IntCol('priority', default=int(dbschema.BugPriority.MEDIUM)),
        IntCol('severity', default=int(dbschema.BugSeverity.NORMAL)),
        ForeignKey(name='binarypackagename', dbName='binarypackagename',
                   foreignKey='BinarypackageName', default=None),
        ForeignKey(name='assignee', dbName='assignee',
                   foreignKey='Person', notNull=True, default=None),
        ]


class BugTrackerType(SQLBase):
    """A type of supported remote  bug system. eg Bugzilla."""

    implements(IBugTrackerType)

    _table = 'BugTrackerType'
    _columns = [
        StringCol('name', notNull=True),
        StringCol('title', notNull=True),
        StringCol('description', notNull=True),
        StringCol('homepage', notNull=True),
        ForeignKey(
                name='owner', foreignKey='Person',
                dbName='owner', default=None
                ),
    ]


class BugTracker(SQLBase):
    """A class to access the BugTracker table of the db. Each BugTracker is a
    distinct instance of that bug tracking tool. For example, each Bugzilla
    deployment is a separate BugTracker. bugzilla.mozilla.org and
    bugzilla.gnome.org are each distinct BugTracker's.
    """
    implements(IBugTracker)
    _table = 'BugTracker'
    _columns = [
        ForeignKey(name='bugtrackertype', dbName='bugtrackertype',
                foreignKey='BugTrackerType', notNull=True),
        StringCol('name', notNull=True, unique=True),
        StringCol('title', notNull=True),
        StringCol('shortdesc', notNull=True),
        StringCol('baseurl', notNull=True),
        ForeignKey(name='owner', dbName='owner', foreignKey='Person',
                notNull=True),
        StringCol('contactdetails', notNull=True),
        ]

# XXX Mark Shuttleworth 05/10/04 We are renaming BugTracker to BugTracker
BugTracker = BugTracker


class BugTrackerSet(object):
    """Implements IBugTrackerSet for a container or set of BugTracker's,
    either the full set in the db, or a subset."""

    implements(IBugTrackerSet)

    table = BugTracker
    
    def __getitem__(self, name):
        try: return self.table.select(self.table.q.name == name)[0]
        except IndexError:
            # Convert IndexError to KeyErrors to get Zope's NotFound page
            raise KeyError, id

    def __iter__(self):
        for row in self.table.select():
            yield row


class BugWatch(SQLBase):
    implements(IBugWatch)
    _table = 'BugWatch'
    _columns = [
        ForeignKey(name='bug', dbName='bug', foreignKey='Bug', notNull=True),
        ForeignKey(name='bugtracker', dbName='bugtracker',
                foreignKey='BugTracker', notNull=True),
        StringCol('remotebug', notNull=True),
        # TODO: Default should be NULL, but column is NOT NULL
        StringCol('remotestatus', notNull=True, default=''),
        DateTimeCol('lastchanged', notNull=True),
        DateTimeCol('lastchecked', notNull=True),
        DateTimeCol('datecreated', notNull=True),
        ForeignKey(name='owner', dbName='owner', foreignKey='Person',
                notNull=True),
        ]

#
# REPORTS
#

class BugsAssignedReport(object):

    implements(IBugsAssignedReport)

    def __init__(self):
        # XXX Mark Shuttleworth 06/10/04  Temp Testing Hack hardcode person
        self.user = 1
        self._table = SourcepackageBugAssignment

    def directAssignments(self):
        """An iterator over the bugs directly assigned to the person."""
        assignments = self._table.selectBy(assigneeID=self.user)
        for assignment in assignments:
            yield assignment

    def sourcepackageAssignments(self):
        """An iterator over bugs assigned to the person's source
        packages."""

