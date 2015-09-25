# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [ 'BugLinkTargetMixin' ]

from lazr.lifecycle.event import (
    ObjectCreatedEvent,
    ObjectDeletedEvent,
    )
from zope.event import notify
from zope.security.interfaces import Unauthorized

from lp.services.webapp.authorization import check_permission


class BugLinkTargetMixin:
    """Mixin class for IBugLinkTarget implementation."""

    def createBugLink(self, bug):
        """Subclass should override that method to create a BugLink instance.
        """
        raise NotImplementedError("missing createBugLink() implementation")

    def deleteBugLink(self, bug):
        """Subclass should override that method to delete a BugLink instance.
        """
        raise NotImplementedError("missing deleteBugLink() implementation")

    # IBugLinkTarget implementation
    def linkBug(self, bug):
        """See IBugLinkTarget."""
        # XXX gmb 2007-12-11 bug=175545:
        #     We shouldn't be calling check_permission here. The user's
        #     permissions should have been checked before this method
        #     was called. Also, we shouldn't be relying on the logged-in
        #     user in this method; the method should accept a user
        #     parameter.
        if not check_permission('launchpad.View', bug):
            raise Unauthorized(
                "cannot link to a private bug you don't have access to")
        if bug in self.bugs:
            # XXX: No longer returns the buglink.
            return
        buglink = self.createBugLink(bug)
        notify(ObjectCreatedEvent(buglink))
        return buglink

    def unlinkBug(self, bug):
        """See IBugLinkTarget."""
        # XXX gmb 2007-12-11 bug=175545:
        #     We shouldn't be calling check_permission here. The user's
        #     permissions should have been checked before this method
        #     was called. Also, we shouldn't be relying on the logged-in
        #     user in this method; the method should accept a user
        #     parameter.
        if not check_permission('launchpad.View', bug):
            raise Unauthorized(
                "cannot unlink a private bug you don't have access to")

        # see if a relevant bug link exists, and if so, delete it
        buglink = self.deleteBugLink(bug)
        if buglink is not None:
            notify(ObjectDeletedEvent(buglink))
        return buglink
