# Zope
from zope.interface import implements

# SQL imports
from sqlobject import StringCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.launchpad.interfaces import ICountry, ICountrySet

from canonical.database.sqlbase import SQLBase


#
# CONTENT CLASSES
#

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


class CountrySet(object):
    """A set of countries"""

    implements(ICountrySet)

    def __getitem__(self, iso3166code2):
        try:
            return Country.selectBy(iso3166code2=iso3166code2)[0]
        except IndexError:
            # Convert IndexError to KeyErrors to get Zope's NotFound page
            raise KeyError, id

    def __iter__(self):
        for row in Country.select():
            yield row


