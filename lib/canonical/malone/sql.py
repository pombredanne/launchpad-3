__metaclass__ = type

# Zope/Python standard libraries
from datetime import datetime
from email.Utils import make_msgid
from zope.interface import implements

# SQL imports
from sqlos import SQLOS
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE

# Interfaces
from canonical.malone.interfaces import IBug, IBugContainer, IBugAttachment
from canonical.malone.interfaces import IBugAttachmentContainer, IBugActivity
from canonical.malone.interfaces import IBugExternalRef, IPerson, IBugMessage
from canonical.malone.interfaces import IBugAttachmentContent, IUsesAddForm
from canonical.malone.interfaces import IProject, IProjectContainer, IProduct
from canonical.malone.interfaces import IProject, IProjectContainer
from canonical.malone.interfaces import IProductBugAssignment, IBugSubscription
from canonical.malone.interfaces import ISourcepackageBugAssignment
from canonical.malone.interfaces import ISourcepackage, IBugExternalRefContainer
from canonical.malone.interfaces import IBugSubscriptionContainer

# TODO: Use IAddFormCustomization from zope.app.???
class BugContainerBase(object):
    implements(IUsesAddForm)
    def add(self, ob):
        return ob

    def nextURL(self):
        return '.'


class Bug(SQLOS):
    """A bug."""

    implements(IBug, IUsesAddForm)

    _defaultOrder = '-id'
    _columns = [
        DateTimeCol('datecreated', dbName='datecreated', notNull=True),
        StringCol('nickname', dbName='nickname', unique=True),
        StringCol('title', notNull=True),
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

    def add(self, ob):
        return ob

    def nextURL(self):
        return '.'

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


def BugFactory(context, **kw):
    now = datetime.utcnow()
    bug = Bug(
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


class BugContainer(BugContainerBase):
    """A container for bugs."""

    implements(IBugContainer)
    table = Bug

    def __getitem__(self, id):
        try:
            return self.table.select(self.table.q.id == id)[0]
        except IndexError:
            # Convert IndexError to KeyErrors to get Zope's NotFound page
            raise KeyError, id

    def __iter__(self):
        for row in self.table.select():
            yield row


class BugAttachment(SQLOS, BugContainerBase):
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

def BugAttachmentFactory(context, **kw):
    bug = context.context.bug # view.attachmentcontainer.bug
    return BugAttachment(bug=bug, **kw)


class BugAttachmentContainer(BugContainerBase):
    """A container for bug attachments."""
 
    implements(IBugAttachmentContainer)
    table = BugAttachment
 
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


class BugAttachmentContent(SQLOS):
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

def BugAttachmentContentFactory(context, **kw):
    bugattachment= context.context.id # view.attachment.id
    daterevised = datetime.utcnow()
    return BugAttachmentContent(
            bugattachment=bugattachment,
            daterevised=daterevised,
            **kw
            )


class BugActivity(SQLOS):
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


class BugExternalRef(SQLOS):
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

def BugExternalRefFactory(context, **kw):
    bug = context.context.bug
    owner = 1 # Will be id of logged in user
    datecreated = datetime.utcnow()
    return BugExternalRef(bug=bug, owner=owner, datecreated=datecreated, **kw)

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


class BugMessage(SQLOS):
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
        ForeignKey(name='personmsg', foreignKey='Person', dbName='personmsg'),
        ForeignKey(name='parent', foreignKey='BugMessage', dbName='parent'),
        ForeignKey(
                name='distribution', foreignKey='Distribution',
                dbName='distribution'
                ),
        StringCol('rfc822msgid', unique=True, notNull=True),
    ]

def BugMessageFactory(context, **kw):
    bug = context.context.context.id # view.comments.bug
    return BugMessage(
            bug=bug, parent=None, datecreated=datetime.utcnow(),
            rfc822msgid=make_msgid('malone'), **kw
            )

def PersonFactory(context, **kw):
    now = datetime.utcnow()
    person = Person(teamowner=1,
                    teamdescription='',
                    karma=0,
                    karmatimestamp=now,
                    **kw)
    return person

class Person(SQLOS):
    """A Person."""

    implements(IPerson)

    _columns = [
        StringCol('presentationname'),
        StringCol('givenname'),
        StringCol('familyname'),
        StringCol('password'),
        ForeignKey(name='teamowner', foreignKey='Person', dbName='teamowner'),
        StringCol('teamdescription'),
        IntCol('karma'),
        DateTimeCol('karmatimestamp')
    ]


class BugSubscription(SQLOS):
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

def BugSubscriptionFactory(context, **kw):
    bug = context.context.bug
    return BugSubscription(bug=bug, **kw)

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
  
def ProductBugAssignmentFactory(context, **kw):
    pba = ProductBugAssignment(bug=context.context.id, **kw)
    return pba

class ProductBugAssignment(SQLOS):
    """A relationship between a Product and a Bug."""

    implements(IProductBugAssignment)

    _table = 'ProductBugAssignment'
    _columns = [
        ForeignKey(name='bug', dbName='bug', foreignKey='Bug'),
        ForeignKey(name='product', dbName='product', foreignKey='Product'),
        IntCol('bugstatus'),
        IntCol('priority'),
        IntCol('severity')
    ]


def SourcepackageBugAssignmentFactory(context, **kw):
    sa = SourcepackageBugAssignment(bug=context.context.id,
                                    binarypackage=None,
                                    **kw)
    return sa

class SourcepackageBugAssignment(SQLOS):
    """A relationship between a Sourcepackage and a Bug."""

    implements(ISourcepackageBugAssignment)

    _table = 'SourcepackageBugAssignment'
    _columns = [
        ForeignKey(name='bug', dbName='bug', foreignKey='Bug'),
        ForeignKey(name='sourcepackage', dbName='sourcepackage',
                   foreignKey='Sourcepackage'),
        IntCol('bugstatus'),
        IntCol('priority'),
        IntCol('severity'),
        IntCol('binarypackage')
    ]

class Product(SQLOS):
    """A Product."""

    implements(IProduct)

    _columns = [
        IntCol('project'),
        IntCol('owner'),
        StringCol('title'),
        StringCol('description'),
        DateTimeCol('datecreated'),
        StringCol('homepageurl'),
        IntCol('manifest')
    ]

    bugs = MultipleJoin('ProductBugAssignment', joinColumn='product')

class Sourcepackage(SQLOS):
    """A Sourcepackage."""

    implements(ISourcepackage)

    _columns = [
        ForeignKey(name='maintainer', dbName='maintainer', foreignKey='Person'),
        StringCol('name'),
        StringCol('title'),
        StringCol('description'),
        IntCol('manifest')
    ]

class Project(SQLOS):
    """A Project"""

    implements(IProject)

    _columns = [
        IntCol('owner'),
        StringCol('name'),
        StringCol('title'),
        StringCol('description'),
        DateTimeCol('datecreated'),
        StringCol('homepageurl')
    ]

    products = MultipleJoin('Product', joinColumn='project')

class ProjectContainer(object):
    """A container for Project objects."""

    implements(IProjectContainer)
    table = Project

    def __getitem__(self, id):
        try:
            return self.table.select(self.table.q.id == id)[0]
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
