# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'MailingList',
    'MailingListSet',
    ]

import pytz

from datetime import datetime
from sqlobject import ForeignKey, StringCol
from zope.component import getUtility
from zope.interface import implements

from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.launchpad.interfaces import (
    ILaunchpadCelebrities, IMailingList, IMailingListSet, MailingListStatus)


class MailingList(SQLBase):
    """'The mailing list for a team.

    Teams may have at most one mailing list, and a mailing list is associated
    with exactly one team.  This table manages the state changes that a team
    mailing list can go through, and it contains information that will be used
    to instruct Mailman how to create, delete, and modify mailing lists (via
    XMLRPC).
    """

    implements(IMailingList)

    team = ForeignKey(dbName='team', foreignKey='Person')

    registrant = ForeignKey(dbName='registrant', foreignKey='Person')

    date_registered = UtcDateTimeCol(notNull=True, default=None)

    reviewer = ForeignKey(dbName='reviewer', foreignKey='Person', default=None)

    date_reviewed = UtcDateTimeCol(notNull=True, default=None)

    date_activated = UtcDateTimeCol(notNull=True, default=None)

    status = EnumCol(enum=MailingListStatus,
                     default=MailingListStatus.REGISTERED)

    welcome_message_text = StringCol(default=None)

    def __repr__(self):
        return '<MailingList for team "%s"; status=%s at %#x>' % (
            self.team.name, self.status.name, id(self))

    def review(self, reviewer, status):
        """See `IMailingList`."""
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
        assert reviewer is not None and reviewer.hasParticipationEntryFor(
            getUtility(ILaunchpadCelebrities).mailing_list_experts), (
            'Reviewer must be a Mailing List Experts')
        self.reviewer = reviewer
        self.status = status
        self.date_reviewed = datetime.now(pytz.timezone('UTC'))

    def startConstructing(self):
        """See `IMailingList`."""
        assert self.status == MailingListStatus.APPROVED, (
            'Only approved mailing lists may be constructed')
        self.status = MailingListStatus.CONSTRUCTING

    def startUpdating(self):
        """See `IMailingList`."""
        assert self.status == MailingListStatus.MODIFIED, (
            'Only modified mailing lists may be updated')
        self.status = MailingListStatus.UPDATING

    def transitionToStatus(self, target_state):
        """See `IMailingList`."""
        # State: From CONSTRUCTING to either ACTIVE or FAILED
        if self.status == MailingListStatus.CONSTRUCTING:
            assert target_state in (MailingListStatus.ACTIVE,
                                    MailingListStatus.FAILED), (
                'target_state result must be active or failed')
        # State: From UPDATING to either ACTIVE or FAILED
        elif self.status == MailingListStatus.UPDATING:
            assert target_state in (MailingListStatus.ACTIVE,
                                    MailingListStatus.FAILED), (
                'target_state result must be active or failed')
        # State: From DEACTIVATING to INACTIVE or FAILED
        elif self.status == MailingListStatus.DEACTIVATING:
            assert target_state in (MailingListStatus.INACTIVE,
                                    MailingListStatus.FAILED), (
                'target_state result must be inactive or failed')
        else:
            raise AssertionError('Not a valid state transition')
        self.status = target_state

    def deactivate(self):
        """See `IMailingList`."""
        assert self.status == MailingListStatus.ACTIVE, (
            'Only active mailing lists may be deactivated')
        self.status = MailingListStatus.DEACTIVATING

    def _get_welcome_message(self):
        return self.welcome_message_text

    def _set_welcome_message(self, text):
        if self.status == MailingListStatus.REGISTERED:
            # Do nothing because the status does not change.  When setting the
            # welcome_message on a newly registered mailing list the XMLRPC
            # layer will essentially tell Mailman to initialize this attribute
            # at list construction time.  It is enough to just set the
            # database attribute to properly notify Mailman what to do.
            pass
        elif self.status == MailingListStatus.ACTIVE:
            # Transition the status to MODIFIED so that the XMLRPC layer knows
            # that it has to inform Mailman that a mailing list attribute has
            # been changed on an active list.
            self.status = MailingListStatus.MODIFIED
        else:
            raise AssertionError(
                'Only registered or active mailing lists may be modified')
        self.welcome_message_text = text

    welcome_message = property(_get_welcome_message, _set_welcome_message)


class MailingListSet:
    implements(IMailingListSet)

    def new(self, team, registrant=None):
        """See `IMailingListSet`."""
        assert team.isTeam(), (
            'Cannot register a list for a person who is not a team')
        assert self.get(team.name) is None, (
            'Mailing list for team "%s" already exists' % team.name)
        if registrant is None:
            registrant = team.teamowner
        else:
            # Check to make sure that registrant is a team owner or admin.
            # This gets tricky because an admin can be a team, and if the
            # registrant is a member of that team, they are by definition an
            # administrator of the team we're creating the mailing list for.
            # So you can't just do "registrant in
            # team.getDirectAdministrators()".  It's okay to use .inTeam() for
            # all cases because a person is always a member of himself.
            for admin in team.getDirectAdministrators():
                if registrant.inTeam(admin):
                    break
            else:
                raise AssertionError(
                    'registrant is not a team owner or administrator')
        return MailingList(team=team, registrant=registrant,
                           date_registered=datetime.now(pytz.timezone('UTC')))

    def get(self, team_name):
        """See `IMailingListSet`."""
        assert isinstance(team_name, basestring), (
            'team_name must be a string, not %s' % type(team_name))
        return MailingList.selectOne("""
            MailingList.team = Person.id
            AND Person.name = %s
            AND Person.teamowner IS NOT NULL
            """ % sqlvalues(team_name),
            clauseTables=['Person'])

    @property
    def registered_lists(self):
        """See `IMailingListSet`."""
        return MailingList.selectBy(status=MailingListStatus.REGISTERED)

    @property
    def approved_lists(self):
        """See `IMailingListSet`."""
        return MailingList.selectBy(status=MailingListStatus.APPROVED)

    @property
    def modified_lists(self):
        """See `IMailingListSet`."""
        return MailingList.selectBy(status=MailingListStatus.MODIFIED)

    @property
    def deactivated_lists(self):
        """See `IMailingListSet`."""
        return MailingList.selectBy(status=MailingListStatus.DEACTIVATING)
