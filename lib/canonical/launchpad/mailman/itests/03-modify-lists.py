# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Launchpad-Mailman integration test #3

Check that Mailman properly modifies a list's welcome message.
"""

import xmlrpclib
import itest_helper


def compare_message(greeting):
    def poll_function():
        stdout = itest_helper.run_mailman(
            './withlist', '-q', '-r', 'mmhelper.welcome', 'team-one')
        return stdout.splitlines()[0] == greeting
    return poll_function


def main():
    """End-to-end testing of mailing list modification."""
    # This test can't currently be done through the web.
    proxy = xmlrpclib.ServerProxy(itest_helper.XMLRPC_URL)
    proxy.testStep('03-modify-lists-A')
    # Now wait a little while for Mailman to modify the mailing list.
    itest_helper.poll(compare_message('Greetings team one members!'))
    # Set a new welcome message and poll until Mailman has done its work.
    proxy.testStep('03-modify-lists-B')
    itest_helper.poll(compare_message('Saluations team one members!'))
