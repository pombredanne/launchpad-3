# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Launchpad-Mailman integration test #1

Check that Mailman actually creates approved mailing lists.
"""

import os
import sys
import time
import datetime
import xmlrpclib

from zope.testbrowser.browser import Browser


XMLRPC_URL = 'http://xmlrpc.launchpad.dev:8087/mailinglists'

def main():
    """Test end-to-end mailing list creation."""
    proxy = xmlrpclib.ServerProxy(XMLRPC_URL)
    #
    # Create Team One, whose list will get approved.
    #
    browser = Browser()
    browser.handleErrors = False
    browser.addHeader('Authorization', auth('no-priv@canonical.com', 'test'))
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
    until = datetime.datetime.now() + datetime.timedelta(seconds=20)
    team_names = None
    while datetime.datetime.now() < until:
        proc = Popen(('./list_lists', '-a', '-b'),
                     stdout=PIPE, stderr=STDOUT,
                     cwd=MAILMAN_BIN)
        stdout, stderr = proc.communicate()
        team_names = sorted(stdout.splitlines())
        if team_names == ['team-one']:
            break
    # On the Mailman side, only team-one should exist.
    if team_names == ['team-one']:
        # The test passed.
        return
    elif 'team-two' in team_names:
        raise IntegrationTestFailure('team-two was created unexpectedly')
    else:
        raise IntegrationTestFailure('unexpected teams: %s' % team_names)
