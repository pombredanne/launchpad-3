# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Bounty', 'BountySet']


from email.Utils import make_msgid

from zope.interface import implements
from zope.app.form.browser.interfaces import IAddFormCustomization

from sqlobject import ForeignKey, StringCol
from sqlobject import CurrencyCol
from sqlobject import SQLMultipleJoin, SQLRelatedJoin

from canonical.launchpad.interfaces import (
    BountyDifficulty, BountyStatus, IBounty, IBountySet, NotFoundError)

from canonical.database.sqlbase import SQLBase
from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol

from canonical.launchpad.database.message import Message, MessageChunk
from canonical.launchpad.database.bountymessage import BountyMessage
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
    bountystatus = EnumCol(enum=BountyStatus, notNull=True,
        default=BountyStatus.OPEN)
    difficulty = EnumCol(enum=BountyDifficulty, notNull=True,
        default=BountyDifficulty.NORMAL)
    reviewer = ForeignKey(dbName='reviewer', notNull=True, foreignKey='Person')
    datecreated = UtcDateTimeCol(notNull=True, default=DEFAULT)
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)

    # useful joins
    subscriptions = SQLMultipleJoin('BountySubscription', joinColumn='bounty',
        orderBy='id')
    products = SQLRelatedJoin('Product', joinColumn='bounty',
        intermediateTable='ProductBounty', otherColumn='product',
        orderBy='name')
    projects = SQLRelatedJoin('Project', joinColumn='bounty',
        intermediateTable='ProjectBounty', otherColumn='project',
        orderBy='name')
    distributions = SQLRelatedJoin('Distribution', joinColumn='bounty',
        intermediateTable='DistributionBounty', otherColumn='distribution',
        orderBy='name')

    # subscriptions
    def subscribe(self, person):
        # first see if a relevant subscription exists, and if so, update it
        for sub in self.subscriptions:
            if sub.person.id == person.id:
                return sub
        # since no previous subscription existed, create a new one
        return BountySubscription(
            bounty=self,
            person=person)

    def unsubscribe(self, person):
        # see if a relevant subscription exists, and if so, delete it
        for sub in self.subscriptions:
            if sub.person.id == person.id:
                sub.destroySelf()
                return

    # message related
    messages = SQLRelatedJoin('Message', joinColumn='bounty',
        otherColumn='message',
        intermediateTable='BountyMessage', orderBy='datecreated')

    def newMessage(self, owner, subject, content):
        """See IMessageTarget."""
        msg = Message(owner=owner, rfc822msgid=make_msgid('bounty'),
            subject=subject)
        chunk = MessageChunk(message=msg, content=content, sequence=1)
        bountymsg = BountyMessage(bounty=self, message=msg)
        return bountymsg

    def linkMessage(self, message):
        """See IMessageTarget."""
        for msg in self.messages:
            if msg == message:
                return None
        BountyMessage(bounty=self, message=message)
        return None

    @property
    def followup_subject(self):
        """See IMessageTarget."""
        if not self.messages:
            return 'Re: '+ self.title
        subject = self.messages[-1].title
        if subject[:4].lower() == 're: ':
            return subject
        return 'Re: ' + subject


class BountySet:
    """A set of bounties."""

    implements(IBountySet, IAddFormCustomization)

    def __init__(self):
        self.title = 'Launchpad Bounties'

    def __getitem__(self, name):
        bounty = Bounty.selectOneBy(name=name)
        if bounty is None:
            raise NotFoundError(name)
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
            owner=owner,
            reviewer=reviewer)

    @property
    def top_bounties(self):
        """See IBountySet."""
        return Bounty.select(orderBy=['-usdvalue'])[:5]

