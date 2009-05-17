#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0403

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

from lp.codehosting.branchfs import LaunchpadInternalServer
from lp.codehosting.vfs import BlockingProxy
from lp.codehosting.vfs.transport import (
    get_chrooted_transport, get_readonly_transport, _MultiServer)
from lp.codehosting.bzrutils import get_branch_stacked_on_url
from canonical.config import config
from lp.services.scripts.base import LaunchpadScript


def get_server(read_only):
    """Get a server that can write to both hosted and mirrored areas."""
    proxy = xmlrpclib.ServerProxy(config.codehosting.branchfs_endpoint)
    authserver = BlockingProxy(proxy)
    hosted_transport = get_chrooted_transport(
        config.codehosting.hosted_branches_root)
    if read_only:
        hosted_transport = get_readonly_transport(hosted_transport)
    mirrored_transport = get_chrooted_transport(
        config.codehosting.mirrored_branches_root)
    if read_only:
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


class UpdateStackedBranches(LaunchpadScript):
    """Update stacked branches so their stacked_on_location matches the db."""

    def __init__(self):
        super(UpdateStackedBranches, self).__init__('update-stacked-on')

    def add_my_options(self):
        self.parser.add_option(
            '-n', '--dry-run', default=False, action="store_true",
            dest="dry_run",
            help=("Don't change anything on disk, just go through the "
                  "motions."))

    def main(self):
        server = get_server(self.options.dry_run)
        server.setUp()
        if self.options.dry_run:
            self.logger.debug('Running read-only')
        self.logger.debug('Beginning processing')
        try:
            self.updateBranches(self.parseFromStream(sys.stdin))
        finally:
            server.tearDown()
        self.logger.info('Done')

    def updateStackedOn(self, branch_id, bzr_branch_url, stacked_on_location):
        """Stack the Bazaar branch at 'bzr_branch_url' on the given URL.

        :param branch_id: The database ID of the branch. This is only used for
            logging.
        :param bzr_branch_url: The URL of the Bazaar branch. Normally this is
            of the form lp-mirrored:/// or lp-hosted:///.
        :param stacked_on_location: The location to store in the branch's
            stacked_on_location configuration variable.
        """
        try:
            bzrdir = BzrDir.open(bzr_branch_url)
        except errors.NotBranchError:
            self.logger.warn(
                "No bzrdir for %r at %r" % (branch_id, bzr_branch_url))
            return

        try:
            current_stacked_on_location = get_branch_stacked_on_url(bzrdir)
        except errors.NotBranchError:
            self.logger.warn(
                "No branch for %r at %r" % (branch_id, bzr_branch_url))
        except errors.NotStacked:
            self.logger.warn(
                "Branch for %r at %r is not stacked at all. Giving up."
                % (branch_id, bzr_branch_url))
        except errors.UnstackableBranchFormat:
            self.logger.error(
                "Branch for %r at %r is unstackable. Giving up."
                % (branch_id, bzr_branch_url))
        else:
            if current_stacked_on_location != stacked_on_location:
                self.logger.info(
                    'Branch for %r at %r stacked on %r, should be on %r.'
                    % (branch_id, bzr_branch_url, current_stacked_on_location,
                       stacked_on_location))
                if not self.options.dry_run:
                    set_branch_stacked_on_url(bzrdir, stacked_on_location)

    def parseFromStream(self, stream):
        """Parse branch input from the given stream.

        Expects the stream to be populated only by blank lines or by lines
        with whitespace-separated fields. Such lines are yielded as tuples.
        Blank lines are ignored.
        """
        for line in stream.readlines():
            if not line.strip():
                continue
            yield line.split()

    def updateBranches(self, branches):
        """Update the stacked_on_location for all branches in 'branches'.

        :param branches: An iterator yielding (branch_id, branch_type,
            unique_name, stacked_on_unique_name).
        """
        for branch_info in branches:
            (branch_id, branch_type, unique_name,
             stacked_on_name) = branch_info
            stacked_on_location = '/' + stacked_on_name
            if branch_type == 'HOSTED':
                self.updateStackedOn(
                    branch_id, get_hosted_url(unique_name),
                    stacked_on_location)
            self.updateStackedOn(
                branch_id, get_mirrored_url(unique_name), stacked_on_location)


if __name__ == '__main__':
    UpdateStackedBranches().lock_and_run()
