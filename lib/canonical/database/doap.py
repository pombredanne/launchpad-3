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
from canonical.database.sqlbase import SQLBase

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

class Project(SQLBase):
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
