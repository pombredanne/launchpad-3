# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.interface import classProvides

from zope.security.interfaces import ISecurityPolicy, IInteraction
from zope.security.checker import CheckerPublic
from zope.security.simplepolicies import ParanoidSecurityPolicy
from zope.security.management import system_user

from canonical.lp.placelessauth import LaunchpadPrincipal


class LaunchpadSecurityPolicy(ParanoidSecurityPolicy):
    classProvides(ISecurityPolicy)

    def checkPermission(self, permission, object):
        # This check shouldn't be needed, strictly speaking.
        # However, it is here as a "belt and braces".
        # XXX: It should emit a warning.
        if permission is CheckerPublic:
            return True

        users = [p.principal
                 for p in self.participations
                 if p.principal is not system_user]

        if not users:
            return False
        for user in users:
            if not isinstance(user, LaunchpadPrincipal):
                return False
        return True
