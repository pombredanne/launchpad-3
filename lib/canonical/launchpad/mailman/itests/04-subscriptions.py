# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Launchpad-Mailman integration test #4

Check that Mailman properly updates a list's subscriptions.
"""

import xmlrpclib
import itest_helper


def dump_membership(expected_members):
    def poll_function():
        stdout = itest_helper.run_mailman(
            './list_members', '-f', '-p', 'team-one')
        return sorted(stdout.splitlines()) == expected_members
    return poll_function


def main():
    """End-to-end testing of mailing list modification."""
    # This test can't currently be done completely through the web.
    proxy = xmlrpclib.ServerProxy(itest_helper.XMLRPC_URL)
    proxy.testStep('04-setup-users-A')
    # Now wait a little while for Mailman to modify the mailing list.
    itest_helper.poll_mailman(dump_membership(['jim']))
