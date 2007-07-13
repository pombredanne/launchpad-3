# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'MailingList',
    'MailingListRegistry',
    ]

import pytz

from datetime import datetime
from sqlobject import ForeignKey, IntCol, StringCol
from zope.component import getUtility
from zope.interface import implements

from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import (
    ILaunchpadCelebrities, IMailingList, IMailingListRegistry)
from canonical.lp.dbschema import MailingListStatus


class MailingList(SQLBase):
    implements(IMailingList)

    def __repr__(self):
        return '<MailingList for team "%s"; status=%s at %#x>' % (
            self.team.name, self.status.name, id(self))

    team = ForeignKey(dbName='team', foreignKey='Person')

    registrant = ForeignKey(dbName='registrant', foreignKey='Person')

    date_registered = UtcDateTimeCol(notNull=True, default=None)

    reviewer = ForeignKey(dbName='reviewer', foreignKey='Person', default=None)

    date_reviewed = UtcDateTimeCol(notNull=True, default=None)

    date_activated = UtcDateTimeCol(notNull=True, default=None)

    status = EnumCol(schema=MailingListStatus,
                     default=MailingListStatus.REGISTERED)

    welcome_message_text = StringCol(default=None)

    def review(self, reviewer, status):
        """See `IMailingList`"""
        # Only mailing lists which are in the REGISTERED state may be
        # reviewed.  This is the state for newly requested mailing lists.
        assert self.status == MailingListStatus.REGISTERED, (
            'Only unreviewed mailing lists may be reviewed')
        # A registered mailing list may only transition to either APPROVED or
        # DECLINED state.
        assert status in (MailingListStatus.APPROVED,
                          MailingListStatus.DECLINED), (
            'Reviewed lists may only be approved or declined')
        # The reviewer must be a Launchpad administrator.
        assert reviewer is not None and reviewer.inTeam(
            getUtility(ILaunchpadCelebrities).admin), (
            'Reviewer must be a Launchpad administrator')
        self.reviewer = reviewer
        self.status = status
        self.date_reviewed = datetime.now(pytz.timezone('UTC'))

    def construct(self):
        """See `IMailingList`"""
        assert self.status == MailingListStatus.APPROVED, (
            'Only approved mailing lists may be constructed')
        self.status = MailingListStatus.CONSTRUCTING

    def reportResult(self, status):
        """See `IMailingList`"""
        # State 1: From CONSTRUCTING to either ACTIVE or FAILED
        if self.status == MailingListStatus.CONSTRUCTING:
            assert status in (MailingListStatus.ACTIVE,
                              MailingListStatus.FAILED), (
                'Status result must be active or failed')
        # State 2: From MODIFIED to either ACTIVE or FAILED
        elif self.status == MailingListStatus.MODIFIED:
            assert status in (MailingListStatus.ACTIVE,
                              MailingListStatus.FAILED), (
                'Status result must be active or failed')
        # State 3: From DEACTIVATING to INACTIVE or FAILED
        elif self.status == MailingListStatus.DEACTIVATING:
            assert status in (MailingListStatus.INACTIVE,
                              MailingListStatus.FAILED), (
                'Status result must be inactive or failed')
        # This is not a valid state change.
        else:
            assert False, 'The mailing list is not waiting for results'
        self.status = status

    def deactivate(self):
        """See `IMailingList`"""
        assert self.status == MailingListStatus.ACTIVE, (
            'Only active mailing lists may be deactivated')
        self.status = MailingListStatus.DEACTIVATING

    def _get_welcome_message(self):
        return self.welcome_message_text

    def _set_welcome_message(self, text):
        if self.status == MailingListStatus.REGISTERED:
            # Don't change the status to MODIFIED because the mailing list
            # hasn't been created by Mailman yet.
            new_status = MailingListStatus.REGISTERED
        elif self.status == MailingListStatus.ACTIVE:
            new_status = MailingListStatus.MODIFIED
        else:
            assert False, (
                'Only registered or active mailing lists may be modified')
        self.welcome_message_text = text
        self.status = new_status

    welcome_message = property(_get_welcome_message, _set_welcome_message)


class MailingListRegistry:
    implements(IMailingListRegistry)

    def register(self, team):
        """See `IMailingListRegistry`"""
        assert team.isTeam(), (
            'Cannot register a list for a person who is not a team')
        assert self.getTeamMailingList(team) is None, (
            'Mailing list for team "%s" already exists' % team.name)
        return MailingList(team=team, registrant=team.teamowner,
                           date_registered=datetime.now(pytz.timezone('UTC')))

    def getTeamMailingList(self, team):
        """See `IMailingListRegistry`"""
        results = list(MailingList.selectBy(team=team))
        if len(results) == 0:
            return None
        elif len(results) == 1:
            return results[0]
        else:
            assert len(results) <= 1, (
                'Too many MailingLists registered for team "%s"' % team.name)

    @property
    def registered_lists(self):
        """See `IMailingListRegistry`"""
        return MailingList.selectBy(status=MailingListStatus.REGISTERED)

    @property
    def approved_lists(self):
        """See `IMailingListRegistry`"""
        return MailingList.selectBy(status=MailingListStatus.APPROVED)

    @property
    def modified_lists(self):
        """See `IMailingListRegistry`"""
        return MailingList.selectBy(status=MailingListStatus.MODIFIED)

    @property
    def deactivated_lists(self):
        """See `IMailingListRegistry`"""
        return MailingList.selectBy(status=MailingListStatus.DEACTIVATING)
