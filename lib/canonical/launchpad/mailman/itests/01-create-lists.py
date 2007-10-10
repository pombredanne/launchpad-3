#! /usr/bin/env python
# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Launchpad-Mailman integration test #1

Check that Mailman actually creates approved mailing lists.
"""

import os
import sys
import time
import base64
import datetime
import xmlrpclib

from subprocess import call, Popen, PIPE, STDOUT
from zope.testbrowser.browser import Browser


XMLRPC_URL = 'http://xmlrpc.launchpad.dev:8087/mailinglists'
MAILMAN_BIN = os.path.normpath(os.path.join(
    os.path.dirname(sys.argv[0]), '../../../../', 'mailman', 'bin'))

# XXX I don't understand why we have to base64 encode the password here, but
# the Launchpad page tests don't.
def auth(user, password):
    return 'Basic ' + base64.encodestring('%s:%s' % (user, password))


def main():
    """Test end-to-end mailing list creation."""
    proxy = xmlrpclib.ServerProxy(XMLRPC_URL)
    # Create Team One, whose list will get approved.
    browser = Browser()
    browser.addHeader('Authorization', auth('no-priv@canonical.com', 'test'))
    browser.open('http://launchpad.dev/people/+newteam')
    # Use the field names here to disambiguate or properly locate the control.
    browser.getControl(name='field.name').value = 'team-one'
    browser.getControl('Display Name').value = 'Team One'
    browser.getControl(name='field.subscriptionpolicy').displayValue = [
        'Open Team']
    browser.getControl('Create').click()
    # Create Team Two, whose list will get declined.
    browser.open('http://launchpad.dev/people/+newteam')
    browser.getControl(name='field.name').value = 'team-two'
    browser.getControl('Display Name').value = 'Team Two'
    browser.getControl(name='field.subscriptionpolicy').displayValue = [
        'Open Team']
    browser.getControl('Create').click()
    # Register a team mailing list for both teams.  XXX When Salgado's
    # contact-address-ui branch lands, we'll do this through the browser.  For
    # now, use the XMLRPC backdoor.
    proxy.testStep('register-lists')
    proxy.testStep('review-lists')
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
        print 'STEP 1; PASSED; team creation'
    elif 'team-two' in team_names:
        print 'STEP 1; FAILED; team-two was created unexpectedly'
    else:
        print 'STEP 1; FAILED; unexpected teams:', team_names
    # We can't clean up totally on the Launchpad side, but we can clean up on
    # the Mailman side.
    for team in team_names:
        call(('./rmlist', '-a', team), cwd=MAILMAN_BIN)
    print 'YOU MUST RUN "make schema" TO CLEAN UP LAUNCHPAD'


if __name__ == '__main__':
    main()
