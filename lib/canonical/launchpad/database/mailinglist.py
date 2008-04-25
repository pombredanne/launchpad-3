# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type

__all__ = [
    'HeldMessageDetails',
    'MailingList',
    'MailingListSet',
    'MailingListSubscription',
    'MessageApproval',
    'MessageApprovalSet',
    ]


import transaction

from email import message_from_string
from email.Header import decode_header, make_header
from itertools import repeat
from string import Template

from sqlobject import ForeignKey, StringCol
from zope.component import getUtility
from zope.event import notify
from zope.interface import implements, providedBy

from canonical.config import config
from canonical.database.constants import DEFAULT, UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.launchpad import _
from canonical.launchpad.event import MessageHeldEvent, SQLObjectModifiedEvent
from canonical.launchpad.interfaces import (
    CannotChangeSubscription, CannotSubscribe, CannotUnsubscribe,
    EmailAddressStatus, IEmailAddressSet, IHeldMessageDetails,
    ILaunchpadCelebrities, IMailingList, IMailingListSet,
    IMailingListSubscription, IMessageApproval, IMessageApprovalSet,
    IMessageSet, MailingListStatus, PostedMessageStatus)
from canonical.launchpad.mailman.config import configure_hostname
from canonical.launchpad.validators.person import public_person_validator
from canonical.launchpad.webapp.snapshot import Snapshot


class MessageApproval(SQLBase):
    """A held message."""

    implements(IMessageApproval)

    message_id = StringCol(notNull=True)

    posted_by = ForeignKey(
        dbName='posted_by', foreignKey='Person',
        validator=public_person_validator,
        notNull=True)

    posted_message = ForeignKey(
        dbName='posted_message', foreignKey='LibraryFileAlias',
        notNull=True)

    posted_date = UtcDateTimeCol(notNull=True, default=UTC_NOW)

    mailing_list = ForeignKey(
        dbName='mailing_list', foreignKey='MailingList',
        notNull=True)

    status = EnumCol(enum=PostedMessageStatus,
                     default=PostedMessageStatus.NEW,
                     notNull=True)

    disposed_by = ForeignKey(
        dbName='disposed_by', foreignKey='Person',
        validator=public_person_validator,
        default=None)

    disposal_date = UtcDateTimeCol(default=None)

    def approve(self, reviewer):
        """See `IMessageApproval`."""
        self.disposed_by = reviewer
        self.disposal_date = UTC_NOW
        self.status = PostedMessageStatus.APPROVAL_PENDING

    def reject(self, reviewer):
        """See `IMessageApproval`."""
        self.disposed_by = reviewer
        self.disposal_date = UTC_NOW
        self.status = PostedMessageStatus.REJECTION_PENDING

    def discard(self, reviewer):
        """See `IMessageApproval`."""
        self.disposed_by = reviewer
        self.disposal_date = UTC_NOW
        self.status = PostedMessageStatus.DISCARD_PENDING

    def acknowledge(self):
        """See `IMessageApproval`."""
        if self.status == PostedMessageStatus.APPROVAL_PENDING:
            self.status = PostedMessageStatus.APPROVED
        elif self.status == PostedMessageStatus.REJECTION_PENDING:
            self.status = PostedMessageStatus.REJECTED
        elif self.status == PostedMessageStatus.DISCARD_PENDING:
            self.status = PostedMessageStatus.DISCARDED
        else:
            raise AssertionError('Not an acknowledgeable state: %s' %
                                 self.status)


