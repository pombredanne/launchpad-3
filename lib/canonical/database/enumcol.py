# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.security.proxy import isinstance as zope_isinstance

from sqlobject.col import SOCol, Col
from sqlobject.include import validators
import sqlobject.constraints as consts

from canonical.database.constants import DEFAULT

from canonical.lazr import DBEnumeratedType, DBItem

__all__ = [
'EnumCol',
    ]

class SODBSchemaEnumCol(SOCol):

    enum = None

    def __init__(self, **kw):
        # XXX: thumper 2007-03-23:
        # While it would be great to just switch everything over at once,
        # in reality it just isn't feasible, so look initially for a key
        # enum, and fall back to schema.
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
        SOCol.__init__(self, **kw)
        validator = DBEnumeratedTypeValidator(self.enum)
        self.validator = validators.All.join(validator, self.validator)

    def autoConstraints(self):
        return [consts.isInt]

    def _sqlType(self):
        return 'INT'


class DBSchemaEnumCol(Col):
    baseClass = SODBSchemaEnumCol


class DBEnumeratedTypeValidator(validators.Validator):

    def __init__(self, enum):
        validators.Validator.__init__(self)
        self.enum = enum

    def fromPython(self, value, state):
        """Convert from DBItem to int.

        >>> from canonical.database.tests.enumeration import *
        >>> validator = DBEnumeratedTypeValidator(enum=DBTestEnumeration)
        >>> validator.fromPython(DBTestEnumeration.VALUE1, None)
        1
        >>> validator.fromPython(UnrelatedTestEnumeration.VALUE1, None)
        Traceback (most recent call last):
        ...
        TypeError: DBItem from wrong type, 'DBTestEnumeration' != 'UnrelatedTestEnumeration'

        >>> validator.fromPython(1, None)
        Traceback (most recent call last):
        ...
        TypeError: Need to set an EnumeratedType Enum column to an Item, not an int
        >>> validator.fromPython(tuple(), None)
        Traceback (most recent call last):
        ...
        TypeError: Not a DBItem: <type 'tuple'>

        """
        if value is None:
            return None
        if value is DEFAULT:
            return value
        if isinstance(value, int):
            raise TypeError(
                'Need to set an EnumeratedType Enum column to an Item,'
                ' not an int')
        if not zope_isinstance(value, DBItem):
            # We use repr(value) because if it's a tuple (yes, it has been
            # seen in some cases) then the interpolation would swallow that
            # fact, confusing poor programmers like Daniel.
            raise TypeError('Not a DBItem: %r' % type(value))
        # Using != rather than 'is not' in order to cope with Security Proxy
        # proxied items and their schemas.
        if self.enum != value.enum:
            raise TypeError('DBItem from wrong type, %r != %r' % (
                self.enum.name, value.enum.name))
        return value.value

    def toPython(self, value, state):
        """Convert from int to DBSchema Item.

        >>> from canonical.database.tests.enumeration import *
        >>> validator = DBEnumeratedTypeValidator(enum=DBTestEnumeration)
        >>> validator.toPython(1, None)
        <DBItem DBTestEnumeration.VALUE1, (1) Some value>

        >>> validator.toPython(2, None)
        <DBItem DBTestEnumeration.VALUE2, (2) Some other value>

        Even though it should never happen if the database and
        the associated types are in sync, a KeyError is raised
        if the value is not found.

        >>> validator.toPython(3, None)
        Traceback (most recent call last):
        ...
        KeyError: 3

        """
        if value is None:
            return None
        if value is DEFAULT:
            return value
        return self.enum.items[value]

EnumCol = DBSchemaEnumCol



