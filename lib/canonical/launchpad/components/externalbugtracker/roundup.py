# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Round ExternalBugTracker utility."""

__metaclass__ = type
__all__ = ['Roundup']

import csv

from canonical.launchpad.components.externalbugtracker import (
    BugNotFound, ExternalBugTracker, InvalidBugId, LookupTree,
    UnknownRemoteStatusError, UnparseableBugData)
from canonical.launchpad.interfaces import (
    BugTaskStatus, BugTaskImportance, UNKNOWN_REMOTE_IMPORTANCE)
from canonical.launchpad.webapp.uri import URI


PYTHON_BUGS_HOSTNAME = 'bugs.python.org'


def _parse_python_status(remote_status):
    """Convert a Python bug status into a (status, resolution) tuple.

    :param remote_status: A bugs.python.org status string in the form
      '<status>:<resolution>', where status is an integer and
      resolution is an integer or None. An AssertionError will be
      raised if these conditions are not met.
    """
    try:
        status, resolution = remote_status.split(':')
    except ValueError:
        raise AssertionError(
            "The remote status must be a string of the form "
            "<status>:<resolution>.")

    if status.isdigit():
        status = int(status)
    else:
        raise AssertionError("The remote status must be an integer.")

    if resolution.isdigit():
        resolution = int(resolution)
    elif resolution == 'None':
        resolution = None
    else:
        raise AssertionError(
            "The resolution must be an integer or 'None'.")

    return (status, resolution)


