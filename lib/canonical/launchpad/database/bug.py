"""Launchpad Bug-related Database Table Objects

Part of the Launchpad system.

(c) 2004 Canonical, Ltd.
"""

from datetime import datetime
from email.Utils import make_msgid

from zope.interface import implements

from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.launchpad.interfaces import IBug, IBugAddForm, IBugSet, \
    IBugTask

from canonical.database.sqlbase import SQLBase
from canonical.database.constants import nowUTC, DEFAULT

from canonical.launchpad.database.bugset import BugSetBase
from canonical.launchpad.database.sourcepackage import SourcePackage
from canonical.launchpad.database.message import Message, MessageSet
from canonical.launchpad.database.bugmessage import BugMessage
from canonical.launchpad.database.product import Product
from canonical.launchpad.database.bugsubscription import BugSubscription
from canonical.lp.dbschema import BugSubscription as BugSubscriptionVocab
from canonical.lp import dbschema

class Bug(SQLBase):
    """A bug."""

    implements(IBug)

    _defaultOrder = '-id'

    # db field names
    name = StringCol(unique=True, default=None)
    title = StringCol(notNull=True)
    shortdesc = StringCol(notNull=False, default=None)
    description = StringCol(notNull=False,
                            default=None)
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)
    duplicateof = ForeignKey(dbName='duplicateof', foreignKey='Bug', default=None)
    datecreated = DateTimeCol(notNull=True, default=nowUTC)
    communityscore = IntCol(dbName='communityscore', notNull=True, default=0)
    communitytimestamp = DateTimeCol(dbName='communitytimestamp',
                                     notNull=True, default=DEFAULT)
    hits = IntCol(dbName='hits', notNull=True, default=0)
    hitstimestamp = DateTimeCol(dbName='hitstimestamp', notNull=True,
                                default=DEFAULT)
    activityscore = IntCol(dbName='activityscore', notNull=True, default=0)
    activitytimestamp = DateTimeCol(dbName='activitytimestamp', notNull=True,
                                    default=DEFAULT)
    
    # useful Joins
    activity = MultipleJoin('BugActivity', joinColumn='bug')
    messages = RelatedJoin('Message', joinColumn='bug',
                           otherColumn='message',
                           intermediateTable='BugMessage')
    tasks = MultipleJoin('BugTask', joinColumn='bug')
    productassignments = MultipleJoin('BugTask', joinColumn='bug')
    packageassignments = MultipleJoin('BugTask', joinColumn='bug')
    productinfestations = MultipleJoin('BugProductInfestation', joinColumn='bug')
    packageinfestations = MultipleJoin('BugPackageInfestation', joinColumn='bug')
    watches = MultipleJoin('BugWatch', joinColumn='bug')
    externalrefs = MultipleJoin('BugExternalRef', joinColumn='bug')
    cverefs = MultipleJoin('CVERef', joinColumn='bug')
    subscriptions = MultipleJoin('BugSubscription', joinColumn='bug')

