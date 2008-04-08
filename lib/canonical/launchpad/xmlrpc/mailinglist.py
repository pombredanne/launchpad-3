# Copyright 2007 Canonical Ltd.  All rights reserved.

"""XMLRPC APIs for mailing lists."""

__metaclass__ = type
__all__ = [
    'MailingListAPIView',
    ]


from zope.component import getUtility
from zope.interface import implements

from canonical.config import config
from canonical.launchpad.interfaces import (
    EmailAddressStatus, IEmailAddressSet, IMailingListAPIView,
    IMailingListSet, IMessageApprovalSet, IMessageSet, IPersonSet,
    MailingListStatus, PersonalStanding, PostedMessageStatus)
from canonical.launchpad.webapp import LaunchpadXMLRPCView
from canonical.launchpad.xmlrpc import faults


# Not all developers will have built the Mailman instance (via
# 'make mailman_instance').  In that case, this import will fail, but in that
# case just use the constant value directly.
try:
    # pylint: disable-msg=F0401
    from Mailman.MemberAdaptor import ENABLED, BYUSER
except ImportError:
    ENABLED = 0
    BYUSER = 2


class MailingListAPIView(LaunchpadXMLRPCView):
    """The XMLRPC API that Mailman polls for mailing list actions."""

    implements(IMailingListAPIView)

    def getPendingActions(self):
        """See `IMailingListAPIView`."""
        list_set = getUtility(IMailingListSet)
        # According to the interface, the return value is a dictionary where
        # the keys are one of the pending actions 'create', 'deactivate', or
        # 'modify'.  Do the 'create' action first, where the value is a
        # sequence of 2-tuples giving the team name and any initial values for
        # the mailing list.
        response = {}
        creates = []
        for mailing_list in list_set.approved_lists:
            initializer = {}
            # If the welcome message is not None, that means it is being
            # initialized when the list is created.  Currently, this is the
            # only value that can be initialized.
            if mailing_list.welcome_message is not None:
                initializer['welcome_message'] = mailing_list.welcome_message
            creates.append((mailing_list.team.name, initializer))
            # In addition, all approved mailing lists that are being
            # constructed by Mailman need to have their status changed.
            mailing_list.startConstructing()
        if len(creates) > 0:
            response['create'] = creates
        # Next do mailing lists that are to be deactivated.
        deactivated = [mailing_list.team.name
                       for mailing_list in list_set.deactivated_lists]
        if len(deactivated) > 0:
            response['deactivate'] = deactivated
        # Do modified lists.  Currently, the only value that can be modified
        # is the welcome message.
        modified = []
        for mailing_list in list_set.modified_lists:
            changes = (mailing_list.team.name,
                       dict(welcome_message=mailing_list.welcome_message))
            modified.append(changes)
            mailing_list.startUpdating()
        if len(modified) > 0:
            response['modify'] = modified
        # Handle unsynchronized lists.
        unsynchronized = [mailing_list.team.name
                          for mailing_list in list_set.unsynchronized_lists]
        if len(unsynchronized) > 0:
            response['unsynchronized'] = unsynchronized
        return response

    def reportStatus(self, statuses):
        """See `IMailingListAPIView`."""
        list_set = getUtility(IMailingListSet)
        for team_name, action_status in statuses.items():
            mailing_list = list_set.get(team_name)
            if mailing_list is None:
                return faults.NoSuchTeamMailingList(team_name)
            if action_status == 'failure':
                if mailing_list.status == MailingListStatus.CONSTRUCTING:
                    mailing_list.transitionToStatus(MailingListStatus.FAILED)
                elif mailing_list.status in (MailingListStatus.UPDATING,
                                             MailingListStatus.DEACTIVATING):
                    mailing_list.transitionToStatus(
                        MailingListStatus.MOD_FAILED)
                else:
                    return faults.UnexpectedStatusReport(
                        team_name, action_status)
            elif action_status == 'success':
                if mailing_list.status in (MailingListStatus.CONSTRUCTING,
                                           MailingListStatus.UPDATING):
                    mailing_list.transitionToStatus(MailingListStatus.ACTIVE)
                elif mailing_list.status == MailingListStatus.DEACTIVATING:
                    mailing_list.transitionToStatus(
                        MailingListStatus.INACTIVE)
                else:
                    return faults.UnexpectedStatusReport(
                        team_name, action_status)
            else:
                return faults.BadStatus(team_name, action_status)
        # Everything was fine.
        return True

    def getMembershipInformation(self, teams):
        """See `IMailingListAPIView`."""
        listset = getUtility(IMailingListSet)
        emailset = getUtility(IEmailAddressSet)
        response = {}
        for team_name in teams:
            mailing_list = listset.get(team_name)
            if mailing_list is None:
                return faults.NoSuchTeamMailingList(team_name)
            # Map {address -> (real_name, flags, status)}
            members = {}
            # Hard code flags to 0 currently, meaning the member will get
            # regular (not digest) delivery, will not get post
            # acknowledgements, will receive their own posts, and will not
            # be moderated.  A future phase may change some of these
            # values.
            flags = 0
            # Start by getting all addresses for all users who are subscribed.
            # These are the addresses that are allowed to post to the mailing
            # list, but may not get deliveries of posted messages.
            for email_address in mailing_list.getSenderAddresses():
                real_name = email_address.person.displayname
                # We'll mark the status of these addresses as disabled BYUSER,
                # which seems like the closest mapping to the semantics we
                # intend.  It doesn't /really/ matter as long as it's disabled
                # because the reason is only evident in the Mailman web u/i,
                # which we're not using.
                members[email_address.email] = (real_name, flags, BYUSER)
            # Now go through just the subscribed addresses, the main
            # difference now being that these addresses are enabled for
            # delivery.  If there are overlaps, the enabled flag wins.
            for email_address in mailing_list.getSubscribedAddresses():
                real_name = email_address.person.displayname
                members[email_address.email] = (real_name, flags, ENABLED)
            # Finally, add the archive recipient if there is one.  This
            # address should never be registered in Launchpad, meaning
            # specifically that the isRegisteredInLaunchpad() test below
            # should always fail for it.  That way, the address can never be
            # used to forge spam onto a list.
            if config.mailman.archive_address:
                members[config.mailman.archive_address] = ('', flags, ENABLED)
            # The response must be a list of tuples.
            response[team_name] = [
                (address, members[address][0],
                 members[address][1], members[address][2])
                for address in sorted(members)]
        return response

    def isRegisteredInLaunchpad(self, address):
        """See `IMailingListAPIView.`."""
        if (config.mailman.archive_address and
            address == config.mailman.archive_address):
            # Hard code that the archive address is never registered in
            # Launchpad, so forged messages from that sender will always be
            # discarded.
            return False
        email_address = getUtility(IEmailAddressSet).getByEmail(address)
        return (email_address is not None and
                email_address.status in (EmailAddressStatus.VALIDATED,
                                         EmailAddressStatus.PREFERRED))

    def inGoodStanding(self, address):
        """See `IMailingListAPIView`."""
        person = getUtility(IPersonSet).getByEmail(address)
        if person is None or person.isTeam():
            return False
        return person.personal_standing in (PersonalStanding.GOOD,
                                            PersonalStanding.EXCELLENT)

    def holdMessage(self, team_name, text):
        """See `IMailingListAPIView`."""
        mailing_list = getUtility(IMailingListSet).get(team_name)
        message = getUtility(IMessageSet).fromEmail(text)
        mailing_list.holdMessage(message)
        return True

    def getMessageDispositions(self):
        """See `IMailingListAPIView`."""
        message_set = getUtility(IMessageApprovalSet)
        # A mapping from message ids to statuses.
        response = {}
        # Start by iterating over all held messages that are pending approval.
        # These are messages that the team owner has approved, but Mailman
        # hasn't yet acted upon.  For each of these, set their state to final
        # approval.
        approved_messages = message_set.getHeldMessagesWithStatus(
            PostedMessageStatus.APPROVAL_PENDING)
        for held_message in approved_messages:
            held_message.acknowledge()
            response[held_message.message_id] = (
                held_message.mailing_list.team.name, 'accept')
        # Similarly handle all held messages that have been rejected by the
        # team administrator but not yet handled by Mailman.
        rejected_messages = message_set.getHeldMessagesWithStatus(
            PostedMessageStatus.REJECTION_PENDING)
        for held_message in rejected_messages:
            held_message.acknowledge()
            response[held_message.message_id] = (
                held_message.mailing_list.team.name, 'decline')
        return response
