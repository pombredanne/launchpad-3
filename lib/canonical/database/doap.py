# Copyright 2004 Canonical Ltd
#
# arch-tag: FA3333EC-E6E6-11D8-B7FE-000D9329A36C
"""Bug tables

"""

# Zope/Python standard libraries
from datetime import datetime
from email.Utils import make_msgid
from zope.interface import implements, Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('canonical')

# Zope schema imports
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, TextLine
from zope.schema import Password, Bool

# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol, BoolCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE
# TODO: Move this wrapper here
from canonical.database.sqlbase import SQLBase, quote


class IProjects(Interface):
    """The collection of projects."""

    def __iter__():
        """Return an iterator over all the projects."""

    def __getitem__(name):
        """Get a project by its name."""

    # XXX needs displayname, shortdesc, NO url
    def new(name, title, url, description, owner):
        """Creates a new project with the given name.

        Returns that project.

        Raises an KeyError if a project with that name already exists.
        """

    def search(query):
        """Search for projects matching a certain strings."""


class DBProjects:
    implements(IProjects)

    def __iter__(self):
        return iter(DBProject.select())

    def __getitem__(self, name):
        ret = DBProject.selectBy(name=name)

        if ret.count() == 0:
            raise KeyError, name
        else:
            return ret[0]

    def new(self, name, title, url, description, owner):
        name = name.encode('ascii')
        # XXX: where did displayName come from?
        ##displayName = displayName.encode('ascii')
        title = title.encode('ascii')
        if type(url) != NoneType:
            url = url.encode('ascii')
        description = description.encode('ascii')

        if Project.selectBy(name=name).count():
            raise KeyError, "There is already a project with that name"

        return Project(name=name,
                       ##displayName=displayName,
                       title=title,
                       url=url,
                       description=description,
                       owner=owner,
                       datecreated='now')

    def search(self, query):
        query = quote('%%' + query + '%%')
        #query = quote(query)
        return DBProject.select(
            'title ILIKE %s OR description ILIKE %s' % (query, query))


class IProject(Interface):
    """A Project."""

    id = Int(title=_('ID'))
    owner = Int(title=_('Owner'))
    name = TextLine(title=_('Name'))
    title = TextLine(title=_('Title'))
    description = Text(title=_('Description'))
    shortdesc = Text(title=_('Short Description'))
    homepageurl = TextLine(title=_('Homepage URL'))

    def displayName(aDesc=None):
        """return the projects shortdesc, setting it if aDesc is provided"""

    def products():
        """Return Products for this Project."""

    def getProduct(name):
        """Get a product with name `name`."""
    
    def rosettaProducts():
        """Iterates over RosettaProducts in this project."""

    # XXX: This will go away once we move to project->product->potemplate
    #      traversal rather than project->potemplate traversal.
    def poTemplate(name):
        """Returns the RosettaPOTemplate with the given name."""

    def shortDescription(aDesc=None):
        """return the projects shortdesc, setting it if aDesc is provided"""



class DBProject(SQLBase):
    """A Project"""

    implements(IProject)

    _table = "Project"

    _columns = [
        IntCol('owner', notNull=True),
        # Rosetta defines 'owner' as a Person not an int, but doesn't use it.
        ##ForeignKey(name='owner', foreignKey='RosettaPerson', notNull=True),
        StringCol('name', notNull=True),
        StringCol('displayname', notNull=True),
        StringCol('title', notNull=True),
        StringCol('shortdesc', notNull=True),
        StringCol('description', notNull=True),
        # XXX: https://bugzilla.warthogs.hbd.com/bugzilla/show_bug.cgi?id=1968
        DateTimeCol('datecreated', notNull=True),
        StringCol('homepageurl', notNull=False, default=None),
        StringCol('wikiurl', notNull=False, default=None),
        StringCol('lastdoap', notNull=False, default=None)
    ]

    products = MultipleJoin('Product', joinColumn='project')
    _productsJoin = MultipleJoin('RosettaProduct', joinColumn='project')

    def rosettaProducts(self):
        return iter(self._productsJoin)

    def getProduct(self, name):
        try:
            return Product.selectBy(projectID=self.id, name=name)[0]
        except IndexError:
            return None

    def poTemplate(self, name):
        # XXX: What does this have to do with DBProject?  This function never
        # uses self.  I suspect this belongs somewhere else.
        results = RosettaPOTemplate.selectBy(name=name)
        count = results.count()

        if count == 0:
            raise KeyError, name
        elif count == 1:
            return results[0]
        else:
            raise AssertionError("Too many results.")


class IProduct(Interface):
    """A Product."""

    project = Int(title=_('Project'))
    owner = Int(title=_('Owner'))
    name = TextLine(title=_('Name'))
    title = TextLine(title=_('Title'))
    description = Text(title=_('Description'))
    homepageurl = TextLine(title=_('Homepage URL'))
    manifest = TextLine(title=_('Manifest'))
    syncs = Attribute(_('Sync jobs'))

    def bugs():
        """Return ProductBugAssignments for this Product."""

class Product(SQLBase):
    """A Product."""

    implements(IProduct)

    _columns = [
        ForeignKey(
                name='project', foreignKey="Project", dbName="project",
                notNull=True
                ),
        ForeignKey(
                name='owner', foreignKey="Product", dbName="owner",
                notNull=True
                ),
        StringCol('name', notNull=True),
        StringCol('displayname', notNull=True),
        StringCol('title', notNull=True),
        StringCol('shortdesc', notNull=True),
        StringCol('description', notNull=True),
        DateTimeCol('datecreated', notNull=True),
        StringCol('homepageurl', notNull=False, default=None),
        StringCol('screenshotsurl', notNull=False, default=None),
        StringCol('wikiurl', notNull=False, default=None),
        StringCol('programminglang', notNull=False, default=None),
        StringCol('downloadurl', notNull=False, default=None),
        StringCol('lastdoap', notNull=False, default=None),
        ]

    bugs = MultipleJoin('ProductBugAssignment', joinColumn='product')

    syncs = MultipleJoin('SourceSource', joinColumn='product')


#
# Soyuz Tables have been moved to soyuz.py
#