def BugFactory(*args, **kw):
    """Create a bug from an IBugAddForm. Note some unusual behaviour in this
    Factory:
    
      - the Summary and Description are not normally passed, we generally
        like to create bugs with just a title and a first comment, and let
        expert users create the summary and description if needed.
      - if a Description is passed without a Summary, then the summary will
        be the first sentence of the description.
      - it is an error to pass neither a product nor a package.
    """

    # make sure that the factory has been passed enough information
    if not (kw.get('distribution') or kw.get('product')):
        raise ValueError, 'Must pass BugFactory a distro or a product'
    if not (kw.get('comment', None) or kw.get('description', None)):
        raise ValueError, 'Must pass BugFactory a comment or description'
    
    description = kw.get('description', None)
    summary = kw.get('shortdesc', None)
    if description and not summary:
        summary = description.split('. ')[0]
    datecreated = kw.get('datecreated', datetime.now())
    bug = Bug(
        title = kw['title'],
        shortdesc = summary,
        description = description,
        owner = kw['owner'],
        datecreated=datecreated)

    # create the bug comment if one was given
    if kw.get('comment', None):
        if not kw.get('rfc822msgid', None):
            kw['rfc822msgid'] = make_msgid('malonedeb')
        try:
            msg = MessageSet().get(rfc822msgid=kw['rfc822msgid'])
        except IndexError:
            msg = Message(title=kw['title'],
                contents = kw['comment'],
                distribution = kw.get('distribution', None),
                rfc822msgid = kw['rfc822msgid'],
                owner = kw['owner']
                )
        bugmsg = BugMessage(bugID=bug.id,
                            messageID=msg.id)


    # create the task on a product if one was passed
    if kw.get('product', None):
        BugTask(
            bug = bug,
            product = kw['product'].id,
            owner = kw['owner'].id)

    # create the task on a source package name if one was passed
    if kw.get('distribution', None):
        BugTask(
            bug = bug,
            distribution = kw['distribution'],
            sourcepackagename = kw['sourcepackagename'],
            binarypackagename = kw.get('binarypackagename', None),
            owner = kw['owner'].id,
            )

    class BugAdded(object):
        implements(IBugAddForm)
        def __init__(self, **kw):
            for attr, val in kw.items():
                setattr(self, attr, val)

    bug_added = BugAdded(**kw)
    bug_added.id = bug.id

    return bug_added

class BugSet(BugSetBase):
    """A set for bugs."""

    implements(IBugSet)
    table = Bug

    def __getitem__(self, id):
        try:
            return self.table.select(self.table.q.id==id)[0]
        except IndexError:
            # Convert IndexError to KeyErrors to get Zope's NotFound page
            raise KeyError, id

    def __iter__(self):
        for row in self.table.select():
            yield row

class BugTask(SQLBase):
    implements(IBugTask)
    _table = "BugTask"
    _defaultOrder = "-bug"

    bug = ForeignKey(dbName='bug', foreignKey='Bug')
    product = ForeignKey(
        dbName='product', foreignKey='Product',
        notNull=False, default=None)
    sourcepackagename = ForeignKey(
        dbName='sourcepackagename', foreignKey='SourcePackageName',
        notNull=False, default=None)
    distribution = ForeignKey(
        dbName='distribution', foreignKey='Distribution',
        notNull=False, default=None)
    milestone = ForeignKey(
        dbName='milestone', foreignKey='Milestone',
        notNull=False, default=None)
    status = IntCol(
        dbName='status', notNull=True,
        default=int(dbschema.BugAssignmentStatus.NEW))
    priority = IntCol(
        dbName='priority', notNull=True,
        default=int(dbschema.BugPriority.MEDIUM))
    severity = IntCol(
        dbName='severity', notNull=True,
        default=int(dbschema.BugSeverity.NORMAL))
    binarypackagename = ForeignKey(
        dbName='binarypackagename', foreignKey='BinaryPackageName',
        notNull=False, default=None)
    assignee = ForeignKey(
        dbName='assignee', foreignKey='Person',
        notNull=False, default=None)
    dateassigned = DateTimeCol(notNull=False, default=nowUTC)
    datecreated  = DateTimeCol(notNull=False, default=nowUTC)
    owner = ForeignKey(
        foreignKey='Person', dbName='owner', notNull=False, default=None)

    def bugtitle(self):
        return self.bug.title

    def maintainer(self):
        # XXX: Brad Bollenbach, 2005-01-06: Only implemented for upstream
        # at the moment.
        if self.product:
            if self.product.owner:
                return self.product.owner.displayname

        return "(none)"

    def bugdescription(self):
        if self.bug.messages:
            return self.bug.messages[0].contents

    maintainer = property(maintainer)
    bugtitle = property(bugtitle)
    bugdescription = property(bugdescription)
