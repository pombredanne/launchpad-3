"""Launchpad Bug-related Database Table Objects

Part of the Launchpad system.

(c) 2004 Canonical, Ltd.
"""

# Zope
from zope.interface import implements
# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.launchpad.interfaces.bug import IBug, IBugContainer
from canonical.launchpad.interfaces import *

from canonical.database.sqlbase import SQLBase
from canonical.database.constants import nowUTC

from canonical.launchpad.database.bugcontainer \
        import BugContainerBase
from canonical.launchpad.database.bugassignment \
        import SourcePackageBugAssignment, ProductBugAssignment
from canonical.launchpad.database.sourcepackage import SourcePackage
from canonical.launchpad.database.product import Product
from canonical.launchpad.database.bugactivity import BugActivity

# Python
from sets import Set
from datetime import datetime

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


class MaloneBug(Bug):
    implements(IMaloneBug)

    _table = 'Bug'

    def __init__(self, **kw):
        # TODO: Fix Z3 so these can use defaults set in the schema.
        # Currently can't use a callable.
        kw['datecreated'] = datetime.utcnow()
        kw['communitytimestamp'] = datetime.utcnow()
        kw['hitstimestamp'] = datetime.utcnow()
        kw['activitytimestamp'] = datetime.utcnow()
        Bug.__init__(self, **kw)

    def add(self, ob):
        return ob

    def nextURL(self):
        return '.'


class MaloneBugAddForm(object):
    implements(IMaloneBugAddForm)
    def __init__(self, **kw):
        for k,v in kw.items():
            setattr(self, k, v)


def BugAdder(object):
    def createAndAdd(self, *args, **kw):
        '''Add a bug from an IMaloneBugAddForm'''
        kw = {}
        attrs = ['name', 'title', 'shortdesc', 'description', 'duplicateof',]
        for a in attrs:
            kw[a] = getattr(ob, a, None)
        #kw['ownerID'] = IPerson(self.request.principal).id
        bug = MaloneBug(**kw)

        # If the user has specified a product, create the ProductBugAssignment
        productid = getattr(ob, 'product', None)
        if productid:
            product = Product.get(productid)
            pba = ProductBugAssignment(bug=bug, product=product)

        # If the user has specified a sourcepackage, create the
        # SourcePackageBugAssignment. This might also link to the
        # binary package if it was specified.
        sourcepkgid = getattr(ob, 'sourcepackage', None)
        binarypkgid = getattr(ob, 'binarypackage', None)
        if sourcepkgid:
            sourcepkg = SourcePackage.get(sourcepkgid)
            if binarypkgid:
                binarypkg = BinaryPackage.get(binarypkgid)
            else:
                binarypkg = None
            sba = SourcePackageBugAssignment(
                    bug=bug, sourcepackage=sourcepkg,
                    binarypackage=binarypkg,
                    )

        return ob # Return this rather than the bug we created from it,
                  # as the return value must be adaptable to the interface
                  # used to generate the form.



class BugContainer(BugContainerBase):
    """A container for bugs."""

    implements(IBugContainer)
    table = MaloneBug

    def __getitem__(self, id):
        try:
            return self.table.select(self.table.q.id==id)[0]
        except IndexError:
            # Convert IndexError to KeyErrors to get Zope's NotFound page
            raise KeyError, id

    def __iter__(self):
        for row in self.table.select():
            yield row

    def add(self, ob):
        '''Add a bug from an IMaloneBugAddForm'''
        kw = {}
        attrs = ['name', 'title', 'shortdesc', 'description', 'duplicateof',]
        for a in attrs:
            kw[a] = getattr(ob, a, None)
        kw['ownerID'] = ob.owner.id

        bug = MaloneBug(**kw)

        # If the user has specified a product, create the ProductBugAssignment
        productid = getattr(ob, 'product', None)
        if productid:
            product = Product.get(productid)
            pba = ProductBugAssignment(bug=bug, product=product)

        # If the user has specified a sourcepackage, create the
        # SourcePackageBugAssignment. This might also link to the
        # binary package if it was specified.
        sourcepkgid = getattr(ob, 'sourcepackage', None)
        binarypkgid = getattr(ob, 'binarypackage', None)
        if sourcepkgid:
            sourcepkg = SourcePackage.get(sourcepkgid)
            if binarypkgid:
                binarypkg = BinaryPackage.get(binarypkgid)
            else:
                binarypkg = None
            sba = SourcePackageBugAssignment(
                    bug=bug, sourcepackage=sourcepkg,
                    binarypackagename=binarypkg,
                    )

        return ob # Return this rather than the bug we created from it,
                  # as the return value must be adaptable to the interface
                  # used to generate the form.


def MaloneBugFactory(context, **kw):
    now = datetime.utcnow()
    # TODO: How do we handle this email address?
    # If the user is not logged in, we might want to create a Person for
    # them (although we really want to link their email address to their
    # existing Person).
    # If the user is not logged in, and the email address they entered is
    # already in the system, do we create the Bug as that Person?
    # If the user is logged in, we want to validate the email address is one
    # of theirs.
    #
    #email = kw.get('email', None)
    #del kw['email']
    #if email:
    #    e = EmailAddress.select(EmailAddress.q.email==email)
    bug = MaloneBug(
            datecreated=now,
            communityscore=0,
            communitytimestamp=now,
            duplicateof=None,
            hits=0,
            hitstimestamp=now,
            activityscore=0,
            activitytimestamp=now,
            owner=1, # will be logged in user
            **kw
            )
    return bug




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
