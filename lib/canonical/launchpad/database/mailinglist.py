# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'MailingList',
    'MailingListSet',
    'MailingListSubscription',
    ]

from sqlobject import ForeignKey, StringCol
from zope.component import getUtility
from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.launchpad.interfaces import (
    CannotChangeSubscription, CannotSubscribe, CannotUnsubscribe,
    EmailAddressStatus, IEmailAddressSet, ILaunchpadCelebrities, IMailingList,
    IMailingListSet, IMailingListSubscription, MailingListStatus,
    MAILING_LISTS_DOMAIN)


class MailingList(SQLBase):
    """The mailing list for a team.

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

    @property
    def address(self):
        """See `IMailingList`."""
        return '%s@%s' % (self.team.name, MAILING_LISTS_DOMAIN)

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
            'Reviewer must be a member of the Mailing List Experts team')
        self.reviewer = reviewer
        self.status = status
        self.date_reviewed = UTC_NOW

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
        # State: From UPDATING to either ACTIVE or MOD_FAILED
        elif self.status == MailingListStatus.UPDATING:
            assert target_state in (MailingListStatus.ACTIVE,
                                    MailingListStatus.MOD_FAILED), (
                'target_state result must be active or mod_failed')
        # State: From DEACTIVATING to INACTIVE or MOD_FAILED
        elif self.status == MailingListStatus.DEACTIVATING:
            assert target_state in (MailingListStatus.INACTIVE,
                                    MailingListStatus.MOD_FAILED), (
                'target_state result must be inactive or mod_failed')
            self._clearSubscriptions()
        else:
            raise AssertionError(
                'Not a valid state transition: %s -> %s'
                % (self.status, target_state))
        self.status = target_state
        if target_state == MailingListStatus.ACTIVE:
            email_set = getUtility(IEmailAddressSet)
            email = email_set.getByEmail(self.address)
            if email is None:
                email = email_set.new(self.address, self.team)
            if email.status in [EmailAddressStatus.NEW, EmailAddressStatus.OLD]:
                # Without this conditional, if the mailing list is the
                # contact method
                # (email.status==EmailAddressStatus.PREFERRED), and a
                # user changes the mailing list configuration, then
                # when the list status goes back to ACTIVE the email
                # will go from PREFERRED to VALIDATED and the list
                # will stop being the contact method.
                email.status = EmailAddressStatus.VALIDATED
            assert email.person == self.team, (
                "Email already associated with another team.")

    def deactivate(self):
        """See `IMailingList`."""
        assert self.status == MailingListStatus.ACTIVE, (
            'Only active mailing lists may be deactivated')
        self.status = MailingListStatus.DEACTIVATING
        email = getUtility(IEmailAddressSet).getByEmail(self.address)
        email.status = EmailAddressStatus.NEW

    def reactivate(self):
        """See `IMailingList`."""
        # XXX: The Mailman side of this is not yet implemented, although it
        # will be implemented soon. -- Guilherme Salgado, 2007-10-08
        # https://launchpad.net/launchpad/+spec/team-mailing-lists-reactivate
        assert self.status == MailingListStatus.INACTIVE, (
            'Only inactive mailing lists may be reactivated')
        self.status = MailingListStatus.APPROVED

    def cancelRegistration(self):
        """See `IMailingList`."""
        assert self.status == MailingListStatus.REGISTERED, (
            "Only mailing lists in the REGISTERED state can be canceled.")
        self.destroySelf()

    def _get_welcome_message(self):
        return self.welcome_message_text

    def canBeContactMethod(self):
        """See `IMailingList`"""
        return self.status in [MailingListStatus.ACTIVE,
                               MailingListStatus.MODIFIED,
                               MailingListStatus.UPDATING,
                               MailingListStatus.MOD_FAILED]

    def _set_welcome_message(self, text):
        if self.status == MailingListStatus.REGISTERED:
            # Do nothing because the status does not change.  When setting the
            # welcome_message on a newly registered mailing list the XMLRPC
            # layer will essentially tell Mailman to initialize this attribute
            # at list construction time.  It is enough to just set the
            # database attribute to properly notify Mailman what to do.
            pass
        elif self.canBeContactMethod():
            # Transition the status to MODIFIED so that the XMLRPC layer knows
            # that it has to inform Mailman that a mailing list attribute has
            # been changed on an active list.
            self.status = MailingListStatus.MODIFIED
        else:
            raise AssertionError(
                'Only registered or active mailing lists may be modified')
        self.welcome_message_text = text

    welcome_message = property(_get_welcome_message, _set_welcome_message)

    def subscribe(self, person, address=None):
        """See `IMailingList`."""
        if not self.status == MailingListStatus.ACTIVE:
            raise CannotSubscribe('Mailing list is not active: %s' %
                                  self.team.displayname)
        if person.isTeam():
            raise CannotSubscribe('Teams cannot be mailing list members: %s' %
                                  person.displayname)
        if not person.hasParticipationEntryFor(self.team):
            raise CannotSubscribe('%s is not a member of team %s' %
                                  (person.displayname, self.team.displayname))
        if address is not None and address.person != person:
            raise CannotSubscribe('%s does not own the email address: %s' %
                                  (person.displayname, address.email))
        subscription = MailingListSubscription.selectOneBy(
            person=person, mailing_list=self)
        if subscription is not None:
            raise CannotSubscribe('%s is already subscribed to list %s' %
                                  (person.displayname, self.team.displayname))
        # Add the subscription for this person to this mailing list.
        MailingListSubscription(
            person=person,
            mailing_list=self,
            email_address=address)

    def unsubscribe(self, person):
        """See `IMailingList`."""
        subscription = MailingListSubscription.selectOneBy(
            person=person, mailing_list=self)
        if subscription is None:
            raise CannotUnsubscribe(
                '%s is not a member of the mailing list: %s' %
                (person.displayname, self.team.displayname))
        subscription.destroySelf()

    def changeAddress(self, person, address):
        """See `IMailingList`."""
        subscription = MailingListSubscription.selectOneBy(
            person=person, mailing_list=self)
        if subscription is None:
            raise CannotChangeSubscription(
                '%s is not a member of the mailing list: %s' %
                (person.displayname, self.team.displayname))
        if address is not None and address.person != person:
            raise CannotChangeSubscription(
                '%s does not own the email address: %s' %
                (person.displayname, address.email))
        subscription.email_address = address

    def _clearSubscriptions(self):
        subscriptions = MailingListSubscription.selectBy(mailing_list=self)
        for subscription in subscriptions:
            subscription.destroySelf()

    def getAddresses(self):
        """See `IMailingList`."""
        subscriptions = MailingListSubscription.select(
            """mailing_list = %s AND
               team = %s AND
               TeamParticipation.person = MailingListSubscription.person
            """ % sqlvalues(self, self.team),
            distinct=True, clauseTables=['TeamParticipation'])
        for subscription in subscriptions:
            yield subscription.subscribed_address.email


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
                           date_registered=UTC_NOW)

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
    def active_lists(self):
        """See `IMailingListSet`."""
        return MailingList.selectBy(status=MailingListStatus.ACTIVE)

    @property
    def modified_lists(self):
        """See `IMailingListSet`."""
        return MailingList.selectBy(status=MailingListStatus.MODIFIED)

    @property
    def deactivated_lists(self):
        """See `IMailingListSet`."""
        return MailingList.selectBy(status=MailingListStatus.DEACTIVATING)


class MailingListSubscription(SQLBase):
    """A mailing list subscription."""

    implements(IMailingListSubscription)

    person = ForeignKey(dbName='person', foreignKey='Person')

    mailing_list = ForeignKey(dbName='mailing_list', foreignKey='MailingList')

    date_joined = UtcDateTimeCol(notNull=True, default=UTC_NOW)

    email_address = ForeignKey(dbName='email_address',
                               foreignKey='EmailAddress')

    @property
    def subscribed_address(self):
        """See `IMailingListSubscription`."""
        if self.email_address is None:
            # Use the person's preferred email address.
            return self.person.preferredemail
        else:
            # Use the subscribed email address.
            return self.email_address
