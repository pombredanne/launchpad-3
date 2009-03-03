# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Components related to persons."""

__metaclass__ = type

from zope.component.interfaces import ComponentLookupError

from canonical.launchpad.webapp.interfaces import ILaunchpadPrincipal


def personFromPrincipal(principal):
    """Adapt ILaunchpadPrincipal to IPerson."""
    if ILaunchpadPrincipal.providedBy(principal):
        if principal.person is None:
            raise ComponentLookupError
        return principal.person
    else:
        # This is not actually necessary when this is used as an adapter
        # from ILaunchpadPrincipal, as we know we always have an
        # ILaunchpadPrincipal.
        #
        # When Zope3 interfaces allow returning None for "cannot adapt"
        # we can return None here.
        ##return None
        raise ComponentLookupError

