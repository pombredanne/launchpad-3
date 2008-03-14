# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Methods dealing with interactions."""

__metaclass__ = type

from zope.app.security.interfaces import IUnauthenticatedPrincipal
from zope.component import getUtility
from zope.interface import implements
from zope.publisher.interfaces import IPublicationRequest
from zope.security.interfaces import IParticipation
from zope.security.management import (
    endInteraction, newInteraction, queryInteraction)

from canonical.launchpad.webapp.interfaces import IOpenLaunchBag


def get_current_principal():
    """Get the principal from the current interaction."""
    interaction = queryInteraction()
    principals = [
        participation.principal
        for participation in interaction.participations]
    assert len(principals) == 1, (
        "There should be only one principal in the current interaction.")
    return principals[0]


def setupInteraction(principal, login=None, participation=None):
    """Sets up a new interaction with the given principal.

    The login gets added to the launch bag.

    You can optionally pass in a participation to be used.  If no
    participation is given, a Participation is used.
    """
    # If principal is None, this method acts just like endInteraction.
    if principal is None:
        endInteraction()
        return

    if participation is None:
        participation = Participation()

    # First end any running interaction, and start a new one.
    endInteraction()
    newInteraction(participation)

    launchbag = getUtility(IOpenLaunchBag)
    if IUnauthenticatedPrincipal.providedBy(principal):
        launchbag.setLogin(None)
    else:
        launchbag.setLogin(login)

    if IPublicationRequest.providedBy(participation):
        # principal is a read-only attribute on requests.
        participation.setPrincipal(principal)
    else:
        # Try setting the attribute directly.
        participation.principal = principal


class Participation:
    implements(IParticipation)

    interaction = None
    principal = None
