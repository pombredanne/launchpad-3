# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Components related to persons."""

__metaclass__ = type

from zope.component.interfaces import ComponentLookupError
from zope.component import getUtility

from canonical.launchpad.webapp.interfaces import ILaunchpadPrincipal

from canonical.launchpad.interfaces import IPersonSet


def personFromPrincipal(principal):
    """Adapt ILaunchpadPrincipal to IPerson."""
    if ILaunchpadPrincipal.providedBy(principal):
        return getUtility(IPersonSet).get(principal.id)
    else:
        # This is not actually necessary when this is used as an adapter
        # from ILaunchpadPrincipal, as we know we always have an
        # ILaunchpadPrincipal.
        #
        # When Zope3 interfaces allow returning None for "cannot adapt"
        # we can return None here.
        ##return None
        raise ComponentLookupError

