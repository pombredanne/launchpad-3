# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Sourceforge ExternalBugTracker utility."""

__metaclass__ = type
__all__ = ['SourceForge']

import re

from BeautifulSoup import BeautifulSoup

from canonical.launchpad.components.externalbugtracker import (
    BugNotFound, ExternalBugTracker, InvalidBugId,
    UnknownRemoteStatusError, UnparseableBugData,)
from canonical.launchpad.interfaces import (
    BugTaskStatus, BugTaskImportance, UNKNOWN_REMOTE_IMPORTANCE)


class SourceForge(ExternalBugTracker):
    """An ExternalBugTracker for SourceForge bugs."""

    # We only allow ourselves to update one SourceForge bug at a time to
    # avoid getting clobbered by SourceForge's rate limiting code.
    export_url = 'support/tracker.php?aid=%s'
    batch_size = 1

    def initializeRemoteBugDB(self, bug_ids):
        """See `ExternalBugTracker`.

        We override this method because SourceForge does not provide a
        nice way for us to export bug statuses en masse. Instead, we
        resort to screen-scraping on a per-bug basis. Therefore the
        usual choice of batch vs. single export does not apply here and
        we only perform single exports.
        """
        self.bugs = {}

        for bug_id in bug_ids:
            query_url = self.export_url % bug_id
            page_data = self._getPage(query_url)

            soup = BeautifulSoup(page_data)
            status_tag = soup.find(text=re.compile('Status:'))

            # If we can't find a status line in the output from
            # SourceForge there's little point in continuing.
            if not status_tag:
                raise UnparseableBugData(
                    'Remote bug %s does not define a status.' % bug_id)

            # We can extract the status by finding the grandparent tag.
            # Happily, BeautifulSoup will turn the contents of this tag
            # into a newline-delimited list from which we can then
            # extract the requisite data.
            status_row = status_tag.findParent().findParent()
            status = status_row.contents[-1]
            status = status.strip()

            # We need to do the same for Resolution, though if we can't
            # find it it's not critical.
            resolution_tag = soup.find(text=re.compile('Resolution:'))
            if resolution_tag:
                resolution_row = resolution_tag.findParent().findParent()
                resolution = resolution_row.contents[-1]
                resolution = resolution.strip()
            else:
                resolution = None

            self.bugs[int(bug_id)] = {
                'id': int(bug_id),
                'status': status,
                'resolution': resolution}

    def getRemoteImportance(self, bug_id):
        """See `ExternalBugTracker`.

        This method is implemented here as a stub to ensure that
        existing functionality is preserved. As a result,
        UNKNOWN_REMOTE_IMPORTANCE will always be returned.
        """
        return UNKNOWN_REMOTE_IMPORTANCE

    def getRemoteStatus(self, bug_id):
        """See `ExternalBugTracker`."""
        try:
            bug_id = int(bug_id)
        except ValueError:
            raise InvalidBugId(
                "bug_id must be convertible to an integer: %s" % str(bug_id))

        try:
            remote_bug = self.bugs[bug_id]
        except KeyError:
            raise BugNotFound(bug_id)

        try:
            return '%(status)s:%(resolution)s' % remote_bug
        except KeyError:
            raise UnparseableBugData(
                "Remote bug %i does not define a status." % bug_id)

    def convertRemoteImportance(self, remote_importance):
        """See `ExternalBugTracker`.

        This method is implemented here as a stub to ensure that
        existing functionality is preserved. As a result,
        BugTaskImportance.UNKNOWN will always be returned.
        """
        return BugTaskImportance.UNKNOWN

    def convertRemoteStatus(self, remote_status):
        """See `IExternalBugTracker`."""
        # SourceForge statuses come in two parts: status and
        # resolution. Both of these are strings. We can look
        # them up in the form status_map[status][resolution]
        status_map = {
            # We use the open status as a fallback when we can't find an
            # exact mapping for the other statuses.
            'Open' : {
                None: BugTaskStatus.NEW,
                'Accepted': BugTaskStatus.CONFIRMED,
                'Duplicate': BugTaskStatus.CONFIRMED,
                'Fixed': BugTaskStatus.FIXCOMMITTED,
                'Invalid': BugTaskStatus.INVALID,
                'Later': BugTaskStatus.CONFIRMED,
                'Out of Date': BugTaskStatus.INVALID,
                'Postponed': BugTaskStatus.CONFIRMED,
                'Rejected': BugTaskStatus.WONTFIX,
                'Remind': BugTaskStatus.CONFIRMED,

                # Some custom SourceForge trackers misspell this, so we
                # deal with the syntactically incorrect version, too.
                "Won't Fix": BugTaskStatus.WONTFIX,
                'Wont Fix': BugTaskStatus.WONTFIX,
                'Works For Me': BugTaskStatus.INVALID,
            },

            'Closed': {
                None: BugTaskStatus.FIXRELEASED,
                'Accepted': BugTaskStatus.FIXCOMMITTED,
                'Fixed': BugTaskStatus.FIXRELEASED,
                'Postponed': BugTaskStatus.WONTFIX,
            },

            'Pending': {
                None: BugTaskStatus.INCOMPLETE,
                'Postponed': BugTaskStatus.WONTFIX,
            },
        }

        # We have to deal with situations where we can't get a
        # resolution to go with the status, so we define both even if we
        # can't get both from SourceForge.
        if ':' in remote_status:
            status, resolution = remote_status.split(':')

            if resolution == 'None':
                resolution = None
        else:
            status = remote_status
            resolution = None

        if status not in status_map:
            raise UnknownRemoteStatusError()

        local_status = status_map[status].get(
            resolution, status_map['Open'].get(resolution))
        if local_status is None:
            raise UnknownRemoteStatusError()
        else:
            return local_status


