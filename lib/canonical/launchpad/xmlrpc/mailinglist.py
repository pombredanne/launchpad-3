# Copyright 2007 Canonical Ltd.  All rights reserved.

"""XMLRPC APIs for mailing lists."""

__metaclass__ = type
__all__ = [
    'RequestedMailingListAPI',
    ]


from zope.component import getUtility
from zope.interface import implements

from canonical.lp.dbschema import MailingListStatus
from canonical.launchpad.interfaces import (
    IMailingListRegistry, IRequestedMailingListAPI)
from canonical.launchpad.webapp import LaunchpadXMLRPCView
from canonical.launchpad.xmlrpc import faults


class RequestedMailingListAPI(LaunchpadXMLRPCView):
    """The XMLRPC API that Mailman polls for mailing list actions."""

    implements(IRequestedMailingListAPI)

    def getPendingActions(self):
        """See `IRequestedMailingListAPI`."""
        registry = getUtility(IMailingListRegistry)
        # According to the interface, the return value is a dictionary where
        # the keys are one of the pending actions 'create', 'deactivate', or
        # 'modify'.  Do the 'create' action first, where the value is a
        # sequence of 2-tuples giving the team name and any initial values for
        # the mailing list.
        response = {}
        creates = []
        for mailing_list in registry.approved_lists:
            initializer = {}
            # If the welcome message is not None, that means it is being
            # initialized when the list is created.  Currently, this is the
            # only value that can be initialized.
            if mailing_list.welcome_message is not None:
                initializer['welcome_message'] = mailing_list.welcome_message
            creates.append((mailing_list.team.name, initializer))
            # In addition, all approved mailing lists that are being
            # constructed by Mailman need to have their status changed.
            mailing_list.construct()
        if creates:
            response['create'] = creates
        # Next do mailing lists that are to be deactivated.
        deactivated = [mailing_list.team.name
                       for mailing_list in registry.deactivated_lists]
        if deactivated:
            response['deactivated'] = deactivated
        # Finally, do modified lists.  Currently, the only value that can be
        # modified is the welcome message.
        modified = []
        for mailing_list in registry.modified_lists:
            changes = (mailing_list.team.name,
                       dict(welcome_message=mailing_list.welcome_message))
            modified.append(changes)
        if modified:
            response['modify'] = modified
        return response

    def reportStatus(self, statuses):
        """See `IRequestedMailingListActions`."""
        registry = getUtility(IMailingListRegistry)
        for team_name, status in statuses.items():
            mailing_list = registry.getTeamMailingList(team_name)
            if mailing_list is None:
                return faults.NoSuchTeam(team_name)
            if status == 'failure':
                if mailing_list.status in (MailingListStatus.CONSTRUCTING,
                                           MailingListStatus.MODIFIED,
                                           MailingListStatus.DEACTIVATING):
                    mailing_list.reportResult(MailingListStatus.FAILED)
                else:
                    return faults.UnexpectedStatusReport(team_name, status)
            elif status == 'success':
                if mailing_list.status in (MailingListStatus.CONSTRUCTING,
                                           MailingListStatus.MODIFIED):
                    mailing_list.reportResult(MailingListStatus.ACTIVE)
                elif mailing_list.status == MailingListStatus.DEACTIVATING:
                    mailing_list.reportResult(MailingListStatus.INACTIVE)
                else:
                    return faults.UnexpectedStatusReport(team_name, status)
            else:
                return faults.BadStatus(team_name, status)
        # Everything was fine.
        return True