class MailingList(SQLBase):
    """The mailing list for a team.

    Teams may have at most one mailing list, and a mailing list is associated
    with exactly one team.  This table manages the state changes that a team
    mailing list can go through, and it contains information that will be used
    to instruct Mailman how to create, delete, and modify mailing lists (via
    XMLRPC).
    """

    implements(IMailingList)

    team = ForeignKey(
        dbName='team', foreignKey='Person',
        validator=public_person_validator,
        notNull=True)

    registrant = ForeignKey(
        dbName='registrant', foreignKey='Person',
        validator=public_person_validator, notNull=True)

    date_registered = UtcDateTimeCol(notNull=True, default=DEFAULT)

    reviewer = ForeignKey(
        dbName='reviewer', foreignKey='Person',
        validator=public_person_validator, default=None)

    date_reviewed = UtcDateTimeCol(notNull=False, default=None)

    date_activated = UtcDateTimeCol(notNull=False, default=None)

    status = EnumCol(enum=MailingListStatus,
                     default=MailingListStatus.REGISTERED,
                     notNull=True)

    # Use a trailing underscore because SQLObject/importfascist doesn't like
    # the typical leading underscore.
    welcome_message_ = StringCol(default=None, dbName='welcome_message')

    @property
    def address(self):
        """See `IMailingList`."""
        return '%s@%s' % (
            self.team.name,
            configure_hostname(config.mailman.build_host_name))

    @property
    def archive_url(self):
        """See `IMailingList`."""
        # These represent states that can occur at or after a mailing list has
        # been activated.  Once it's been activated, a mailing list could have
        # an archive.
        if self.status not in [MailingListStatus.ACTIVE,
                               MailingListStatus.INACTIVE,
                               MailingListStatus.MODIFIED,
                               MailingListStatus.UPDATING,
                               MailingListStatus.DEACTIVATING,
                               MailingListStatus.MOD_FAILED]:
            return None
        # There could be an archive, return its url.
        template = Template(config.mailman.archive_url_template)
        return template.safe_substitute(team_name=self.team.name)

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
        else:
            raise AssertionError(
                'Not a valid state transition: %s -> %s'
                % (self.status, target_state))
        self.status = target_state
        if target_state == MailingListStatus.ACTIVE:
            self._setAndNotifyDateActivated()
            email_set = getUtility(IEmailAddressSet)
            email = email_set.getByEmail(self.address)
            if email is None:
                email = email_set.new(self.address, self.team)
            if email.status in [EmailAddressStatus.NEW,
                                EmailAddressStatus.OLD]:
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

    def _setAndNotifyDateActivated(self):
        """Set the date_activated field and fire a
        SQLObjectModified event.

        The date_activated field is only set once - repeated calls
        will not change the field's value.

        Similarly, the modification event only fires the first time
        that the field is set.
        """
        if self.date_activated is not None:
            return

        old_mailinglist = Snapshot(self, providing=providedBy(self))
        self.date_activated = UTC_NOW
        notify(SQLObjectModifiedEvent(
                self,
                object_before_modification=old_mailinglist,
                edited_fields=['date_activated']))

    def deactivate(self):
        """See `IMailingList`."""
        assert self.status == MailingListStatus.ACTIVE, (
            'Only active mailing lists may be deactivated')
        self.status = MailingListStatus.DEACTIVATING
        email = getUtility(IEmailAddressSet).getByEmail(self.address)
        email.status = EmailAddressStatus.NEW

    def reactivate(self):
        """See `IMailingList`."""
        assert self.status == MailingListStatus.INACTIVE, (
            'Only inactive mailing lists may be reactivated')
        self.status = MailingListStatus.APPROVED

    def cancelRegistration(self):
        """See `IMailingList`."""
        assert self.status == MailingListStatus.REGISTERED, (
            "Only mailing lists in the REGISTERED state can be canceled.")
        self.destroySelf()

    def isUsable(self):
        """See `IMailingList`"""
        return self.status in [MailingListStatus.ACTIVE,
                               MailingListStatus.MODIFIED,
                               MailingListStatus.UPDATING,
                               MailingListStatus.MOD_FAILED]

    def _get_welcome_message(self):
        return self.welcome_message_

    def _set_welcome_message(self, text):
        if self.status == MailingListStatus.REGISTERED:
            # Do nothing because the status does not change.  When setting the
            # welcome_message on a newly registered mailing list the XMLRPC
            # layer will essentially tell Mailman to initialize this attribute
            # at list construction time.  It is enough to just set the
            # database attribute to properly notify Mailman what to do.
            pass
        elif self.isUsable():
            # Transition the status to MODIFIED so that the XMLRPC layer knows
            # that it has to inform Mailman that a mailing list attribute has
            # been changed on an active list.
            self.status = MailingListStatus.MODIFIED
        else:
            raise AssertionError(
                'Only registered or usable mailing lists may be modified')
        self.welcome_message_ = text

    welcome_message = property(_get_welcome_message, _set_welcome_message)

    def getSubscription(self, person):
        """See `IMailingList`."""
        return MailingListSubscription.selectOneBy(person=person,
                                                   mailing_list=self)

    def subscribe(self, person, address=None):
        """See `IMailingList`."""
        if not self.isUsable():
            raise CannotSubscribe('Mailing list is not usable: %s' %
                                  self.team.displayname)
        if person.isTeam():
            raise CannotSubscribe('Teams cannot be mailing list members: %s' %
                                  person.displayname)
        if address is not None and address.person != person:
            raise CannotSubscribe('%s does not own the email address: %s' %
                                  (person.displayname, address.email))
        subscription = self.getSubscription(person)
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
        subscription = self.getSubscription(person)
        if subscription is None:
            raise CannotUnsubscribe(
                '%s is not a member of the mailing list: %s' %
                (person.displayname, self.team.displayname))
        subscription.destroySelf()

    def changeAddress(self, person, address):
        """See `IMailingList`."""
        subscription = self.getSubscription(person)
        if subscription is None:
            raise CannotChangeSubscription(
                '%s is not a member of the mailing list: %s' %
                (person.displayname, self.team.displayname))
        if address is not None and address.person != person:
            raise CannotChangeSubscription(
                '%s does not own the email address: %s' %
                (person.displayname, address.email))
        subscription.email_address = address

    def _getSubscriptions(self):
        """Return the IMailingListSubscriptions for this mailing list."""
        return MailingListSubscription.select(
            """mailing_list = %s AND
               TeamParticipation.team = %s AND
               MailingList.status <> %s AND
               MailingList.id = MailingListSubscription.mailing_list AND
               TeamParticipation.person = MailingListSubscription.person
            """ % sqlvalues(self, self.team, MailingListStatus.INACTIVE),
            distinct=True, clauseTables=['TeamParticipation', 'MailingList'])

    def getSubscribedAddresses(self):
        """See `IMailingList`."""
        # Import here to avoid circular imports.
        from canonical.launchpad.database.emailaddress import EmailAddress
        # In order to handle the case where the preferred email address is
        # used (i.e. where MailingListSubscription.email_address is NULL), we
        # need to UNION, those using a specific address and those using the
        # preferred address.
        clause_tables = ('MailingList',
                         'MailingListSubscription',
                         'TeamParticipation')
        preferred = EmailAddress.select("""
            EmailAddress.person = MailingListSubscription.person AND
            MailingList.id = MailingListSubscription.mailing_list AND
            TeamParticipation.person = MailingListSubscription.person AND
            MailingListSubscription.mailing_list = %s AND
            TeamParticipation.team = %s AND
            MailingList.status <> %s AND
            MailingListSubscription.email_address IS NULL AND
            EmailAddress.status = %s
            """ % sqlvalues(self, self.team,
                            MailingListStatus.INACTIVE,
                            EmailAddressStatus.PREFERRED),
            clauseTables=clause_tables)
        specific = EmailAddress.select("""
            EmailAddress.id = MailingListSubscription.email_address AND
            MailingList.id = MailingListSubscription.mailing_list AND
            TeamParticipation.person = MailingListSubscription.person AND
            MailingListSubscription.mailing_list = %s AND
            TeamParticipation.team = %s AND
            MailingList.status <> %s
            """ % sqlvalues(self, self.team, MailingListStatus.INACTIVE),
            clauseTables=clause_tables)
        return preferred.union(specific)

    def getSenderAddresses(self):
        """See `IMailingList`."""
        # Import here to avoid circular imports.
        from canonical.launchpad.database.emailaddress import EmailAddress
        return EmailAddress.select("""
            EmailAddress.person = MailingListSubscription.person AND
            MailingList.id = MailingListSubscription.mailing_list AND
            TeamParticipation.person = MailingListSubscription.person AND
            MailingListSubscription.mailing_list = %s AND
            TeamParticipation.team = %s AND
            MailingList.status <> %s AND
            EmailAddress.status IN %s
            """ % sqlvalues(self, self.team, MailingListStatus.INACTIVE,
                            (EmailAddressStatus.VALIDATED,
                             EmailAddressStatus.PREFERRED)),
            distinct=True, clauseTables=['MailingListSubscription',
                                         'TeamParticipation',
                                         'MailingList'])

    def holdMessage(self, message):
        """See `IMailingList`."""
        held_message = MessageApproval(message_id=message.rfc822msgid,
                                       posted_by=message.owner,
                                       posted_message=message.raw,
                                       posted_date=message.datecreated,
                                       mailing_list=self)
        # This is required because the notification process needs IMessage.id
        # in order to pull the raw message text from the librarian.  Without
        # this commit, the id won't be assigned and the process will fail with
        # a KeyError.
        transaction.commit()
        notify(MessageHeldEvent(self, held_message))
        return held_message

    def getReviewableMessages(self):
        return MessageApproval.select("""
            MessageApproval.mailing_list = %s AND
            MessageApproval.status = %s
            """ % sqlvalues(self, PostedMessageStatus.NEW),
            distinct=True, clauseTables=['MailingList'],
            orderBy=['posted_date', 'message_id'])


