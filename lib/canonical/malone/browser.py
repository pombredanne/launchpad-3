# Copyright 2004 Canonical Ltd
#
# arch-tag: FA3333EC-E6E6-11D8-B7FE-000D9329A36C

# XXX: 2004-10-08 Brad Bollenbach: I've noticed several hardcodings of
# owner ID being set to 1 in this module (and to do some quick
# testing, I've just done the same once more myself.) This needs
# immediate fixing.

from datetime import datetime
from email.Utils import make_msgid

from zope.interface import implements
from zope.app.form.browser.interfaces import IAddFormCustomization
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.schema import TextLine, Int, Choice
from zope.event import notify

from canonical.launchpad.database import \
        SourcePackage, SourcePackageName, BinaryPackage, \
        BugTracker, BugsAssignedReport, BugWatch, Product, Person, EmailAddress, \
        Bug, BugAttachment, BugExternalRef, BugSubscription, BugMessage, \
        ProductBugAssignment, SourcePackageBugAssignment, \
        BugProductInfestation, BugPackageInfestation
from canonical.database import sqlbase
from canonical.launchpad.events import BugCommentAddedEvent, BugAssignedProductAddedEvent

# I18N support for Malone
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('malone')

from canonical.lp import dbschema

# Interface imports
from canonical.launchpad.interfaces import \
        IMaloneBug, IMaloneBugAttachment, \
        IBugContainer, IBugAttachmentContainer, IBugExternalRefContainer, \
        IBugSubscriptionContainer, ISourcePackageContainer, \
        IBugWatchContainer, IProductBugAssignmentContainer, \
        ISourcePackageBugAssignmentContainer, IBugProductInfestationContainer, \
        IBugPackageInfestationContainer, IPerson, \
        IBugMessagesView, IBugExternalRefsView

def traverseBug(bug, request, name):
    if name == 'attachments':
        return BugAttachmentContainer(bug=bug.id)
    elif name == 'references':
        return BugExternalRefContainer(bug=bug.id)
    elif name == 'people':
        return BugSubscriptionContainer(bug=bug.id)
    elif name == 'watches':
        return BugWatchContainer(bug=bug.id)
    elif name == 'productassignments':
        return ProductBugAssignmentContainer(bug=bug.id)
    elif name == 'sourcepackageassignments':
        return SourcePackageBugAssignmentContainer(bug=bug.id)
    elif name == 'productinfestations':
        return BugProductInfestationContainer(bug=bug.id)
    elif name == 'packageinfestations':
        return BugPackageInfestationContainer(bug=bug.id)
    else:
       raise KeyError, name

def traverseBugs(bugcontainer, request, name):
    if name == 'assigned':
        return BugsAssignedReport()
    else:
        return BugContainer()[int(name)]


def traverseBugAttachment(bugattachment, request, name):
    # TODO: Find out how to make SQLObject only retrieve the
    # desired IBugAttachmentContent rather than all of them
    # and only returning the requested one.
    try:
        name = int(name)
        content = bugattachment.versions
        for c in content:
            if c.bugattachment == bugattachment.id:
                return c
        raise KeyError, name
    except ValueError:
        raise KeyError, name


def newBugTracker(form, owner):
    """Process a form to create a new BugTracker Bug Tracking instance
    object."""
    #
    # Verify that the form was in fact submitted, and that it looks like
    # the right form (by checking the contents of the submit button
    # field, called "Update").
    #
    if not form.has_key('Register'): return
    if not form['Register'] == 'Register Bug Tracker': return
    #
    # Extract the BugTracker details, which are in self.form
    #
    name = form['name']
    title = form['title']
    shortdesc = form['shortdesc']
    baseurl = form['baseurl']
    contactdetails = form['contactdetails']
    #
    # XXX Mark Shuttleworth 05/10/04 Hardcoded Bugzilla for the moment
    #
    bugtrackertype = 1
    #
    # Create the new BugTracker
    #
    bugtracker = BugTracker(name=name,
                          bugtrackertype=bugtrackertype,
                          title=title,
                          shortdesc=shortdesc,
                          baseurl=baseurl,
                          contactdetails=contactdetails,
                          owner=owner)
    #
    # return the bugtracker
    #
    return bugtracker


