# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['SchemaSet', 'Schema', 'Label']

from zope.interface import implements

from sqlobject import ForeignKey, StringCol, MultipleJoin
from sqlobject import RelatedJoin, SQLObjectNotFound
from canonical.database.sqlbase import SQLBase, quote

from canonical.launchpad.interfaces import ISchemaSet, ISchema, ILabel


class SchemaSet:
    """The set of schemas."""
    implements(ISchemaSet)

    def __getitem__(self, name):
        try:
            schema = Schema.byName(name)
        except SQLObjectNotFound:
            raise KeyError, name
        else:
            return schema

    def keys(self):
        return [schema.name for schema in Schema.select()]


class Schema(SQLBase):
    implements(ISchema)

    _table = 'Schema'

    _columns = [
        ForeignKey(name='owner', foreignKey='Person',
            dbName='owner', notNull=True),
        StringCol(name='name', dbName='name', notNull=True, alternateID=True),
        StringCol(name='title', dbName='title', notNull=True),
        StringCol(name='description', dbName='description', notNull=True),
        #BoolCol(name='extensible', dbName='extensible', notNull=True),
    ]

    _labelsJoin = MultipleJoin('Label', joinColumn='schema')

    def labels(self):
        return iter(self._labelsJoin)

    def label(self, name):
        """SELECT * FROM Label WHERE Label.schema = id AND Label.name = name;
        """
        label = Label.selectOne('Label.schema = %d AND Label.name = %s' %
            sqlvalues(self.id, name))
        if label is None:
            raise KeyError, name
        return label


class Label(SQLBase):
    implements(ILabel)

    _table = 'Label'

    _columns = [
        ForeignKey(name='schema', foreignKey='Schema', dbName='schema',
            notNull=True),
        StringCol(name='name', dbName='name', notNull=True),
        StringCol(name='title', dbName='title', notNull=True),
        StringCol(name='description', dbName='description', notNull=True),
        ]

    _personsJoin = RelatedJoin('Person', joinColumn='label',
        otherColumn='person', intermediateTable='PersonLabel')

    def persons(self):
        for person in self._personsJoin:
            yield person[0]

