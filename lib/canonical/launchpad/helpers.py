# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.interfaces import ITeamParticipationSet, \
    ILaunchBag, IHasOwner

def is_maintainer(hasowner):
    """Returns True if the logged in user is an owner of hasowner.

    Returns False if he's not an owner.

    The user is an owner if it either matches has.owner directly or is a
    member of the hasowner.owner team.

    Raises TypeError is hasowner does not provide IHasOwner.
    """
    if not IHasOwner.providedBy(hasowner):
        raise TypeError, "hasowner doesn't provide IHasOwner"
    teampart = getUtility(ITeamParticipationSet)
    launchbag = getUtility(ILaunchBag)
    return launchbag.user in teampart.getAllMembers(hasowner.owner)

