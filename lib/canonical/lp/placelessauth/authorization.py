from zope.security.interfaces import ISecurityPolicy, IInteraction
from zope.security.checker import CheckerPublic
from zope.security.simplepolicies import ParanoidSecurityPolicy
from zope.security.management import system_user
from zope.interface import classProvides
from canonical.lp.placelessauth.launchpadsourceutility \
    import LaunchpadPrincipal

class LaunchpadSecurityPolicy(ParanoidSecurityPolicy):
    classProvides(ISecurityPolicy)

    def checkPermission(self, permission, object):
        if permission is CheckerPublic:
            return True
        users = [p.principal
                 for p in self.participations
                 if p.principal is not system_user]

        if not users:
            return False
        for u in users:
            if not isinstance(u, LaunchpadPrincipal):
                return False
        return True