class MaloneApplicationView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def update(self):
        '''Handle request and setup this view the way the templates expect it
        '''
        from sqlobject import OR, LIKE, CONTAINSSTRING, AND
        if self.request.form.has_key('query'):
            # TODO: Make this case insensitive
            s = self.request.form['query']
            self.results = SourcePackage.select(AND(
                SourcePackage.q.sourcepackagenameID == SourcePackageName.q.id,
                OR(
                    CONTAINSSTRING(SourcePackageName.q.name, s),
                    CONTAINSSTRING(SourcePackage.q.shortdesc, s),
                    CONTAINSSTRING(SourcePackage.q.description, s)
                    )
                ))
            self.noresults = not self.results
        else:
            self.noresults = False
            self.results = []


class BugContainerBase(object):
    implements(IBugContainer, IAddFormCustomization)
    def __init__(self, bug=None):
        self.bug = bug

    def __getitem__(self, id):
        try:
            return self.table.select(self.table.q.id == id)[0]
        except IndexError:
            # Convert IndexError to KeyErrors to get Zope's NotFound page
            raise KeyError, id

    def __iter__(self):
        for row in self.table.select(self.table.q.bugID == self.bug):
            yield row

    def add(self, ob):
        return ob

    def nextURL(self):
        return '.'


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


class IMaloneBugAddForm(IMaloneBug):
    ''' Information we need to create a bug '''
    #email = TextLine(title=_("Your Email Address"))
    product = Choice(
            title=_("Product"), required=False,
            vocabulary="Product",
            )
    sourcepackage = Choice(
            title=_("Source Package"), required=False,
            vocabulary="SourcePackage",
            )
    binarypackage = Choice(
            title=_("Binary Package"), required=False,
            vocabulary="BinaryPackage"
            )
    owner = Int(title=_("Owner"), required=True)


class MaloneBugAddForm(object):
    implements(IMaloneBugAddForm)
    def __init__(self, **kw):
        for k,v in kw.items():
            setattr(self, k, v)


# TODO: It should be possible to specify all this via ZCML and not require
# the MaloneBugView class with its ViewPageTemplateFile attributes
class MaloneBugView(object):
    # XXX fix these horrific relative paths
    watchPortlet = ViewPageTemplateFile(
        '../launchpad/templates/portlet-bug-watch.pt')
    productAssignmentPortlet = ViewPageTemplateFile(
        '../launchpad/templates/portlet-bug-productassignment.pt')
    sourcepackageAssignmentPortlet = ViewPageTemplateFile(
        '../launchpad/templates/portlet-bug-sourcepackageassignment.pt')
    productInfestationPortlet = ViewPageTemplateFile(
        '../launchpad/templates/portlet-bug-productinfestation.pt')
    packageInfestationPortlet = ViewPageTemplateFile(
        '../launchpad/templates/portlet-bug-sourcepackageinfestation.pt')
    referencePortlet = ViewPageTemplateFile(
            '../launchpad/templates/portlet-bug-reference.pt'
            )
    peoplePortlet = ViewPageTemplateFile(
            '../launchpad/templates/portlet-bug-people.pt'
            )

class MaloneBugAttachment(BugAttachment, BugContainerBase):
    implements(IMaloneBugAttachment)
    _table = 'BugAttachment'


class BugAttachmentContentView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def index(self):
        self.request.response.setHeader('Content-Type', self.context.mimetype)
        return self.context.content


class BugMessagesView(object):
    implements(IBugMessagesView)
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def add(self, ob):
        return ob

    # TODO: Use IAbsoluteURL
    def nextURL(self):
        return '..'


class BugContainer(BugContainerBase):
    """A container for bugs."""

    implements(IBugContainer)
    table = MaloneBug

    def __getitem__(self, id):
        try:
            return self.table.select(self.table.q.id == id)[0]
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


class BugAttachmentContainer(BugContainerBase):
    """A container for bug attachments."""

    implements(IBugAttachmentContainer)
    table = MaloneBugAttachment

    def __init__(self, bug=None):
        self.bug = bug

    def __getitem__(self, id):
        try:
            return self.table.select(self.table.q.id == id)[0]
        except IndexError:
            # Convert IndexError to KeyErrors to get Zope's NotFound page
            raise KeyError, id

    def __iter__(self):
        for row in self.table.select(self.table.q.bug == self.bug):
            yield row


def BugAttachmentFactory(context, **kw):
    bug = context.context.bug # view.attachmentcontainer.bug
    return MaloneBugAttachment(bug=bug, **kw)


