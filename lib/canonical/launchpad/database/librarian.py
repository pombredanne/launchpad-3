

import psycopg

from canonical.database.sqlbase import quote, SQLBase
from sqlobject import StringCol, BoolCol, ForeignKey, IntCol, DateTimeCol, \
                      MultipleJoin

from canonical.launchpad.interfaces import ArchiveAlreadyRegistered, ArchiveNotRegistered, ArchiveLocationDoublyRegistered
from canonical.launchpad.interfaces import RevisionNotRegistered
from canonical.launchpad.interfaces import RevisionAlreadyRegistered
from canonical.launchpad.interfaces import VersionNotRegistered
from canonical.launchpad.interfaces import VersionAlreadyRegistered
from canonical.launchpad.interfaces import BranchAlreadyRegistered
from canonical.launchpad.interfaces import CategoryAlreadyRegistered

from zope.interface import implements
from canonical.launchpad.interfaces import IBranch

class LibraryFileContent(SQLBase):
    """A pointer to file content in the librarian."""

    _table = 'LibraryFileContent'

    _columns = [
        # FIXME: make sqlobject let us use the default in the DB
        DateTimeCol('dateCreated', dbName='dateCreated', notNull=True,
                    default='NOW'),
        DateTimeCol('dateMirrored', dbName='dateMirrored', default=None),
        IntCol('filesize', dbName='filesize', notNull=True),
        StringCol('sha1', dbName='sha1', notNull=True),
    ]


class LibraryFileAlias(SQLBase):
    """A filename and mimetype that we can serve some given content with."""
    
    _table = 'LibraryFileAlias'

    _columns = [
        ForeignKey(name='content', dbName='content',
                   foreignKey='LibraryFileContent', notNull=True),
        StringCol('filename', dbName='filename', notNull=True),
        StringCol('mimetype', dbName='mimetype', notNull=True),
    ]

