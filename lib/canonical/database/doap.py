# Copyright 2004 Canonical Ltd
#
# arch-tag: FA3333EC-E6E6-11D8-B7FE-000D9329A36C
"""Bug tables

"""

# Zope/Python standard libraries
from datetime import datetime
from email.Utils import make_msgid
from zope.interface import implements, Interface
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('canonical')

# Zope schema imports
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, TextLine
from zope.schema import Password

# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE
# TODO: Move this wrapper here
from canonical.arch.sqlbase import SQLBase

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
    """A Sourcepackage."""

    maintainer = Int(title=_('Maintainer'))
    name = TextLine(title=_('Name'))
    title = TextLine(title=_('Title'))
    description = Text(title=_('Description'))
    manifest = Int(title=_('Manifest'))

class Sourcepackage(SQLBase):
    """A Sourcepackage."""

    implements(ISourcepackage)

    _columns = [
        ForeignKey(name='maintainer', dbName='maintainer', foreignKey='Person'),
        StringCol('name'),
        StringCol('title'),
        StringCol('description'),
        IntCol('manifest')
    ]

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



