# Zope interfaces
from zope.interface import implements
from zope.exceptions import NotFoundError

# SQL imports
from sqlobject import StringCol, MultipleJoin, SQLObjectNotFound
from canonical.database.sqlbase import SQLBase

# canonical imports
from canonical.launchpad.interfaces import IPOTemplateName

class POTemplateNameSet(object):
    def __getitem__(self, name):
        try:
            return POTemplateName.byName(name)
        except SQLObjectNotFound:
            raise NotFoundError, name

    def __iter__(self):
        for potemplatename in POTemplateName.select():
            yield potemplatename

    def new(self, name, title):
        return POTemplateName(name=name, title=title)


class POTemplateName(SQLBase):
    implements(IPOTemplateName)

    _table = 'POTemplateName'

    name = StringCol(dbName='name', notNull=True, unique=True, alternateID=True)
    title = StringCol(dbName='title', notNull=True)
    description = StringCol(dbName='description', notNull=False, default=None)
    potemplates = MultipleJoin('POTemplate', joinColumn='potemplatename')

