# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Bugs support for the scanner."""

__metaclass__ = type
__all__ = [
    'BugBranchLinker',
    ]

import urlparse

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    BugBranchStatus, IBugBranchSet, IBugSet, ILaunchpadCelebrities,
    NotFoundError)


class BadLineInBugsProperty(Exception):
    """Raised when the scanner encounters a bad line in a bug property."""


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

    def _parseBugLine(self, line):
        """Parse a line from a bug property.

        :param line: A line from a Bazaar bug property.
        :raise BadLineInBugsProperty: if the line is invalid. Raising this
            will cause the line to be skipped.
        :return: (bug_url, bug_id) if the line is good; None if the line
            is technically valid but should be skipped.
        """
        valid_statuses = {'fixed': BugBranchStatus.FIXAVAILABLE}
        line = line.strip()

        # Skip blank lines.
        if len(line) == 0:
            return None

        # Lines must be <url> <status>.
        try:
            url, status = line.split(None, 2)
        except ValueError:
            raise BadLineInBugsProperty('Invalid line: %r' % line)
        protocol, host, path, ignored, ignored = urlparse.urlsplit(url)

        # Skip URLs that don't point to Launchpad.
        if host != 'launchpad.net':
            return None

        # Don't allow Launchpad URLs that aren't /bugs/<integer>.
        try:
            # Remove empty path segments.
            bug_segment, bug_id = [
                segment for segment in path.split('/') if len(segment) > 0]
            if bug_segment != 'bugs':
                raise ValueError('Bad path segment')
            bug = int(path.split('/')[-1])
        except ValueError:
            raise BadLineInBugsProperty('Invalid bug reference: %s' % url)

        # Make sure the status is acceptable.
        try:
            status = valid_statuses[status.lower()]
        except KeyError:
            raise BadLineInBugsProperty('Invalid bug status: %r' % status)
        return bug, status

    def extractBugInfo(self, bug_property):
        """Parse bug information out of the given revision property.

        :param bug_status_prop: A string containing lines of
            '<bug_url> <status>'.
        :return: dict mapping bug IDs to BugBranchStatuses.
        """
        bug_statuses = {}
        for line in bug_property.splitlines():
            try:
                parsed_line = self._parseBugLine(line)
                if parsed_line is None:
                    continue
                bug, status = parsed_line
            except BadLineInBugsProperty, e:
                continue
            bug_statuses[bug] = status
        return bug_statuses

    def createBugBranchLinksForRevision(self, bzr_revision):
        """Create bug-branch links for a revision.

        This looks inside the 'bugs' property of the given Bazaar revision and
        creates a BugBranch record for each bug mentioned.
        """
        bug_property = bzr_revision.properties.get('bugs', None)
        if bug_property is None:
            return
        bug_set = getUtility(IBugSet)
        for bug_id, status in self.extractBugInfo(bug_property).iteritems():
            try:
                bug = bug_set.get(bug_id)
            except NotFoundError:
                pass
            else:
                set_bug_branch_status(bug, self.db_branch, status)
