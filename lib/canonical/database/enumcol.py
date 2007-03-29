# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.security.proxy import isinstance as zope_isinstance

from sqlobject.col import SOCol, Col
from sqlobject.include import validators
import sqlobject.constraints as consts

from canonical.database.constants import DEFAULT

from canonical.launchpad.webapp.enum import DBSchema, DBEnumeratedType, DBItem
from canonical.launchpad.webapp.enum import DBSchemaItem as Item

__all__ = [
'EnumCol',
    ]

class SODBSchemaEnumCol(SOCol):

    enum = None
    
    def __init__(self, **kw):
        # XXX: thumper 2007-03-23
        # While it would be great to just switch everything over at once,
        # in reality it just isn't feasible, so look initially for a key
        # enum, and fall back to schema.
        try:
            self.enum = kw.pop('enum')
            if not issubclass(self.enum, DBEnumeratedType):
                raise TypeError(
                    'enum must be a DBEnumeratedType: %r' % self.enum)
        except KeyError:
            self.schema = kw.pop('schema')
            if not issubclass(self.schema, DBSchema):
                raise TypeError('schema must be a DBSchema: %r' % self.schema)
        SOCol.__init__(self, **kw)
        if self.enum is not None:
            validator = DBEnumeratedTypeValidator(self.enum)
        else:
            validator = DBSchemaValidator(schema=self.schema)
        self.validator = validators.All.join(validator, self.validator)

    def autoConstraints(self):
        return [consts.isInt]

    def _sqlType(self):
        return 'INT'


class DBSchemaEnumCol(Col):
    baseClass = SODBSchemaEnumCol


class DBSchemaValidator(validators.Validator):
            
    def __init__(self, **kw):
        self.schema = kw.pop('schema')
        validators.Validator.__init__(self, **kw)

    def fromPython(self, value, state):
        """Convert from DBSchema Item to int.

        >>> from canonical.lp.dbschema import BugTaskStatus, ImportTestStatus
        >>> validator = DBSchemaValidator(schema=BugTaskStatus)
        >>> validator.fromPython(BugTaskStatus.FIXCOMMITTED, None)
        25
        >>> validator.fromPython(tuple(), None)
        Traceback (most recent call last):
        ...
        TypeError: Not a DBSchema Item: ()
        >>> validator.fromPython(ImportTestStatus.NEW, None)
        Traceback (most recent call last):
        ...
        TypeError: DBSchema Item from wrong class, <class 'canonical.lp.dbschema.ImportTestStatus'> != <class 'canonical.lp.dbschema.BugTaskStatus'>
        >>>

        """
        if value is None:
            return None
        if value is DEFAULT:
            return value
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
    
    def toPython(self, value, state):
        """Convert from int to DBSchema Item.

        >>> from canonical.lp.dbschema import BugTaskStatus
        >>> validator = DBSchemaValidator(schema=BugTaskStatus)
        >>> validator.toPython(25, None) is BugTaskStatus.FIXCOMMITTED
        True

        """
        if value is None:
            return None
        if value is DEFAULT:
            return value
        return self.schema.items[value]


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
        >>> validator.fromPython(InheritedTestEnumeration.VALUE1, None)
        1
        >>> validator.fromPython(ExtendedTestEnumeration.VALUE1, None)
        1
        >>> validator.fromPython(UnrelatedTestEnumeration.VALUE1, None)
        Traceback (most recent call last):
        ...
        TypeError: DBItem from wrong type, 'DBTestEnumeration' not in ['UnrelatedTestEnumeration']

        >>> validator.fromPython(1, None)
        Traceback (most recent call last):
        ...
        TypeError: Need to set an EnumeratedType Enum column to an Item, not an int
        >>> validator.fromPython(tuple(), None)
        Traceback (most recent call last):
        ...
        TypeError: Not a DBItem: ()

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
            raise TypeError('Not a DBItem: %s' % repr(value))
        # Using != rather than 'is not' in order to cope with Security Proxy
        # proxied items and their schemas.
        if not self.enum.name in value.used_in_enums:
            raise TypeError('DBItem from wrong type, %r not in %r' % (
                self.enum.name, value.used_in_enums))
        return value.db_value
    
    def toPython(self, value, state):
        """Convert from int to DBSchema Item.

        >>> from canonical.database.tests.enumeration import *
        >>> validator = DBEnumeratedTypeValidator(enum=DBTestEnumeration)
        >>> validator.toPython(1, None)
        <DBItem DBTestEnumeration.VALUE1, (1) Some value>

        >>> validator.toPython(2, None)
        <DBItem DBTestEnumeration.VALUE2, (2) Some other value>

        Even though it should never happen if the database and
        the associated types are in sync, a LookupError is raised
        if the value is not found.

        >>> validator.toPython(3, None)
        Traceback (most recent call last):
        ...
        LookupError: 3

        """
        if value is None:
            return None
        if value is DEFAULT:
            return value
        return self.enum.getTerm(value)

EnumCol = DBSchemaEnumCol



