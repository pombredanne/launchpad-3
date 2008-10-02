#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Update stacked_on_location for all Bazaar branches.

Expects standard input of:
    '<id> <branch_type> <unique_name> <stacked_on_unique_name>\n'.

Such input can be provided using "get-stacked-on-branches.py".

This script makes the stacked_on_location variables in all Bazaar branches
match the stacked_on column in the Launchpad database. This is useful for
updating stacked branches when their stacked-on branch has been moved or
renamed.
"""

__metaclass__ = type

import _pythonpath
import sys
import xmlrpclib

from bzrlib.bzrdir import BzrDir
from bzrlib.config import TransportConfig
from bzrlib import errors

from canonical.codehosting.transport import (
    BlockingProxy, LaunchpadInternalServer,
    get_chrooted_transport, get_readonly_transport, _MultiServer)
from canonical.codehosting.bzrutils import get_branch_stacked_on_url
from canonical.config import config
from canonical.launchpad.scripts import execute_zcml_for_scripts


READ_ONLY = False


def get_server():
    """Get a server that can write to both hosted and mirrored areas."""
    proxy = xmlrpclib.ServerProxy(config.codehosting.branchfs_endpoint)
    authserver = BlockingProxy(proxy)
    hosted_transport = get_chrooted_transport(
        config.codehosting.branches_root)
    if READ_ONLY:
        hosted_transport = get_readonly_transport(hosted_transport)
    mirrored_transport = get_chrooted_transport(
        config.supermirror.branchesdest)
    if READ_ONLY:
        mirrored_transport = get_readonly_transport(mirrored_transport)
    hosted_server = LaunchpadInternalServer(
        'lp-hosted:///', authserver, hosted_transport)
    mirrored_server = LaunchpadInternalServer(
        'lp-mirrored:///', authserver, mirrored_transport)
    return _MultiServer(hosted_server, mirrored_server)


def get_hosted_url(unique_name):
    """Return the hosted URL for the branch with 'unique_name'."""
    return 'lp-hosted:///%s' % unique_name


def get_mirrored_url(unique_name):
    """Return the mirrored URL for the branch with 'unique_name'."""
    return 'lp-mirrored:///%s' % unique_name


def set_branch_stacked_on_url(bzrdir, stacked_on_url):
    """Set the stacked_on_location for the branch at 'bzrdir'.

    We cannot use Branch.set_stacked_on, since that requires us to first open
    the branch. Opening the branch requires a working stacked_on_url:
    something we don't yet have.
    """
    branch_transport = bzrdir.get_branch_transport(None)
    branch_config = TransportConfig(branch_transport, 'branch.conf')
    stacked_on_url = branch_config.set_option(
        stacked_on_url, 'stacked_on_location')


def update_stacked_on(branch_id, bzr_branch_url, stacked_on_location):
    """Update the Bazaar branch at 'bzr_branch_url' to be stacked correctly.

    :param branch_id: The database ID of the branch. This is only used for
        logging.
    :param bzr_branch_url: The URL of the Bazaar branch. Normally this is of
        the form lp-mirrored:/// or lp-hosted:///.
    :param stacked_on_location: The location to store in the branch's
        stacked_on_location configuration variable.
    """
    try:
        bzrdir = BzrDir.open(bzr_branch_url)
    except errors.NotBranchError:
        print "No bzrdir for %r at %r" % (branch_id, bzr_branch_url)
        return

    try:
        current_stacked_on_location = get_branch_stacked_on_url(bzrdir)
    except errors.NotBranchError:
        print "No branch for %r at %r" % (branch_id, bzr_branch_url)
    except errors.NotStacked:
        print "Branch for %r at %r is not stacked at all. Giving up." % (
            branch_id, bzr_branch_url)
    except errors.UnstackableBranchFormat:
        print "Branch for %r at %r is unstackable. Giving up." % (
            branch_id, bzr_branch_url)
    else:
        if current_stacked_on_location != stacked_on_location:
            print (
                'Branch for %r at %r stacked on %r, should be on %r. Fixing.'
                % (branch_id, bzr_branch_url, current_stacked_on_location,
                   stacked_on_location))
            if not READ_ONLY:
                set_branch_stacked_on_url(bzrdir, stacked_on_location)


def parse_from_stream(stream):
    """Parse branch input from the given stream.

    Expects the stream to be populated only by blank lines or by lines of the
    form: '<foo> <bar> <baz> <qux>\n'. Such lines are yielded as 4-tuples.
    Blank lines are ignored.
    """
    for line in stream.readlines():
        if not line.strip():
            continue
        branch_id, branch_type, unique_name, stacked_on_name = line.split()
        yield branch_id, branch_type, unique_name, stacked_on_name


def main():
    execute_zcml_for_scripts()
    server = get_server()
    server.setUp()
    print "Processing..."
    try:
        for branch_info in parse_from_stream(sys.stdin):
            (branch_id, branch_type, unique_name, stacked_on_name) = branch_info
            stacked_on_location = '/' + stacked_on_name
            if branch_type == 'HOSTED':
                update_stacked_on(
                    branch_id, get_hosted_url(unique_name),
                    stacked_on_location)
            update_stacked_on(
                branch_id, get_mirrored_url(unique_name), stacked_on_location)
    finally:
        server.tearDown()
    print "Done."


if __name__ == '__main__':
    main()
