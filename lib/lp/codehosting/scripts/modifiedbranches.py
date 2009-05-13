# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Implementation of the Launchpad script to list modified branches."""

__metaclass__ = type
__all__ = ['ModifiedBranchesScript']


from datetime import datetime, timedelta
import os
from time import strptime

import pytz
from zope.component import getUtility

from lp.codehosting.vfs import branch_id_to_path
from canonical.config import config
from canonical.launchpad.scripts.base import (
    LaunchpadScript, LaunchpadScriptFailure)
from lp.code.interfaces.branch import BranchType
from lp.code.interfaces.branchcollection import IAllBranches


class ModifiedBranchesScript(LaunchpadScript):
    """List branches modified since the specified time.

    Only branches that have been modified since the specified time will be
    returned.  It is possible that the branch will have been modified only in
    the web UI and not actually received any more revisions, and will be a
    false positive.

    If the branch is REMOTE it is ignored.
    If the branch is HOSTED, both the hosted and mirrored area are returned.
    If the branch is an IMPORT or MIRROR branch, only the mirrored area is
    shown.
    """

    description = (
        "List branch paths for branches modified since the specified time.")

    def __init__(self, name, dbuser=None, test_args=None):
        LaunchpadScript.__init__(self, name, dbuser, test_args)
        # Cache this on object creation so it can be used in tests.
        self.now_timestamp = datetime.utcnow()

    def add_my_options(self):
        self.parser.add_option(
            "-s", "--since", metavar="DATE",
            help="A date in the format YYYY-MM-DD.  Branches that "
            "have been modified since this date will be returned.")
        self.parser.add_option(
            "-l", "--last-hours", metavar="HOURS", type="int",
            help="Return the branches that have been modified in "
            "the last HOURS number of hours.")

    def get_last_modified_epoch(self):
        """Return the timezone aware datetime for the last modified epoch. """
        if (self.options.last_hours is not None and
            self.options.since is not None):
            raise LaunchpadScriptFailure(
                "Only one of --since or --last-hours can be specified.")
        last_modified = None
        if self.options.last_hours is not None:
            last_modified = (
                self.now_timestamp - timedelta(hours=self.options.last_hours))
        elif self.options.since is not None:
            try:
                parsed_time = strptime(self.options.since, '%Y-%m-%d')
                last_modified = datetime(*(parsed_time[:3]))
            except ValueError, e:
                raise LaunchpadScriptFailure(str(e))
        else:
            raise LaunchpadScriptFailure(
                "One of --since or --last-hours needs to be specified.")

        # Make the datetime timezone aware.
        return last_modified.replace(tzinfo=pytz.UTC)

    def branch_locations(self, branch):
        """Return a list of branch paths for the given branch."""
        path = branch_id_to_path(branch.id)
        yield os.path.join(config.codehosting.mirrored_branches_root, path)
        if branch.branch_type == BranchType.HOSTED:
            yield os.path.join(config.codehosting.hosted_branches_root, path)

    def main(self):
        last_modified = self.get_last_modified_epoch()
        self.logger.info(
            "Looking for branches modified since %s", last_modified)
        collection = getUtility(IAllBranches)
        collection = collection.withBranchType(
            BranchType.HOSTED, BranchType.MIRRORED, BranchType.IMPORTED)
        collection = collection.scannedSince(last_modified)
        for branch in collection.getBranches():
            self.logger.info(branch.unique_name)
            for location in self.branch_locations(branch):
                print location

        self.logger.info("Done.")

