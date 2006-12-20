# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Components related to branches."""

__metaclass__ = type

from zope.interface import implements

from canonical.launchpad.interfaces import IBranchDelta

class BranchDelta:
    """See canonical.launchpad.interfaces.IBranchDelta."""
    implements(IBranchDelta)
    def __init__(self, branch, user,
                 name=None, title=None,
                 summary=None, url=None, whiteboard=None,
                 landing_target=None, 
                 bugs_linked=None, bugs_unlinked=None,
                 specs_linked=None, specs_unlinked=None,
                 lifecycle_status=None, revision_count=None):
        self.branch = branch
        self.user = user

        self.name = name
        self.title = title
        self.summary = summary
        self.url = url
        self.whiteboard = whiteboard
        self.landing_target = landing_target

        self.bugs_linked = bugs_linked
        self.bugs_unlinked = bugs_unlinked
        self.specs_linked = specs_linked
        self.specs_unlinked = specs_unlinked
        
        self.lifecycle_status = lifecycle_status
        self.revision_count = revision_count
