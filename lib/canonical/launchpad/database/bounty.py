# Zope
from zope.interface import implements

# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol
from sqlobject import CurrencyCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.launchpad.interfaces import IBounty, IBountySet, \
                                           IAddFormCustomization, \
                                           IObjectAuthorization

from canonical.database.sqlbase import SQLBase
from canonical.database.constants import DEFAULT

# Python
import datetime

class Bounty(SQLBase):
    """A bounty."""

    implements(IBounty, IObjectAuthorization)

    # default to listing newest first
    _defaultOrder = '-id'

    # db field names
    name = StringCol(dbName='name', unique=True, notNull=True)
    title = StringCol(dbName='title', notNull=True)
    summary = StringCol(dbName='summary', notNull=True)
    description = StringCol(dbName='description', notNull=True)
    usdvalue = CurrencyCol(dbName='usdvalue', notNull=True)
    difficulty = IntCol(dbName='difficulty', notNull=True, default=50)
    duration = DateTimeCol(dbName='duration', notNull=True,
                           default=datetime.timedelta(7))
    reviewer = ForeignKey(dbName='reviewer', notNull=True,
                          foreignKey='Person')
    datecreated = DateTimeCol(dbName='datecreated', notNull=True,
                          default=DEFAULT)
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)

    def checkPermission(self, principal, permission):
        if permission == 'launchpad.Edit':
            return self.owner.id == principal.id


class BountySet(object):
    """A set of bounties"""

    implements(IBountySet, IAddFormCustomization)

    def __getitem__(self, name):
        try:
            return Bounty.selectBy(name=name)[0]
        except IndexError:
            # Convert IndexError to KeyErrors to get Zope's NotFound page
            raise KeyError, id

    def __iter__(self):
        for row in Bounty.select():
            yield row

    def add(self, ob):
        '''Add a new Bounty. This method is called by the addform. ob will
        be a thing that looks like an IBounty'''
        kw = {}
        attrs = ['name', 'title', 'summary', 'description']
        for a in attrs:
            kw[a] = getattr(ob, a, None)
        kw['ownerID'] = ob.owner.id

        # create the bounty in the db
        bounty = Bounty(**kw)

        return ob # Return this rather than the bounty we created from it,
                  # as the return value must be adaptable to the interface
                  # used to generate the form.


