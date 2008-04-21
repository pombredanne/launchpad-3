# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from storm import sqlobject
from storm.properties import SimpleProperty
from storm.variables import Variable

from zope.security.proxy import isinstance as zope_isinstance

from canonical.lazr import DBEnumeratedType, DBItem

__all__ = [
'DBEnum',
'EnumCol',
    ]


class DBEnumVariable(Variable):
    """A Storm variable class representing a DBEnumeratedType."""

    def __init__(self, *args, **kwargs):
        self._enum = kwargs.pop("enum")
        if not issubclass(self._enum, DBEnumeratedType):
            raise TypeError(
                '%s must be a DBEnumeratedType: %r'
                % (source, type(self._enum)))
        super(DBEnumVariable, self).__init__(*args, **kwargs)

    def parse_set(self, value, from_db):
        if from_db:
            return self._enum.items[value]
        else:
            if not zope_isinstance(value, DBItem):
                raise TypeError("Not a DBItem: %r" % type(value))
            if self._enum != value.enum:
                raise TypeError("DBItem from wrong type, %r != %r" % (
                        self._enum.name, value.enum.name))
            return value

    def parse_get(self, value, to_db):
        if to_db:
            return value.value
        else:
            return value


class DBEnum(SimpleProperty):
    variable_class = DBEnumVariable


class DBSchemaEnumCol(sqlobject.PropertyAdapter, DBEnum):
    def __init__(self, **kw):
        try:
            enum = kw.pop('enum')
        except KeyError:
            enum = kw.pop('schema')
        self._kwargs = {
            'enum': enum
            }
        super(DBSchemaEnumCol, self).__init__(**kw)


EnumCol = DBSchemaEnumCol



