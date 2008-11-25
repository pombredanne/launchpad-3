# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Import mailing list information."""

__metaclass__ = type
__all__ = [
    'Import',
    ]


from zope.component import getUtility

from canonical.launchpad.interfaces.emailaddress import IEmailAddressSet
from canonical.launchpad.interfaces.mailinglist import (
    IMailingListSet, MailingListStatus)
from canonical.launchpad.interfaces.person import IPersonSet


class Importer:
    """Perform mailing list imports for command line scripts."""

    def __init__(self, team_name):
        self.team_name = team_name
        self.team = getUtility(IPersonSet).getByName(team_name)
        assert self.team is not None, (
            'No team with name: %s' % team_name)
        self.mailing_list = getUtility(IMailingListSet).get(team_name)
        assert self.mailing_list is not None, (
            'Team has no mailing list: %s' % team_name)
        assert self.mailing_list.status == MailingListStatus.ACTIVE, (
            'Team mailing list is not active: %s' % team_name)

    def importAddresses(self, addresses):
        """Import all addresses.

        Every address that is preferred or validated and connected to a person
        is made a member of the team, and is subscribed to the mailing list
        (with the address given).  If the address is not valid, or if it is
        associated with a team, the address is ignored.

        :param addresses: The email addresses to join and subscribe.
        :type addresses: sequence of strings
        """
        email_set = getUtility(IEmailAddressSet)
        person_set = getUtility(IPersonSet)
        for address in addresses:
            person = person_set.getByEmail(address)
            if person is None or person.isTeam():
                # XXX Log this.
                continue
            email = email_set.getByEmail(address)
            assert email is not None, (
                'Address has no IEmailAddress? %s' % address)
            person.join(self.team)
            self.mailing_list.subscribe(person, email)
