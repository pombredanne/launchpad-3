"""Launchpad Bug-related Database Table Objects

Part of the Launchpad system.

(c) 2004 Canonical, Ltd.
"""

# Zope
from zope.interface import implements
# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.launchpad.interfaces.bug import IBug
from canonical.launchpad.interfaces import *

from canonical.database.sqlbase import SQLBase
from canonical.database.constants import nowUTC

from canonical.launchpad.database.bugassignment \
        import SourcePackageBugAssignment, ProductBugAssignment
from canonical.launchpad.database.sourcepackage import SourcePackage
from canonical.launchpad.database.product import Product
from canonical.launchpad.database.bugactivity import BugActivity

# Python
from sets import Set

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
    duplicateof = ForeignKey(dbName='duplicateof', foreignKey='Bug')
    datecreated = DateTimeCol(dbName='datecreated', notNull=True)
    communityscore = IntCol(dbName='communityscore', notNull=True, default=0)
    communitytimestamp = DateTimeCol(dbName='communitytimestamp', notNull=True)
    hits = IntCol(dbName='hits', notNull=True, default=0)
    hitstimestamp = DateTimeCol(dbName='hitstimestamp', notNull=True)
    activityscore = IntCol(dbName='activityscore', notNull=True, default=0)
    activitytimestamp = DateTimeCol(dbName='activitytimestamp', notNull = True)
    
    # useful Joins
    activity = MultipleJoin('BugActivity', joinColumn='bug')
    messages = MultipleJoin('BugMessage', joinColumn='bug')
    # TODO: Standardize on pluralization and naming for table relationships
    productassignment = MultipleJoin('ProductBugAssignment', joinColumn='bug')
    sourceassignment = MultipleJoin('SourcePackageBugAssignment',
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

    def _url(self):
        if int(self.bugreftype) == int(dbschema.BugExternalReferenceType.CVE):
            return 'http://www.cve.mitre.org/cgi-bin/cvename.cgi?name=%s' % (
                    urlquote(self.data)
                    )
        else:
            return self.data
    url = property(_url, None)


# REPORTS
class BugsAssignedReport(object):

    implements(IBugsAssignedReport)

    def __init__(self):
        # initialise the user to None, will raise an exception if the
        # calling class does not set this to a person.id
        self.user = None
        self.BSA = SourcePackageBugAssignment
        self.BPA = ProductBugAssignment

    def assignedBugs(self):
        bugs = Set()
        buglist = Bug.select(OR(AND(Bug.q.id==self.BSA.q.bugID,
                                    self.BSA.q.assigneeID==self.user.id),
                                AND(Bug.q.id==self.BPA.q.bugID,
                                    self.BPA.q.assigneeID==self.user.id),
                                AND(Bug.q.id==self.BSA.q.bugID,
                                    self.BSA.q.sourcepackageID==SourcePackage.q.id,
                                    SourcePackage.q.maintainerID==self.user.id),
                                AND(Bug.q.id==self.BPA.q.bugID,
                                    self.BPA.q.productID==Product.q.id,
                                    Product.q.ownerID==self.user.id),
                                ))
        for bug in buglist:
            bugs.add(bug)
        return bugs
