# Copyright (c) 2004 Canonical Ltd
#
"""Soyuz Tables

These classes implement the functionality in the Soyuz tables in
the Launchpad system from Canonical. These tables manage the
packages and releases that make up a distribution. Soyuz is
the "distribution management" component of Launchpad.
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


#
# Interface we expect a Sourcepackage to provide.
#
class ISourcepackage(Interface):
    """A Sourcepackage"""
    id = Int(title=_("ID"), required=True)
    maintainer = Int(title=_("Maintainer"), required=True)
    name = TextLine(title=_("Name"), required=True)
    title = TextLine(title=_("Title"), required=True)
    shortdesc = Text(title=_("Description"), required=True)
    description = Text(title=_("Description"), required=True)
    manifest = Int(title=_("Manifest"), required=False)
    distro = Int(title=_("Distribution"), required=False)
    sourcepackagename = Int(title=_("Sourcepackage Name"), required=True)
    bugs = Attribute("bugs")



#
# The basic implementation of a Sourcepackage object.
#
class Sourcepackage(SQLBase):
    implements(ISourcepackage)
    _columns = [
        ForeignKey(
                name='maintainer', dbName='maintainer', foreignKey='Person',
                notNull=True,
                ),
        StringCol('shortdesc', notNull=True),
        StringCol('description', notNull=True),
        ForeignKey(
                name='manifest', dbName='manifest', foreignKey='Manifest',
                notNull=False,
                ),
        ForeignKey(
                name='distro', dbName='distro', foreignKey='Distribution',
                notNull=False,
                ),
        ForeignKey(
                name='sourcepackagename', dbName='sourcepackagename',
                foreignKey='SourcepackageName', notNull=True
                ),
        ]

    bugs = MultipleJoin(
            'SourcepackageBugAssignment', joinColumn='sourcepackage'
            )

    sourcepackagereleases = MultipleJoin(
            'SourcepackageRelease', joinColumn='sourcepackage'
            )

    def name(self):
        return self.sourcepackagename.name


#
# Interface provied by a SourcepackageName. This is a tiny
# table that allows multiple Sourcepackage entities to share
# a single name.
#
class ISourcepackageName(Interface):
    """Name of a Sourcepackage"""
    id = Int(title=_("ID"), required=True)
    name = TextLine(title=_("Name"), required=True)


#
# Basic implementation of a SourcepackageName object.
#
class SourcepackageName(SQLBase):
    _table='SourcepackageName'
    implements(ISourcepackage)
    _columns = [
        StringCol('name', notNull=True, unique=True),
        ]



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



#
# Interface provided by a Binarypackage
#
class IBinarypackage(Interface):
    id = Int(title=_('ID'), required=True)
    #sourcepackagerelease = Int(required=True)
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


#
# Basic implementation of a Binarypackage object.
#
class Binarypackage(SQLBase):
    implements(IBinarypackage)
    _columns = [
        #ForeignKey(
        #        name='sourcepackagerelease', dbName='sourcepackagerelease',
        #        foreignKey='SourcepackageRelease', notNull=True,
        #        ),
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

