# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Country', 'CountrySet']

from zope.interface import implements

from sqlobject import StringCol, RelatedJoin

from canonical.launchpad.interfaces import ICountry, ICountrySet
from canonical.database.sqlbase import SQLBase


class Country(SQLBase):
    """A country."""

    implements(ICountry)

    _table = 'Country'

    # default to listing newest first
    _defaultOrder = 'name'

    # db field names
    name = StringCol(dbName='name', unique=True, notNull=True)
    iso3166code2 = StringCol(dbName='iso3166code2', unique=True,
                             notNull=True)
    iso3166code3 = StringCol(dbName='iso3166code3', unique=True,
                             notNull=True)
    title = StringCol(dbName='title', notNull=True)
    description = StringCol(dbName='description', notNull=True)
    languages = RelatedJoin('Language', joinColumn='country',
                            otherColumn='language',
                            intermediateTable='SpokenIn')


class CountrySet:
    """A set of countries"""

    implements(ICountrySet)

    def __getitem__(self, iso3166code2):
        country = Country.selectOneBy(iso3166code2=iso3166code2)
        if country is None:
            raise KeyError(iso3166code2)
        return country

    def __iter__(self):
        for row in Country.select():
            yield row

