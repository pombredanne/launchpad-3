# Copyright (c) 2004 Canonical Ltd
#
# Buttress Database Access Classes
"""Buttress Classes

These classes implement access to the Buttress tables in the Launchpad
database. Buttress is our Arch Repository Management infrastructure,
that coordinates and manages tens of thousands of branches in thousands
of Arch archives.
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

class SourceSource(SQLBase): 
    #, importd.Job.Job):
    #from canonical.soyuz.sql import SourcePackage, Branch
    """SourceSource table!"""

    _table = 'SourceSource'
    _columns = [
        StringCol('name', dbName='name', notNull=True),
        StringCol('title', dbName='title', notNull=True),
        StringCol('description', dbName='description', notNull=True),
        ForeignKey(name='product', foreignKey='SoyuzProduct', dbName='product',
                   default=1),
        StringCol('cvsroot', dbName='cvsroot', default=None),
        StringCol('cvsmodule', dbName='cvsmodule', default=None),
        ForeignKey(name='cvstarfile', foreignKey='LibraryFileAlias',
                   dbName='cvstarfile', default=None),
        StringCol('cvstarfileurl', dbName='cvstarfileurl', default=None),
        StringCol('cvsbranch', dbName='cvsbranch', default=None),
        StringCol('svnrepository', dbName='svnrepository', default=None),
        StringCol('releaseroot', dbName='releaseroot', default=None),
        StringCol('releaseverstyle', dbName='releaseverstyle', default=None),
        StringCol('releasefileglob', dbName='releasefileglob', default=None),
        ForeignKey(name='releaseparentbranch', foreignKey='Branch',
                   dbName='releaseparentbranch', default=None),
        ForeignKey(name='sourcepackage', foreignKey='SourcePackage',
                   dbName='sourcepackage', default=None),
        ForeignKey(name='branch', foreignKey='Branch',
                   dbName='branch', default=None),
        DateTimeCol('lastsynced', dbName='lastsynced', default=None),
        DateTimeCol('frequency', dbName='syncinterval', default=None),
        # WARNING: syncinterval column type is "interval", not "integer"
        # WARNING: make sure the data is what buildbot expects

        #IntCol('rcstype', dbName='rcstype', default=RCSTypeEnum.cvs,
        #       notNull=True),
        
        # FIXME: use 'RCSTypeEnum.cvs' rather than '1'
        IntCol('rcstype', dbName='rcstype', default=1,
               notNull=True),

        StringCol('hosted', dbName='hosted', default=None),
        StringCol('upstreamname', dbName='upstreamname', default=None),
        DateTimeCol('processingapproved', dbName='processingapproved',
                    notNull=False, default=None),
        DateTimeCol('syncingapproved', dbName='syncingapproved', notNull=False,
                    default=None),

        # For when Rob approves it
        StringCol('newarchive', dbName='newarchive'),
        StringCol('newbranchcategory', dbName='newbranchcategory'),
        StringCol('newbranchbranch', dbName='newbranchbranch'),
        StringCol('newbranchversion', dbName='newbranchversion'),

        # Temporary keybuk stuff
        StringCol('package_distro', dbName='packagedistro', default=None),
        StringCol('package_files_collapsed', dbName='packagefiles_collapsed',
                default=None),

        ForeignKey(name='owner', foreignKey='ArchPerson', dbName='owner',
                   notNull=True),
        StringCol('currentgpgkey', dbName='currentgpgkey', default=None),
    ]

