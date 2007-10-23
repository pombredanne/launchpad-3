# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Launchpad-Mailman integration test #4

Check that Mailman properly updates a list's subscriptions.
"""

import xmlrpclib
import itest_helper


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
    proxy = xmlrpclib.ServerProxy(itest_helper.XMLRPC_URL)
    proxy.testStep('04-setup-users-A')
    # Now wait a little while for Mailman to modify the mailing list.
    itest_helper.poll(dump_membership([
        'Anne Person <anne.person@example.com>',
        'Bart Person <bperson@example.org>',
        ]))
    # Add Cris and Dirk, change Anne's preferred email address address and
    # unsubscribe Bart.
    proxy.testStep('04-setup-users-B')
    itest_helper.poll(dump_membership([
        'Anne Person <aperson@example.org>',
        'Cris Person <cris.person@example.com>',
        'Dirk Person <dirk.person@example.com>',
        ]))
