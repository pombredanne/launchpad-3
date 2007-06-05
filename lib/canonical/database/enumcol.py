# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.security.proxy import isinstance as zope_isinstance

from sqlobject.col import SOCol, Col
from sqlobject.include import validators
import sqlobject.constraints as consts

from canonical.database.constants import DEFAULT

from canonical.launchpad.webapp.enum import DBSchema, Item

__all__ = [
'EnumCol',
    ]

class SODBSchemaEnumCol(SOCol):

    def __init__(self, **kw):
        self.schema = kw.pop('schema')
        if not issubclass(self.schema, DBSchema):
            raise TypeError('schema must be a DBSchema: %r' % self.schema)
        SOCol.__init__(self, **kw)
        self.validator = validators.All.join(
            DBSchemaValidator(schema=self.schema), self.validator)

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

        >>> validator = DBSchemaValidator(schema=BugTaskStatus)
        >>> validator.toPython(25, None) is BugTaskStatus.FIXCOMMITTED
        True

        """
        if value is None:
            return None
        if value is DEFAULT:
            return value
        return self.schema.items[value]

EnumCol = DBSchemaEnumCol



