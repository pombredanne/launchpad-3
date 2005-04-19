# Zope
from zope.interface import implements

# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol
from sqlobject import CurrencyCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.launchpad.interfaces import IBounty, IBountySet, \
    IAddFormCustomization

from canonical.database.sqlbase import SQLBase
from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.launchpad.database.bountysubscription import BountySubscription

# Python
import datetime

class Bounty(SQLBase):
    """A bounty."""

    implements(IBounty)

    # default to listing newest first
    _defaultOrder = '-id'

    # db field names
    name = StringCol(unique=True, notNull=True)
    title = StringCol( notNull=True)
    summary = StringCol(notNull=True)
    description = StringCol( notNull=True)
    usdvalue = CurrencyCol(notNull=True)
    difficulty = IntCol(notNull=True, default=50)
    duration = DateTimeCol(notNull=True,
                           default=datetime.timedelta(7))
    reviewer = ForeignKey(dbName='reviewer', notNull=True,
                          foreignKey='Person')
    datecreated = UtcDateTimeCol(notNull=True,
                                 default=DEFAULT)
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)

    # useful joins
    subscriptions = MultipleJoin('BountySubscription', joinColumn='bounty')

    products = RelatedJoin('Product', joinColumn='bounty',
                    intermediateTable='ProductBounty',
                    otherColumn='product')

    projects = RelatedJoin('Project', joinColumn='bounty',
                    intermediateTable='ProjectBounty',
                    otherColumn='project')

    distributions = RelatedJoin('Distribution', joinColumn='bounty',
                    intermediateTable='DistroBounty',
                    otherColumn='distribution')

    # subscriptions
    def subscribe(self, person, subscription):
        # first see if a relevant subscription exists, and if so, update it
        for sub in self.subscriptions:
            if sub.person.id == person.id:
                sub.subscription = int(subscription)
                return sub
        # since no previous subscription existed, create a new one
        return BountySubscription(
            bounty=self,
            person=person,
            subscription=subscription)

    def unsubscribe(self, person):
        # see if a relevant subscription exists, and if so, delete it
        for sub in self.subscriptions:
            if sub.person.id == person.id:
                BountySubscription.delete(sub.id)
                return

    def checkPermission(self, principal, permission):
        if permission == 'launchpad.Edit':
            return self.owner.id == principal.id

class BountySet(object):
    """A set of bounties"""

    implements(IBountySet, IAddFormCustomization)

    def __init__(self):
        self.title = 'A Set of Bounties'

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


