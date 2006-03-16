# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Components related to bugs."""

__metaclass__ = type

from zope.interface import implements

from canonical.launchpad.interfaces import IBugDelta

class BugDelta:
    """See canonical.launchpad.interfaces.IBugDelta."""
    implements(IBugDelta)
    def __init__(self, bug, bugurl, user, comment_on_change=None,
                 title=None, description=None, name=None,
                 private=None, duplicateof=None, external_reference=None,
                 bugwatch=None, cve=None, attachment=None, added_bugtasks=None,
                 bugtask_deltas=None):
        self.bug = bug
        self.bugurl = bugurl
        self.user = user
        self.title = title
        self.description = description
        self.name = name
        self.private = private
        self.duplicateof = duplicateof
        self.external_reference = external_reference
        self.bugwatch = bugwatch
        self.cve = cve
        self.attachment = attachment
        self.added_bugtasks = added_bugtasks
        self.bugtask_deltas = bugtask_deltas
        self.comment_on_change = comment_on_change
