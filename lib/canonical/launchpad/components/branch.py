# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Components related to branches."""

__metaclass__ = type

from zope.interface import implements

from canonical.launchpad.interfaces import IBranchDelta

# XXX: thumper 2006-12-20, this needs to be extended
# to cover bugs and specs linked and unlinked, as
# well as landing target when it is added to the UI

class BranchDelta:
    """See canonical.launchpad.interfaces.IBranchDelta."""
    implements(IBranchDelta)
    def __init__(self, branch, user,
                 name=None, title=None, summary=None, url=None,
                 whiteboard=None, lifecycle_status=None,
                 revision_count=None, last_scanned_id=None):
        self.branch = branch
        self.user = user

        self.name = name
        self.title = title
        self.summary = summary
        self.url = url
        self.whiteboard = whiteboard
        self.lifecycle_status = lifecycle_status
        self.revision_count = revision_count
        self.last_scanned_id = last_scanned_id
        
