# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Launchpad-Mailman integration test #1

Check that Mailman actually creates approved mailing lists.
"""

import xmlrpclib
import itest_helper


def check_lists():
    stdout = itest_helper.run_mailman('./list_lists', '-a', '-b')
    team_names = sorted(stdout.splitlines())
    return team_names == ['team-one']


def main():
    """Test end-to-end mailing list creation."""
    proxy = xmlrpclib.ServerProxy(itest_helper.XMLRPC_URL)
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
    proxy.testStep('01-review-lists')
    # Now wait a little while for Mailman to create the Team One mailing list.
    # Using the default Mailman polling frequency, the list should get created
    # in under 20 seconds.
    itest_helper.poll_mailman(check_lists)
