"""Launchpad Bug-related Database Table Objects

Part of the Launchpad system.

(c) 2004 Canonical, Ltd.
"""

from datetime import datetime

from zope.interface import implements

from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.launchpad.interfaces import IBug, IBugContainer
from canonical.launchpad.interfaces import *

from canonical.database.sqlbase import SQLBase
from canonical.database.constants import nowUTC, DEFAULT

from canonical.launchpad.database.bugcontainer import BugContainerBase
from canonical.launchpad.database.bugassignment \
        import SourcePackageBugAssignment, ProductBugAssignment
from canonical.launchpad.database.sourcepackage import SourcePackage
from canonical.launchpad.database.product import Product
from canonical.launchpad.database.bugactivity import BugActivity
from canonical.launchpad.database.bugsubscription import BugSubscription
from canonical.lp.dbschema import BugSubscription as BugSubscriptionVocab

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
    productassignments = MultipleJoin('ProductBugAssignment', joinColumn='bug')
    packageassignments = MultipleJoin('SourcePackageBugAssignment',
                                    joinColumn='bug')
    productinfestations = MultipleJoin('BugProductInfestation', joinColumn='bug')
    packageinfestations = MultipleJoin('BugPackageInfestation', joinColumn='bug')
    watches = MultipleJoin('BugWatch', joinColumn='bug')
    externalrefs = MultipleJoin('BugExternalRef', joinColumn='bug')
    subscriptions = MultipleJoin('BugSubscription', joinColumn='bug')

    def _set_title(self, value):
        # Record changes of title in activity log
        # TODO: We might want a 'Bug Created' log entry
        if hasattr(self, 'id'):
            log = BugActivity(bug=self.id,
                            datechanged=nowUTC,
                            person=1, # should be the logged in user
                            whatchanged='title',
                            oldvalue=self.title,
                            newvalue=value,
                            message='Message here')
        self._SO_set_title(value)

def BugFactory(*args, **kw):
    """Create a bug from an IBugAddForm"""
    bug = Bug(
        title = kw['title'],
        shortdesc = kw['shortdesc'],
        description = kw['description'],
        owner = kw['owner'])

    # If the user has specified a product, create the ProductBugAssignment
    if kw.get('product', None):
        ProductBugAssignment(bug=bug, product=kw['product'], owner=kw['owner'])

    if kw.get('sourcepackage', None):
        SourcePackageBugAssignment(
            bug=bug, sourcepackage=kw['sourcepackage'], binarypackagename=None,
            owner=kw['owner'])

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

class BugContainer(BugContainerBase):
    """A container for bugs."""

    implements(IBugContainer)
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

