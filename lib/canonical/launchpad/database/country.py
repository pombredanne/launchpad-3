# Zope interfaces
from zope.interface import implements

# SQL imports
from sqlobject import ForeignKey, StringCol
from sqlobject import RelatedJoin
from canonical.database.sqlbase import SQLBase

# canonical imports
from canonical.launchpad.interfaces import ICountry


class Country(SQLBase):
    implements(ICountry)

    _table = 'Country'

    iso3166code2 = StringCol(dbName='iso3166code2', notNull=True, unique=True,
        alternateID=True)
    iso3166code3 = StringCol(dbName='iso3166code3', notNull=True, unique=True,
        alternateID=True)
    name = StringCol(dbName='name', notNull=True)
    title = StringCol(dbName='title', notNull=False, default=None)
    description = StringCol(dbName='description', notNull=False,
        default=None)

    # RelatedJoin gives us also an addLanguage and removeLanguage for free
    languages = RelatedJoin('Language', joinColumn='country',
        otherColumn='language', intermediateTable='SpokenIn')

