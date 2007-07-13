# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import datetime

from sqlobject import (
    BoolCol, ForeignKey, IntCol, MultipleJoin, SQLMultipleJoin,
    SQLObjectNotFound, SQLRelatedJoin, StringCol)
from sqlobject.sqlbuilder import AND, OR, SQLConstant
from zope.interface import implements

from canonical.database.constants import UTC_NOW, DEFAULT
from canonical.database.enumcol import EnumCol
from canonical.launchpad.interfaces import IMailingList, IMailingListRegistry
from canonical.lp.dbschema import MailingListStatus


class MailingList(SQLBase):
    implements(IMailingList)

    team = ForeignKey(dbName='team', foreignKey='Person')

    registrant = ForeignKey(dbName='registrant', foreignKey='Person')
    date_registered = UtcDateTimeCol(notNull=True, default=UTC_NOW)

    reviewer = ForeignKey(dbName='reviewer', foreignKey='Person', default=None)
    date_reviewed = UtcDateTimeCol(notNull=True, default=UTC_NOW)

    date_activated = UtcDateTimeCol(notNull=True, default=UTC_NOW)

    status = EnumCol(schema=MailingListStatus, default=None)

    welcome_message_text = StringCol(default=None)

    def review(self, reviewer, status):
        # Only mailing lists which are in the REGISTERED state may be
        # reviewed.  This is the state for newly requested mailing lists.
        assert self.status == MailingListStatus.REGISTERED, (
            'Only registered mailing lists may be reviewed.')
        # A registered mailing list may only transition to either APPROVED or
        # DECLINED state.
        assert status in (MailingListStatus.APPROVED,
                          MailingListStatus.DECLINED), (
            'Reviewed lists may only be approved or declined')
        # The reviewer must be a Launchpad administrator.
        # XXX
        self.reviewer = reviewer
        self.status = status
        self.date_reviewed = datetime.datetime.now()

    def construct(self):
        assert self.status == MailingListStatus.APPROVED, (
            'Only approved mailing lists may be constructed')
        self.status = MailingListStatus.CONSTRUCTING

    def reportConstructionResult(self, status):
        assert self.status == MailingListStatus.CONSTRUCTING, (
            'The mailing list is not under construction')
        assert status in (MailingListStatus.ACTIVE,
                          MailingListStatus.FAILED), (
            'Construction status must be active or failed')
        self.status = status

    def deactivate(self):
        assert self.status == MailingListStatus.ACTIVE, (
            'Only active mailing lists may be deactivated')


class MailingListRegistry:
    implements(IMailingListRegistry)

    def register(self, team):
        # XXX

    def getTeamMailingList(self, team):
        # XXX

    @property
    def registered_lists(self):
        # XXX

    @property
    def approved_lists(self):
        # XXX