class MailingListSet:
    implements(IMailingListSet)

    title = _('Team mailing lists')

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

    @property
    def unsynchronized_lists(self):
        """See `IMailingListSet`."""
        return MailingList.select('status IN %s' % sqlvalues(
            (MailingListStatus.CONSTRUCTING, MailingListStatus.UPDATING)))


class MailingListSubscription(SQLBase):
    """A mailing list subscription."""

    implements(IMailingListSubscription)

    person = ForeignKey(
        dbName='person', foreignKey='Person',
        validator=public_person_validator,
        notNull=True)

    mailing_list = ForeignKey(
        dbName='mailing_list', foreignKey='MailingList',
        notNull=True)

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


class MessageApprovalSet:
    """Sets of held messages."""

    implements(IMessageApprovalSet)

    def getMessageByMessageID(self, message_id):
        """See `IMessageApprovalSet`."""
        response = MessageApproval.selectBy(message_id=message_id)
        if response.count() == 0:
            return None
        return response[0]

    def getHeldMessagesWithStatus(self, status):
        """See `IMessageApprovalSet`."""
        return MessageApproval.selectBy(status=status)


class HeldMessageDetails:
    """Details about a held message."""

    implements(IHeldMessageDetails)

    def __init__(self, message_approval):
        self.message_approval = message_approval
        self.message_id = message_approval.message_id
        # We need to get the IMessage object associated with this
        # IMessageApproval object.  The tie-in is the Message-ID.
        messages = getUtility(IMessageSet).get(self.message_id)
        assert len(messages) == 1, (
            'Expected exactly one message with Message-ID: %s' %
            self.message_id)
        message = messages[0]
        self.subject = message.subject
        self.date = message.datecreated
        message.raw.open()
        try:
            self.email_message = message_from_string(message.raw.read())
        finally:
            message.raw.close()
        self.body = message.text_contents

    @property
    def author(self):
        """Return the sender, but as a link to their person page."""
        originators = self.email_message.get_all('from', [])
        originators.extend(self.email_message.get_all('reply-to', []))
        if len(originators) == 0:
            return 'n/a'
        unicode_parts = []
        for bytes, charset in decode_header(originators[0]):
            if charset is None:
                charset = 'us-ascii'
            unicode_parts.append(
                bytes.decode(charset, 'replace').encode('utf-8'))
        header = make_header(zip(unicode_parts, repeat('utf-8')))
        return unicode(header)
