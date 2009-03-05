# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Components related to accounts."""

__metaclass__ = type

from zope.component.interfaces import ComponentLookupError

from canonical.launchpad.webapp.interfaces import ILaunchpadPrincipal


def accountFromPrincipal(principal):
    """Adapt ILaunchpadPrincipal to IAccount."""
    if ILaunchpadPrincipal.providedBy(principal):
        return principal.account
    else:
        # This is not actually necessary when this is used as an adapter
        # from ILaunchpadPrincipal, as we know we always have an
        # ILaunchpadPrincipal.
        #
        # When Zope3 interfaces allow returning None for "cannot adapt"
        # we can return None here.
        ##return None
        raise ComponentLookupError

