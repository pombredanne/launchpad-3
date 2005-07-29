# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Poll', 'PollSet', 'PollOption', 'PollOptionSet',
           'VoteCast', 'Vote']

from datetime import datetime
import pytz

from zope.interface import implements

from sqlobject import (
    ForeignKey, StringCol, BoolCol, SQLObjectNotFound, IntCol, AND)

from canonical.lp.dbschema import PollSecrecy, PollAlgorithm, EnumCol

from canonical.database.sqlbase import SQLBase
from canonical.database.datetimecol import UtcDateTimeCol

from canonical.launchpad.interfaces import (
    IPoll, IPollSet, IPollOption, IPollOptionSet, IVote, IVoteCast,
    PollStatus, IPollOptionSubset)


class Poll(SQLBase):
    """See IPoll."""

    implements(IPoll)
    _table = 'Poll'
    _defaultOrder = 'title'

    team = ForeignKey(dbName='team', foreignKey='Person', notNull=True)

    name = StringCol(dbName='name', notNull=True)

    title = StringCol(dbName='title', notNull=True, unique=True)

    dateopens = UtcDateTimeCol(dbName='dateopens', notNull=True)

    datecloses = UtcDateTimeCol(dbName='datecloses', notNull=True)

    proposition = StringCol(dbName='proposition',  notNull=True)

    type = EnumCol(dbName='type', schema=PollAlgorithm,
                   default=PollAlgorithm.CONDORCET)

    allowspoilt = BoolCol(dbName='allowspoilt', default=True, notNull=True)

    secrecy = EnumCol(dbName='secrecy', schema=PollSecrecy,
                      default=PollSecrecy.SECRET)

    def isOpen(self, when=None):
        """See IPoll."""
        if when is None:
            when = datetime.now(pytz.timezone('UTC'))
        return (self.datecloses >= when and self.dateopens <= when)

    def isClosed(self, when=None):
        """See IPoll."""
        if when is None:
            when = datetime.now(pytz.timezone('UTC'))
        return self.datecloses <= when

    def getAllOptions(self):
        """See IPoll."""
        return IPollOptionSubset(self).getAll()

    def personVoted(self, person):
        """See IPoll."""
        results = VoteCast.selectBy(personID=person.id, pollID=self.id)
        return bool(results.count())


class PollSet:
    """See IPollSet."""

    implements(IPollSet)

    _defaultOrder = Poll._defaultOrder

    def new(self, team, name, title, proposition, dateopens, datecloses,
            poll_type, secrecy, allowspoilt):
        """See IPollSet."""
        return Poll(teamID=team.id, name=name, title=title,
                proposition=proposition, dateopens=dateopens,
                datecloses=datecloses, type=poll_type, secrecy=secrecy,
                allowspoilt=allowspoilt)

    def selectByTeam(self, team, status=PollStatus.ALL, orderBy=None, when=None):
        """See IPollSet."""
        if when is None:
            when = datetime.now(pytz.timezone('UTC'))

        if orderBy is None:
            orderBy = self._defaultOrder

        teamfilter = Poll.q.teamID == team.id
        results = Poll.select(teamfilter)
        status = set(status)

        if PollStatus.OPEN not in status:
            openpolls = Poll.select(
                AND(teamfilter, Poll.q.dateopens<=when, Poll.q.datecloses>when))
            results = results.except_(openpolls)

        if PollStatus.CLOSED not in status:
            closedpolls = Poll.select(AND(teamfilter, Poll.q.datecloses<=when))
            results = results.except_(closedpolls)

        if PollStatus.NOT_YET_OPENED not in status:
            notyetopenedpolls = Poll.select(
                AND(teamfilter, Poll.q.dateopens>when))
            results = results.except_(notyetopenedpolls)

        return results.orderBy(orderBy)

    def getByTeamAndName(self, team, name, default=None):
        """See IPollSet."""
        query = AND(Poll.q.teamID == team.id, Poll.q.name == name)
        try:
            return Poll.selectOne(query)
        except SQLObjectNotFound:
            return default


class PollOption(SQLBase):
    """See IPollOption."""

    implements(IPollOption)
    _table = 'PollOption'
    _defaultOrder = 'shortname'

    poll = ForeignKey(dbName='poll', foreignKey='Poll', notNull=True)

    name = StringCol(dbName='name', notNull=True)

    shortname = StringCol(dbName='shortname', notNull=True)

    active = BoolCol(dbName='active', notNull=True, default=False)

    @property
    def title(self):
        """See IPollOption."""
        return self.shortname


class PollOptionSet:
    """See IPollOptionSet."""

    implements(IPollOptionSet)

    def new(self, poll, name, shortname, active=True):
        """See IPollOptionSet."""
        return PollOption(
            pollID=poll.id, name=name, shortname=shortname, active=active)

    def selectByPoll(self, poll, only_active=False):
        """See IPollOptionSet."""
        query = PollOption.q.pollID == poll.id
        if only_active:
            query = AND(query, PollOption.q.active==True)
        return PollOption.select(query)

    def getByPollAndId(self, poll, option_id, default=None):
        """See IPollOptionSet."""
        query = AND(PollOption.q.pollID == poll.id, 
                    PollOption.q.id == option_id)
        try:
            return PollOption.selectOne(query)
        except SQLObjectNotFound:
            return default


class VoteCast(SQLBase):
    """See IVoteCast."""

    implements(IVoteCast)
    _table = 'VoteCast'

    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)

    poll = ForeignKey(dbName='poll', foreignKey='Poll', notNull=True)


class Vote(SQLBase):
    """See IVote."""

    implements(IVote)
    _table = 'Vote'

    person = ForeignKey(dbName='person', foreignKey='Person')

    poll = ForeignKey(dbName='poll', foreignKey='Poll', notNull=True)

    option = ForeignKey(dbName='polloption', foreignKey='PollOption',
                        notNull=True)

    preference = IntCol(dbName='preference', notNull=True)

    token = StringCol(dbName='token', notNull=True, unique=True)

