# Copyright 2004 Canonical Ltd
#
# arch-tag: FA3333EC-E6E6-11D8-B7FE-000D9329A36C

from datetime import datetime
from email.Utils import make_msgid

from zope.interface import implements
from zope.app.form.browser.interfaces import IAddFormCustomization
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.schema import TextLine, Int, Choice

#
# Database access objects
#
from canonical.launchpad.database import \
        Sourcepackage, SourcepackageName, Binarypackage, \
        BugSystem, BugWatch, Product, Person, EmailAddress, \
        Bug, BugAttachment, BugExternalRef, BugSubscription, BugMessage, \
        ProductBugAssignment, SourcepackageBugAssignment
from canonical.database import sqlbase

#
# I18N support for Malone
#
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('malone')

from canonical.lp import dbschema

#
# Interface imports
#
from canonical.launchpad.interfaces import \
        IBugMessagesView, IBugExternalRefsView, \
        IMaloneBug, IMaloneBugAttachment, \
        IBugContainer, IBugAttachmentContainer, IBugExternalRefContainer, \
        IBugSubscriptionContainer, \
        ISourcepackageContainer, IBugWatchContainer, \
        IProductBugAssignmentContainer, \
        ISourcepackageBugAssignmentContainer, IPerson


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
        return SourcepackageBugAssignmentContainer(bug=bug.id)
    else:
       raise KeyError, name


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
    """Process a form to create a new BugSystem Bug Tracking instance
    object."""
    #
    # Verify that the form was in fact submitted, and that it looks like
    # the right form (by checking the contents of the submit button
    # field, called "Update").
    #
    if not form.has_key('Register'): return
    if not form['Register'] == 'Register Bug Tracker': return
    #
    # Extract the BugSystem details, which are in self.form
    #
    name = form['name']
    title = form['title']
    shortdesc = form['shortdesc']
    baseurl = form['baseurl']
    contactdetails = form['contactdetails']
    #
    # XXX Mark Shuttleworth 05/10/04 Hardcoded Bugzilla for the moment
    #
    bugsystemtype = 1
    #
    # Create the new BugSystem
    #
    bugsystem = BugSystem(name=name,
                          bugsystemtype=bugsystemtype,
                          title=title,
                          shortdesc=shortdesc,
                          baseurl=baseurl,
                          contactdetails=contactdetails,
                          owner=owner)
    #
    # return the bugsystem
    #
    return bugsystem


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
            self.results = Sourcepackage.select(AND(
                Sourcepackage.q.sourcepackagenameID == SourcepackageName.q.id,
                OR(
                    CONTAINSSTRING(SourcepackageName.q.name, s),
                    CONTAINSSTRING(Sourcepackage.q.shortdesc, s),
                    CONTAINSSTRING(Sourcepackage.q.description, s)
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
        for row in self.table.select(self.table.q.bug == self.bug):
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
            vocabulary="Sourcepackage",
            )
    binarypackage = Choice(
            title=_("Binary Package"), required=False,
            vocabulary="Binarypackage"
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
    watchPortlet = ViewPageTemplateFile('../launchpad/templates/portlet-bug-watch.pt')
    productAssignmentPortlet = ViewPageTemplateFile(
            '../launchpad/templates/portlet-bug-productassignment.pt'
            )
    sourcepackageAssignmentPortlet = ViewPageTemplateFile(
            '../launchpad/templates/portlet-bug-sourcepackageassignment.pt'
            )
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
        # SourcepackageBugAssignment. This might also link to the
        # binary package if it was specified.
        sourcepkgid = getattr(ob, 'sourcepackage', None)
        binarypkgid = getattr(ob, 'binarypackage', None)
        if sourcepkgid:
            sourcepkg = Sourcepackage.get(sourcepkgid)
            if binarypkgid:
                binarypkg = Binarypackage.get(binarypkgid)
            else:
                binarypkg = None
            sba = SourcepackageBugAssignment(
                    bug=bug, sourcepackage=sourcepkg,
                    binarypackage=binarypkg,
                    )

        return ob # Return this rather than the bug we created from it,
                  # as the return value must be adaptable to the interface
                  # used to generate the form.


def BugAdder(object):
    def createAndAdd(self, *args, **kw):
        '''Add a bug from an IMaloneBugAddForm'''
        import pdb; pdb.set_trace()
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
        # SourcepackageBugAssignment. This might also link to the
        # binary package if it was specified.
        sourcepkgid = getattr(ob, 'sourcepackage', None)
        binarypkgid = getattr(ob, 'binarypackage', None)
        if sourcepkgid:
            sourcepkg = Sourcepackage.get(sourcepkgid)
            if binarypkgid:
                binarypkg = Binarypackage.get(binarypkgid)
            else:
                binarypkg = None
            sba = SourcepackageBugAssignment(
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
    return BugMessage(
            bug=bug, parent=None, datecreated=datetime.utcnow(),
            ownerID=1, rfc822msgid=make_msgid('malone'), **kw
            )


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
    return pba


class SourcepackageBugAssignmentContainer(BugContainerBase):
    """A container for SourcepackageBugAssignment"""

    implements(ISourcepackageBugAssignmentContainer)
    table = SourcepackageBugAssignment


def SourcepackageBugAssignmentFactory(context, **kw):
    sa = SourcepackageBugAssignment(bug=context.context.bug,
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
  

class SourcepackageContainer(object):
    """A container for Sourcepackage objects."""

    implements(ISourcepackageContainer)
    table = Sourcepackage

    #
    # We need to return a Sourcepackage given a name. For phase 1 (warty)
    # we can assume that there is only one package with a given name, but
    # later (XXX) we will have to deal with multiple source packages with
    # the same name.
    #
    def __getitem__(self, name):
        return self.table.select("Sourcepackage.sourcepackagename = \
        SourcepackageName.id AND SourcepackageName.name = %s" %     \
        sqlbase.quote(name))[0]

    def __iter__(self):
        for row in self.table.select():
            yield row

    _bugassignments = SourcepackageBugAssignment

    def bugassignments(self, orderby='-id'):
        # TODO: Ordering
        return self._bugassignments.select(orderBy=orderby)

    #
    # return a result set of Sourcepackages with bugs assigned to them
    # which in future might be limited by distro, for example
    #
    def withBugs(self):
        return self.table.select("Sourcepackage.id = \
        SourcepackageBugAssignment.sourcepackage")


class BugExternalRefsView(object):
    implements(IBugExternalRefsView)
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def add(self, ob):
        return ob

    def nextURL(self):
        return '..'


class SourcepackageView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def affectedBinaryPackages(self):
        '''Return a list of [Binarypackage, {severity -> count}]'''
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


class BugSystemSetView(object):
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
        bugsystem = newBugTracker(self.form, owner)
        if not bugsystem: return
        # Now redirect to view it again
        self.request.response.redirect(self.request.URL[-1])



class BugSystemView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form = request.form

    def edit(self):
        """Process a form to update or edit the details of a BugSystem
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
        # Update the BugSystem, which is in self.context
        #
        self.context.title = self.form['title']
        self.context.shortdesc = self.form['shortdesc']
        self.context.baseurl = self.form['baseurl']
        self.context.contactdetails = self.form['contactdetails']
        #
        # Now redirect to view it again
        #
        self.request.response.redirect(self.request.URL[-1])
