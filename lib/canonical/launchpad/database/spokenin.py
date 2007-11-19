# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['SpokenIn']

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.launchpad.interfaces import ISpokenIn
from canonical.database.sqlbase import SQLBase

class SpokenIn(SQLBase):
    """A way of telling which languages are spoken in which countries.

    This table maps a language which is SpokenIn a country.
    """

    implements(ISpokenIn)

    _table = 'SpokenIn'

    country = ForeignKey(dbName='country', notNull=True, foreignKey='Country')
    language = ForeignKey(dbName='language', notNull=True,
                          foreignKey='Language')

