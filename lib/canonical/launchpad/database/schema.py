# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['SchemaSet', 'Schema', 'Label']

from zope.interface import implements

from sqlobject import (
    ForeignKey, StringCol, SQLMultipleJoin, SQLRelatedJoin, SQLObjectNotFound)
from canonical.database.sqlbase import SQLBase, sqlvalues

from canonical.launchpad.interfaces import (
    ISchemaSet, ISchema, ILabel, NotFoundError)


class SchemaSet:
    """The set of schemas."""
    implements(ISchemaSet)

    def __getitem__(self, name):
        try:
            schema = Schema.byName(name)
        except SQLObjectNotFound:
            raise NotFoundError(name)
        else:
            return schema

    def keys(self):
        return [schema.name for schema in Schema.select()]


class Schema(SQLBase):
    implements(ISchema)

    _table = 'Schema'

    owner = ForeignKey(foreignKey='Person', dbName='owner', notNull=True)
    name = StringCol(dbName='name', notNull=True, alternateID=True)
    title = StringCol(dbName='title', notNull=True)
    description = StringCol(dbName='description', notNull=True)
    #extensible = BoolCol(dbName='extensible', notNull=True)
    labels = SQLMultipleJoin('Label', joinColumn='schema')

    def label(self, name):
        """SELECT * FROM Label WHERE Label.schema = id AND Label.name = name;
        """
        label = Label.selectOne('Label.schema = %d AND Label.name = %s' %
            sqlvalues(self.id, name))
        if label is None:
            raise NotFoundError(name)
        return label


class Label(SQLBase):
    implements(ILabel)

    _table = 'Label'

    schema = ForeignKey(foreignKey='Schema', dbName='schema', notNull=True)
    name = StringCol(dbName='name', notNull=True)
    title = StringCol(dbName='title', notNull=True)
    description = StringCol(dbName='description', notNull=True),

    persons = SQLRelatedJoin('Person', joinColumn='label',
        otherColumn='person', intermediateTable='PersonLabel')

