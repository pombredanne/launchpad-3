# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Launchpad-Mailman integration test #2

Check that Mailman properly deactivates lists.
"""

import os
import xmlrpclib
import itest_helper

from zope.component import getUtility
from canonical.config import config
from canonical.launchpad.interfaces import (
    ILaunchpadCelebrities, IMailingListSet, MailingListStatus)


def check_lists_active():
    """Poll function looking for expected active mailing lists."""
    stdout = itest_helper.run_mailman('./list_lists', '-a', '-b')
    team_names = sorted(stdout.splitlines())
    # This test creates team-three; team-one exists due to a previous test.
    return 'team-one' in team_names and 'team-three' in team_names


def check_lists_deactive():
    """Poll function looking for expected mailing lists after deactivation."""
    stdout = itest_helper.run_mailman('./list_lists', '-a', '-b')
    team_names = sorted(stdout.splitlines())
    return 'team-one' in team_names and 'team-three' not in team_names


def main():
    """Test end-to-end mailing list deactivation."""
    proxy = xmlrpclib.ServerProxy(config.mailman.xmlrpc_url)
    # Create Team Three's mailing list.
    browser = itest_helper.make_browser()
    browser.open('http://launchpad.dev/people/+newteam')
    # Use the field names here to disambiguate or properly locate the control.
    browser.getControl(name='field.name').value = 'team-three'
    browser.getControl('Display Name').value = 'Team Three'
    browser.getControl(name='field.subscriptionpolicy').displayValue = [
        'Open Team']
    browser.getControl('Create').click()
    # Register a team mailing list.
    browser.getLink('Change contact address').click()
    browser.getControl('Apply for Mailing List').click()
    # We cannot approve lists through the web yet.
    list_set = getUtility(IMailingListSet)
    experts = getUtility(ILaunchpadCelebrities).mailing_list_experts
    lpadmin = list(experts.allmembers)[0]
    list_three = list_set.get('team-three')
    list_three.review(lpadmin, MailingListStatus.APPROVED)
    itest_helper.transactionmgr.commit()
    itest_helper.poll(check_lists_active)
    # Before we deactivate the mailing list, use withlist to get a path we'll
    # need to check later.
    stdout = itest_helper.run_mailman(
        './withlist', '-q', '-r', 'mmhelper.backup', 'team-three')
    backup_path = stdout.splitlines()[0]
    # Now deactivate the mailing list and check that the backup file exists.
    # we cannot deactivate mailing lists through the web yet.
    list_three = list_set.get('team-three')
    list_three.deactivate()
    itest_helper.transactionmgr.commit()
    itest_helper.poll(check_lists_deactive)
    try:
        if not os.path.exists(backup_path):
            raise itest_helper.IntegrationTestFailure(
                'Backup file is missing: %s' % backup_path)
    finally:
        os.remove(backup_path)
