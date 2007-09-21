# Copyright 2007 Canonical Ltd.  All rights reserved.

"""XMLRPC APIs for mailing lists."""

__metaclass__ = type
__all__ = [
    'MailingListAPIView',
    ]


from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.interfaces import (
    IMailingListAPIView, IMailingListSet, MailingListStatus)
from canonical.launchpad.webapp import LaunchpadXMLRPCView
from canonical.launchpad.xmlrpc import faults


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
        if creates:
            response['create'] = creates
        # Next do mailing lists that are to be deactivated.
        deactivated = [mailing_list.team.name
                       for mailing_list in list_set.deactivated_lists]
        if deactivated:
            response['deactivate'] = deactivated
        # Finally, do modified lists.  Currently, the only value that can be
        # modified is the welcome message.
        modified = []
        for mailing_list in list_set.modified_lists:
            changes = (mailing_list.team.name,
                       dict(welcome_message=mailing_list.welcome_message))
            modified.append(changes)
            mailing_list.startUpdating()
        if modified:
            response['modify'] = modified
        return response

    def reportStatus(self, statuses):
        """See `IMailingListAPIView`."""
        list_set = getUtility(IMailingListSet)
        for team_name, action_status in statuses.items():
            mailing_list = list_set.get(team_name)
            if mailing_list is None:
                return faults.NoSuchTeamMailingList(team_name)
            if action_status == 'failure':
                if mailing_list.status in (MailingListStatus.CONSTRUCTING,
                                           MailingListStatus.UPDATING,
                                           MailingListStatus.DEACTIVATING):
                    mailing_list.transitionToStatus(MailingListStatus.FAILED)
                else:
                    return faults.UnexpectedStatusReport(
                        team_name, action_status)
            elif action_status == 'success':
                if mailing_list.status in (MailingListStatus.CONSTRUCTING,
                                           MailingListStatus.UPDATING):
                    mailing_list.transitionToStatus(MailingListStatus.ACTIVE)
                elif mailing_list.status == MailingListStatus.DEACTIVATING:
                    mailing_list.transitionToStatus(MailingListStatus.INACTIVE)
                else:
                    return faults.UnexpectedStatusReport(
                        team_name, action_status)
            else:
                return faults.BadStatus(team_name, action_status)
        # Everything was fine.
        return True

    def getMembershipInformation(self, teams):
        """See `IMailingListAPIView.`."""
        return {}

    def isLaunchpadMember(self, address):
        """See `IMailingListAPIView.`."""
        return False