class Roundup(ExternalBugTracker):
    """An ExternalBugTracker descendant for handling Roundup bug trackers."""

    def __init__(self, baseurl):
        """Create a new Roundup instance.

        :bugtracker: The Roundup bugtracker.

        If the bug tracker's baseurl is one which points to
        bugs.python.org, the behaviour of the Roundup bugtracker will be
        different from that which it exhibits to every other Roundup bug
        tracker, since the Python Roundup instance is very specific to
        Python and in fact behaves rather more like SourceForge than
        Roundup.
        """
        super(Roundup, self).__init__(baseurl)

        if self.isPython():
            # The bug export URLs differ only from the base Roundup ones
            # insofar as they need to include the resolution column in
            # order for us to be able to successfully export it.
            self.single_bug_export_url = (
                "issue?@action=export_csv&@columns=title,id,activity,"
                "status,resolution&@sort=id&@group=priority&@filter=id"
                "&@pagesize=50&@startwith=0&id=%i")
            self.batch_bug_export_url = (
                "issue?@action=export_csv&@columns=title,id,activity,"
                "status,resolution&@sort=activity&@group=priority"
                "&@pagesize=50&@startwith=0")
        else:
            # XXX: 2007-08-29 Graham Binns
            #      I really don't like these URLs but Roundup seems to
            #      be very sensitive to changing them. These are the
            #      only ones that I can find that work consistently on
            #      all the roundup instances I can find to test them
            #      against, but I think that refining these should be
            #      looked into at some point.
            self.single_bug_export_url = (
                "issue?@action=export_csv&@columns=title,id,activity,"
                "status&@sort=id&@group=priority&@filter=id"
                "&@pagesize=50&@startwith=0&id=%i")
            self.batch_bug_export_url = (
                "issue?@action=export_csv&@columns=title,id,activity,"
                "status&@sort=activity&@group=priority&@pagesize=50"
                "&@startwith=0")

    @property
    def status_map(self):
        """Return the remote status -> BugTaskStatus mapping for the
        current remote bug tracker.
        """
        if self.isPython():
            # Python bugtracker statuses come in two parts: status and
            # resolution. Both of these are integer values. We can look
            # them up in the form status_map[status][resolution]
            return {
                # Open issues (status=1). We also use this as a fallback
                # for statuses 2 and 3, for which the mappings are
                # different only in a few instances.
                1: {
                    None: BugTaskStatus.NEW,       # No resolution
                    1: BugTaskStatus.CONFIRMED,    # Resolution: accepted
                    2: BugTaskStatus.CONFIRMED,    # Resolution: duplicate
                    3: BugTaskStatus.FIXCOMMITTED, # Resolution: fixed
                    4: BugTaskStatus.INVALID,      # Resolution: invalid
                    5: BugTaskStatus.CONFIRMED,    # Resolution: later
                    6: BugTaskStatus.INVALID,      # Resolution: out-of-date
                    7: BugTaskStatus.CONFIRMED,    # Resolution: postponed
                    8: BugTaskStatus.WONTFIX,      # Resolution: rejected
                    9: BugTaskStatus.CONFIRMED,    # Resolution: remind
                    10: BugTaskStatus.WONTFIX,     # Resolution: wontfix
                    11: BugTaskStatus.INVALID},    # Resolution: works for me

                # Closed issues (status=2)
                2: {
                    None: BugTaskStatus.WONTFIX,   # No resolution
                    1: BugTaskStatus.FIXCOMMITTED, # Resolution: accepted
                    3: BugTaskStatus.FIXRELEASED,  # Resolution: fixed
                    7: BugTaskStatus.WONTFIX},     # Resolution: postponed

                # Pending issues (status=3)
                3: {
                    None: BugTaskStatus.INCOMPLETE,# No resolution
                    7: BugTaskStatus.WONTFIX},     # Resolution: postponed
            }

        else:
            # Our mapping of Roundup => Launchpad statuses.  Roundup
            # statuses are integer-only and highly configurable.
            # Therefore we map the statuses available by default so that
            # they can be overridden by subclassing the Roundup class.
            return {
                1: BugTaskStatus.NEW,          # Roundup status 'unread'
                2: BugTaskStatus.CONFIRMED,    # Roundup status 'deferred'
                3: BugTaskStatus.INCOMPLETE,   # Roundup status 'chatting'
                4: BugTaskStatus.INCOMPLETE,   # Roundup status 'need-eg'
                5: BugTaskStatus.INPROGRESS,   # Roundup status 'in-progress'
                6: BugTaskStatus.INPROGRESS,   # Roundup status 'testing'
                7: BugTaskStatus.FIXCOMMITTED, # Roundup status 'done-cbb'
                8: BugTaskStatus.FIXRELEASED,} # Roundup status 'resolved'

    def isPython(self):
        """Return True if the remote bug tracker is at bugs.python.org.

        Return False otherwise.
        """
        return PYTHON_BUGS_HOSTNAME in self.baseurl

    def _getBug(self, bug_id):
        """Return the bug with the ID bug_id from the internal bug list.

        :param bug_id: The ID of the remote bug to return.
        :type bug_id: int

        BugNotFound will be raised if the bug does not exist.
        InvalidBugId will be raised if bug_id is not of a valid format.
        """
        try:
            bug_id = int(bug_id)
        except ValueError:
            raise InvalidBugId(
                "bug_id must be convertible an integer: %s." % str(bug_id))

        try:
            return self.bugs[bug_id]
        except KeyError:
            raise BugNotFound(bug_id)

    def getRemoteBug(self, bug_id):
        """See `ExternalBugTracker`."""
        bug_id = int(bug_id)
        query_url = '%s/%s' % (
            self.baseurl, self.single_bug_export_url % bug_id)
        reader = csv.DictReader(self._fetchPage(query_url))
        return (bug_id, reader.next())

    def getRemoteBugBatch(self, bug_ids):
        """See `ExternalBugTracker`"""
        # XXX: 2007-08-28 Graham Binns
        #      At present, Roundup does not support exporting only a
        #      subset of bug ids as a batch (launchpad bug 135317). When
        #      this bug is fixed we need to change this method to only
        #      export the bug ids needed rather than hitting the remote
        #      tracker for a potentially massive number of bugs.
        query_url = '%s/%s' % (self.baseurl, self.batch_bug_export_url)
        remote_bugs = csv.DictReader(self._fetchPage(query_url))
        bugs = {}
        for remote_bug in remote_bugs:
            # We're only interested in the bug if it's one of the ones in
            # bug_ids.
            if remote_bug['id'] not in bug_ids:
                continue

            bugs[int(remote_bug['id'])] = remote_bug

        return bugs

    def getRemoteImportance(self, bug_id):
        """See `ExternalBugTracker`.

        This method is implemented here as a stub to ensure that
        existing functionality is preserved. As a result,
        UNKNOWN_REMOTE_IMPORTANCE will always be returned.
        """
        return UNKNOWN_REMOTE_IMPORTANCE

    def getRemoteStatus(self, bug_id):
        """See `ExternalBugTracker`."""
        remote_bug = self._getBug(bug_id)
        if self.isPython():
            # A remote bug must define a status and a resolution, even
            # if that resolution is 'None', otherwise we can't
            # accurately assign a BugTaskStatus to it.
            try:
                status = remote_bug['status']
                resolution = remote_bug['resolution']
            except KeyError:
                raise UnparseableBugData(
                    "Remote bug %s does not define both a status and a "
                    "resolution." % bug_id)

            # Remote status is stored as a string, so for sanity's sake
            # we return an easily-parseable string.
            return '%s:%s' % (status, resolution)

        else:
            try:
                return remote_bug['status']
            except KeyError:
                raise UnparseableBugData(
                    "Remote bug %s does not define a status.")

    def convertRemoteImportance(self, remote_importance):
        """See `ExternalBugTracker`.

        This method is implemented here as a stub to ensure that
        existing functionality is preserved. As a result,
        BugTaskImportance.UNKNOWN will always be returned.
        """
        return BugTaskImportance.UNKNOWN

    # Our mapping of Roundup => Launchpad statuses. Roundup statuses
    # are integer-only and highly configurable.  Therefore we map the
    # statuses available by default so that they can be overridden by
    # subclassing the Roundup class.
    _status_lookup_standard = LookupTree(
        (1, BugTaskStatus.NEW),          # Roundup status 'unread'
        (2, BugTaskStatus.CONFIRMED),    # Roundup status 'deferred'
        (3, BugTaskStatus.INCOMPLETE),   # Roundup status 'chatting'
        (4, BugTaskStatus.INCOMPLETE),   # Roundup status 'need-eg'
        (5, BugTaskStatus.INPROGRESS),   # Roundup status 'in-progress'
        (6, BugTaskStatus.INPROGRESS),   # Roundup status 'testing'
        (7, BugTaskStatus.FIXCOMMITTED), # Roundup status 'done-cbb'
        (8, BugTaskStatus.FIXRELEASED),  # Roundup status 'resolved'
        )

    # Python bugtracker statuses come in two parts: status and
    # resolution. Both of these are integer values. We can look them
    # up in the form status_map[status][resolution]
    _status_lookup_python_1 = LookupTree(
        # Open issues (status=1). We also use this as a fallback for
        # statuses 2 and 3, for which the mappings are different only
        # in a few instances.
        (None, BugTaskStatus.NEW),       # No resolution
        (1, BugTaskStatus.CONFIRMED),    # Resolution: accepted
        (2, BugTaskStatus.CONFIRMED),    # Resolution: duplicate
        (3, BugTaskStatus.FIXCOMMITTED), # Resolution: fixed
        (4, BugTaskStatus.INVALID),      # Resolution: invalid
        (5, BugTaskStatus.CONFIRMED),    # Resolution: later
        (6, BugTaskStatus.INVALID),      # Resolution: out-of-date
        (7, BugTaskStatus.CONFIRMED),    # Resolution: postponed
        (8, BugTaskStatus.WONTFIX),      # Resolution: rejected
        (9, BugTaskStatus.CONFIRMED),    # Resolution: remind
        (10, BugTaskStatus.WONTFIX),     # Resolution: wontfix
        (11, BugTaskStatus.INVALID),     # Resolution: works for me
        )
    _status_lookup_python = LookupTree(
        (1, _status_lookup_python_1),
        (2, LookupTree(
                (None, BugTaskStatus.WONTFIX),   # No resolution
                (1, BugTaskStatus.FIXCOMMITTED), # Resolution: accepted
                (3, BugTaskStatus.FIXRELEASED),  # Resolution: fixed
                (7, BugTaskStatus.WONTFIX),      # Resolution: postponed
                _status_lookup_python_1)),    # Failback
        (3, LookupTree(
                (None, BugTaskStatus.INCOMPLETE),# No resolution
                (7, BugTaskStatus.WONTFIX),      # Resolution: postponed
                _status_lookup_python_1)),    # Failback
        )

    # Combine custom mappings with the standard mappings.
    _status_lookup_titles = (
        'Remote host', 'Roundup status', 'Roundup resolution')
    _status_lookup = LookupTree(
        (PYTHON_BUGS_HOSTNAME, _status_lookup_python),
        (_status_lookup_standard,), # Default
        )

    def convertRemoteStatus(self, remote_status):
        """See `IExternalBugTracker`."""
        if self.isPython():
            remote_status_key = _parse_python_status(remote_status)
        elif remote_status.isdigit():
            remote_status_key = (int(remote_status),)
        else:
            raise UnknownRemoteStatusError(remote_status)

        host = URI(self.baseurl).host
        try:
            return self._status_lookup(host, *remote_status_key)
        except KeyError:
            raise UnknownRemoteStatusError(remote_status)
