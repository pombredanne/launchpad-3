# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [ 'BugLinkTargetMixin' ]

import lazr.lifecycle.event
from lazr.lifecycle.event import (
    ObjectCreatedEvent,
    ObjectDeletedEvent,
    )
from zope.event import notify
from zope.interface import implementer
from zope.security.interfaces import Unauthorized

from lp.bugs.interfaces.buglink import (
    IObjectLinkedEvent,
    IObjectUnlinkedEvent,
    )
from lp.services.webapp.authorization import check_permission


# XXX wgrant 2015-09-25: lazr.lifecycle.event.LifecyleEventBase is all
# of mispelled, private, and the sole implementer of user-fetching
# logic that we require.
@implementer(IObjectLinkedEvent)
class ObjectLinkedEvent(lazr.lifecycle.event.LifecyleEventBase):

    def __init__(self, object, other_object, user=None):
        super(ObjectLinkedEvent, self).__init__(object, user=user)
        self.other_object = other_object


@implementer(IObjectUnlinkedEvent)
class ObjectUnlinkedEvent(lazr.lifecycle.event.LifecyleEventBase):

    def __init__(self, object, other_object, user=None):
        super(ObjectUnlinkedEvent, self).__init__(object, user=user)
        self.other_object = other_object


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
    def linkBug(self, bug, user=None):
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
            return False
        buglink = self.createBugLink(bug)
        notify(ObjectCreatedEvent(buglink, user=user))
        notify(ObjectLinkedEvent(bug, self, user=user))
        notify(ObjectLinkedEvent(self, bug, user=user))
        return True

    def unlinkBug(self, bug, user=None):
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
            notify(ObjectDeletedEvent(buglink, user=user))
            notify(ObjectUnlinkedEvent(bug, self, user=user))
            notify(ObjectUnlinkedEvent(self, bug, user=user))
            return True
        return False
