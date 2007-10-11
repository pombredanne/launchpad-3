# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Launchpad-Mailman integration test #2

Check that Mailman properly deactivates lists.
"""

import shutil
import xmlrpclib

from zope.testbrowser.browser import Browser


def main():
    """Test end-to-end mailing list deactivation."""
    proxy = xmlrpclib.ServerProxy(XMLRPC_URL)
    # Create Team Three's mailing list.
    browser = Browser()
    browser.handleErrors = False
    browser.addHeader('Authorization', auth('no-priv@canonical.com', 'test'))
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
    # We cannot deactivate lists through the web yet.
    proxy.testStep('02-review-lists')
    # Now wait a little while for Mailman to create the Team Three mailing
    # list.  Using the default Mailman polling frequency, the list should get
    # created in under 20 seconds.
    until = datetime.datetime.now() + datetime.timedelta(seconds=20)
    team_names = None
    while datetime.datetime.now() < until:
        proc = Popen(('./list_lists', '-a', '-b'),
                     stdout=PIPE, stderr=STDOUT,
                     cwd=MAILMAN_BIN)
        stdout, stderr = proc.communicate()
        team_names = sorted(stdout.splitlines())
        if team_names == ['team-three']:
            break
    # On the Mailman side, only team-three should exist.  'team-one' exists
    # because of previous tests.
    if team_names != ['team-one', 'team-three']:
        raise IntegrationTestFailure('unexpected teams: %s' % team_names)
    # Before we deactivate the mailing list, use withlist to get a path we'll
    # need to check later.
    # Make sure the backup file was created.  This is a bit crufty due to
    # Mailman constraints.
    src_path = os.path.join(HERE, 'mmpaths.py')
    dst_path = os.path.join(MAILMAN_BIN, 'mmpaths.py')
    shutil.copyfile(src_path, dst_path)
    proc = Popen(('./withlist', '-q', '-r', 'mmpaths.backup', 'team-three'),
                 stdout=PIPE, stderr=STDOUT,
                 cwd=MAILMAN_BIN)
    stdout, stderr = proc.communicate()
    backup_path = stdout.splitlines()[0]
    # Now deactivate the mailing list.
    proxy.testStep('02-deactivate-lists')
    # Now wait a little while for Mailman to remove the Team Three mailing
    # list.  Using the default Mailman polling frequency, the list should get
    # deleted in under 20 seconds.
    until = datetime.datetime.now() + datetime.timedelta(seconds=20)
    team_names = None
    while datetime.datetime.now() < until:
        proc = Popen(('./list_lists', '-a', '-b'),
                     stdout=PIPE, stderr=STDOUT,
                     cwd=MAILMAN_BIN)
        stdout, stderr = proc.communicate()
        team_names = sorted(stdout.splitlines())
        if team_names == []:
            break
    # On the Mailman side, no teams should exist.
    if team_names != ['team-one']:
        raise IntegrationTestFailure('unexpected teams: %s' % team_names)
    try:
        if not os.path.exists(backup_path):
            raise IntegrationTestFailure('Backup file is missing: %s' %
                                         backup_path)
    finally:
        os.remove(dst_path)
        os.remove(backup_path)
