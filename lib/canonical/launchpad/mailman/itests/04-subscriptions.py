# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Launchpad-Mailman integration test #4

Check that Mailman properly updates a list's subscriptions.
"""

import xmlrpclib
import itest_helper

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy
from canonical.config import config
from canonical.launchpad.ftests.mailinglists_helper import (
    get_alternative_email, new_person)
from canonical.launchpad.interfaces import IMailingListSet, IPersonSet


def dump_membership(expected_members):
    """Check that the mailing list has the expected set of members."""
    def poll_function():
        stdout = itest_helper.run_mailman(
            './list_members', '-f', '-p', 'team-one')
        people = sorted(line.strip()
                        for line in stdout.splitlines()
                        if line.strip())
        return people == expected_members
    return poll_function


def main():
    """End-to-end testing of mailing list modification."""
    # This test can't currently be set up through the web.
    proxy = xmlrpclib.ServerProxy(config.mailman.xmlrpc_url)
    list_set = getUtility(IMailingListSet)
    person_set = getUtility(IPersonSet)
    team_one = person_set.getByName('team-one')
    list_one = list_set.get('team-one')
    # Subscribe Anne with her preferred address.
    anne = new_person('Anne')
    anne.join(team_one)
    list_one.subscribe(removeSecurityProxy(anne))
    # Subscribe Bart with his alternative address.
    bart = new_person('Bart')
    bart.join(team_one)
    list_one.subscribe(removeSecurityProxy(bart),
                       get_alternative_email(bart))
    itest_helper.transactionmgr.commit()
    # Now wait a little while for Mailman to modify the mailing list.
    itest_helper.poll(dump_membership([
        'Anne Person <anne.person@example.com>',
        'Bart Person <bperson@example.org>',
        ]))
    # Add Cris and Dirk, change Anne's preferred email address address and
    # unsubscribe Bart.
    team_one = person_set.getByName('team-one')
    list_one = list_set.get('team-one')
    # Subscribe Cris with her preferred address.
    cris = new_person('Cris')
    cris.join(team_one)
    list_one.subscribe(removeSecurityProxy(cris))
    # Subscribe Dirk with his preferred address.
    dirk = new_person('Dirk')
    dirk.join(team_one)
    list_one.subscribe(removeSecurityProxy(dirk))
    # Unsubscribe Bart.
    bart = person_set.getByName('bart')
    list_one.unsubscribe(bart)
    # Change Anne's email address to her alternative.
    anne = person_set.getByName('anne')
    anne.setPreferredEmail(get_alternative_email(anne))
    itest_helper.transactionmgr.commit()
    itest_helper.poll(dump_membership([
        'Anne Person <aperson@example.org>',
        'Cris Person <cris.person@example.com>',
        'Dirk Person <dirk.person@example.com>',
        ]))
