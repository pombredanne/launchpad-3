"""Launchpad Bug-related Database Table Objects

Part of the Launchpad system.

(c) 2004 Canonical, Ltd.
"""

from datetime import datetime
from warnings import warn

from zope.interface import implements

from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.launchpad.interfaces import IBug, IBugAddForm, IBugSet, \
    IBugTask

from canonical.database.sqlbase import SQLBase
from canonical.database.constants import nowUTC, DEFAULT

from canonical.launchpad.database.bugset import BugSetBase
from canonical.launchpad.database.sourcepackage import SourcePackage
from canonical.launchpad.database.product import Product
from canonical.launchpad.database.bugsubscription import BugSubscription
from canonical.lp.dbschema import BugSubscription as BugSubscriptionVocab
from canonical.lp import dbschema

class Bug(SQLBase):
    """A bug."""

    implements(IBug)

    _defaultOrder = '-id'

    # db field names
    name = StringCol(dbName='name', unique=True, default=None)
    title = StringCol(dbName='title', notNull=True)
    shortdesc = StringCol(dbName='shortdesc', notNull=True)
    description = StringCol(dbName='description', notNull=True)
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)
    duplicateof = ForeignKey(dbName='duplicateof', foreignKey='Bug', default=None)
    datecreated = DateTimeCol(dbName='datecreated', notNull=True,
                              default=nowUTC)
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
    """Create a bug from an IBugAddForm"""
    description = kw['description']
    summary = description.split('\n')[0]
    kw['shortdesc'] = summary
    bug = Bug(
        title = kw['title'],
        shortdesc = kw['shortdesc'],
        description = kw['description'],
        owner = kw['owner'])

    if kw.get('product', None):
        BugTask(
            bug = bug, product = kw['product'].id, owner = kw['owner'].id)

    if kw.get('sourcepackagename', None):
        warn("Distribution name is hardcoded to 1")
        BugTask(
            bug = bug, sourcepackagename = kw['sourcepackagename'],
            binarypackagename = None, owner = kw['owner'].id,
            distribution = 1)

    # auto-Cc the person who submitted the bug
    BugSubscription(
        person = kw['owner'], bugID = bug.id,
        subscription = BugSubscriptionVocab.CC.value)

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
    _defaultOrder = "bug"

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