def BugAttachmentContentFactory(context, **kw):
    bugattachment= context.context.id # view.attachment.id
    daterevised = datetime.utcnow()
    return BugAttachmentContent(
            bugattachment=bugattachment,
            daterevised=daterevised,
            **kw
            )


def BugMessageFactory(context, **kw):
    bug = context.context.context.id # view.comments.bug
    bm =  BugMessage(
            bug=bug, parent=None, datecreated=datetime.utcnow(),
            ownerID=1, rfc822msgid=make_msgid('malone'), **kw)
    comment_added = BugCommentAddedEvent(Bug.get(bug), bm)
    notify(comment_added)

    return bm


def PersonFactory(context, **kw):
    now = datetime.utcnow()
    person = Person(teamowner=1,
                    teamdescription='',
                    karma=0,
                    karmatimestamp=now,
                    **kw)
    return person


def BugSubscriptionFactory(context, **kw):
    bug = context.context.bug
    return BugSubscription(bug=bug, **kw)


class ProductBugAssignmentContainer(BugContainerBase):
    """A container for ProductBugAssignment"""

    implements(IProductBugAssignmentContainer)
    table = ProductBugAssignment


def ProductBugAssignmentFactory(context, **kw):
    pba = ProductBugAssignment(bug=context.context.bug, **kw)
    product_assigned = BugAssignedProductAddedEvent(
        Bug.get(context.context.bug), pba)
    notify(product_assigned)

    return pba

class BugProductInfestationContainer(BugContainerBase):
    """A container for BugProductInfestation."""
    implements(IBugProductInfestationContainer)
    table = BugProductInfestation

    def __getitem__(self, id):
        try:
            return self.table.select(self.table.q.id == id)[0]
        except IndexError:
            # Convert IndexError to KeyErrors to get Zope's NotFound page
            raise KeyError, id

    def __iter__(self):
        for row in self.table.select(self.table.q.bugID == self.bug):
            yield row

def BugProductInfestationFactory(context, **kw):
    now = datetime.utcnow()
    bpi = BugProductInfestation(
        bug=context.context.bug,
        explicit=True,
        datecreated=now,
        creatorID=1, # XXX: (2004-10-08) Brad Bollenbach: Should be the real owner ID
        dateverified=now,
        verifiedbyID=1,
        lastmodified=now,
        lastmodifiedbyID=1,
        **kw)
    return bpi

class BugPackageInfestationContainer(BugContainerBase):
    """A container for BugPackageInfestation."""
    implements(IBugPackageInfestationContainer)
    table = BugPackageInfestation

    def __getitem__(self, id):
        try:
            return self.table.select(self.table.q.id == id)[0]
        except IndexError:
            # Convert IndexError to KeyErrors to get Zope's NotFound page
            raise KeyError, id

    def __iter__(self):
        for row in self.table.select(self.table.q.bugID == self.bug):
            yield row

def BugPackageInfestationFactory(context, **kw):
    now = datetime.utcnow()
    bpi = BugPackageInfestation(
        bug=context.context.bug,
        explicit=True,
        datecreated=now,
        creatorID=1, # XXX: (2004-10-11) Brad Bollenbach: Should be the real owner ID
        dateverified=now,
        verifiedbyID=1,
        lastmodified=now,
        lastmodifiedbyID=1,
        **kw)
    return bpi

class SourcePackageBugAssignmentContainer(BugContainerBase):
    """A container for SourcePackageBugAssignment"""

    implements(ISourcePackageBugAssignmentContainer)
    table = SourcePackageBugAssignment


def SourcePackageBugAssignmentFactory(context, **kw):
    sa = SourcePackageBugAssignment(bug=context.context.bug,
                                    binarypackage=None,
                                    **kw)
    return sa


class BugExternalRefContainer(BugContainerBase):
    """A container for BugExternalRef."""

    implements(IBugExternalRefContainer)
    table = BugExternalRef


def BugExternalRefFactory(context, **kw):
    bug = context.context.bug
    owner = 1 # Will be id of logged in user
    datecreated = datetime.utcnow()
    return BugExternalRef(bug=bug, owner=owner, datecreated=datecreated, **kw)


class BugWatchContainer(BugContainerBase):
    """A container for BugWatch"""

    implements(IBugWatchContainer)
    table = BugWatch


