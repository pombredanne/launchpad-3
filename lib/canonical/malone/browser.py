# Copyright 2004 Canonical Ltd
#
# arch-tag: FA3333EC-E6E6-11D8-B7FE-000D9329A36C

from datetime import datetime
from email.Utils import make_msgid
from zope.interface import implements
from zope.app.form.browser.interfaces import IAddFormCustomization
from zope.schema import TextLine, Int
from canonical.database.doap import Product, Sourcepackage, Binarypackage
from canonical.database import sqlbase

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('malone')

from canonical.lp import dbschema

# TODO: These interfaces should probably be moved into this file, since there
# is only ever one class implementing them
from interfaces import \
        IBugMessagesView, IBugExternalRefsView, \
        IMaloneBug, IMaloneBugAttachment, \
        IBugContainer, IBugAttachmentContainer, IBugExternalRefContainer, \
        IBugSubscriptionContainer, IProjectContainer, \
        ISourcepackageContainer

# TODO: Anything that relies on these imports should not be in this file!
from canonical.database.malone import \
        Bug, BugAttachment, BugExternalRef, BugSubscription, BugMessage, \
        ProductBugAssignment, SourcepackageBugAssignment
from canonical.database.doap import Project, Sourcepackage
from canonical.database.foaf import Person, EmailAddress

def traverseBug(bug, request, name):
    if name == 'attachments':
        return BugAttachmentContainer(bug=bug.id)
    elif name == 'references':
        return BugExternalRefContainer(bug=bug.id)
    elif name == 'people':
        return BugSubscriptionContainer(bug=bug.id)
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


class MaloneApplicationView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def update(self):
        '''Handle request and setup this view the way the templates expect it
        '''
        if self.request.form.has_key('query'):
            query = sqlbase.quote(self.request.form['query'].lower())
            query = "'%%%%' || %s || '%%%%'" % query
            q = (
                r"lower(name) LIKE %(query)s "
                r"OR lower(title) LIKE %(query)s "
                #r"OR lower(description) LIKE %(query)s"
                ) % vars()
            self.results = Sourcepackage.select(q)
            self.noresults = not self.results
        else:
            self.noresults = False
            self.results = []

class BugContainerBase(object):
    implements(IBugContainer, IAddFormCustomization)
    def add(self, ob):
        '''Add a bug from an IMaloneBugAddForm'''
        kw = {}
        attrs = [
            'name', 'title', 'shortdesc', 'description',
            'duplicateof',
            ]
        for a in attrs:
            kw[a] = getattr(ob, a, None)
        # TODO: Get real owner when auth system is in place
        kw['ownerID'] = 1
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
    product = Int(title=_("Product"), required=False)
    sourcepackage = Int(title=_("Source Package"), required=False)
    binarypackage = Int(title=_("Binary Package"), required=False)


class MaloneBugAddForm(object):
    implements(IMaloneBugAddForm)
    def __init__(self, **kw):
        for k,v in kw.items():
            setattr(self, k, v)


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

def ProductBugAssignmentFactory(context, **kw):
    pba = ProductBugAssignment(bug=context.context.id, **kw)
    return pba

def SourcepackageBugAssignmentFactory(context, **kw):
    sa = SourcepackageBugAssignment(bug=context.context.id,
                                    binarypackage=None,
                                    **kw)
    return sa


class BugExternalRefContainer(BugContainerBase):
    """A container for BugExternalRef."""

    implements(IBugExternalRefContainer)
    table = BugExternalRef

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

def BugExternalRefFactory(context, **kw):
    bug = context.context.bug
    owner = 1 # Will be id of logged in user
    datecreated = datetime.utcnow()
    return BugExternalRef(bug=bug, owner=owner, datecreated=datecreated, **kw)


class BugSubscriptionContainer(BugContainerBase):
    """A container for BugSubscription objects."""

    implements(IBugSubscriptionContainer)
    table = BugSubscription

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

    def delete(self, id):
        # BugSubscription.delete(id) raises an error in SQLObject
        # why this is I do not know
        conn = BugSubscription._connection
        # I want an exception raised if id can't be converted to an int
        conn.query('DELETE FROM BugSubscription WHERE id=%d' % int(id))
  

class ProjectContainer(object):
    """A container for Project objects."""

    implements(IProjectContainer)
    table = Project

    def __getitem__(self, name):
        try:
            return self.table.select(self.table.q.name == name)[0]
        except IndexError:
            # Convert IndexError to KeyErrors to get Zope's NotFound page
            raise KeyError, id

    def __iter__(self):
        for row in self.table.select():
            yield row

    def search(self, name, title):
        if name and title:
            return Project.select(AND(Project.q.name==name,
                                      Project.q.title==title))
        elif name:
            return Project.select(Project.q.name==name)
        elif title:
            return Project.select(LIKE(Project.q.title, '%%' + title + '%%'))
        else:
            return []


class SourcepackageContainer(object):
    """A container for Sourcepackage objects."""

    implements(ISourcepackageContainer)
    table = Sourcepackage

    def __getitem__(self, name):
        print '-===== %s ==== ' % name
        try:
            return self.table.select(self.table.q.name == name)[0]
        except IndexError:
            # Convert IndexError to KeyErrors to get Zope's NotFound page
            raise KeyError, id

    def __iter__(self):
        for row in self.table.select():
            yield row


class BugExternalRefsView(object):
    implements(IBugExternalRefsView)
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def add(self, ob):
        return ob

    def nextURL(self):
        return '..'


