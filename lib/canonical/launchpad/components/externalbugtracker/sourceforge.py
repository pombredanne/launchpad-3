# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Sourceforge ExternalBugTracker utility."""

__metaclass__ = type
__all__ = ['SourceForge']

import re

from BeautifulSoup import BeautifulSoup

from canonical.launchpad.components.externalbugtracker import (
    BugNotFound, ExternalBugTracker, InvalidBugId, Lookup, PrivateRemoteBug,
    UnknownRemoteStatusError, UnparseableBugData)
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

            status = None
            private = False
            if status_tag:
                # We can extract the status by finding the grandparent tag.
                # Happily, BeautifulSoup will turn the contents of this tag
                # into a newline-delimited list from which we can then
                # extract the requisite data.
                status_row = status_tag.findParent().findParent()
                status = status_row.contents[-1]
                status = status.strip()
            else:
                error_message = self._extractErrorMessage(page_data)

                # If the error message suggests that the bug is private,
                # set the bug's private field to True.
                # XXX 2008-05-01 gmb:
                #     We should know more about possible errors and deal
                #     with them accordingly (bug 225354).
                if error_message and 'private' in error_message.lower():
                    private = True
                else:
                    # If we can't find a status line in the output from
                    # SourceForge there's little point in continuing.
                    raise UnparseableBugData(
                        'Remote bug %s does not define a status.' % bug_id)

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
                'private': private,
                'status': status,
                'resolution': resolution,
                }

    def _extractErrorMessage(self, page_data):
        """Extract an error message from a SourceForge page and return it."""
        soup = BeautifulSoup(page_data)
        error_frame = soup.find(attrs={'class': 'error'})

        if not error_frame:
            return None

        # We find the error message by going via the somewhat shakey
        # method of looking for the only paragraph inside the
        # error_frame div.
        error_message = error_frame.find(name='p')
        if error_message:
            # Strip out any leading or trailing whitespace and return the
            # error message.
            return error_message.string.strip()
        else:
            # We know there was an error, but we can't tell what it was.
            return 'Unspecified error.'

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

        # If the remote bug is private, raise a PrivateRemoteBug error.
        if remote_bug['private']:
            raise PrivateRemoteBug(
                "Bug %i on %s is private." % (bug_id, self.baseurl))

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

    # SourceForge statuses come in two parts: status and
    # resolution. Both of these are strings.  We use the open status
    # as a fallback when we can't find an exact mapping for the other
    # statuses.
    _status_lookup_open = Lookup(
        (None, BugTaskStatus.NEW),
        ('Accepted', BugTaskStatus.CONFIRMED),
        ('Duplicate', BugTaskStatus.CONFIRMED),
        ('Fixed', BugTaskStatus.FIXCOMMITTED),
        ('Invalid', BugTaskStatus.INVALID),
        ('Later', BugTaskStatus.CONFIRMED),
        ('Out of Date', BugTaskStatus.INVALID),
        ('Postponed', BugTaskStatus.CONFIRMED),
        ('Rejected', BugTaskStatus.WONTFIX),
        ('Remind', BugTaskStatus.CONFIRMED),
        # Some custom SourceForge trackers misspell this, so we
        # deal with the syntactically incorrect version, too.
        ("Won't Fix", BugTaskStatus.WONTFIX),
        ('Wont Fix', BugTaskStatus.WONTFIX),
        ('Works For Me', BugTaskStatus.INVALID),
        )
    _status_lookup_titles = 'SourceForge status', 'SourceForge resolution'
    _status_lookup = Lookup(
        ('Open', _status_lookup_open),
        ('Closed', Lookup(
                (None, BugTaskStatus.FIXRELEASED),
                ('Accepted', BugTaskStatus.FIXCOMMITTED),
                ('Fixed', BugTaskStatus.FIXRELEASED),
                ('Postponed', BugTaskStatus.WONTFIX),
                _status_lookup_open)),
        ('Pending', Lookup(
                (None, BugTaskStatus.INCOMPLETE),
                ('Postponed', BugTaskStatus.WONTFIX),
                _status_lookup_open)),
        )

    def convertRemoteStatus(self, remote_status):
        """See `IExternalBugTracker`."""
        # We have to deal with situations where we can't get a
        # resolution to go with the status, so we define both even if
        # we can't get both from SourceForge.
        if ':' in remote_status:
            status, resolution = remote_status.split(':')
            if resolution == 'None':
                resolution = None
        else:
            status = remote_status
            resolution = None

        try:
            return self._status_lookup(status, resolution)
        except KeyError:
            raise UnknownRemoteStatusError(remote_status)
