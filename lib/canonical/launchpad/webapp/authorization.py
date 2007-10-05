# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import warnings

from zope.interface import classProvides
from zope.component import queryAdapter
from zope.component.interfaces import IView

from zope.security.interfaces import ISecurityPolicy
from zope.security.checker import CheckerPublic
from zope.security.proxy import removeSecurityProxy
from zope.security.simplepolicies import ParanoidSecurityPolicy
from zope.security.management import (
    system_user, checkPermission as zcheckPermission)
from zope.app.security.permission import (
    checkPermission as check_permission_is_registered)

from canonical.launchpad.webapp.interfaces import (
    ILaunchpadPrincipal, IAuthorization)

steveIsFixingThis = False

class LaunchpadSecurityPolicy(ParanoidSecurityPolicy):
    classProvides(ISecurityPolicy)

    def checkPermission(self, permission, object):
        """Check the permission, object, user against the launchpad
        authorization policy.

        If the object is a view, then consider the object to be the view's
        context.

        Workflow:
        - If we have zope.Public, allow.  (We shouldn't ever get this, though.)
        - If we have launchpad.AnyPerson and the principal is an
          ILaunchpadPrincipal then allow.
        - If the object has an IAuthorization named adapter, named
          after the permission, use that to check the permission.
        - Otherwise, deny.
        """
        # XXX kiko 2007-02-07:
        # webapp shouldn't be depending on launchpad interfaces..
        from canonical.launchpad.interfaces import IPerson

        # This check shouldn't be needed, strictly speaking.
        # However, it is here as a "belt and braces".

        # XXX Steve Alexander 2005-01-12: 
        # This warning should apply to the policy in zope3 also.
        if permission == 'zope.Public':
            if steveIsFixingThis:
                warnings.warn('zope.Public being used raw on object %r' % object)
            return True
        if permission is CheckerPublic:
            return True
        principals = [p.principal
                     for p in self.participations
                     if p.principal is not system_user]

        if not principals:
            principal = None
        elif len(principals) > 1:
            raise RuntimeError, "More than one principal participating."
        else:
            principal = principals[0]
        if (permission == 'launchpad.AnyPerson' and
            ILaunchpadPrincipal.providedBy(principal)):
            return True
        else:
            # If we have a view, get its context and use that to get an
            # authorization adapter.
            if IView.providedBy(object):
                objecttoauthorize = object.context
            else:
                objecttoauthorize = object

            # Remove security proxies from object to authorize.
            objecttoauthorize = removeSecurityProxy(objecttoauthorize)

            # Look for an IAuthorization adapter.  If there is no
            # IAuthorization adapter then the permission is not granted.
            #
            # The IAuthorization is a named adapter from objecttoauthorize,
            # providing IAuthorization, named after the permission.
            authorization = queryAdapter(
                objecttoauthorize, IAuthorization, permission)
            if authorization is None:
                return False
            else:
                user = IPerson(principal, None)
                if user is None:
                    result = authorization.checkUnauthenticated()
                else:
                    result = authorization.checkAuthenticated(user)
                if type(result) is not bool:
                    warnings.warn(
                        'authorization returning non-bool value: %r' %
                        authorization)
                return bool(result)

def check_permission(permission_name, context):
    """Like zope.security.management.checkPermission, but also ensures that
    permission_name is real permission.

    Raises ValueError if the permission doesn't exist.
    """
    # This will raise ValueError if the permission doesn't exist.
    check_permission_is_registered(context, permission_name)

    # Now call Zope's checkPermission.
    return zcheckPermission(permission_name, context)


