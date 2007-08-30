# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Country', 'CountrySet', 'Continent']

from zope.interface import implements

from sqlobject import StringCol, SQLRelatedJoin, ForeignKey

from canonical.launchpad.interfaces import (
    ICountry, ICountrySet, IContinent, NotFoundError)
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
    description = StringCol(dbName='description')
    continent = ForeignKey(
        dbName='continent', foreignKey='Continent', default=None)
    languages = SQLRelatedJoin(
        'Language', joinColumn='country', otherColumn='language',
        intermediateTable='SpokenIn')


class CountrySet:
    """A set of countries"""

    implements(ICountrySet)

    def __getitem__(self, iso3166code2):
        country = Country.selectOneBy(iso3166code2=iso3166code2)
        if country is None:
            raise NotFoundError(iso3166code2)
        return country

    def __iter__(self):
        for row in Country.select():
            yield row


class Continent(SQLBase):
    """See IContinent."""

    implements(IContinent)

    _table = 'Continent'
    _defaultOrder = ['name', 'id']

    name = StringCol(unique=True, notNull=True)
    code = StringCol(unique=True, notNull=True)
