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
    homepageurl = TextLine(title=_('Homepage URL'))

    def products():
        """Return Products for this Project."""

    def rosettaProducts():
        """Iterates over RosettaProducts in this project."""

    # XXX: This will go away once we move to project->product->potemplate
    #      traversal rather than project->potemplate traversal.
    def poTemplate(name):
        """Returns the RosettaPOTemplate with the given name."""


class DBProject(SQLBase):
    """A Project"""

    implements(IProject)

    _table = "Project"

    _columns = [
        IntCol('owner', notNull=True),
        # Rosetta defines 'owner' as a Person not an int, but doesn't use it.
        ##ForeignKey(name='owner', foreignKey='RosettaPerson', notNull=True),
        StringCol('name', notNull=True),
        StringCol('title', notNull=True),
        StringCol('description', notNull=True),
        DateTimeCol('datecreated', notNull=True),
        StringCol('homepageurl')
    ]

    products = MultipleJoin('Product', joinColumn='project')
    _productsJoin = MultipleJoin('RosettaProduct', joinColumn='project')

    def rosettaProducts(self):
        return iter(self._productsJoin)

    def poTemplate(self, name):
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
    title = TextLine(title=_('Title'))
    description = Text(title=_('Description'))
    homepageurl = TextLine(title=_('Homepage URL'))
    manifest = TextLine(title=_('Manifest'))

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
        StringCol('title', notNull=True),
        StringCol('description', notNull=True),
        DateTimeCol('datecreated', notNull=True),
        StringCol('homepageurl'),
        StringCol('screenshotsurl'),
        StringCol('wikiurl'),
        StringCol('programminglang'),
        StringCol('downloadurl'),
        StringCol('lastdoap'),
        ]

    bugs = MultipleJoin('ProductBugAssignment', joinColumn='product')


class ISourcepackage(Interface):
    """A Sourcepackage"""
    id = Int(title=_("ID"), required=True)
    maintainer = Int(title=_("Maintainer"), required=True)
    name = TextLine(title=_("Name"), required=True)
    title = TextLine(title=_("Title"), required=True)
    description = Text(title=_("Description"), required=True)
    manifest = Int(title=_("Manifest"), required=False)
    distro = Int(title=_("Distribution"), required=False)

    bugs = Attribute('bugs')

class Sourcepackage(SQLBase):
    implements(ISourcepackage)
    _columns = [
        ForeignKey(
                name='maintainer', dbName='maintainer', foreignKey='Person',
                notNull=True,
                ),
        StringCol('name', notNull=True),
        StringCol('title', notNull=True),
        StringCol('description', notNull=True),
        ForeignKey(
                name='manifest', dbName='manifest', foreignKey='Manifest',
                notNull=False,
                ),
        ForeignKey(
                name='distro', dbName='distro', foreignKey='Distribution',
                notNull=False,
                ),
        ]

    bugs = MultipleJoin(
            'SourcepackageBugAssignment', joinColumn='sourcepackage'
            )
    sourcepackagereleases = MultipleJoin(
            'SourcepackageRelease', joinColumn='sourcepackage'
            )

""" Currently unneeded
class SourcepackageRelease(SQLBase):
    _table = 'SourcepackageRelease'
    _columns = [
        ForeignKey(
            name='sourcepackage', dbName='sourcepackage',
            foreignKey='Sourcepackage', notNull=True,
            ),
        IntCol(name='srcpackageformat', notNull=True,),
        ForeignKey(
            name='creator', dbName='creator',
            foreignKey='Person', notNull=True,
            ),
        StringCol('version', notNull=True),
        DatetimeCol('dateuploaded', notNull=True),
        IntCol('urgency', notNull=True),
        ForeignKey(
            name='dscsigningkey', dbName='dscsigningkey', notNull=False),
            )
        IntCol('component', notNull=False),
        StringCol('changelog', notNull=False),
        StringCol('builddepends', notNull=False),
        StringCol('builddependsindep', notNull=False),
        StringCol('architecturehintlist', notNull=False),
        StringCol('dsc', notNull=False),
        ]
"""

class IBinarypackage(Interface):
    id = Int(title=_('ID'), required=True)
    sourcepackagerelease = Int(required=True)
    binarypackagename = Int(required=True)
    version = TextLine(required=True)
    shortdesc = Text(required=True)
    description = Text(required=True)
    build = Int(required=True)
    binpackageformat = Int(required=True)
    component = Int(required=True)
    section = Int(required=True)
    priority = Int(required=False)
    shlibdeps = Text(required=False)
    recommends = Text(required=False)
    suggests = Text(required=False)
    conflicts = Text(required=False)
    replaces = Text(required=False)
    provides = Text(required=False)
    essential = Bool(required=False)
    installedsize = Int(required=False)
    copyright = Text(required=False)
    licence = Text(required=False)

    title = TextLine(required=True, readonly=True)

class Binarypackage(SQLBase):
    implements(IBinarypackage)
    _columns = [
        ForeignKey(
                name='sourcepackagerelease', dbName='sourcepackagerelease',
                foreignKey='SourcepackageRelease', notNull=True,
                ),
        ForeignKey(
                name='binarypackagename', dbName='binarypackagename',
                foreignKey='BinarypackageName', notNull=True,
                ),
        StringCol('version', notNull=True),
        StringCol('shortdesc', notNull=True),
        StringCol('description', notNull=True),
        ForeignKey(
                name='build', dbName='build', foreignKey='Build', notNull=True,
                ),
        IntCol('binpackageformat', notNull=True),
        ForeignKey(
                name='component', dbName='component', foreignKey='Component',
                notNull=True,
                ),
        ForeignKey(
                name='section', dbName='section', foreignKey='Section',
                notNull=True,
                ),
        IntCol('priority'),
        StringCol('shlibdeps'),
        StringCol('recommends'),
        StringCol('suggests'),
        StringCol('conflicts'),
        StringCol('replaces'),
        StringCol('provides'),
        BoolCol('essential'),
        IntCol('installedsize'),
        StringCol('copyright'),
        StringCol('licence'),
        ]
    
    def _title(self):
        return '%s-%s' % (self.binarypackagename.name, self.version)
    title = property(_title, None)

class IBinarypackageName(Interface):
    id = Int(title=_('ID'), required=True)
    name = TextLine(title=_('Name'), required=True)
    binarypackages = Attribute('binarypackages')

class BinarypackageName(SQLBase):
    implements(IBinarypackageName)
    _table = 'BinarypackageName'
    _columns = [
        StringCol('name', notNull=True, unique=True),
        ]
    binarypackages = MultipleJoin(
            'Binarypackage', joinColumn='binarypackagename'
            )

