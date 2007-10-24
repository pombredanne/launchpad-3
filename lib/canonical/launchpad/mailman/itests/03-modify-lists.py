# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Launchpad-Mailman integration test #3

Check that Mailman properly modifies a list's welcome message.
"""

import xmlrpclib
import itest_helper

from zope.component import getUtility
from canonical.config import config
from canonical.launchpad.interfaces import IMailingListSet


def compare_message(greeting):
    """Check that the mailing list has the expected welcome message."""
    def poll_function():
        stdout = itest_helper.run_mailman(
            './withlist', '-q', '-r', 'mmhelper.welcome', 'team-one')
        return stdout.splitlines()[0] == greeting
    return poll_function


def main():
    """End-to-end testing of mailing list modification."""
    # These actions can't currently be done through the web.
    proxy = xmlrpclib.ServerProxy(config.mailman.xmlrpc_url)
    list_set = getUtility(IMailingListSet)
    list_one = list_set.get('team-one')
    list_one.welcome_message = 'Greetings team one members!'
    itest_helper.transactionmgr.commit()
    # Now wait a little while for Mailman to modify the mailing list.
    itest_helper.poll(compare_message('Greetings team one members!'))
    # Set a new welcome message and poll until Mailman has done its work.
    list_one = list_set.get('team-one')
    list_one.welcome_message = 'Saluations team one members!'
    itest_helper.transactionmgr.commit()
    itest_helper.poll(compare_message('Saluations team one members!'))
