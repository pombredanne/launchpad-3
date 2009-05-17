# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Bugs support for the scanner."""

__metaclass__ = type
__all__ = [
    'BugBranchLinker',
    ]

import urlparse

from bzrlib.errors import InvalidBugStatus
from zope.component import adapter, getUtility

from lp.codehosting.scanner import events
from canonical.launchpad.interfaces import (
    BugBranchStatus, IBugBranchSet, IBugSet, ILaunchpadCelebrities,
    NotFoundError)


def set_bug_branch_status(bug, branch, status):
    """Ensure there's a BugBranch for 'bug' and 'branch' set to 'status'.

    This creates a BugBranch if one doesn't exist, and changes the status if
    it does. If a BugBranch is created, the registrant is the branch owner.

    If the BugBranch status is set to BESTFIX, we don't change it. That way,
    we avoid overwriting data set in the web UI.

    :return: The updated BugBranch.
    """
    bug_branch_set = getUtility(IBugBranchSet)
    bug_branch = bug_branch_set.getBugBranch(bug, branch)
    if bug_branch is None:
        return bug.addBranch(
            branch=branch, status=status,
            registrant=getUtility(ILaunchpadCelebrities).janitor)
    if bug_branch.status != BugBranchStatus.BESTFIX:
        bug_branch.status = status
    return bug_branch


class BugBranchLinker:
    """Links branches to bugs based on revision metadata."""

    def __init__(self, db_branch):
        self.db_branch = db_branch

    def _getBugFromUrl(self, url):
        protocol, host, path, ignored, ignored = urlparse.urlsplit(url)

        # Skip URLs that don't point to Launchpad.
        if host != 'launchpad.net':
            return None

        # Remove empty path segments.
        segments = [
            segment for segment in path.split('/') if len(segment) > 0]
        # Don't allow Launchpad URLs that aren't /bugs/<integer>.
        try:
            bug_segment, bug_id = segments
        except ValueError:
            return None
        if bug_segment != 'bugs':
            return None
        try:
            return int(bug_id)
        except ValueError:
            return None

    def _getBugStatus(self, bzr_status):
        # Make sure the status is acceptable.
        valid_statuses = {'fixed': BugBranchStatus.FIXAVAILABLE}
        return valid_statuses.get(bzr_status.lower(), None)

    def extractBugInfo(self, bzr_revision):
        """Parse bug information out of the given revision property.

        :param bug_status_prop: A string containing lines of
            '<bug_url> <status>'.
        :return: dict mapping bug IDs to BugBranchStatuses.
        """
        bug_statuses = {}
        for url, status in bzr_revision.iter_bugs():
            bug = self._getBugFromUrl(url)
            status = self._getBugStatus(status)
            if bug is None or status is None:
                continue
            bug_statuses[bug] = status
        return bug_statuses

    def createBugBranchLinksForRevision(self, bzr_revision):
        """Create bug-branch links for a revision.

        This looks inside the 'bugs' property of the given Bazaar revision and
        creates a BugBranch record for each bug mentioned.
        """
        try:
            bug_info = self.extractBugInfo(bzr_revision)
        except InvalidBugStatus:
            return
        bug_set = getUtility(IBugSet)
        for bug_id, status in bug_info.iteritems():
            try:
                bug = bug_set.get(bug_id)
            except NotFoundError:
                pass
            else:
                set_bug_branch_status(bug, self.db_branch, status)


@adapter(events.NewRevision)
def got_new_revision(new_revision):
    if new_revision.isMainline():
        linker = BugBranchLinker(new_revision.db_branch)
        linker.createBugBranchLinksForRevision(new_revision.bzr_revision)