def BugWatchFactory(context, **kw):
    bug = context.context.bug
    owner = 1 # XXX: Will be id of logged in user
    now = datetime.utcnow()
    return BugWatch(
            bug=bug, owner=owner, datecreated=now, lastchanged=now,
            lastchecked=now, **kw
            )


class BugSubscriptionContainer(BugContainerBase):
    """A container for BugSubscription objects."""

    implements(IBugSubscriptionContainer)
    table = BugSubscription

    def delete(self, id):
        # BugSubscription.delete(id) raises an error in SQLObject
        # why this is I do not know
        conn = BugSubscription._connection
        # I want an exception raised if id can't be converted to an int
        conn.query('DELETE FROM BugSubscription WHERE id=%d' % int(id))


class BugExternalRefsView(object):
    implements(IBugExternalRefsView)
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def add(self, ob):
        return ob

    def nextURL(self):
        return '..'


class SourcePackageView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def affectedBinaryPackages(self):
        '''Return a list of [BinaryPackage, {severity -> count}]'''
        m = {}
        sevdef = {}
        BugSeverity = dbschema.BugSeverity
        for i in BugSeverity.items:
            sevdef[i.name] = 0
        for bugass in self.context.bugs:
            binarypackage = bugass.binarypackage
            if binarypackage:
                severity = BugSeverity.items[i].name
                stats = m.setdefault(binarypackage, sevdef.copy())
                m[binarypackage][severity] += 1
        rv = m.items()
        rv.sort(lambda a,b: cmp(a.id, b.id))
        return rv


class BugTrackerSetView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form = request.form

    def newBugTracker(self):
        """This method is triggered by a tal:dummy element in the page
        template, so it is run even when the page is first displayed. It
        calls newBugTracker which will check if a form has been submitted,
        and if so it creates one accordingly and redirects back to its
        display page."""
        #
        # The person who is logged in needs to end up owning this bug
        # tracking instance.
        #
        owner = IPerson(self.request.principal).id
        #
        # Try to process the form
        #
        bugtracker = newBugTracker(self.form, owner)
        if not bugtracker: return
        # Now redirect to view it again
        self.request.response.redirect(self.request.URL[-1])

class BugTrackerView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form = request.form

    def edit(self):
        """Process a form to update or edit the details of a BugTracker
        object. This method is triggered by a tal:dummy element in the page
        template, so it is run even when the page is first displayed. It
        determines whether or not a form has been submitted, and if so it
        updates itself accordingly and redirects back to its display
        page."""
        #
        # Verify that the form was in fact submitted, and that it looks like
        # the right form (by checking the contents of the submit button
        # field, called "Update").
        #
        if not self.form.has_key('Update'): return
        if not self.form['Update'] == 'Update Bug Tracker': return
        #
        # Update the BugTracker, which is in self.context
        #
        self.context.title = self.form['title']
        self.context.shortdesc = self.form['shortdesc']
        self.context.baseurl = self.form['baseurl']
        self.context.contactdetails = self.form['contactdetails']
        #
        # Now redirect to view it again
        #
        self.request.response.redirect(self.request.URL[-1])


# Bug Reports
class BugsAssignedReportView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form = self.request.form
        # Default to showing bugs assigned to the logged in user.
        username = self.form.get('user', None)
        if username: self.user = Person.selectBy(name=username)[0]
        else:
            try: self.user = IPerson(self.request.principal)
            except TypeError: self.user = None
        self.context.user = self.user

    def userSelector(self):
        html = '<select name="user" onclick="form.submit()">\n'
        for person in self.allPeople():
            html = html + '<option value="'+person.name+'"'
            if person==self.user: html = html + ' selected="yes"'
            html = html + '>'
            html = html + person.browsername() + '</option>\n'
        html = html + '</select>\n'
        return html

    def allPeople(self):
        return Person.select()


class BugsCreatedByView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def getAllPeople(self):
        return Person.select()

    def _getBugsForOwner(self, owner):
        bugs_created_by_owner = []
        if owner:
            persons = Person.select(Person.q.name == owner)
            if persons:
                person = persons[0]
                bugs_created_by_owner = Bug.select(Bug.q.ownerID == person.id)
        else:
            bugs_created_by_owner = Bug.select()

        return bugs_created_by_owner

    def getBugs(self):
        bugs_created_by_owner = self._getBugsForOwner(self.request.get("owner", ""))
        return bugs_created_by_owner
