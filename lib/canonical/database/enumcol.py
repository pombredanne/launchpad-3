# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.security.proxy import isinstance as zope_isinstance

from storm.properties import SimpleProperty
from storm.variables import Variable
from storm.sqlobject import PropertyAdapter

from canonical.launchpad.webapp.enum import DBSchema, Item

__all__ = [
'EnumCol',
    ]


class DBSchemaVariable(Variable):
    def __init__(self, schema, *args, **kwargs):
        self.schema = schema
        Variable.__init__(self, *args, **kwargs)

    def _parse_set(self, value, db):
        if db:
            return self.schema.items[value]
        else:
            if isinstance(value, int):
                raise TypeError(
                    'Need to set a dbschema Enum column to a dbschema Item,'
                    ' not an int')
            if not zope_isinstance(value, Item):
                # We use repr(value) because if it's a tuple (yes, it has been
                # seen in some cases) then the interpolation would swallow that
                # fact, confusing poor programmers like Daniel.
                raise TypeError('Not a DBSchema Item: %s' % repr(value))
            # Using != rather than 'is not' in order to cope with Security Proxy
            # proxied items and their schemas.
            if value.schema != self.schema:
                raise TypeError('DBSchema Item from wrong class, %r != %r' % (
                    value.schema, self.schema))
            return value.value


# XXX: Why don't we call this DBSchemaCol?
class EnumCol(PropertyAdapter, SimpleProperty):
    variable_class = DBSchemaVariable
    def __init__(self, *args, **kwargs):
        schema = kwargs.pop('schema')
        if not issubclass(schema, DBSchema):
            raise TypeError('schema must be a DBSchema: %r' % schema)
        self._kwargs = {'schema': schema}
        super(EnumCol, self).__init__(*args, **kwargs)

