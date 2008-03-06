# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from storm.properties import Enum
from storm.sqlobject import PropertyAdapter

from canonical.lazr import DBEnumeratedType

__all__ = [
'EnumCol',
    ]

class DBSchemaEnumCol(PropertyAdapter, Enum):
    def __init__(self, **kw):
        try:
            self.enum = kw.pop('enum')
            source = 'enum'
        except KeyError:
            self.enum = kw.pop('schema')
            source = 'schema'
        if not issubclass(self.enum, DBEnumeratedType):
            raise TypeError(
                '%s must be a DBEnumeratedType: %r'
                % (source, type(self.enum)))
        self._kwargs = {
            'map': dict((item, item.value) for item in self.enum.items)
            }
        super(DBSchemaEnumCol, self).__init__(**kw)


EnumCol = DBSchemaEnumCol



