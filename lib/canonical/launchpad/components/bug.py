# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Components related to bugs."""

__metaclass__ = type

from zope.interface import implements

from canonical.launchpad.interfaces import IBugDelta

class BugDelta:
    """See canonical.launchpad.interfaces.IBugDelta."""
    implements(IBugDelta)
    def __init__(self, bug, bugurl, user,
                 title=None, description=None, name=None,
                 private=None, security_related=None, duplicateof=None,
                 external_reference=None, bugwatch=None, cve=None,
                 attachment=None, tags=None,
                 added_bugtasks=None, bugtask_deltas=None,
                 bug_before_modification=None):
        self.bug = bug
        self.bug_before_modification = bug_before_modification
        self.bugurl = bugurl
        self.user = user
        self.title = title
        self.description = description
        self.name = name
        self.private = private
        self.security_related = security_related
        self.duplicateof = duplicateof
        self.external_reference = external_reference
        self.bugwatch = bugwatch
        self.cve = cve
        self.attachment = attachment
        self.tags = tags
        self.added_bugtasks = added_bugtasks
        self.bugtask_deltas = bugtask_deltas
