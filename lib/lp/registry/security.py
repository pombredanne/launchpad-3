# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Security adapters for Registry."""

__metaclass__ = type
__all__ = []

from canonical.launchpad.security import AuthorizationBase
from lp.registry.interfaces.structuralsubscription import (
    IStructuralSubscription,
    )


class EditStructuralSubscription(AuthorizationBase):
    """Edit permissions for `IStructuralSubscription`."""

    usedfor = IStructuralSubscription
    permission = "launchpad.Edit"

    def checkAuthenticated(self, user):
        """Subscribers can edit their own structural subscriptions."""
        return user.inTeam(self.obj.subscriber)
