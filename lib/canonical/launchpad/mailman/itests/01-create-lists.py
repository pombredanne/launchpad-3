# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Launchpad-Mailman integration test #1

Check that Mailman actually creates approved mailing lists.
"""

import xmlrpclib
import itest_helper

from zope.component import getUtility
from canonical.config import config
from canonical.launchpad.interfaces import (
    ILaunchpadCelebrities, IMailingListSet, MailingListStatus)


def check_lists():
    """Poll function looking for expected active mailing lists."""
    stdout = itest_helper.run_mailman('./list_lists', '-a', '-b')
    team_names = sorted(stdout.splitlines())
    # Use a containment test instead of equality so that sample data is
    # ignored.
    return 'team-one' in team_names


def main():
    """Test end-to-end mailing list creation."""
    proxy = xmlrpclib.ServerProxy(config.mailman.xmlrpc_url)
    browser = itest_helper.make_browser()
    #
    # Create Team One, whose list will get approved.
    #
    browser.open('http://launchpad.dev/people/+newteam')
    # Use the field names here to disambiguate or properly locate the control.
    browser.getControl(name='field.name').value = 'team-one'
    browser.getControl('Display Name').value = 'Team One'
    browser.getControl(name='field.subscriptionpolicy').displayValue = [
        'Open Team']
    browser.getControl('Create').click()
    # Register a team mailing list.
    browser.getLink('Change contact address').click()
    browser.getControl('Apply for Mailing List').click()
    #
    # Create Team Two, whose list will get declined.
    #
    browser.open('http://launchpad.dev/people/+newteam')
    browser.getControl(name='field.name').value = 'team-two'
    browser.getControl('Display Name').value = 'Team Two'
    browser.getControl(name='field.subscriptionpolicy').displayValue = [
        'Open Team']
    browser.getControl('Create').click()
    # Register a team mailing list.
    browser.getLink('Change contact address').click()
    browser.getControl('Apply for Mailing List').click()
    # Reviewing lists is currently not available through the web.
    list_set = getUtility(IMailingListSet)
    experts = getUtility(ILaunchpadCelebrities).mailing_list_experts
    lpadmin = list(experts.allmembers)[0]
    list_one = list_set.get('team-one')
    list_one.review(lpadmin, MailingListStatus.APPROVED)
    list_two = list_set.get('team-two')
    list_two.review(lpadmin, MailingListStatus.DECLINED)
    itest_helper.transactionmgr.commit()
    # Now wait a little while for Mailman to create the Team One mailing list.
    # Using the default Mailman polling frequency, the list should get created
    # in under 20 seconds.
    itest_helper.poll(check_lists)
