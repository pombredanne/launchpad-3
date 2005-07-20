# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Bounty', 'BountySet']


import datetime

from zope.interface import implements
from zope.app.form.browser.interfaces import IAddFormCustomization

from sqlobject import ForeignKey, IntCol, StringCol, IntervalCol
from sqlobject import CurrencyCol
from sqlobject import MultipleJoin, RelatedJoin

from canonical.launchpad.interfaces import IBounty, IBountySet

from canonical.database.sqlbase import SQLBase
from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.launchpad.database.bountysubscription import BountySubscription


class Bounty(SQLBase):
    """A bounty."""

    implements(IBounty)

    # default to listing newest first
    _defaultOrder = '-id'

    # db field names
    name = StringCol(unique=True, notNull=True)
    title = StringCol(notNull=True)
    summary = StringCol(notNull=True)
    description = StringCol( notNull=True)
    usdvalue = CurrencyCol(notNull=True)
    difficulty = IntCol(notNull=True, default=50)
    duration = IntervalCol(notNull=True, default=datetime.timedelta(7))
    reviewer = ForeignKey(dbName='reviewer', notNull=True, foreignKey='Person')
    datecreated = UtcDateTimeCol(notNull=True, default=DEFAULT)
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
                sub.subscription = subscription
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


class BountySet:
    """A set of bounties."""

    implements(IBountySet, IAddFormCustomization)

    def __init__(self):
        self.title = 'A Set of Bounties'

    def __getitem__(self, name):
        bounty = Bounty.selectOneBy(name=name)
        if bounty is None:
            raise KeyError, name
        return bounty

    def __iter__(self):
        for row in Bounty.select():
            yield row

    def new(self, name, title, summary, description, usdvalue, owner,
            reviewer):
        return Bounty(
            name=name,
            title=title,
            summary=summary,
            description=description,
            usdvalue=usdvalue,
            ownerID=owner.id,
            reviewerID=reviewer.id)

