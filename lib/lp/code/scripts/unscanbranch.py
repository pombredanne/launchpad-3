# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'UnscanBranchScript',
    ]


import transaction
from zope.component import getUtility

from lp.code.interfaces.branchlookup import IBranchLookup
from lp.code.model.branchjob import BranchScanJob
from lp.code.model.branchrevision import BranchRevision
from lp.services.database.lpstorm import IStore
from lp.services.scripts.base import (
    LaunchpadScript,
    LaunchpadScriptFailure,
    )


class UnscanBranchScript(LaunchpadScript):
    """Unscan a branch.

    Resets the database scan data (eg. BranchRevision records and
    last_scanned_id) for a branch, and optionally requests a rescan.

    Mostly useful for working around performance bugs in the branch scanner
    that don't affect fresh branches.
    """

    description = __doc__
    usage = "%prog <branch URL>"

    def add_my_options(self):
        self.parser.add_option(
            "--rescan", dest="rescan", action="store_true", default=False,
            help="Request a rescan of the branch after unscanning it.")

    def main(self):
        if len(self.args) != 1:
            self.parser.error("Wrong number of arguments.")
        branch = getUtility(IBranchLookup).getByUrl(self.args[0])
        if branch is None:
            raise LaunchpadScriptFailure(
                "Branch does not exist: %s" % self.args[0])

        self.logger.info(
            "Unscanning %s (last scanned id: %s)", branch.displayname,
            branch.last_scanned_id)
        self.logger.info("Purging BranchRevisions.")
        IStore(BranchRevision).find(BranchRevision, branch=branch).remove()

        self.logger.info("Resetting scan data.")
        branch.last_scanned = branch.last_scanned_id = None
        branch.revision_count = 0

        if self.options.rescan:
            self.logger.info("Requesting rescan.")
            job = BranchScanJob.create(branch)
            job.celeryRunOnCommit()

        transaction.commit()
